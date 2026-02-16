---
name: /speclife-start
id: speclife-start
category: SpecLife
description: Create a new branch for a change, optionally in a worktree for parallel work.
---
**Guardrails**
- Execute immediately when invoked
- Parse input for resume keywords (`resume`, `continue`, `pick up`, `implement <id>`)
- Parse for mode keywords: "in a worktree" or "with worktree" → worktree, otherwise → branch-only (default)
- STOP after scaffolding—do NOT auto-invoke `/openspec-apply`

**Steps**
1. If resume intent detected, verify `openspec/changes/<id>/` exists; error with available proposals if not found.
2. For new proposals: derive kebab-case change-id from description (prefix: add-, fix-, update-, remove-, refactor-).
3. Create workspace: branch-only → `git checkout -b spec/<id>`, worktree → `speclife worktree create <id>`.
4. For new proposals only: scaffold `proposal.md` and `tasks.md` under `openspec/changes/<id>/` (follow `/openspec-proposal` for format), then run `openspec validate <id> --strict`.
5. Report: change-id, branch/worktree created, path to work directory. If worktree, emphasize: "All edits must happen in worktrees/<id>/".

**Reference**
- Branch name always `spec/<change-id>` regardless of mode
- Resume skips proposal scaffolding; proceed directly to `/openspec-apply`
- Use `/speclife convert` to switch modes later
