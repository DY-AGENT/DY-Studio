"""One fresh process per generation; exiting returns all GPU allocations."""
import json
import os
import random
import sys
import time
import traceback
import types
from pathlib import Path
from common import ROOT, DATA, safe_path, environment, save_json, commercial_model, write_rights

def event(message, progress=0, **extra):
    print('\nSTUDIO_EVENT ' + json.dumps(dict(message=message, progress=progress, **extra), ensure_ascii=False), flush=True)

def setup_source(kind):
    if kind in ('mesh', 'music'):
        sys.path.insert(0, str(DATA / 'engines' / kind))
    if kind == 'music':
        # Upstream's default preflight includes a generative LM. This workspace
        # deliberately installs only the DiT, VAE and required embedding encoder.
        import acestep.model_downloader as downloader
        downloader.MAIN_MODEL_COMPONENTS = ['acestep-v15-turbo', 'vae', 'Qwen3-Embedding-0.6B']
    if kind == 'mesh':
        # TripoSR's torchmcubes extension requires a Windows C++/CUDA toolchain.
        # Equivalent CPU mesh extraction via scikit-image avoids that dependency.
        import torch
        from skimage.measure import marching_cubes
        module = types.ModuleType('torchmcubes')
        def cpu_mc(volume, level):
            vertices, faces, _, _ = marching_cubes(volume.detach().float().cpu().numpy(), level=level)
            # torchmcubes reports xyz as reversed volume axes; TripoSR reverses it again.
            # Reverse scikit-image's descent winding so solid surfaces face out.
            return torch.from_numpy(vertices[:, [2, 1, 0]].copy()), torch.from_numpy(faces[:, ::-1].copy()).long()
        module.marching_cubes = cpu_mc
        sys.modules['torchmcubes'] = module

def probe(kind):
    setup_source(kind)
    model_dir = DATA / 'models' / kind
    if kind == 'image':
        from diffusers import StableDiffusionPipeline
        required = ['model_index.json', 'unet/diffusion_pytorch_model.fp16.safetensors',
                    'text_encoder/model.fp16.safetensors', 'vae/diffusion_pytorch_model.fp16.safetensors']
    elif kind == 'video':
        from diffusers import CogVideoXPipeline
        required = ['model_index.json', 'transformer/config.json', 'vae/config.json', 'text_encoder/config.json']
    elif kind == 'mesh':
        from tsr.system import TSR
        from huggingface_hub import hf_hub_download
        hf_hub_download('facebook/dino-vitb16', filename='config.json', local_files_only=True)
        if not (DATA / 'models' / 'cutout' / 'u2net.onnx').is_file():
            raise RuntimeError('Background removal weights required for 3D preprocessing are missing.')
        required = ['config.yaml', 'model.ckpt']
    elif kind == 'music':
        from acestep.handler import AceStepHandler
        from acestep.inference import GenerationParams, GenerationConfig, generate_music
        required = ['acestep-v15-turbo/config.json', 'vae/config.json', 'Qwen3-Embedding-0.6B/config.json']
    else:
        from rembg import new_session
        if not (model_dir / 'u2net.onnx').is_file():
            raise RuntimeError('The background removal model file is missing.')
        return
    weight_dir = model_dir / ('checkpoints' if kind == 'music' else 'weights')
    for name in required:
        if not (weight_dir / name).is_file():
            raise RuntimeError('Missing model file: ' + name)

def input_image(job):
    from PIL import Image, ImageOps
    image = Image.open(safe_path(DATA / 'uploads', job['upload']))
    if image.width * image.height > 40_000_000:
        raise ValueError('The image has too many pixels. Reduce its width and height before uploading.')
    image = ImageOps.exif_transpose(image)
    image.thumbnail((2048, 2048))
    return image

