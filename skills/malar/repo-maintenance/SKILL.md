---
name: repo-maintenance
description: How to maintain the mermaid-floorplan monorepo. Use when working with
  building, testing, grammar changes, image export, OpenSpec workflow, SpecLife commands,
  development servers, or troubleshooting build issues.
metadata:
  tags:
  - maintenance
  - monorepo
  - build
  - project-specific
  author: malar
  repo: github.com/malar/mermaid-floorplan
---

# Repo Maintenance

## Project Overview

A Mermaid-aligned floorplan DSL with:
- **floorplan-language**: Langium grammar + SVG rendering
- **floorplan-mcp-server**: AI integration via MCP
- **floorplan-viewer**: Web-based 3D viewer (Vite + Monaco)
- **floorplan-editor**: Interactive editor
- **floorplan-3d-core**: Three.js 3D rendering
- **floorplan-common**: Shared utilities

## Common Maintenance Tasks

### 1. After Grammar Changes

```bash
npm run langium:generate   # Regenerate parser
npm run build              # Rebuild all packages
npm test                   # Verify no regressions
```

### 2. Full Rebuild

```bash
make rebuild               # Clean + build + regenerate images
# or manually:
npm run clean && npm run build
```

### 3. Running Tests

```bash
npm test                   # All tests (language + mcp-server)
npm run --workspace floorplan-language test
npm run --workspace floorplan-mcp-server test
```

### 4. Development Servers

```bash
make dev          # Default viewer dev server
make viewer-dev   # 3D viewer
make editor-dev   # Interactive editor
make mcp-server   # MCP server for AI tools
```

### 5. Image Export

```bash
make export-images                    # SVG + PNG all floors
make export-3d                        # 3D isometric view
make export-annotated SHOW_AREA=1     # With area annotations
```

## OpenSpec Workflow

This project uses spec-driven development:

### Structure
```
openspec/
├── specs/       # Current capabilities (source of truth)
├── changes/     # Proposed changes (in progress)
└── commands/    # Automation scripts
```

### Key Commands
```bash
openspec list              # List active changes
openspec list --specs      # List capabilities
openspec show [item]       # View details
openspec validate [change] # Validate change
```

### Change Lifecycle
1. **Propose**: Create `changes/[verb]-[name]/` with `proposal.md`, `tasks.md`
2. **Implement**: Work through tasks, mark `[x]` when complete
3. **Archive**: Move to `changes/archive/YYYY-MM-DD-[name]/`

### Slash Commands Reference

The project uses slash commands to automate common workflows. These commands live in `.claude/commands/`.

#### OpenSpec Workflow Commands

| Command | When to Use | What It Does | Example |
|---------|-------------|--------------|---------|
| `/openspec:proposal` | Starting new feature/change | Scaffolds `proposal.md`, `tasks.md`, spec deltas, validates strictly | Creating a new capability |
| `/openspec:apply` | Implementing approved proposal | Reads proposal/tasks, implements changes sequentially, updates checklist | After proposal is approved |
| `/openspec:archive` | After deployment | Moves change to archive, updates main specs | When PR is merged |

#### SpecLife Workflow Commands

| Command | When to Use | What It Does | Example |
|---------|-------------|--------------|---------|
| `/speclife-start` | Beginning new work | Creates branch (spec/* or feat/*), optionally in worktree | New feature development |
| `/speclife-implement` | Implementing changes | Convenience proxy to `/openspec:apply` | Implementing tasks |
| `/speclife-ship` | Ready to review | Commits changes, validates, pushes, creates PR | Creating pull request |
| `/speclife-land` | After PR approval | Merges PR, cleans up branch, triggers auto-release | Merging approved work |
| `/speclife-sync` | Updating branch | Syncs current branch with latest main | Resolving conflicts |
| `/speclife-convert` | Switching workflows | Converts between branch-only and worktree modes | Parallel work needed |
| `/speclife-retrofit` | Formalizing ad-hoc work | Creates spec for untracked changes on main | Documenting emergency fixes |
| `/speclife-setup` | Initial setup | Discovers project config, populates `openspec/speclife.md` | First time setup |
| `/speclife-release` | Version bumps | Creates release with version bump (major versions) | Creating releases |

#### Command Categories

**Planning & Design**
- `/openspec:proposal` - Create new change proposal

**Implementation**
- `/speclife-start` - Begin work
- `/openspec:apply` or `/speclife-implement` - Build features
- `/speclife-sync` - Stay updated

**Review & Ship**
- `/speclife-ship` - Create PR
- `/speclife-land` - Merge PR

**Maintenance**
- `/openspec:archive` - Archive completed work
- `/speclife-retrofit` - Document ad-hoc changes
- `/speclife-release` - Create releases

#### Typical Workflow Example

```bash
# 1. Create proposal
/openspec:proposal
# Follow prompts to create change-id, scaffold files

# 2. Start work
/speclife-start
# Creates spec/add-my-feature branch

# 3. Implement
/speclife-implement
# Reads proposal, implements tasks

# 4. Ship for review
/speclife-ship
# Commits, validates, creates PR

# 5. After approval
/speclife-land
# Merges PR, cleans up

# 6. Archive
/openspec:archive
# Moves to archive/, updates specs
```

## Code Conventions

### Naming
- **Files**: kebab-case (`openai-chat.ts`)
- **Types/Interfaces**: PascalCase (`Floorplan`)
- **Functions/Variables**: camelCase

### TypeScript
- Strict mode enabled
- Use `.js` extensions in imports
- ESM modules throughout

### Testing
- Framework: Vitest
- Location: `[package]/test/`
- Focus on grammar parsing and AST structure

## Dependencies

### Node Version
- Required: >= 20.10.0 (Langium 4.x requirement)
- Pinned via Volta: 20.19.2

### Package Manager
- npm workspaces
- Run `npm install` at root

## Troubleshooting

### Parser Not Updating
```bash
npm run langium:generate   # Must regenerate after .langium changes
```

### Build Failures
```bash
npm run clean              # Clear artifacts
npm run langium:generate   # Regenerate parser
npm run build              # Rebuild
```

### Test Sandbox Issues
Some tests may fail in Cursor sandbox. Use proper permissions or run outside sandbox.

## Quick Reference

| Task | Command |
|------|---------|
| Install deps | `npm install` |
| Generate parser | `npm run langium:generate` |
| Build all | `npm run build` |
| Run tests | `npm test` |
| Start dev | `make dev` |
| Full rebuild | `make rebuild` |
| Export images | `make export-images` |
| List changes | `openspec list` |
