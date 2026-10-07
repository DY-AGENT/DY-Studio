---
library_name: transformers
license: mit
pipeline_tag: text-to-audio
tags:
- audio
- music
- text2music
---

<h1 align="center">ACE-Step 1.5</h1>
<h1 align="center">Pushing the Boundaries of Open-Source Music Generation</h1>
<p align="center">
    <a href="https://ace-step.github.io/ace-step-v1.5.github.io/">Project</a> |
    <a href="https://huggingface.co/collections/ACE-Step/ace-step-15">Hugging Face</a> |
    <a href="https://modelscope.cn/models/ACE-Step/Ace-Step1.5">ModelScope</a> |
    <a href="https://huggingface.co/spaces/ACE-Step/Ace-Step-v1.5">Space Demo</a> |
    <a href="https://discord.gg/PeWDxrkdj7">Discord</a>
    <a href="https://arxiv.org/abs/2602.00744">Tech Report</a>
</p>


![image](https://cdn-uploads.huggingface.co/production/uploads/62dfaf90c42558bcbd0a4f6f/b84r7t0viIw7rKSr_ja9_.png)

## Model Details

🚀 **ACE-Step v1.5** is a highly efficient open-source music foundation model designed to bring commercial-grade music generation to consumer hardware. 

### Key Features

*   **💰 Commercial-Ready:** Unlike many models trained on ambiguous datasets, ACE-Step v1.5 is designed for creators. You can strictly use the generated music for **commercial purposes**.
*   **📚 Safe & Robust Training Data:** The model is trained on a massive, legally compliant dataset consisting of:
    *   **Licensed Data:** Professionally licensed music tracks.
    *   **Royalty-Free / No-Copyright Data:** A vast collection of public domain and royalty-free music.
    *   **Synthetic Data:** High-quality audio generated via advanced MIDI-to-Audio conversion.
*   **⚡ Extreme Speed:** Generates a full song in under 2 seconds on an A100 and under 10 seconds on an RTX 3090.
*   **🖥️ Consumer Hardware Friendly:** Runs locally with less than 4GB of VRAM.

### Technical Capabilities

🌉 At its core lies a novel hybrid architecture where the Language Model (LM) functions as an omni-capable planner: it transforms simple user queries into comprehensive song blueprints—scaling from short loops to 10-minute compositions—while synthesizing metadata, lyrics, and captions via Chain-of-Thought to guide the Diffusion Transformer (DiT). ⚡ Uniquely, this alignment is achieved through intrinsic reinforcement learning relying solely on the model's internal mechanisms, thereby eliminating the biases inherent in external reward models or human preferences. 🎚️

🔮 Beyond standard synthesis, ACE-Step v1.5 unifies precise stylistic control with versatile editing capabilities—such as cover generation, repainting, and vocal-to-BGM conversion—while maintaining strict adherence to prompts across 50+ languages. This paves the way for powerful tools that seamlessly integrate into the creative workflows of music artists, producers, and content creators. 🎸

- **Developed by:** [ACE-STEP]
- **Model type:** [Text2Music]
- **Language(s):** [50+ languages]
- **License:** [MIT]

## Evaluation

![image](https://cdn-uploads.huggingface.co/production/uploads/62dfaf90c42558bcbd0a4f6f/n9aKi_NhSmlMOgmGzahZi.png)

## 🏗️ Architecture


![image](https://cdn-uploads.huggingface.co/production/uploads/62dfaf90c42558bcbd0a4f6f/V_d1rTdqkQyoSM8td7OWl.png)


## 🦁 Model Zoo


![image](https://cdn-uploads.huggingface.co/production/uploads/62dfaf90c42558bcbd0a4f6f/B49V0OTKse_FRefTmTPsQ.png)

### DiT Models

| DiT Model | Pre-Training | SFT | RL | CFG | Step | Refer audio | Text2Music | Cover | Repaint | Extract | Lego | Complete | Quality | Diversity | Fine-Tunability | Hugging Face |
|-----------|:------------:|:---:|:--:|:---:|:----:|:-----------:|:----------:|:-----:|:-------:|:-------:|:----:|:--------:|:-------:|:---------:|:---------------:|--------------|
| `acestep-v15-base` | ✅ | ❌ | ❌ | ✅ | 50 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Medium | High | Easy | [Link](https://huggingface.co/ACE-Step/acestep-v15-base) |
| `acestep-v15-sft` | ✅ | ✅ | ❌ | ✅ | 50 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | High | Medium | Easy | [Link](https://huggingface.co/ACE-Step/acestep-v15-sft) |
| `acestep-v15-turbo` | ✅ | ✅ | ❌ | ❌ | 8 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | Very High | Medium | Medium | [Link](https://huggingface.co/ACE-Step/Ace-Step1.5) |
| `acestep-v15-turbo-rl` | ✅ | ✅ | ✅ | ❌ | 8 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | Very High | Medium | Medium | To be released |

### LM Models

| LM Model | Pretrain from | Pre-Training | SFT | RL | CoT metas | Query rewrite | Audio Understanding | Composition Capability | Copy Melody | Hugging Face |
|----------|---------------|:------------:|:---:|:--:|:---------:|:-------------:|:-------------------:|:----------------------:|:-----------:|--------------|
| `acestep-5Hz-lm-0.6B` | Qwen3-0.6B | ✅ | ✅ | ✅ | ✅ | ✅ | Medium | Medium | Weak | ✅ |
| `acestep-5Hz-lm-1.7B` | Qwen3-1.7B | ✅ | ✅ | ✅ | ✅ | ✅ | Medium | Medium | Medium | ✅ |
| `acestep-5Hz-lm-4B` | Qwen3-4B | ✅ | ✅ | ✅ | ✅ | ✅ | Strong | Strong | Strong | ✅ |


## 🙏 Acknowledgements

This project is co-led by ACE Studio and StepFun.


## 📖 Citation

If you find this project useful for your research, please consider citing:

```BibTeX
@misc{gong2026acestep,
	title={ACE-Step 1.5: Pushing the Boundaries of Open-Source Music Generation},
	author={Junmin Gong, Yulin Song, Wenxiao Zhao, Sen Wang, Shengyuan Xu, Jing Guo}, 
	howpublished={\url{https://github.com/ace-step/ACE-Step-1.5}},
	year={2026},
	note={GitHub repository}
}
