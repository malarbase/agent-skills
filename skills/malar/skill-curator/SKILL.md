---
name: skill-curator
description: Publish and maintain curated skills in the agent-skills repository. Handles
  importing skills from GitHub repos, local paths, or URLs, validating structure,
  creating PRs, and landing changes. Use when publishing skills, curating skills,
  shipping skills to the agent-skills repo, or managing the malarbase/agent-skills
  inventory.
metadata:
  author: malar
  repo: github.com/malarbase/agent-skills
  tags:
  - curator
  - skills
  - publishing
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
| Staging dir | `.staging/` (in repo) or `~/.cache/skill-curator/staging` (outside repo) | `SKILL_CURATOR_STAGING` |
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

## Pre-flight Checklist

Before running `ship`, verify:

- [ ] Local git repo has no uncommitted changes: `git status`
- [ ] No stashed changes that should be included: `git stash list`
- [ ] Skills are staged and validated: `curator.py status`
- [ ] Changes are what you expect: review staged skill files in `.staging/` (or `~/.cache/skill-curator/staging/` if outside repo)

**Note**: The `ship` command automatically cleans up the staging area after successfully creating a PR.

### Handling Repository Changes

If you have uncommitted changes to the curator tool or other repo files:

**Recommended: Separate PRs**
```bash
# 1. Commit repo changes first
git add .gitignore skills/malar/skill-curator/
git commit -m "feat(curator): improve staging workflow"
git push

# 2. Then ship skills (creates separate PR)
python scripts/curator.py ship
```

**Why separate PRs?**
- Different review types (code review vs content review)
- Independent rollback if issues arise
- Cleaner commit history and PR purpose
- Easier to review focused changes

The `ship` command will fail if uncommitted changes exist, preventing accidental mixing of concerns.

## Reviewing Staged Skills

### Default Staging Location

When working **within the agent-skills repository**, skills are staged to `.staging/` in the repo root for easy editor access. This directory is gitignored, so staged skills won't clutter `git status`.

When working **outside the agent-skills repository**, skills are staged to `~/.cache/skill-curator/staging`.

### Editor-Based Review Workflow

1. Import skills - they appear in `.staging/author/skill-name/` in your editor's file tree
2. Browse, read, and validate staged skills directly in your editor
3. Make edits if needed (fix typos, adjust metadata, etc.)
4. Run `validate` to ensure all skills pass checks
5. Run `ship` to copy from `.staging/` to `skills/` and create a PR

### Opening Staged Skills

From within the agent-skills repo:
```bash
# Staged skills are in .staging/ - already visible in your editor tree
code .staging/author/skill-name/SKILL.md
```

From outside the repo (using cache):
```bash
# Open staging area in a new editor window
code ~/.cache/skill-curator/staging
```

### Custom Staging Location

Override the default with:
```bash
export SKILL_CURATOR_STAGING=/custom/path/to/staging
```

### Local Repository Detection

If you run `curator.py ship` from within the agent-skills repository itself, the curator will:

1. Detect the local repo and use it directly (no cloning)
2. Check for uncommitted changes (fails if found)
3. Create a new branch from your current branch
4. Commit and push the staged skills
5. Create the PR
6. Return you to your original branch

This is more efficient and lets you review the changes with `git diff` before shipping.

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

- For detailed command documentation, see [commands.md](commands.md)
- For troubleshooting common issues, see [troubleshooting.md](troubleshooting.md)
