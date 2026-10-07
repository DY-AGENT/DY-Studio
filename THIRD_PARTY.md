# Third-party models and code

Official licenses and model cards were checked on 2026-10-07. Original copies are included in licenses/. DY Studio's MIT license applies to its own application code; downloaded models, libraries and upstream documents retain their original terms.

| Engine | Code license | Weight license | Primary sources |
| --- | --- | --- | --- |
| Stable Diffusion 1.5 | Diffusers Apache-2.0 | CreativeML OpenRAIL-M, including use restrictions | [Model card](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5), [OpenRAIL](https://github.com/CompVis/stable-diffusion/blob/main/LICENSE) |
| ACE-Step 1.5 | MIT | MIT | [Code license](https://github.com/ace-step/ACE-Step-1.5/blob/ca1e85fe9430179831e6bc6be790c332190a3866/LICENSE), [Model card](https://huggingface.co/ACE-Step/Ace-Step1.5/blob/main/README.md) |
| CogVideoX-2B | Diffusers Apache-2.0 | Apache-2.0 | [Weight license](https://huggingface.co/zai-org/CogVideoX-2b/blob/main/LICENSE), [Diffusers](https://github.com/huggingface/diffusers/blob/main/LICENSE) |
| TripoSR | MIT | MIT | [Code license](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/LICENSE), [Model card](https://huggingface.co/stabilityai/TripoSR/blob/main/README.md) |
| rembg / U²-Net | rembg MIT | U²-Net Apache-2.0 for publicly supplied weights | [rembg](https://github.com/danielgatis/rembg/blob/main/LICENSE.txt), [U²-Net](https://github.com/xuebinqin/U-2-Net/blob/master/LICENSE), [Weight distribution](https://github.com/xuebinqin/U-2-Net) |

MIT/Apache redistribution requires preserving copyright and license notices. These code/weight redistribution obligations are not automatically assigned to generated files. OpenRAIL-M is not an unrestricted MIT license. MusicGen noncommercial weights and conversational LLMs are not included.

ACE-Step's model card expressly permits commercial use of generated music. OpenRAIL-M section 6 says the provider claims no rights in outputs, subject to compliance with its terms. Input material and third-party rights remain separate. Provenance sidecars neither relicense outputs nor grant exclusive rights.

Required internal encoders: [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) and [DINO](https://huggingface.co/facebook/dino-vitb16) are Apache-2.0 models. Qwen is used for music description embeddings, without text generation.

## Pinned versions and memory evidence

TripoSR code: `107cefdc244c39106fa830359024f6a2f1c78871`.
ACE-Step code: `ca1e85fe9430179831e6bc6be790c332190a3866`.
Reviewed weight revisions are pinned in catalog.json and recorded in data/models/<tool>/download.json at installation.

Official memory guidance is distinct from local measurements:

- [CogVideoX-2B](https://huggingface.co/zai-org/CogVideoX-2b): optimized Diffusers configurations reduce memory use. This app uses BF16 because its initial FP16 test produced blank frames.
- [TripoSR](https://github.com/VAST-AI-Research/TripoSR): approximately 6GB for default single-image inference.
- [ACE-Step](https://github.com/ace-step/ACE-Step-1.5): low-memory DiT-only and CPU-offload configurations. This app does not download XL or language-generation models.
- [Diffusers offload](https://huggingface.co/docs/diffusers/en/optimization/memory): memory savings trade off with speed.

To avoid a Windows compiler requirement, worker.py supplies a scikit-image CPU adapter for TripoSR's torchmcubes interface, preserving upstream engine sources. See VALIDATION.md for runtime checks.
