---
name: /speclife-convert
id: speclife-convert
category: SpecLife
description: Switch between branch-only and worktree modes for current change.
---
**Guardrails**
- Execute immediately—parse "to worktree" or "to branch" from invocation
- Require: on a `spec/*` branch
- Handle uncommitted changes: prompt to commit or stash

**Steps (to worktree)**
1. Check: must be on `spec/*` branch in main repo, worktree doesn't already exist.
2. Commit any uncommitted changes (or ask user to stash).
3. Create worktree: `git worktree add worktrees/<change-id> <branch>`.
4. Return main repo to main: `git checkout main`.
5. Report: worktree created, next step is `cd worktrees/<change-id>/`.

**Steps (to branch)**
1. Check: must be in a worktree on `spec/*` branch.
2. Commit any uncommitted changes.
3. Go to main repo, checkout the branch: `git checkout <branch>`.
4. Remove worktree: `git worktree remove worktrees/<change-id>`.
5. Report: worktree removed, continue in main repo.

**Reference**
- Converts preserve all commits and history
- Branch name stays same; spec files work in both modes
