# Advanced Topics

Worktree environment bootstrapping, monorepo support, mode conversion, and global configuration.

## Worktree Environment Bootstrapping

When `scripts/worktree.sh create <id>` creates a worktree, it bootstraps the development environment based on the project type:

| Ecosystem | Strategy | Details |
|-----------|----------|---------|
| Node.js | Symlink `node_modules` | Links `node_modules/` from main repo into worktree. For monorepos, also links workspace `node_modules/`. |
| Python | Symlink `.venv` | Links `.venv/` from main repo into worktree. |
| Go | No-op | Uses global module cache (`GOMODCACHE`). |
| Rust | No-op | Uses global `target/` cache or workspace-level target. |

This avoids duplicating large dependency directories and ensures worktrees are immediately usable.

**Manual bootstrapping** (if scripts aren't available):
```bash
git worktree add worktrees/<id> spec/<id>
cd worktrees/<id>
ln -s ../../node_modules .    # Node.js
ln -s ../../.venv .           # Python
```

## Monorepo Support

The worktree scripts detect monorepo setups:

**Detection**: Checks for `workspaces` field in package.json, `pnpm-workspace.yaml`, `lerna.json`, or `yarn.lock` with workspaces.

**Auto-patching**: For TypeScript monorepos, patches `tsconfig.json` with `paths` entries pointing to local packages within the worktree (not back to the main repo). This ensures IDE resolution works correctly.

**npm workspace version bumps**: When `/speclife land` bumps versions, it uses:
```bash
npm version <bump> -ws --no-git-tag-version --workspaces-update=false
```
This bumps ALL package.json files (root + packages/*). Missing any causes npm publish 403 errors.

## Branch-Only vs Worktree Mode

| Aspect | Branch-only (default) | Worktree |
|--------|----------------------|----------|
| Working directory | Main repo | `worktrees/<change-id>/` |
| Parallel work | No (must switch branches) | Yes (each change has own directory) |
| Main branch | Changes with checkout | Stays on `main` |
| Setup | `git checkout -b spec/<id>` | `scripts/worktree.sh create <id>` |
| File paths | Use main repo paths | Must use `worktrees/<id>/` paths |
| Cleanup | Delete branch | Remove worktree + branch |

**When to use worktrees:**
- Working on multiple changes simultaneously
- Need main branch available for reference
- Long-running changes that shouldn't block other work

**When branch-only is fine:**
- Single change at a time
- Quick fixes
- Most common workflow

## Global Configuration

Global config lives at `~/.config/speclife/config.yaml`. The agent edits this file directly -- no CLI needed.

```yaml
# ~/.config/speclife/config.yaml
defaults:
  worktreeMode: false       # Default to branch-only
  autoRelease: true         # Auto-release on land (patch/minor)
  rebaseOnSync: true        # Default sync strategy
  squashOnLand: true        # Squash merge PRs
```

Project-level `.specliferc.yaml` overrides global config for project-specific settings (base branch, spec directory, etc.).

## /speclife convert Details

Converts between branch-only and worktree modes without losing any work.

**To worktree** (from branch-only):
1. Must be on `spec/*` branch in main repo
2. Commits or stashes uncommitted changes
3. Creates worktree: `git worktree add worktrees/<id> <branch>`
4. Returns main repo to `main`: `git checkout main`
5. All subsequent work happens in `worktrees/<id>/`

**To branch** (from worktree):
1. Must be in a worktree on `spec/*` branch
2. Commits uncommitted changes
3. In main repo: `git checkout <branch>`
4. Removes worktree: `git worktree remove worktrees/<id>`
5. All subsequent work happens in main repo

Both directions preserve full commit history. Branch name stays `spec/<id>` regardless of mode.

## /speclife retrofit Details

Formalizes changes that were made directly on `main` without a spec.

**When to use:** You (or someone) made changes on main that should go through review:
- Uncommitted changes in working directory
- Unpushed commits on main
- Both uncommitted and committed changes

**What it creates:**
- `proposal.md` in past tense (documents what was done, not what will be done)
- `tasks.md` with all tasks marked `[x]` (already completed)
- Spec deltas if applicable

**Key difference from `start`:** Retrofit is retrospective. The spec describes reality, not aspirations. The proposal should read as a summary of completed work.

**Flow:** Detect changes -> analyze diffs -> create spec -> validate -> branch -> commit + archive -> push -> create PR

Uncommitted changes automatically move to the new `spec/<id>` branch.
