"""
AI配图生成模块
- 通过 OpenAI 兼容 API 调用图像生成模型
- 支持本地配置的 Gemini 等模型
"""

import base64
import os
import time
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI


@dataclass
class ImageConfig:
    """图片生成配置"""
    width: int = 1024
    height: int = 768
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    seed: int | None = None


@dataclass
class GeneratedImage:
    """生成的图片"""
    prompt: str
    path: Path
    width: int
    height: int
    model: str


class ImageGenerator:
    """AI配图生成器 - 通过 OpenAI 兼容 API 调用"""

    def __init__(
        self,
        model: str = "google/gemini-2.0-flash-preview-image-generation",
        api_key: str | None = None,
        base_url: str | None = None,
        output_dir: Path | str = "./output/images",
    ):
        self.model_id = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 设置 API 配置（延迟检查）
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._client = None

    @property
    def client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            if not self._api_key:
                raise ValueError("需要设置 OPENAI_API_KEY 环境变量")
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    def generate(
        self,
        prompt: str,
        config: ImageConfig | None = None,
        output_name: str | None = None,
        enhance_prompt: bool = True,
    ) -> GeneratedImage:
        """
        生成配图

        Args:
            prompt: 图片描述prompt
            config: 生成配置
            output_name: 输出文件名
            enhance_prompt: 是否增强prompt

        Returns:
            生成的图片信息
        """
        config = config or ImageConfig()

        # 增强prompt（针对科技文章配图优化）
        if enhance_prompt:
            prompt = self._enhance_prompt(prompt)

        print(f"🎨 正在生成配图...")
        print(f"   模型: {self.model_id}")
        print(f"   Prompt: {prompt[:100]}...")

        # 通过 OpenAI 兼容 API 调用图像生成
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate an image: {prompt}"
                    }
                ],
            )

            # 从响应中提取图片数据
            image_data = None
            message = response.choices[0].message

            # 检查是否有图片内容
            if hasattr(message, 'content') and message.content:
                # 尝试从 content 中提取 base64 图片
                content = message.content
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            if part.get('type') == 'image_url':
                                image_url = part.get('image_url', {}).get('url', '')
                                if image_url.startswith('data:image'):
                                    # 提取 base64 数据
                                    base64_data = image_url.split(',')[1] if ',' in image_url else image_url
                                    image_data = base64.b64decode(base64_data)
                                    break
                            elif part.get('type') == 'image' and part.get('data'):
                                image_data = base64.b64decode(part['data'])
                                break

            # 如果响应中有 inline_data（Gemini 风格）
            if image_data is None and hasattr(response, 'candidates'):
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                image_data = part.inline_data.data
                                break

            if image_data is None:
                raise ValueError("API 没有返回图片数据，请检查模型是否支持图像生成")

            # 保存图片
            image_path = self._save_image(image_data, output_name)

            print(f"✅ 配图生成成功: {image_path}")

            return GeneratedImage(
                prompt=prompt,
                path=image_path,
                width=config.width,
                height=config.height,
                model=self.model_id,
            )

        except Exception as e:
            print(f"❌ 配图生成失败: {e}")
            raise

    def _enhance_prompt(self, prompt: str) -> str:
        """增强prompt，优化生成效果"""
        # 添加质量和风格修饰词
        enhancements = [
            "high quality",
            "professional illustration",
            "clean design",
            "modern style",
        ]

        # 检查是否已经包含这些词
        prompt_lower = prompt.lower()
        additions = [e for e in enhancements if e not in prompt_lower]

        if additions:
            prompt = f"{prompt}, {', '.join(additions[:2])}"

        return prompt

    def _save_image(self, image_data: bytes, output_name: str | None = None) -> Path:
        """保存生成的图片"""
        # 生成文件名
        if output_name is None:
            timestamp = int(time.time())
            output_name = f"generated_{timestamp}.png"

        if not output_name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            output_name += ".png"

        output_path = self.output_dir / output_name
        output_path.write_bytes(image_data)

        return output_path

    def generate_cover(
        self,
        title: str,
        topic: str = "AI",
        style: str = "tech",
    ) -> GeneratedImage:
        """
        生成文章封面图

        Args:
            title: 文章标题
            topic: 主题
            style: 风格

        Returns:
            生成的封面图
        """
        # 构建封面prompt
        style_prompts = {
            "tech": "futuristic technology, digital art, abstract neural network visualization, blue and purple gradient",
            "minimal": "minimalist design, clean white background, simple geometric shapes",
            "academic": "academic illustration, scientific diagram style, professional",
            "creative": "creative abstract art, colorful, dynamic composition",
        }

        style_desc = style_prompts.get(style, style_prompts["tech"])

        prompt = f"Article cover image about {topic}: {title}. {style_desc}"

        # 封面图使用16:9比例
        config = ImageConfig(width=1200, height=675)

        return self.generate(prompt, config, enhance_prompt=True)

    def batch_generate(
        self,
        prompts: list[str],
        config: ImageConfig | None = None,
    ) -> list[GeneratedImage]:
        """
        批量生成配图

        Args:
            prompts: prompt列表
            config: 生成配置

        Returns:
            生成的图片列表
        """
        results = []

        for i, prompt in enumerate(prompts):
            print(f"\n[{i + 1}/{len(prompts)}] 生成配图...")
            try:
                output_name = f"batch_{i + 1}.png"
                image = self.generate(prompt, config, output_name)
                results.append(image)
            except Exception as e:
                print(f"⚠️ 跳过失败的生成: {e}")

            # 避免API限流
            if i < len(prompts) - 1:
                time.sleep(1)

        return results


# 便捷函数
def generate_image(
    prompt: str,
    model: str = "google/gemini-2.0-flash-preview-image-generation",
    output_dir: str = "./output/images",
) -> Path:
    """生成配图的便捷函数"""
    generator = ImageGenerator(model=model, output_dir=output_dir)
    result = generator.generate(prompt)
    return result.path


if __name__ == "__main__":
    # 测试
    generator = ImageGenerator()

    # 生成测试图片
    result = generator.generate(
        "Abstract visualization of transformer neural network architecture, "
        "attention mechanism flowing between nodes, digital art style"
    )
    print(f"\n生成成功: {result.path}")
