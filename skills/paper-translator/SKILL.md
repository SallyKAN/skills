---
name: paper-translator
description: Automated academic paper to WeChat article translation pipeline. Use this skill when users need to convert academic papers (arXiv, PDF) into WeChat Official Account articles with LLM-based generation, reflection refinement, and image processing.
---

# Paper Translator

Convert academic papers into engaging WeChat Official Account articles with automated parsing, LLM-based writing, reflection-based refinement, and illustration generation.

## Overview

This skill provides a complete pipeline for transforming academic papers into readable Chinese articles suitable for WeChat Official Account publishing:

1. **Parse** - Download and extract text, metadata, and figures from PDF papers
2. **Generate** - Create initial draft using LLM (Claude/GPT) with customizable prompts
3. **Refine** - Second-pass quality improvement with reflection-based review
4. **Illustrate** - Extract paper figures + generate AI cover images
5. **Publish** - Upload to WeChat Official Account draft box (optional)

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/SallyKAN/skills.git
cd skills/skills/paper-translator

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Required API Keys

```bash
# LLM (choose one)
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# Image generation (OpenAI-compatible endpoint)
OPENAI_BASE_URL=https://your-api-router.com/v1  # optional

# WeChat publishing (optional)
WECHAT_APP_ID=wx_xxx
WECHAT_APP_SECRET=xxx
```

### Basic Usage

```bash
# Basic translation
python -m src.main https://arxiv.org/abs/1706.03762

# With citation count
python -m src.main https://arxiv.org/abs/1706.03762 --citations 100000

# Translate and publish to WeChat
python -m src.main https://arxiv.org/abs/1706.03762 --publish

# Custom config and output directory
python -m src.main <url> --config config/my_config.yaml --output ./my_output
```

## Architecture

### Pipeline Flow

The main translation pipeline executes 5 sequential stages:

1. **Parse** (`src/parser/pdf_parser.py`): Downloads PDF, extracts text/metadata/figures using PyMuPDF
2. **Generate** (`src/generator/writer.py`): Calls LLM to create initial draft from paper content
3. **Refine** (`src/generator/refiner.py`): Second LLM pass for reflection-based quality improvement
4. **Illustrate** (`src/image/`): Extracts paper figures + generates AI cover/illustrations
5. **Publish** (`src/publisher/wechat.py`): Uploads to WeChat Official Account draft box

### Key Design Patterns

**Prompt Template System**: Both `ArticleWriter` and `ArticleRefiner` load Markdown prompt templates from `prompts/` directory and perform variable substitution (`{{title}}`, `{{content}}`, etc.).

**Provider Abstraction**: LLM modules support both Anthropic and OpenAI via a `provider` parameter, with unified API handling.

**Configuration Hierarchy**: Config loading checks `config.local.yaml` first (gitignored), then falls back to `config.yaml`.

## Project Structure

```
paper-translator/
├── config/
│   └── config.yaml          # Configuration file
├── src/
│   ├── parser/              # Paper parsing
│   │   └── pdf_parser.py    # PDF text+figure extraction
│   ├── generator/           # Article generation
│   │   ├── writer.py        # Initial draft generation
│   │   └── refiner.py       # Reflection-based refinement
│   ├── image/               # Image processing
│   │   ├── extractor.py     # Paper figure extraction
│   │   └── generator.py     # AI image generation
│   ├── publisher/           # Publishing
│   │   └── wechat.py        # WeChat draft API
│   └── main.py              # Main orchestration
├── prompts/                 # Prompt templates
│   ├── translate.md         # Translation prompt
│   └── refine.md            # Refinement prompt
├── output/                  # Output directory
└── requirements.txt
```

## Configuration

Edit `config/config.yaml` to customize:

```yaml
# LLM configuration
llm:
  provider: "anthropic"  # anthropic / openai
  model: "claude-sonnet-4-20250514"

# Image generation
replicate:
  model: "nano-banana-pro"

# Article settings
article:
  language: "zh-CN"
  style: "accessible and engaging"
  audience: "tech enthusiasts interested in AI"
  generate_cover: true
  use_paper_figures: true
```

## Python API

```python
from src.main import PaperTranslator, TranslatorConfig

config = TranslatorConfig(
    llm_provider="anthropic",
    generate_cover=True,
    auto_publish=False,
)

translator = PaperTranslator(config)
result = translator.translate(
    paper_url="https://arxiv.org/abs/1706.03762",
    citations=100000,
)

print(f"Title: {result['article_title']}")
print(f"Output: {result['outputs']['article_path']}")
```

## Output Structure

Each translation run creates output in the `output/` directory:

```
output/
├── paper.pdf              # Downloaded PDF
├── draft.md               # Initial LLM-generated draft
├── article.md             # Refined final article
├── figures/               # Extracted paper figures
│   └── fig_p1_1.png
└── images/                # AI-generated illustrations
    ├── generated_xxx.png
    └── cover.png
```

## Supported Paper Sources

- arXiv URLs: `https://arxiv.org/abs/XXXX.XXXXX` or `https://arxiv.org/pdf/XXXX.XXXXX`
- Direct PDF links: Any publicly accessible PDF URL

## Customizing Prompts

Modify files in `prompts/` directory to adjust generation style:

- `translate.md` - Controls initial draft generation style and structure
- `refine.md` - Controls review criteria for refinement pass

## Notes

1. **API Costs**: LLM and image generation APIs incur costs
2. **WeChat Limits**: Draft API has daily call limits
3. **Image Copyright**: Paper figures are for academic exchange only

## License

MIT
