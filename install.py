"""Explicit, resumable model installation. Never changes global packages."""
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from common import ROOT, DATA, MODELS, environment, runtime, save_json, commercial_model

PINS = {'mesh': ('https://github.com/VAST-AI-Research/TripoSR.git', '107cefdc244c39106fa830359024f6a2f1c78871'),
        'music': ('https://github.com/ace-step/ACE-Step-1.5.git', 'ca1e85fe9430179831e6bc6be790c332190a3866')}

def event(message, progress=0):
    print('STUDIO_EVENT ' + json.dumps(dict(message=message, progress=progress), ensure_ascii=False), flush=True)

def run(args):
    subprocess.run([str(x) for x in args], cwd=ROOT, env=environment(), check=True)

def ensure_runtime(kind):
    exe = runtime(kind)
    if exe.exists():
        return exe
    base_python = sys.executable
    if kind == 'music':
        # ACE-Step supports Python 3.11–3.12. Use the bundled runtime if present.
        bundled = Path(os.environ.get('USERPROFILE', '')) / '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        candidates = [bundled]
        for version in ('3.12', '3.11'):
            try:
                candidates.append(Path(subprocess.check_output(['py', '-' + version, '-c',
                    'import sys; print(sys.executable)'], text=True, stderr=subprocess.DEVNULL).strip()))
            except (OSError, subprocess.CalledProcessError):
                pass
        base_python = next((str(x) for x in candidates if x.is_file()), None)
        if base_python is None:
            raise RuntimeError('The music engine requires Python 3.11 or 3.12. Install it and try again.')
    event('Creating an isolated runtime · existing Python packages are preserved.', 3)
    args = [base_python, '-m', 'venv']
    if kind != 'music':
        args.append('--system-site-packages')
    run(args + [exe.parent.parent])
    return exe

def install(job):
    commercial_model(job['kind'])
    kind = job['kind']
    exe = ensure_runtime(kind)
    pip = [exe, '-m', 'pip', 'install', '--disable-pip-version-check']
    event('Installing runtime libraries · see the download log for details.', 8)
    if kind != 'cutout':
        result = subprocess.run([str(exe), '-c', 'import torch; assert torch.cuda.is_available()'],
                                env=environment(), capture_output=True)
        if result.returncode:
            run(pip + ['torch==2.10.0', 'torchvision==0.25.0', 'torchaudio==2.10.0',
                       '--index-url', 'https://download.pytorch.org/whl/cu128'])
    shared = ['diffusers==0.38.0', 'transformers==4.57.6', 'accelerate>=1.12,<2',
              'safetensors>=0.4', 'huggingface-hub>=0.34,<1', 'Pillow>=10.4', 'sentencepiece',
              'protobuf', 'imageio', 'imageio-ffmpeg']
    if kind in ('image', 'video'):
        run(pip + shared)
    elif kind == 'mesh':
        run(pip + shared + ['omegaconf==2.3.0', 'einops>=0.7', 'trimesh>=4,<5',
                           'scikit-image>=0.24', 'rembg[cpu]==2.0.72'])
    elif kind == 'cutout':
        run(pip + ['rembg[cpu]==2.0.72', 'huggingface-hub>=0.34,<1'])
    else:
        # No chat, LM runtime, vLLM, training UI, or model-reasoning dependencies.
        run(pip + shared + ['torchaudio==2.10.0', '--extra-index-url', 'https://download.pytorch.org/whl/cu128',
                           'scipy', 'soundfile>=0.13', 'loguru', 'einops>=0.8', 'numba>=0.63',
                           'vector-quantize-pytorch>=1.27', 'toml', 'peft>=0.18', 'pytorch-wavelets',
                           'pywavelets', 'matplotlib', 'diskcache', 'tqdm', 'einops'])
    if kind in PINS:
        repo, revision = PINS[kind]
        source = DATA / 'engines' / kind
        if not (source / '.git').exists():
            run(['git', 'clone', repo, source])
        run(['git', '-C', source, 'checkout', '--detach', revision])
    event('Downloading model files · the first install takes time; downloads can resume after cancellation.', 25)
    # Run downloads with the same interpreter that will run inference.
    run([exe, str(ROOT / 'install.py'), job['id'], '--weights'])
    event('Checking libraries and model files', 95)
    run([exe, str(ROOT / 'worker.py'), job['id'], '--probe'])
    save_json(DATA / 'models' / kind / 'ready.json', dict(model=MODELS[kind]['model'], installed=time.time()))
    event('Installation complete · ready to generate.', 100)

def weights(kind):
    from huggingface_hub import snapshot_download, hf_hub_download, HfApi
    model_dir = DATA / 'models' / kind
    model_dir.mkdir(parents=True, exist_ok=True)
    if kind == 'cutout':
        from rembg import new_session
        new_session('u2net', providers=['CPUExecutionProvider'])
        save_json(model_dir / 'download.json', dict(repo='u2net', revision=MODELS[kind]['revision'],
            source='https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx',
            verified_md5='60024c5c889badc19c04ad937298a77b', llm_downloaded=False))
        return
    repo = MODELS[kind]['repo']
    # Save the exact downloaded revision for reproducibility and source attribution.
    revision = MODELS[kind]['revision']
    patterns = None
    if kind == 'image':
        patterns = ['model_index.json', '*/*.json', '*/*.txt', '*/*.model', '*/*.fp16.safetensors', 'README.md']
    elif kind == 'video':
        patterns = ['model_index.json', '*/*.json', '*/*.txt', '*/*.model', '*/*.safetensors', 'LICENSE', 'README.md']
    elif kind == 'mesh':
        patterns = ['config.yaml', 'model.ckpt', 'README.md']
    elif kind == 'music':
        patterns = ['acestep-v15-turbo/*', 'vae/*', 'Qwen3-Embedding-0.6B/*', 'README.md', 'LICENSE']
    target = model_dir / ('checkpoints' if kind == 'music' else 'weights')
    snapshot_download(repo, revision=revision, local_dir=target, allow_patterns=patterns)
    if kind == 'mesh':
        from rembg import new_session
        new_session('u2net', providers=['CPUExecutionProvider'])
        # The checkpoint contains DINO weights, but upstream still reads its config.
        hf_hub_download('facebook/dino-vitb16', filename='config.json')
    save_json(model_dir / 'download.json', dict(repo=repo, revision=revision, llm_downloaded=False))

if __name__ == '__main__':
    os.environ.update(environment())
    job = json.loads((DATA / 'jobs' / (sys.argv[1] + '.json')).read_text(encoding='utf-8'))
    try:
        if '--weights' in sys.argv:
            weights(job['kind'])
        else:
            install(job)
    except Exception as exc:
        event('Installation failed: ' + str(exc))
        traceback.print_exc()
        sys.exit(1)