def generate(job):
    commercial_model(job['kind'])
    kind = job['kind']
    if kind in ('mesh', 'cutout') and not (DATA / 'models' / 'cutout' / 'u2net.onnx').is_file():
        raise RuntimeError('Background removal weights are missing. Reinstall the model.')
    setup_source(kind)
    destination = DATA / 'results' / job['id']
    destination.mkdir(parents=True, exist_ok=True)
    weights = DATA / 'models' / kind / 'weights'
    seed = job['seed'] if job['seed'] >= 0 else random.randrange(2**32)
    started = time.perf_counter()
    event('Loading model', 5)
    if kind != 'cutout':
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('No NVIDIA CUDA GPU was found. Check the GPU driver and runtime environment.')
        torch.cuda.reset_peak_memory_stats()
    if kind == 'image':
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
        pipe = StableDiffusionPipeline.from_pretrained(str(weights), torch_dtype=torch.float16,
                variant='fp16', use_safetensors=True, local_files_only=True)
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe.enable_model_cpu_offload()
        pipe.enable_vae_slicing()
        pipe.enable_vae_tiling()
        def callback(_pipe, step, timestep, kwargs):
            event(f'Generating image · {step + 1}/24', 15 + round((step + 1) / 24 * 75))
            return kwargs
        result = pipe(prompt=job['prompt'], negative_prompt=job['negative'],
                     height=job['size'], width=job['size'], num_inference_steps=24,
                     generator=torch.Generator('cpu').manual_seed(seed),
                     callback_on_step_end=callback)
        if result.nsfw_content_detected and any(result.nsfw_content_detected):
            raise RuntimeError('The model safety check blocked this image. Change the prompt and try again.')
        result.images[0].save(destination / 'image.png')
    elif kind == 'video':
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
        if not torch.cuda.is_bf16_supported():
            raise RuntimeError('Video generation requires an NVIDIA GPU with BF16 support (RTX 30-series or newer).')
        pipe = CogVideoXPipeline.from_pretrained(str(weights), torch_dtype=torch.bfloat16,
                                                local_files_only=True, use_safetensors=True)
        # Keep only the 2B denoiser resident during sampling. T5 and VAE use
        # leaf offload; release the denoiser before VAE decoding to keep peaks apart.
        pipe._exclude_from_cpu_offload = ['transformer']
        pipe.enable_sequential_cpu_offload()
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()
        def callback(_pipe, step, timestep, kwargs):
            latents = kwargs['latents']
            if not torch.isfinite(latents).all():
                raise RuntimeError('Video generation produced non-finite values. No output was saved.')
            if step == 29:
                torch.save(latents.detach().cpu(), DATA / 'jobs' / (job['id'] + '-latents.pt'))
                _pipe.transformer.to('cpu')
                torch.cuda.empty_cache()
                event('Decoding video frames', 87)
                return kwargs
            event(f'Generating video · {step + 1}/30 · Memory-saving mode can take a long time.',
                  15 + round((step + 1) / 30 * 70))
            return kwargs
        event('Encoding prompt and preparing video', 10)
        result = pipe(prompt=job['prompt'], num_frames=49, height=480, width=720,
                      num_inference_steps=30, guidance_scale=6,
                      generator=torch.Generator('cpu').manual_seed(seed), callback_on_step_end=callback)
        event('Saving video file', 92)
        import numpy as np
        sample_frames = [np.asarray(result.frames[0][i]) for i in (0, 24, 48)]
        if all(frame.std() < 2.5 for frame in sample_frames):
            raise RuntimeError('The generated video is nearly blank. Change the prompt and try again.')
        export_to_video(result.frames[0], str(destination / 'video.mp4'), fps=8)
    elif kind == 'music':
        from acestep.handler import AceStepHandler
        from acestep.inference import GenerationParams, GenerationConfig, generate_music
        os.environ['ACESTEP_CHECKPOINTS_DIR'] = str(DATA / 'models' / 'music' / 'checkpoints')
        os.environ['ACESTEP_PROJECT_ROOT'] = str(DATA / 'models' / 'music')
        handler = AceStepHandler()
        message, ok = handler.initialize_service(project_root=str(DATA / 'models' / 'music'),
            config_path='acestep-v15-turbo', device='cuda', use_flash_attention=False,
            compile_model=False, offload_to_cpu=True, offload_dit_to_cpu=True, quantization=None)
        if not ok:
            raise RuntimeError(message)
        event('Generating music · language generation disabled', 30)
        params = GenerationParams(caption=job['prompt'], lyrics='[Instrumental]' if job['instrumental'] else job['lyrics'],
             instrumental=job['instrumental'], duration=job['duration'], inference_steps=8, seed=seed,
             thinking=False, use_cot_metas=False, use_cot_caption=False, use_cot_language=False,
             use_cot_lyrics=False)
        config = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[seed], audio_format='wav')
        result = generate_music(handler, None, params, config, save_dir=str(destination))
        if not result.success:
            raise RuntimeError(result.error or result.status_message)
        if not list(destination.glob('*.wav')):
            raise RuntimeError('The music engine did not return a WAV file.')
    elif kind == 'mesh':
        import numpy as np
        from PIL import Image
        from tsr.system import TSR
        from tsr.utils import resize_foreground
        from rembg import remove, new_session
        image = input_image(job).convert('RGBA')
        if image.getextrema()[3] == (255, 255):
            image = remove(image, session=new_session('u2net', providers=['CPUExecutionProvider']))
        image = resize_foreground(image, 0.85)
        rgba = np.asarray(image).astype(np.float32) / 255
        rgb = rgba[..., :3] * rgba[..., 3:4] + (1 - rgba[..., 3:4]) * 0.5
        image = Image.fromarray((rgb * 255).astype(np.uint8))
        model = TSR.from_pretrained(str(weights), config_name='config.yaml', weight_name='model.ckpt')
        model.renderer.set_chunk_size(4096)
        model.to('cuda').eval()
        event('Estimating object shape', 30)
        with torch.inference_mode():
            codes = model([image], device='cuda')
            event('Extracting mesh · saving colors and surfaces.', 65)
            mesh = model.extract_mesh(codes, has_vertex_color=True, resolution=128)[0]
        if not len(mesh.vertices) or not len(mesh.faces):
            raise RuntimeError('No 3D surface was found. Use an image with a larger, clearly visible object.')
        # TripoSR/OBJ use Z-up; glTF uses Y-up.
        import trimesh
        gltf_mesh = mesh.copy()
        gltf_mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
        gltf_mesh.export(destination / 'model.glb')
        mesh.export(destination / 'model.obj')
        save_json(destination / 'mesh-info.json', dict(vertices=len(mesh.vertices), faces=len(mesh.faces)))
    else:
        from rembg import remove, new_session
        event('Separating the subject from the background', 35)
        session = new_session('u2net', providers=['CPUExecutionProvider'])
        remove(input_image(job), session=session).save(destination / 'cutout.png')
    metrics = dict(seconds=round(time.perf_counter() - started, 2), seed=seed,
                   peak_vram_gb=round(torch.cuda.max_memory_allocated() / 1024**3, 3)
                       if kind != 'cutout' else 0,
                   note='PyTorch allocations only; excludes other applications and CUDA runtime memory.')
    save_json(destination / 'generation.json', dict(job=job, metrics=metrics))
    write_rights(destination, job)
    files = [dict(name=p.name, url='/results/' + job['id'] + '/' + p.name)
             for p in destination.iterdir() if p.is_file() and (p.suffix in ('.png', '.wav', '.mp4', '.glb', '.obj')
                                                              or p.name in ('rights.json', 'commercial-use.txt'))]
    event('Files saved', 98, files=files, metrics=metrics)

if __name__ == '__main__':
    os.environ.update(environment())
    # Generation is offline; missing files cause an error instead of downloading other models.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    job = json.loads((DATA / 'jobs' / (sys.argv[1] + '.json')).read_text(encoding='utf-8'))
    try:
        if '--probe' in sys.argv:
            probe(job['kind'])
        else:
            generate(job)
    except Exception as exc:
        msg = str(exc)
        if 'out of memory' in msg.lower():
            msg = 'Not enough GPU memory. Close other GPU applications and try again. ' + msg[:300]
        event('Job failed: ' + msg)
        traceback.print_exc()
        sys.exit(1)
