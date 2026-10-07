# DY Studio

<img src="web/assets/logo.png" alt="DY AGENT" width="160">

A local AI creative workspace for Windows: generate images, music, short videos and 3D assets, or remove image backgrounds. DY Studio has an English interface, runs one job at a time, and uses no conversational or lyric-writing LLM.

## Creative tools

| Tool | Model | Output | Memory settings |
| --- | --- | --- | --- |
| Image generation | Stable Diffusion 1.5 | PNG | FP16, CPU offload, 384–640px |
| Music generation | ACE-Step 1.5 2B Turbo | WAV | CPU offload, 10–60 seconds, instrumental or supplied lyrics |
| Video generation | CogVideoX-2B | MP4 | BF16, text encoder/VAE offload, 720×480, 49 frames at 8fps |
| Image to 3D | TripoSR | Colored GLB and OBJ | Chunk size 4096, grid 128, CPU marching cubes |
| Background removal | U²-Net / rembg | Transparent PNG | CPU ONNX |

Required text encoders interpret prompts without running as chatbots or writing agents. Video output is silent. Single-image 3D reconstruction estimates hidden surfaces; it is not a precise scan or CAD tool.

## Getting started

1. Install Python 3.11 or later, Git, and a current NVIDIA driver. Music requires Python 3.11 or 3.12, discoverable through the Windows Python launcher.
2. Download this repository as a ZIP and extract it, or clone it.
3. Double-click `START.bat`, or run `python server.py` from the repository root.
4. Open `http://127.0.0.1:8768/`. In **Model management**, install the tools you want.
5. Submit a prompt or upload an image. Open **Results** to preview and download completed files.

The UI/server starts with Python's standard library. Model installation creates local environments and downloads dependencies and weights; existing global Python packages are not modified. No API key or external generation account is required. An EXE installer and MCP server are not included in this version.

## Hardware and the 8GB target

GPU generation requires an NVIDIA CUDA GPU. Video uses BF16 and requires an RTX 30-series or newer GPU. Background removal runs on the CPU.

All five tools were exercised on Windows with an RTX 5060 Laptop GPU (8,151MiB) and 16GB system RAM. This is a tested single-sample configuration, not a guarantee for every GPU or input. See [VALIDATION.md](VALIDATION.md) for timings, memory measurements and limits.

Only one install/generation job runs at a time. Each generation runs in a separate process and releases its CUDA allocation when that process exits. Other applications' GPU memory remains allocated. Video favors memory savings over speed: the validated clip took about 14 minutes and used the Windows page file with 16GB RAM.

The 8GB target refers to **GPU VRAM**, not download size, disk storage or system RAM. Allow roughly 10–15GB extra for a fresh CUDA PyTorch environment, plus model files and caches. Installing every model uses substantially more than 8GB of disk space.

## Commercial use and open-source license

DY Studio's own application code is released under the [MIT License](LICENSE), permitting modification, distribution and commercial use with the required notice.

Downloaded models, dependencies and third-party documents retain their own licenses. See [THIRD_PARTY.md](THIRD_PARTY.md) and the original notices in `licenses/`. The app's MIT license does not automatically license model weights or generated assets.

The selected models permit commercial use subject to their terms. Stable Diffusion 1.5 uses CreativeML OpenRAIL-M, including use restrictions; ACE-Step uses MIT and its model card expressly permits commercial use of generated music. Each output directory includes `rights.json` and `commercial-use.txt` for provenance and applicable terms. These files do not grant exclusive copyright or guarantee non-infringement. Rights to input images, lyrics and other reference material must be obtained separately.

Model repositories and reviewed revisions are pinned. Unreviewed replacements are rejected before installation or generation. Model weights and personal job records are not distributed in this repository.

## Generated content disclaimer

DY Studio is provided "as is", without warranties. You are solely responsible for the content you generate and how you use, publish or distribute it, including compliance with applicable laws, model licenses and third-party rights. To the fullest extent permitted by applicable law, DY Studio's developers and contributors accept no liability for generated content or any claims, losses or damages arising from its creation or use.

## Local storage and privacy

Runtime data stays under `data/`, excluded by `.gitignore`:

- `runtime/` and `music-runtime/`: isolated execution environments.
- `models/` and `engines/`: weights and pinned upstream engine sources.
- `uploads/`: input images.
- `jobs/`: job records and logs.
- `results/`: generated assets, settings and provenance notices.

After installation, generation uses Hugging Face offline mode. The UI has no CDN, remote fonts or analytics. The server binds only to `127.0.0.1` and validates the Host header, request tokens and file paths.

GLB uses glTF's Y-up coordinates; OBJ preserves TripoSR's Z-up coordinates. The mesh preview shows all faces and supports rotation by dragging.

## Troubleshooting

- **Out of GPU memory:** close other GPU applications and try a smaller image size.
- **Interrupted installation:** inspect the queue log and reinstall; downloaded files can be reused.
- **Music cannot start:** install Python 3.11/3.12 through the Windows launcher, then retry.
- **Port occupied:** close the previous instance or run `python server.py --port 8770`.
- **RTX 50-series:** the installer selects CUDA 12.8 PyTorch when no working CUDA PyTorch is available.
- **Slow video:** check system RAM, page-file availability and disk space.

## Development

Run `python -m unittest discover -s tests -v` from the repository root. Server, queue, input-boundary and provenance tests need no model downloads. The mesh integration test runs only after the 3D engine and its dependencies are installed; otherwise it is skipped. Unit tests do not prove GPU performance or output quality.

See [AGENTS.md](AGENTS.md) for repository guidance for Codex and other coding agents.
