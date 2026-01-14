---
name: claude-skill-installer
description: Install Claude Code skills into $CLAUDE_HOME/skills from the Anthropic skills repository or from any GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). Supports direct GitHub URLs like https://agent-skills.md/skills/anthropics/skills/skill-name.
author: malar
repo: github.com/malar/skills
tags: [installer, skills, utility]
---

# Claude Skill Installer

Helps install skills for Claude Code. By default these are from https://github.com/anthropics/skills, but users can also provide other locations.

Use the helper scripts based on the task:
- List curated skills when the user asks what is available, or if the user uses this skill without specifying what to do.
- Install from the curated list when the user provides a skill name.
- Install from another repo when the user provides a GitHub repo/path (including private repos).
- Install from a URL when the user provides a direct GitHub URL (like https://agent-skills.md/skills/anthropics/skills/doc-coauthoring).

Install skills with the helper scripts.

## Communication

When listing curated skills, output approximately as follows, depending on the context of the user's request:
"""
Skills from {repo}:
1. skill-1
2. skill-2 (already installed)
3. ...
Which ones would you like installed?
"""

After installing a skill, tell the user: "Restart Claude Code to pick up new skills."

## Scripts

All of these scripts use network, so when running in the sandbox, request escalation when running them.

- `scripts/list-curated-skills.py` (prints curated list with installed annotations)
- `scripts/list-curated-skills.py --format json`
- `scripts/install-skill-from-github.py --repo <owner>/<repo> --path <path/to/skill> [<path/to/skill> ...]`
- `scripts/install-skill-from-github.py --url https://github.com/<owner>/<repo>/tree/<ref>/<path>`

## Behavior and Options

- Defaults to direct download for public GitHub repos.
- If download fails with auth/permission errors, falls back to git sparse checkout.
- Aborts if the destination skill directory already exists.
- Installs into `$CLAUDE_HOME/skills/<skill-name>` (defaults to `~/.claude/skills`).
- Multiple `--path` values install multiple skills in one run, each named from the path basename unless `--name` is supplied.
- Options: `--ref <ref>` (default `main`), `--dest <path>`, `--method auto|download|git`.

## URL Handling

When users provide URLs from https://agent-skills.md/skills/, these are shortcuts to the Anthropic skills repository. Convert them to the proper GitHub format:
- Input: `https://agent-skills.md/skills/anthropics/skills/doc-coauthoring`
- Convert to: `https://github.com/anthropics/skills/tree/main/skills/doc-coauthoring`

## Skill Metadata

Installed skills should include metadata in their YAML frontmatter for attribution and discovery:

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

- Curated listing is fetched from `https://github.com/anthropics/skills/tree/main/skills` via the GitHub API. If it is unavailable, explain the error and exit.
- Private GitHub repos can be accessed via existing git credentials or optional `GITHUB_TOKEN`/`GH_TOKEN` for download.
- Git fallback tries HTTPS first, then SSH.
- Installed annotations come from `$CLAUDE_HOME/skills`.
