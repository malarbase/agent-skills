---
name: skill-installer
description: Install AI agent skills from GitHub repositories into the current editor's skills directory. Works across all major AI coding editors (Claude Code, OpenCode, Antigravity, Cursor, etc.) by auto-detecting the editor and its skills location. Use when a user asks to list available skills, install a skill, or manage skills from GitHub repos (including private repos). Supports the Anthropic curated skills repository and custom skill sources.
metadata:
  author: malar
  repo: github.com/malar/skills
  tags: [installer, skills, utility, cross-editor]
---

# Skill Installer

A universal skill installer that works across all major AI coding editors by auto-detecting the active environment.

## Supported Editors

### Global Skills (User-level)

| Editor | Home Variable | Default Path | Skills Location |
|--------|---------------|--------------|-----------------|
| Claude Code | `CLAUDE_HOME` | `~/.claude` | `~/.claude/skills` |
| OpenCode | `OPENCODE_HOME` | `~/.opencode` | `~/.opencode/skills` |
| Antigravity | `GEMINI_HOME` | `~/.gemini` | `~/.gemini/skills` |
| Gemini CLI | `GEMINI_CLI_HOME` | `~/.gemini` | `~/.gemini/skills` |
| Cursor | `CURSOR_HOME` | `~/.cursor` | `~/.cursor/skills` |
| Windsurf | `WINDSURF_HOME` | `~/.windsurf` | `~/.windsurf/skills` |
| Generic | `AGENT_HOME` | `~/.agent` | `~/.agent/skills` |

The installer auto-detects the editor in this priority order, falling back to `.agent` if none found.

### Project-Local Skills (Per-project)

Each editor has its own project-local directory at the git repository root:

| Editor | Project Directory | Skills Location |
|--------|-------------------|-----------------|
| Claude Code | `.claude/` | `.claude/skills/` |
| OpenCode | `.opencode/` | `.opencode/skills/` |
| **Antigravity** | **`.agent/`** | **`.agent/skills/`** |
| Gemini CLI | `.gemini/` | `.gemini/skills/` |
| Cursor | `.cursor/` | `.cursor/skills/` |
| Windsurf | `.windsurf/` | `.windsurf/skills/` |
| Generic | `.agent/` | `.agent/skills/` |

> **Note**: Antigravity uses `.agent/` for project-local config, NOT `.gemini/`. The `.gemini/` directory is used by Gemini CLI, which is a different product.

Use `--project` to auto-detect the editor's project directory, or `--project-editor` to specify which one:

```bash
# Auto-detect (uses first found: .claude, .opencode, .agent, .gemini, etc.)
scripts/install-skill.py --skill docx --project

# Explicitly use .claude/skills
scripts/install-skill.py --skill docx --project-editor claude

# Explicitly use .agent/skills (for Antigravity)
scripts/install-skill.py --skill docx --project-editor antigravity
```

## Usage

Use the helper scripts based on the task:

- **List skills**: Show available curated skills from the Anthropic repository
- **Install by name**: Install a curated skill by its name
- **Install from repo**: Install from any GitHub `owner/repo` with a path
- **Install from URL**: Install from a direct GitHub URL

## Scripts

All scripts use network access. When running in sandboxed environments, escalation may be required.

```bash
# List curated skills (with install status)
scripts/list-curated-skills.py

# JSON output format
scripts/list-curated-skills.py --format json

# Install from curated list
scripts/install-skill.py --skill <skill-name>

# Install from GitHub repo + path
scripts/install-skill.py --repo <owner>/<repo> --path <path/to/skill>

# Install from GitHub URL
scripts/install-skill.py --url https://github.com/<owner>/<repo>/tree/<ref>/<path>

# Install multiple skills at once
scripts/install-skill.py --repo <owner>/<repo> --path <path1> <path2> <path3>

# Install to project-local skills (auto-detect editor)
scripts/install-skill.py --skill <skill-name> --project

# Install to specific editor's project directory
scripts/install-skill.py --skill <skill-name> --project-editor claude

# List skills with project install status
scripts/list-curated-skills.py --project
scripts/list-curated-skills.py --project-editor antigravity
```

## Options

| Option | Description |
|--------|-------------|
| `--skill` | Install a curated skill by name |
| `--repo` | GitHub `owner/repo` format |
| `--path` | Path(s) to skill(s) inside the repo |
| `--url` | Full GitHub URL to skill directory |
| `--ref` | Git ref (branch/tag), default: `main` |
| `--dest` | Override destination skills directory |
| `--name` | Custom skill name (default: path basename) |
| `--editor` | Force global editor: `claude`, `opencode`, `antigravity`, `cursor`, `windsurf`, `agent` |
| `--project` | Install to project-local skills (auto-detect editor directory) |
| `--project-editor` | Specify which editor's project dir: `claude` (`.claude/`), `antigravity` (`.gemini/`), etc. |
| `--method` | Download method: `auto`, `download`, `git` |

## Behavior

1. **Auto-detection**: Checks environment variables in priority order to find the active editor
2. **Project-local**: With `--project`, auto-detects and uses the editor's project directory (e.g., `.claude/skills/`)
3. **Editor-specific**: Use `--project-editor` to explicitly choose which editor's project directory to use
4. **Download-first**: Attempts direct download for public repos, falls back to git sparse checkout
5. **Validation**: Ensures skill has `SKILL.md` before installing
6. **No overwrite**: Aborts if destination skill directory already exists
7. **Private repos**: Supports `GITHUB_TOKEN` or `GH_TOKEN` for authentication

## Communication

When listing curated skills:
```
Available skills from anthropics/skills:

1. skill-name
2. another-skill (already installed)
3. ...

Detected editor: Claude Code (~/.claude/skills)
Which skills would you like to install?
```

After installing:
```
Installed <skill-name> to <path>
Restart your editor to pick up new skills.
```

## Skill Metadata

Installed skills should include YAML frontmatter:

```yaml
---
name: skill-name
description: What the skill does and when to use it.
author: author-name-or-org
repo: github.com/owner/repo
tags: [category, workflow, etc]
---
```

Required: `name`, `description`
Optional: `author`, `repo`, `license`, `tags`

## Notes

- Curated skills are fetched from `https://github.com/anthropics/skills/tree/main/skills`
- Private repos require git credentials or `GITHUB_TOKEN`/`GH_TOKEN`
- Git fallback tries HTTPS first, then SSH
- The `--editor` flag overrides auto-detection when needed
- The `--project` flag installs to `.agent/skills` in the git repository root (or current directory if not in a git repo)
- Project-local skills in `.agent/skills` can be committed to version control for team sharing
