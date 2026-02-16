---
name: /speclife-ship
id: speclife-ship
category: SpecLife
description: Commit changes, push to remote, and create a PR for review.
---
**Guardrails**
- Execute immediately—do not ask for confirmation
- Detect branch type: `spec/*` = full OpenSpec workflow, other non-main = ad-hoc, `main` = error
- STOP after PR created—do NOT auto-invoke `/speclife land`
- Do NOT manually replicate `openspec` commands—run them and report errors if they fail

**Steps**
1. For spec branches: run `openspec validate <id>`, commit changes, run `openspec archive <id> --yes`, commit archive.
2. For ad-hoc branches: infer commit type from branch name (`fix/*` → `fix:`, `feat/*` → `feat:`), ask if ambiguous.
3. Push branch: `git push -u origin <branch>`.
4. Create/update PR: `gh pr create --title "<type>: <description>" --body "<body>" --base main` (add `--draft` if requested).
5. Report: commits made, branch pushed, PR URL. Next: `/speclife land` after approval.

**Reference**
- Commit type inference: fix/bugfix/hotfix → `fix:`, feat/feature → `feat:`, docs → `docs:`, refactor → `refactor:`, chore → `chore:`
- If PR exists, push updates it automatically
- PR title: use conventional commit format (`<type>: <meaningful description>`)
- PR body: if `.github/pull_request_template.md` exists, read it and fill in each section based on the change context
