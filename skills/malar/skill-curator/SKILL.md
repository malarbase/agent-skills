---
name: skill-curator
description: Publish and maintain curated skills in the agent-skills repository. Handles
  importing skills from GitHub repos, local paths, or URLs, validating structure,
  creating PRs, and landing changes. Use when publishing skills, curating skills,
  shipping skills to the agent-skills repo, or managing the malarbase/agent-skills
  inventory.
metadata:
  tags:
  - curator
  - skills
  - publishing
  author: malar
  repo: github.com/malarbase/agent-skills
---

# Skill Curator

Publish curated skills to the `malarbase/agent-skills` repository. This is the "producer" complement to `skill-installer` (the "consumer").

## Quick Reference

| Command | Purpose |
|---------|---------|
| `import <source>` | Fetch skill from source, stage locally |
| `validate [path]` | Check skill structure and metadata |
| `ship` | Create branch, commit, push, open PR |
| `land <PR#>` | Merge PR, update inventory |
| `update <skill> --from <source>` | Update an existing skill |
| `list` | Show current inventory from repo |
| `status` | Show staged skills ready to ship |

## Scripts

All scripts live in `scripts/` and require Python 3.10+. Push/PR operations require `gh` CLI.

- `scripts/curator.py import <source> [--author <author>] [--tags <tags>]` — stage a skill locally
- `scripts/curator.py validate [<path>]` — validate staged or specified skill
- `scripts/curator.py ship [--draft]` — push staged skills and create PR
- `scripts/curator.py land <pr-number>` — merge PR and update inventory
- `scripts/curator.py update <skill> --from <source>` — update existing skill
- `scripts/curator.py list` — show inventory from remote repo
- `scripts/curator.py status` — show what's staged

## Configuration

| Setting | Default | Env Override |
|---------|---------|--------------|
| Target repo | `malarbase/agent-skills` | `SKILL_CURATOR_REPO` |
| Staging dir | `~/.cache/skill-curator/staging` | `SKILL_CURATOR_STAGING` |
| Clone cache | `~/.cache/skill-curator/repo` | `SKILL_CURATOR_CLONE` |

## Authentication

Push and PR operations require GitHub authentication:

1. Run `gh auth status` to verify
2. If not authenticated: `gh auth login`
3. Fallback: set `GITHUB_TOKEN` or `GH_TOKEN` env var

## Decision Tree

**Have a skill to publish?**
→ `import <source>` then `ship`

**Updating an existing skill?**
→ `update <skill-name> --from <source>` then `ship`

**Reviewing what's staged?**
→ `status` to see pending, `validate` to check

**PR approved and ready?**
→ `land <PR#>`

**Just browsing?**
→ `list` to see current inventory

## Workflow Example

```bash
# 1. Import a skill from a GitHub repo
python scripts/curator.py import https://github.com/user/repo/tree/main/my-skill --author malar

# 2. Check it looks good
python scripts/curator.py status
python scripts/curator.py validate

# 3. Ship it (creates branch + PR)
python scripts/curator.py ship

# 4. After review, land it
python scripts/curator.py land 42
```

## Source Formats

The `import` command accepts:
- **GitHub URL**: `https://github.com/owner/repo/tree/ref/path/to/skill`
- **Repo path**: `owner/repo:path/to/skill` (uses default ref `main`)
- **Local path**: `/absolute/path/to/skill` or `./relative/path`

## Metadata Handling

Skills in this repo use `metadata:` in SKILL.md frontmatter for repo-specific fields,
per the [agentskills.io spec](https://agentskills.io/specification):

```yaml
---
name: my-skill
description: What this skill does and when to use it.
metadata:
  author: malar
  repo: github.com/owner/repo
  tags: [category, workflow]
---
```

The `import` command auto-populates these fields when they are missing:

| Field | Auto-populated from |
|-------|---------------------|
| `metadata.author` | `--author` flag, or `$USER` |
| `metadata.repo` | Source GitHub URL (if imported from GitHub) |
| `metadata.tags` | Derived from skill name + `curated` tag, or `--tags` flag |

Override tags explicitly:

```bash
curator.py import ./my-skill --author malar --tags "api,integration,curated"
```

**When importing from external sources**, skills may have `author`, `repo`, or `tags`
as top-level frontmatter fields (non-spec). The `import` command automatically moves
these under `metadata:` during staging.

## Additional Resources

For detailed command documentation, see [commands.md](commands.md).
