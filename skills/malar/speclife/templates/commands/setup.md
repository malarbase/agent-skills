---
name: /speclife-setup
id: speclife-setup
category: SpecLife
description: Discover project configuration and populate openspec/speclife.md.
---
**Guardrails**
- Execute immediately—scan project to auto-detect configuration
- Don't overwrite existing user customizations in speclife.md
- Ask before creating publish workflow (don't auto-create)

**Steps**
1. Read existing `openspec/speclife.md` if present.
2. Detect build system: package.json (Node), Cargo.toml (Rust), go.mod (Go), pyproject.toml (Python), etc.
3. Extract commands: test, build, lint from detected system (e.g., `npm test`, `cargo test`).
4. Detect publish config: registry (npm/crates.io/PyPI), required secret, private flag.
5. Check `.github/workflows/` for existing release/publish workflows.
6. Identify context files: `openspec/project.md`, `openspec/AGENTS.md`, `README.md`.
7. Update `openspec/speclife.md` with discovered values.
8. If publishable and no publish workflow exists: ask user, create if agreed, remind about secrets.
9. Report: project type, detected commands, workflow status, what was configured.

**Reference**
- Publish workflow templates: Node.js, Rust, Python (standard patterns)
- Private packages (`"private": true`) skip publish workflow
- Go has no central registry—skip publish step
