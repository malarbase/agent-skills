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

### anthropic (4 skills)
- **doc-coauthoring** - Guide users through a structured workflow for co-authoring documentation
- **docx** - Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (
- **frontend-design** - Create distinctive, production-grade frontend interfaces with high design quality
- **skill-creator** - Guide for creating effective skills

### malar (11 skills)
- **3d-rendering** - How to generate 3D visualizations from floorplan DSL files
- **doc-with-diagrams** - Convert markdown documents with ASCII/text diagrams into professional Word documents with embedded Mermaid diagrams
- **experiment-log** - Proactively log infrastructure, performance, and integration experiments to a structured experiments
- **gsuite** - Standalone Google Workspace CLI for Docs, Drive, Sheets, Calendar, and Gmail operations via googleapis
- **maintain-skills** - Maintain Skills and Agents
- **mcp-integration** - How to use the Floorplan MCP server for AI-powered floorplan manipulation
- **md-collection-to-google-docs** - Convert a collection of interlinked markdown files into Google Docs with rendered diagrams, tables, and cross-references
- **repo-maintenance** - How to maintain the mermaid-floorplan monorepo
- **skill-curator** - Publish and maintain curated skills in the agent-skills repository
- **skill-installer** - Install AI agent skills from GitHub repositories into the current editor's skills directory
- **speclife** - Automate spec-driven development workflows with git and GitHub

### obra (14 skills)
- **brainstorming** - You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior
- **dispatching-parallel-agents** - Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
- **executing-plans** - Use when you have a written implementation plan to execute in a separate session with review checkpoints
- **finishing-a-development-branch** - Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
- **receiving-code-review** - Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
- **requesting-code-review** - Use when completing tasks, implementing major features, or before merging to verify work meets requirements
- **subagent-driven-development** - Use when executing implementation plans with independent tasks in the current session
- **systematic-debugging** - Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- **test-driven-development** - Use when implementing any feature or bugfix, before writing implementation code
- **using-git-worktrees** - Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification
- **using-superpowers** - Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
- **verification-before-completion** - Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
- **writing-plans** - Use when you have a spec or requirements for a multi-step task, before touching code
- **writing-skills** - Use when creating new skills, editing existing skills, or verifying skills work before deployment

### openai (1 skill)
- **skill-installer** - Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path

### softaworks (1 skill)
- **mermaid-diagrams** - Comprehensive guide for creating software diagrams using Mermaid syntax

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
