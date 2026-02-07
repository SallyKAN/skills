"""
AI配图生成模块
- 通过 OpenRouter API 调用图像生成模型
- 支持 google/gemini-2.0-flash-exp-image-generation 等模型
- 通用的配图生成能力,可用于各种内容类型
"""

import base64
import os
import time
import requests
from dataclasses import dataclass
from pathlib import Path


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
    """AI配图生成器 - 通过 OpenRouter API 调用"""

    def __init__(
        self,
        model: str = "google/gemini-3-pro-image-preview",
        api_key: str | None = None,
        base_url: str | None = None,
        output_dir: Path | str = "./output/images",
    ):
        """
        初始化图像生成器

        Args:
            model: 图像生成模型ID
            api_key: OpenRouter API密钥 (默认从环境变量读取)
            base_url: API基础URL (默认使用 OpenRouter)
            output_dir: 输出目录
        """
        self.model_id = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 设置 API 配置 - 优先使用 OpenRouter
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url or os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"

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

        Raises:
            ValueError: 如果未设置 API 密钥
            requests.HTTPError: 如果 API 请求失败
        """
        config = config or ImageConfig()

        # 增强prompt（针对科技文章配图优化）
        if enhance_prompt:
            prompt = self._enhance_prompt(prompt)

        print(f"🎨 正在生成配图...")
        print(f"   模型: {self.model_id}")
        print(f"   Prompt: {prompt[:100]}...")

        if not self._api_key:
            raise ValueError("需要设置 OPENROUTER_API_KEY 或 OPENAI_API_KEY 环境变量")

        # 通过 OpenRouter API 调用图像生成
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/wechat-documents",
                "X-Title": "WeChat Documents",
            }

            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Generate an image: {prompt}"
                    }
                ],
            }

            response = requests.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=300,  # 图像生成需要更长时间
            )
            response.raise_for_status()
            result = response.json()

            # 从响应中提取图片数据
            image_data = self._extract_image_data(result)

            if image_data is None:
                raise ValueError(f"API 没有返回图片数据。响应内容: {str(result)[:500]}")

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

    def _extract_image_data(self, result: dict) -> bytes | None:
        """从 API 响应中提取图片数据"""
        message = result.get("choices", [{}])[0].get("message", {})
        image_data = None

        # 首先检查 images 数组 (OpenRouter + Gemini 格式)
        if "images" in message and isinstance(message["images"], list):
            for img in message["images"]:
                if isinstance(img, dict) and img.get("type") == "image_url":
                    image_url = img.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image"):
                        base64_data = image_url.split(",")[1] if "," in image_url else image_url
                        image_data = base64.b64decode(base64_data)
                        break

        # 回退：从 content 中提取
        content = message.get("content", "")
        if image_data is None and isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    # 检查 inline_data 格式 (Gemini 风格)
                    if "inline_data" in part:
                        inline_data = part["inline_data"]
                        if "data" in inline_data:
                            image_data = base64.b64decode(inline_data["data"])
                            break
                    # 检查 image_url 格式
                    if part.get("type") == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image"):
                            base64_data = image_url.split(",")[1] if "," in image_url else image_url
                            image_data = base64.b64decode(base64_data)
                            break
                    # 检查 image 格式
                    if part.get("type") == "image" and part.get("data"):
                        image_data = base64.b64decode(part["data"])
                        break
        elif isinstance(content, str):
            # 检查是否是 base64 编码的图片数据
            if content.startswith("data:image"):
                base64_data = content.split(",")[1] if "," in content else content
                image_data = base64.b64decode(base64_data)

        return image_data

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
        style: str = "chalkboard",
    ) -> GeneratedImage:
        """
        生成文章封面图

        Args:
            title: 文章标题
            topic: 主题
            style: 风格 (chalkboard/tech/minimal/academic/creative)

        Returns:
            生成的封面图
        """
        # 构建封面prompt
        style_prompts = {
            "chalkboard": (
                f"根据这个自媒体标题：{title} 生成一张黑板报风格的封面图："
                "采用黑色黑板背景和粉笔手绘风格，横版（16:9）构图。"
                "信息精简，突出关键词与核心概念，多留白，易于一眼抓住重点。"
                "加入少量简洁的卡通元素、图标或名人画像，增强趣味性和视觉记忆。"
                "所有图像、文字必须使用彩色粉笔绘制，没有写实风格图画元素"
            ),
            "tech": "futuristic technology, digital art, abstract neural network visualization, blue and purple gradient",
            "minimal": "minimalist design, clean white background, simple geometric shapes",
            "academic": "academic illustration, scientific diagram style, professional",
            "creative": "creative abstract art, colorful, dynamic composition",
        }

        if style == "chalkboard":
            # 黑板报风格使用完整的中文prompt，不需要额外拼接
            prompt = style_prompts["chalkboard"]
        else:
            style_desc = style_prompts.get(style, style_prompts["tech"])
            prompt = f"Article cover image about {topic}: {title}. {style_desc}"

        # 封面图使用16:9比例
        config = ImageConfig(width=1200, height=675)

        # 黑板报风格不需要enhance_prompt，避免添加英文修饰词
        enhance = style != "chalkboard"

        return self.generate(prompt, config, output_name="cover.png", enhance_prompt=enhance)

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
    model: str = "google/gemini-3-pro-image-preview",
    output_dir: str = "./output/images",
) -> Path:
    """
    生成配图的便捷函数

    Args:
        prompt: 图片描述
        model: 模型ID
        output_dir: 输出目录

    Returns:
        生成的图片路径
    """
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
