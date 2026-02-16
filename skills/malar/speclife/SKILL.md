---
name: speclife
description: 'Automate spec-driven development workflows with git and GitHub. Manages
  the full change lifecycle: creating branches/worktrees, implementing via OpenSpec,
  shipping PRs, landing merges, and releasing versions. Use when the user mentions
  speclife, spec-driven development, worktrees, shipping changes, landing PRs, creating
  releases, or any /speclife command.'
metadata:
  author: malar
  repo: github.com/malarbase/agent-skills
  tags:
  - speclife
  - curated
---

# SpecLife

Git/GitHub automation for spec-driven development. SpecLife complements OpenSpec:
- **SpecLife** handles git (branches, worktrees, PRs, merges, releases)
- **OpenSpec** handles specs (proposals, validation, implementation)

## Change Lifecycle

One-time setup: `init` (runs `scripts/init.sh` from this skill directory).

Repeating cycle for each change:

```
start → [implement via /openspec-apply] → ship → land
  │                                          │       │
  ├─ Creates branch or worktree              │       ├─ Merges PR (squash)
  ├─ Scaffolds proposal + tasks              │       ├─ Cleans up branch/worktree
  └─ STOP (don't auto-chain)                 │       └─ Auto-releases (patch/minor)
                                             │
                                             ├─ Validates + archives spec
                                             ├─ Commits, pushes, creates PR
                                             └─ STOP (don't auto-chain)
```

## Command Quick Reference

| Command | Purpose | How |
|---------|---------|-----|
| `start` | Create branch/worktree for new change | Agent: git commands |
| `ship` | Commit, push, create PR | Agent: git/gh commands |
| `land` | Merge PR, cleanup, release | Agent: git/gh commands |
| `release` | Manual release (major versions) | Agent: git/gh commands |
| `sync` | Update branch from main | Agent: git commands |
| `setup` | Auto-detect project config | Agent: reads project files |
| `implement` | Proxy to `/openspec-apply` | Agent: delegates |
| `convert` | Switch branch-only <-> worktree | Agent: git commands |
| `retrofit` | Formalize ad-hoc changes as spec | Agent: git/gh commands |
| `init` (one-time) | Project setup | Script: `scripts/init.sh` |
| `worktree create/rm/list` | Manage worktrees | Script: `scripts/worktree.sh` |
| `validate` | Check spec completeness | Script: `scripts/validate.sh` |

**Agent-executed** commands follow the steps in [commands.md](commands.md). **Script** commands run shell scripts from this skill's `scripts/` directory.

## Decision Tree

- **New change with spec?** -> `start "description"` then `/openspec-apply`
- **Resume existing change?** -> `start "resume <id>"`
- **Ad-hoc branch (no spec)?** -> `ship` works on any non-main branch
- **Changes already on main?** -> `retrofit` to formalize as spec + PR
- **Branch out of date?** -> `sync`
- **Parallel work needed?** -> `start "description in a worktree"`
- **Switch between modes?** -> `convert` (branch-only <-> worktree)
- **First time in project?** -> `init` then `setup`
- **Major version release?** -> `release --major` (patch/minor use `land`)

## Key Conventions

### Branch Naming

Always `spec/<change-id>`. The change-id is kebab-case with a verb prefix:
- `add-user-auth`, `fix-login-bug`, `update-api-docs`, `remove-legacy-code`, `refactor-db-layer`

### Conventional Commits for PR Titles

```
feat: add user authentication          → minor bump
fix: correct date parsing              → patch bump
docs: update API reference             → patch bump
chore: upgrade dependencies            → patch bump
feat!: redesign auth API               → major bump
```

### Release Trigger

A commit message matching `chore(release): vX.X.X` triggers the GitHub Actions release workflow, which creates a git tag and GitHub release.

### PR Body

If `.github/pull_request_template.md` exists, read it and fill in each section based on the change context. Otherwise, use a concise summary with conventional commit context.

## Worktree Safety

**CRITICAL**: When working in a worktree, ALL file edits must use `worktrees/<change-id>/` paths, NOT the main repo root.

Before making any file edits in a worktree context:
1. Run `git branch --show-current` to verify you're on the correct branch
2. Confirm file paths include `worktrees/<change-id>/`
3. If a worktree exists but you're about to edit main repo paths, **STOP** and ask the user

Branch-only mode (default) works directly in the main repo -- this is correct when no worktree exists.

## Scripts

This skill includes utility scripts in `scripts/`:

| Script | Usage | Purpose |
|--------|-------|---------|
| `init.sh` | `bash scripts/init.sh` | One-time project setup |
| `worktree.sh` | `bash scripts/worktree.sh create\|rm\|list [change-id]` | Worktree management with env bootstrapping |
| `validate.sh` | `bash scripts/validate.sh <change-id>` | Spec validation (checks proposal.md, tasks.md) |

Scripts use `uv` when available, falling back to `python3`. Run from the skill directory (`~/.cursor/skills/speclife/`).

## Configuration Files

### `.specliferc.yaml` (project root)

```yaml
specDir: openspec         # Spec directory name
git:
  baseBranch: main        # Base branch for PRs
  branchPrefix: spec/     # Branch prefix for changes
  worktreeDir: worktrees  # Directory for worktrees
```

### `openspec/speclife.md` (AI context)

Read by slash commands for project-specific info:

```markdown
## Commands
- **Test:** `npm test`
- **Build:** `npm run build`
- **Lint:** `npm run lint`

## Release Policy
- Auto-release: patch and minor
- Manual release: major (breaking changes)

## Context Files
- `openspec/project.md`
- `openspec/AGENTS.md`
```

## Additional Resources

- For full command details, read [commands.md](commands.md)
- For project setup details, read [init-reference.md](init-reference.md)
- For worktrees, monorepo support, and advanced topics, read [advanced.md](advanced.md)
