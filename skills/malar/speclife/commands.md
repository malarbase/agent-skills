# SpecLife Command Reference

Detailed steps for each agent-executed command. All commands execute immediately when invoked.

---

## /speclife start

Create a new branch for a change, optionally in a worktree for parallel work.

**Guardrails**
- Parse input for resume keywords (`resume`, `continue`, `pick up`, `implement <id>`) -- skip scaffolding
- Parse for mode keywords: "in a worktree" or "with worktree" -> worktree mode; otherwise -> branch-only (default)
- STOP after scaffolding -- do NOT auto-invoke `/openspec-apply`

**Steps**
1. **Resume?** If resume intent detected, verify `openspec/changes/<id>/` exists. Error with available proposals if not found.
2. **New change:** Derive kebab-case change-id from description (prefix: `add-`, `fix-`, `update-`, `remove-`, `refactor-`).
3. **Create workspace:**
   - Branch-only (default): `git checkout -b spec/<id>`
   - Worktree: run `scripts/worktree.sh create <id>` from skill directory
4. **Scaffold** (new changes only): Create `proposal.md` and `tasks.md` under `openspec/changes/<id>/` following `/openspec-proposal` format. Run `openspec validate <id> --strict`.
5. **Report:** change-id, branch/worktree created, work directory path. If worktree, emphasize: "All edits must happen in `worktrees/<id>/`".

**Notes**
- Branch name always `spec/<change-id>` regardless of mode
- Resume skips scaffolding; proceed directly to `/openspec-apply`
- Use `/speclife convert` to switch modes later

---

## /speclife ship

Commit changes, push to remote, and create a PR for review.

**Guardrails**
- Detect branch type: `spec/*` = full OpenSpec workflow, other non-main = ad-hoc, `main` = error
- STOP after PR created -- do NOT auto-invoke `/speclife land`
- Do NOT manually replicate `openspec` commands -- run them and report errors if they fail

**Steps**
1. **Spec branches:** Run `openspec validate <id>`, commit all changes, run `openspec archive <id> --yes`, commit the archive.
2. **Ad-hoc branches:** Infer commit type from branch name (`fix/*` -> `fix:`, `feat/*` -> `feat:`). Ask if ambiguous.
3. **Push:** `git push -u origin <branch>`.
4. **Create PR:** `gh pr create --title "<type>: <description>" --body "<body>" --base main`. Add `--draft` if requested.
5. **Report:** Commits made, branch pushed, PR URL. Suggest: `/speclife land` after approval.

**Notes**
- Commit type inference: fix/bugfix/hotfix -> `fix:`, feat/feature -> `feat:`, docs -> `docs:`, refactor -> `refactor:`, chore -> `chore:`
- If PR already exists, push updates it automatically
- PR body: if `.github/pull_request_template.md` exists, read and fill in each section

---

## /speclife land

Merge an approved PR, clean up, and trigger auto-release.

