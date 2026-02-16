---
name: /speclife-retrofit
id: speclife-retrofit
category: SpecLife
description: Formalize ad-hoc changes on main into a spec-tracked change for review.
---
**Guardrails**
- Execute immediately—must be on `main` with uncommitted changes or unpushed commits
- Generate spec from actual changes (retrospective), not speculation
- STOP after PR created—do NOT auto-invoke `/speclife land`
- Do NOT manually replicate `openspec archive`—run the command and report errors if it fails

**Steps**
1. Detect changes: `git status --short` and `git log origin/main..HEAD --oneline`; error if no changes.
2. Analyze diffs to understand what was done; infer change type (feat, fix, refactor, docs).
3. Derive change-id: kebab-case with verb prefix (add-, fix-, update-, remove-, refactor-).
4. Review context: `openspec list --specs`, `cat openspec/project.md`.
5. Create retrospective spec: `proposal.md` (past tense), `tasks.md` (all `[x]` completed), spec deltas if applicable.
6. Validate and branch: `openspec validate <id>`, `git checkout -b spec/<id>`.
7. Commit, archive, push, PR: commit changes, run `openspec archive <id> --yes`, commit archive, push, create PR with `gh pr create --title "<type>: <description>" --body "<body>"`.
8. Report: change-id, spec created, PR URL. Next: `/speclife land` after approval.

**Reference**
- Proposal documents what was done (reality), not aspirations
- Uncommitted changes move to the new branch automatically
- PR title: use conventional commit format (`<type>: <meaningful description>`)
- PR body: if `.github/pull_request_template.md` exists, read it and fill in each section based on the change context
