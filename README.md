# Agent Skills

A curated collection of skills for AI coding agents (Claude Code, Codex, etc.).

## Structure

Skills are organized by author:

```
skills/
├── anthropic/          # Official Anthropic skills
├── malar/              # malar's skills
├── obra/               # Jesse Vincent's superpowers skills
└── openai/             # OpenAI Codex skills
```

## Skills Inventory

### anthropic (3 skills)
- **doc-coauthoring** - Structured workflow for co-authoring documentation
- **frontend-design** - Create distinctive, production-grade frontend interfaces
- **skill-creator** - Guide for creating effective skills

### malar (7 skills)
- **3d-rendering** - Generate 3D visualizations from floorplan DSL files
- **claude-skill-installer** - Install Claude Code skills from GitHub repos
- **maintain-skills** - Audit, inventory, and maintain skills
- **mcp-integration** - Floorplan MCP server integration
- **repo-maintenance** - Mermaid-floorplan monorepo maintenance
- **skill-curator** - Publish and maintain curated skills in the agent-skills repo
- **speclife** - Automate spec-driven development workflows with git and GitHub

### obra (14 skills)
- **brainstorming** - Explore user intent and design before implementation
- **dispatching-parallel-agents** - Handle independent tasks in parallel
- **executing-plans** - Execute implementation plans with review checkpoints
- **finishing-a-development-branch** - Guide completion of development work
- **receiving-code-review** - Handle code review feedback properly
- **requesting-code-review** - Request code review before merging
- **subagent-driven-development** - Execute plans with fresh subagents per task
- **systematic-debugging** - Debug systematically before proposing fixes
- **test-driven-development** - Write tests before implementation
- **using-git-worktrees** - Create isolated git worktrees for feature work
- **using-superpowers** - Establish how to find and use skills
- **verification-before-completion** - Verify work before claiming completion
- **writing-plans** - Write implementation plans before coding
- **writing-skills** - Create and verify skills

### openai (1 skill)
- **skill-installer** - Install Codex skills from curated list or GitHub

## Skill Metadata

Each skill includes YAML frontmatter with:

```yaml
---
name: skill-name
description: What the skill does and when to use it.
author: author-name
repo: github.com/owner/repo
tags: [category, workflow, etc]
---
```

## Installation

Use the `claude-skill-installer` skill to install skills from this repo:

```
Install skill from malarbase/agent-skills: skills/obra/brainstorming
```

## Contributing

1. Fork the repo
2. Add your skill under `skills/<your-username>/<skill-name>/`
3. Ensure SKILL.md has proper frontmatter with author metadata
4. Create a PR

## License

Individual skills may have their own licenses. Check each skill's LICENSE.txt if present.
