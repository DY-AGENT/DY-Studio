# DY Studio

Windows-first local creative app. Keep application UI, errors, logs and documentation in English and retain DY STUDIO branding.
Serve only on loopback; preserve Host validation, request tokens and path containment.
Never commit data/: models, runtimes, uploads, generated media and job logs are local.
No conversational or lyric-writing LLM. Required model text encoders are allowed.
Run one install/generation job at a time and release GPU memory by process exit.
Keep reviewed model repositories and exact revisions pinned in catalog.json/common.py.
Before adding a model, verify code, weights and output terms separately from primary sources.

Validation: python -m unittest discover -s tests -v
Mesh tests need the installed TripoSR engine, torch, trimesh, numpy and scikit-image. GPU generation is a separate runtime check;
unit tests do not prove model installation, output quality or an 8GB VRAM bound.
Do not download large weights or run GPU jobs automatically for routine code changes.
