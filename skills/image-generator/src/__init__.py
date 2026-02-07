"""
AI Image Generator - Shared Module

通用的 AI 配图生成模块,可用于:
- 论文翻译配图
- 博客文章配图
- 教程配图
- 封面图生成

Example:
    >>> from src.generator import ImageGenerator, ImageConfig
    >>> generator = ImageGenerator()
    >>> result = generator.generate("Abstract neural network visualization")
    >>> print(result.path)
"""

from .generator import (
    ImageGenerator,
    ImageConfig,
    GeneratedImage,
    generate_image,
)

__all__ = [
    "ImageGenerator",
    "ImageConfig",
    "GeneratedImage",
    "generate_image",
]
