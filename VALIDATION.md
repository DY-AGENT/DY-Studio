# Runtime validation

Validated on 2026-10-07: Windows, NVIDIA RTX 5060 Laptop GPU (8,151MiB), 16GB system RAM. All five tools used local models and were submitted through the browser UI. No remote generation API or conversational LLM was used.

| Tool | Verified output | Time | Peak PyTorch GPU allocation | Maximum sampled total GPU usage |
| --- | --- | --- | --- | --- |
| Image | 512×512 PNG | 62.51s | 2.318GB | Monitor not yet started |
| Background removal | 512×512 RGBA PNG, alpha 0–255 | 33.94s | 0GB | 1.280GB |
| 3D | Colored GLB/OBJ, 7,987 vertices, 15,986 faces | 27.01s | 1.824GB | 3.342GB |
| Music | 10s WAV, 48kHz stereo | 68.13s | 4.521GB | 5.803GB |
| Video | 720×480 MP4, 49 frames, 8fps, 6.125s | 861.62s | 5.015GB | 7.526GB |

Times include loading and saving, but exclude installation and queue delays. PyTorch allocation excludes other applications and some CUDA overhead. Total GPU usage was sampled approximately every two seconds with nvidia-smi and includes other applications; it does not prove a bound on instantaneous peaks. Individual hardware, drivers and inputs can change results.

## Output checks

- Image: decoded with Pillow, dimensions/mode checked, visually inspected.
- Background removal: RGBA output with transparent and opaque pixels confirmed.
- 3D: GLB/OBJ read back with trimesh; matching face counts, watertight surface and positive volume confirmed. Chair shape inspected in the built-in viewer. GLB is Y-up and OBJ is Z-up.
- Music: soundfile confirmed duration, sample rate, channels, finite non-silent samples and peak amplitude 0.8912. This does not assess musical quality or non-infringement.
- Video: ffmpeg decoded the clip; dimensions, frame count, duration and beginning/middle/end frames checked. Browser playback advanced successfully with readyState=4. BF16 and 30 sampling steps were used.

## Program checks

The installed development environment passed 14 automated checks covering real subprocess queue order and cancellation, path boundaries, Host/request-token validation, invalid parameters, duplicate-launch state preservation, progress parsing, mesh axes/winding, pinned commercial model enforcement and provenance sidecars. JavaScript syntax validation passed.

The clean source distribution passed 13 checks and skipped the mesh integration check because the upstream 3D engine was not installed there. GPU generation and these automated checks are separate evidence.

## Video correction

The first FP16 run saved a decodable MP4 but produced nearly blank frames and failed visual validation. The implementation was changed to BF16 with memory release before decoding, then retested using the same prompt and seed. The table reports the corrected run.

## Limits

Only this PC and individual samples were exercised. Fresh installation on other PCs, other GPUs/OSes, vocal music, 60-second music and all prompt/input combinations remain unverified. Video loading used the Windows page file with 16GB RAM. This version requires Python, Git and an NVIDIA driver; it is not a standalone EXE installer.

Licensing evidence is in THIRD_PARTY.md and licenses/. Model permissions do not guarantee exclusive copyright or non-infringement of inputs or outputs.
