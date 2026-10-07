---
datasets:
- allenai/objaverse
tags:
- 3d
extra_gated_fields:
  Name: text
  Email: text
  Country: text
  Organization or Affiliation: text
  I ALLOW Stability AI to email me about new model releases: checkbox
license: mit
pipeline_tag: image-to-3d
---

> Try our new model: **SF3D** with several improvements such as faster generation and more game-ready assets.
> 
> The model is available [here](https://huggingface.co/stabilityai/stable-fast-3d) and we also have a [demo](https://huggingface.co/spaces/stabilityai/stable-fast-3d).
 
# TripoSR
![](figures/input800.mp4)
TripoSR is a fast and feed-forward 3D generative model developed in collaboration between Stability AI and Tripo AI.


## Model Details

### Model Description

We closely follow [LRM](https://arxiv.org/abs/2311.04400) network architecture for the model design, where TripoSR incorporates a series of technical advancements over the LRM model in terms of both data curation as well as model and training improvements. For more technical details and evaluations, please refer to [our tech report](https://arxiv.org/abs/2403.02151).

* **Developed by**: [Stability AI](https://stability.ai/), [Tripo AI](https://tripo3d.ai/)
* **Model type**: Feed-forward 3D reconstruction from a single image
* **License**: MIT
* **Hardware**: We train `TripoSR` for 5 days on 22 GPU nodes each with 8 A100 40GB GPUs

### Model Sources

* **Repository**: https://github.com/VAST-AI-Research/TripoSR
* **Tech report**: https://arxiv.org/abs/2403.02151
* **Demo**: https://huggingface.co/spaces/stabilityai/TripoSR

### Training Dataset

We use renders from the [Objaverse](https://objaverse.allenai.org/objaverse-1.0) dataset, utilizing our enhanced rendering method that more closely replicate the distribution of images found in the real world, significantly improving our model’s ability to generalize. We selected a carefully curated subset of the Objaverse dataset for the training data, which is available under the CC-BY license. 


## Usage

* For usage instructions, please refer to our [TripoSR GitHub repository](https://github.com/VAST-AI-Research/TripoSR)

* You can also try it in [our gradio demo](https://huggingface.co/spaces/stabilityai/TripoSR)


### Misuse, Malicious Use, and Out-of-Scope Use

The model should not be used to intentionally create or disseminate 3D models that people would foreseeably find disturbing, distressing, or offensive; or content that propagates historical or current stereotypes.
