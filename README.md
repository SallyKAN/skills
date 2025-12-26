# Skills

A collection of custom skills for Claude Code that extend Claude's capabilities with specialized knowledge, workflows, and tool integrations.

## About Skills

Skills are folders of instructions, scripts, and resources that Claude loads dynamically to improve performance on specialized tasks. Skills teach Claude how to complete specific tasks in a repeatable way.

For more information about skills, see:
- [What are skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
- [Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [How to create custom skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)

## Available Skills

### paper-translator

Automated academic paper to WeChat article translation pipeline. Converts academic papers (arXiv, PDF) into engaging WeChat Official Account articles with:

- PDF parsing and figure extraction
- LLM-based article generation (Claude/GPT)
- Reflection-based quality refinement
- AI cover image generation
- WeChat Official Account publishing

**Usage:**
```bash
python -m src.main https://arxiv.org/abs/1706.03762
```

See [skills/paper-translator/SKILL.md](skills/paper-translator/SKILL.md) for full documentation.

## Installation

### Claude Code Plugin

You can register this repository as a Claude Code Plugin marketplace:

```
/plugin marketplace add SallyKAN/skills
```

Then install skills:
```
/plugin install paper-translator-skills@sally-skills
```

### Manual Installation

1. Clone this repository
2. Copy desired skill folders to `~/.claude/skills/` for personal use or `.claude/skills/` for project-specific use

## Creating New Skills

Use the template in `template/` as a starting point:

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Add your instructions here]
```

## License

MIT