**Guardrails**
- If PR number provided (#42), use it; if on feature branch, find its PR; if on main, prompt for PR number
- Confirm with user only for major (breaking) version bumps
- STOP after reporting -- GitHub Actions handles the actual release

**Steps**
1. **Find PR:** By branch (`gh pr view`) or by number (`gh pr view <num>`). Error if not found.
2. **Check readiness:** state=open, approved (or no reviews required), CI passing, no conflicts. Report issues and stop if not ready.
3. **Detect version bump** from PR title/commits: `feat:` -> minor, `fix:/docs:/chore:` -> patch, `feat!:/BREAKING CHANGE` -> major.
4. **Major bump:** Confirm with user. Abort if declined (suggest `/speclife release --major`).
5. **Bump version** in feature branch: for npm workspaces use `npm version <bump> -ws --no-git-tag-version --workspaces-update=false` to bump all packages. Commit `chore(release): v<version>`, push.
6. **Squash merge:** `gh pr merge --squash --delete-branch`.
7. **Update local:** `git checkout main && git pull`.
8. **Cleanup:** If spec branch with worktree, run `scripts/worktree.sh rm <id>`. Otherwise delete local branch.
9. **Report:** Version bumped, PR merged, cleanup done, GitHub Actions creating release.

**Notes**
- Version bump happens BEFORE merge so it's included in the squash commit
- Release workflow triggered by `chore(release): vX.X.X` commit message
- For npm workspaces: bump ALL package.json files (root + packages/*) or publish will fail

---

## /speclife release

Create a release with version bump (typically for major versions).

**Guardrails**
- Must be on `main` with clean working directory
- Use for major releases or when auto-release was skipped
- For patch/minor, prefer `/speclife land` which handles auto-release

**Steps**
1. **Check:** Must be on `main`. Error otherwise.
2. **Analyze commits** since last tag: `feat:` -> minor, `fix:` -> patch, `BREAKING CHANGE` or `!` -> major. Use explicit flag (`--major`/`--minor`/`--patch`) if provided.
3. **Calculate** new version from current `package.json`.
4. **Update version:** `npm version <bump> --no-git-tag-version` (and workspaces if monorepo).
5. **Update** CHANGELOG.md with grouped commits.
6. **Commit:** `git commit -am "chore(release): v<version>"`.
7. **Push:** `git push origin main`.
8. **Report:** Version bumped, pushed, GitHub Actions will create tag and release.

---

## /speclife sync

Update current branch with latest changes from main.

**Guardrails**
- Default to rebase unless `--merge` specified
- Require: not on main, working directory clean
- Guide user through conflict resolution if any

**Steps**
1. **Check:** Error if on main or uncommitted changes exist.
2. **Fetch:** `git fetch origin main`. If already up to date, report and exit.
3. **Rebase** (default) or merge: `git rebase origin/main` or `git merge origin/main`.
4. **Conflicts?** List conflicting files, explain resolution (edit files, `git add`, `git rebase --continue`), offer to help resolve.
5. **Push:** `git push --force-with-lease` (rebase) or `git push` (merge).
6. **Report:** Commits synced, conflicts resolved (if any), pushed.

---

## /speclife setup

Discover project configuration and populate `openspec/speclife.md`.

**Guardrails**
- Don't overwrite existing user customizations in speclife.md
- Ask before creating publish workflow (don't auto-create)

**Steps**
1. **Read** existing `openspec/speclife.md` if present.
2. **Detect** build system: package.json (Node), Cargo.toml (Rust), go.mod (Go), pyproject.toml (Python).
3. **Extract** commands: test, build, lint from detected system.
4. **Detect** publish config: registry, required secret, private flag.
5. **Check** `.github/workflows/` for existing release/publish workflows.
6. **Identify** context files: `openspec/project.md`, `openspec/AGENTS.md`, `README.md`.
7. **Update** `openspec/speclife.md` with discovered values.
8. **Publish workflow:** If publishable and no workflow exists, ask user, create if agreed, remind about secrets.
9. **Report:** Project type, detected commands, workflow status, what was configured.

**Notes**
- Private packages (`"private": true`) skip publish workflow
- Go has no central registry -- skip publish step

---

## /speclife implement

Convenience proxy to `/openspec-apply`.

**Steps**
1. Immediately invoke `/openspec-apply`. No additional behavior.

---

## /speclife convert

Switch between branch-only and worktree modes for current change.

**Guardrails**
- Parse "to worktree" or "to branch" from invocation
- Require: on a `spec/*` branch
- Handle uncommitted changes: prompt to commit or stash

**Steps (to worktree)**
1. Check: on `spec/*` branch in main repo, worktree doesn't already exist.
2. Commit any uncommitted changes (or ask user to stash).
3. Create worktree: `git worktree add worktrees/<change-id> <branch>`.
4. Return main repo to main: `git checkout main`.
5. Report: worktree created, work in `worktrees/<change-id>/`.

**Steps (to branch)**
1. Check: in a worktree on `spec/*` branch.
2. Commit any uncommitted changes.
3. Go to main repo, checkout the branch: `git checkout <branch>`.
4. Remove worktree: `git worktree remove worktrees/<change-id>`.
5. Report: worktree removed, continue in main repo.

**Notes**
- Converts preserve all commits and history
- Branch name stays the same; spec files work in both modes

---

## /speclife retrofit

Formalize ad-hoc changes on main into a spec-tracked change.

**Guardrails**
- Must be on `main` with uncommitted changes or unpushed commits
- Generate spec from actual changes (retrospective), not speculation
- STOP after PR created -- do NOT auto-invoke `/speclife land`
- Do NOT manually replicate `openspec archive` -- run the command

**Steps**
1. **Detect changes:** `git status --short` and `git log origin/main..HEAD --oneline`. Error if nothing.
2. **Analyze** diffs to understand what was done. Infer change type (feat, fix, refactor, docs).
3. **Derive** change-id: kebab-case with verb prefix.
4. **Review context:** `openspec list --specs`, read `openspec/project.md`.
5. **Create retrospective spec:** `proposal.md` (past tense), `tasks.md` (all `[x]` completed), spec deltas if applicable.
6. **Validate and branch:** `openspec validate <id>`, `git checkout -b spec/<id>`.
7. **Commit, archive, push, PR:** Commit changes, run `openspec archive <id> --yes`, commit archive, push, create PR.
8. **Report:** change-id, spec created, PR URL. Suggest: `/speclife land` after approval.

**Notes**
- Proposal documents what was done (reality), not aspirations
- Uncommitted changes move to the new branch automatically
- PR body: if `.github/pull_request_template.md` exists, fill in each section
