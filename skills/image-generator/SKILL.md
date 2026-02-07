---
name: image-generator
description: Use when generating AI images, article covers, or illustrations. Triggers include "生成配图", "创建封面图", "AI配图", or when needing images for articles/tutorials.
---

# AI Image Generator

通过 OpenRouter API 生成高质量 AI 配图，支持多种风格和批量生成。

## 功能

- **AI 配图生成** - 通过 OpenRouter API 调用图像生成模型
- **封面图生成** - 支持多种风格（黑板报、科技、简约、学术、创意）
- **批量生成** - 一次生成多张配图
- **Prompt 增强** - 自动优化生成效果

## 前置条件

1. **环境变量**:
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-xxx
   # 或
   OPENAI_API_KEY=sk-xxx
   ```

2. **依赖安装**:
   ```bash
   cd ~/skills/skills/image-generator
   pip install -r requirements.txt
   ```

## 快速使用

```python
import os
os.environ['OPENROUTER_API_KEY'] = 'your_api_key'

from src.generator import ImageGenerator

generator = ImageGenerator(output_dir="./output/images")

# 生成配图
result = generator.generate(
    prompt="Neural network architecture diagram, digital art style"
)
print(f"生成成功: {result.path}")

# 生成封面图（黑板报风格）
cover = generator.generate_cover(
    title="Transformer 模型详解",
    topic="AI/深度学习",
    style="chalkboard"
)
```

## API 参考

| 方法 | 描述 |
|------|------|
| `generate(prompt, config, output_name, enhance_prompt)` | 生成单张配图 |
| `generate_cover(title, topic, style)` | 生成封面图 |
| `batch_generate(prompts, config)` | 批量生成配图 |

## 封面风格

| 风格 | 描述 |
|------|------|
| `chalkboard` | 黑板报风格（推荐，适合公众号） |
| `tech` | 科技风格（渐变色、抽象可视化） |
| `minimal` | 简约风格（简洁、几何形状） |
| `academic` | 学术风格（专业、科学图解） |
| `creative` | 创意风格（抽象、多彩） |

## 数据类

```python
@dataclass
class ImageConfig:
    width: int = 1024
    height: int = 768
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    seed: int | None = None

@dataclass
class GeneratedImage:
    prompt: str
    path: Path
    width: int
    height: int
    model: str
```

## 支持的模型

- `google/gemini-3-pro-image-preview`（默认，推荐）
- `google/gemini-2.0-flash-exp-image-generation`（快速）
- `openai/dall-e-3`（最高质量，成本较高）

## Prompt 技巧

```python
# ❌ 不好的 prompt
"神经网络图"

# ✅ 好的 prompt
"Neural network architecture diagram, multiple layers with interconnected nodes, professional technical illustration, blue and purple gradient"
```

## 常见错误

| 错误 | 解决方案 |
|------|----------|
| `需要设置 OPENROUTER_API_KEY` | 设置环境变量 |
| `API 没有返回图片数据` | 检查网络或更换模型 |
| `HTTPError: 404` | 检查模型 ID 是否正确 |
