---
name: /speclife-sync
id: speclife-sync
category: SpecLife
description: Update current branch with latest changes from main.
---
**Guardrails**
- Execute immediately—default to rebase unless `--merge` specified
- Require: not on main, working directory clean
- Guide user through conflict resolution if any

**Steps**
1. Check state: error if on main or uncommitted changes exist.
2. Fetch and check: `git fetch origin main`; if already up to date, report and exit.
3. Rebase (default) or merge: `git rebase origin/main` or `git merge origin/main`.
4. If conflicts: list conflicting files, explain resolution (edit files, `git add`, `git rebase --continue`), offer to help resolve.
5. Push: `git push --force-with-lease` (rebase) or `git push` (merge).
6. Report: commits synced, conflicts resolved (if any), pushed.

**Reference**
- Conflict markers: `<<<<<<< HEAD`, `=======`, `>>>>>>> origin/main`
- Abort rebase: `git rebase --abort`
