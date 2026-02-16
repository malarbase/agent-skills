# Init Reference

Details on project setup via `scripts/init.sh` and the files it creates.

## What `scripts/init.sh` Does

1. Creates `.specliferc.yaml` with project settings
2. Installs slash commands to `openspec/commands/speclife/`
3. Creates `openspec/speclife.md` (AI context template)
4. Creates `.github/workflows/speclife-release.yml`
5. Configures editor symlinks/settings (auto-detects installed editors)
6. Initializes `openspec/` directory structure if missing

Run from project root: `bash ~/.cursor/skills/speclife/scripts/init.sh`

## Editor Support

| Editor | Command Directory | Notes |
|--------|-------------------|-------|
| Cursor | `.cursor/commands/speclife/` | Symlink to `openspec/commands/speclife/`, dash-prefix (`-start.md`) |
| Claude Code | `.claude/commands/speclife/` | Symlink to `openspec/commands/speclife/` |
| OpenCode | `.opencode/commands/speclife/` | Symlink to `openspec/commands/speclife/` |
| VS Code | `.vscode/settings.json` + `tasks.json` | Task-based integration |
| Windsurf | `.windsurf/commands/speclife/` | Symlink to `openspec/commands/speclife/` |
| Gemini | `.gemini/commands/speclife/` | Symlink to `openspec/commands/speclife/` |
| Qwen | `.qwen/commands/speclife/` | Symlink, dash-prefix (`-start.md`) |
| Antigravity | `.agent/workflows/speclife-*.md` | Flat files (no subdirectory), one per command |

Commands are canonical in `openspec/commands/speclife/`; editor directories are symlinks (or copies for editors that don't support symlinks).

## `.specliferc.yaml` Format

```yaml
specDir: openspec           # Directory containing specs and commands
git:
  baseBranch: main          # Base branch for PRs (main, master, develop)
  branchPrefix: spec/       # Prefix for change branches
  worktreeDir: worktrees    # Directory for git worktrees
```

All fields have sensible defaults. The agent reads this at the start of each command.

## `openspec/speclife.md` Format

AI-readable project context, populated by `/speclife setup`:

```markdown
# SpecLife Configuration

## Commands
- **Test:** `npm test`
- **Build:** `npm run build`
- **Lint:** `npm run lint`

## Release Policy
- **Auto-release:** patch and minor versions
- **Manual release:** major versions (breaking changes)

## Context Files
When implementing changes, always read:
- `openspec/project.md` - project context and conventions
- `openspec/AGENTS.md` - agent guidelines
```

The **Commands** section is the most important -- it tells the agent how to test/build/lint during implementation and shipping.

## GitHub Actions Release Workflow

Created at `.github/workflows/speclife-release.yml`. Triggered by commits matching `chore(release): vX.X.X`:

1. Extracts version from commit message
2. Creates git tag `vX.X.X`
3. Creates GitHub Release with auto-generated notes
4. Optionally runs publish steps (npm, crates.io, PyPI)

The workflow is triggered on push to main, filtered by commit message pattern.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `openspec/` directory missing | Run `scripts/init.sh` or create manually |
| Editor commands not appearing | Check symlink: `ls -la .cursor/commands/speclife/` |
| Release not triggering | Verify commit message matches exactly: `chore(release): vX.X.X` |
| Slash commands outdated | Re-run `scripts/init.sh` to refresh |
| `.specliferc.yaml` missing | Run `scripts/init.sh` or create manually with defaults above |
| Wrong base branch | Edit `.specliferc.yaml` -> `git.baseBranch` |
