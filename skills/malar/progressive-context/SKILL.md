---
name: progressive-context
description: Manages AI context files (CLAUDE.md, AGENTS.md, .cursor/rules/, skills)
  with progressive disclosure layers and content-aware freshness tracking. Bootstraps
  context structure in new projects, audits existing context for staleness via git
  hooks, and stamps files after review. Use when setting up context management, auditing
  freshness, restructuring CLAUDE.md for progressive disclosure, or when git hooks
  report stale context. Triggers on "context audit", "setup context", "progressive
  disclosure", "slim CLAUDE.md", "freshness check", "context freshness".
metadata:
  author: malar
  tags:
  - context
  - freshness
  - progressive-disclosure
  - agent-context
---

# Progressive Context

Manage AI context files with progressive disclosure and automatic freshness
tracking. Context files watch the source code they document — when source
changes, stale context surfaces automatically via git hooks.

## Concepts

### Progressive Disclosure

Not every context file belongs in the root CLAUDE.md. Organize into layers:

| Layer | Example Files | When Loaded |
|-------|--------------|-------------|
| **Always** | `CLAUDE.md`, `AGENTS.md` | Every conversation |
| **Path-triggered** | `.cursor/rules/*.md` | When editing matched files |
| **On-demand** | `.cursor/skills/*/SKILL.md` | When skill is invoked |
| **Reference** | `docs/context/*.md` | When agent reads explicitly |

### Freshness Markers

Each context file embeds an HTML comment tracking what it documents:

```html
<!-- freshness
watches_hash: a3f2b1c
last_verified: 2026-02-16
watches:
  - src/renderer/**
  - src/styles.ts
-->
```

The hash is **content-aware** — computed from git blob hashes of watched files
via `git ls-files -s`. It changes when file content changes, not just when files
are added or removed.

See [references/freshness-format.md](references/freshness-format.md) for the
full format specification.

---

## Gotchas

Hard-won lessons. Read before running any workflow.

### 1. Always copy `context_lib.py`

All `context_*.py` scripts import from `context_lib.py`. If you copy scripts to
a project without it, they will fail with `ModuleNotFoundError`.

```bash
# WRONG — missing shared module
cp scripts/context_audit.py project/scripts/

# RIGHT — always include context_lib.py
cp scripts/context_lib.py scripts/context_*.py project/scripts/
```

### 2. Watch globs must match real directory names

Monorepos often prefix package directories (e.g., `floorplan-language/` not
`language/`). If your Context Index or watch globs use the wrong name,
routing and freshness tracking silently fail.

**Verify before writing globs:**
```bash
ls -d */   # Check actual directory names on disk
```

### 3. `fnmatch` treats `*` and `**` identically

Python's `fnmatch` does not treat `/` as special — `*` matches across directory
boundaries just like `**`. We standardize on `**` by convention so intent is
clear and code remains compatible if the matching engine ever changes.

```
floorplan-app/src/routes/**    # GOOD — convention says "recursive"
floorplan-app/src/routes/*     # WORKS but misleading
```

### 4. Keep CLAUDE.md and AGENTS.md in sync

If both files exist with the same content, edits to one must be mirrored in the
other. They serve different agent systems (Claude Code vs Cursor/other agents).

### 5. Hook scripts must handle special filenames

Use NUL-delimited output (`-z`) with `xargs -0` to handle filenames containing
spaces or special characters:

```sh
# WRONG — breaks on "my file.ts"
git diff-tree --name-only -r HEAD | xargs python3 script.py

# RIGHT
git diff-tree --name-only -r HEAD -z | xargs -0 python3 script.py
```

---

## Workflows

### Workflow A: `setup` — Bootstrap in a New Project

1. **Scan existing context files:**
   ```bash
   python3 scripts/context_bootstrap.py --scan .
   ```

2. **Analyze project structure** — determine which source directories each
   context file documents. Propose watch globs. **Verify directory names** with
   `ls -d */` before writing globs (see Gotcha #2).

3. **Propose disclosure layers** — categorize context files into the four layers.
   Suggest moving verbose sections from CLAUDE.md into reference files.

4. **Copy scripts to the project** (include `context_lib.py`):
   ```bash
   cp scripts/context_lib.py scripts/context_*.py scripts/install_hooks.py project/scripts/
   chmod +x project/scripts/context_*.py project/scripts/install_hooks.py
   ```

5. **Add freshness markers:**
   ```bash
   python3 scripts/context_bootstrap.py <context-file> "my-pkg/src/**" "other/glob.ts"
   ```

6. **Build a Context Index** in CLAUDE.md mapping directory globs to context
   files. This enables `context_for.py` routing.

   ```markdown
   ## Context Index

   | Directory | Context File |
   |-----------|-------------|
   | `my-app-language/**` | `docs/context/language.md` |
   | `my-app-server/**` | `docs/context/server.md` |
   ```

7. **Install git hooks:**
   ```bash
   python3 scripts/install_hooks.py
   ```

8. **Run initial audit** to confirm everything is `OK`:
   ```bash
   python3 scripts/context_audit.py
   ```

9. **Report token savings** — compare original monolithic CLAUDE.md token count
   against the new always-loaded subset.

### Workflow B: `audit` — Check Context Freshness

1. Run the audit:
   ```bash
   python3 scripts/context_audit.py
   ```

2. For each `STALE` file: open the context file and its watched source, determine
   what changed, update the prose if needed.

3. After reviewing, stamp the file (Workflow C).

### Workflow C: `verify-and-stamp` — Update Freshness After Review

1. Verify the context file is accurate (read it, compare with source).

2. Stamp it:
   ```bash
   python3 scripts/context_update_hash.py <context-file>
   ```

3. Commit the updated hash so future audits use the new baseline.

### Workflow D: `teardown` — Remove from a Project

1. **Remove git hooks:**
   ```bash
   python3 scripts/install_hooks.py --uninstall
   ```

2. **Strip freshness markers** (optional — markers are inert HTML comments):
   ```bash
   python3 -c "
   import re, pathlib, glob as g
   for f in g.glob('docs/context/*.md') + g.glob('.cursor/rules/*.md'):
       p = pathlib.Path(f)
       text = p.read_text()
       cleaned = re.sub(r'\n?<!-- freshness\n.*?-->\n?', '', text, flags=re.DOTALL)
       if cleaned != text:
           p.write_text(cleaned)
           print(f'Stripped marker from {f}')
   "
   ```

3. **Remove context scripts:**
   ```bash
   rm -f scripts/context_lib.py scripts/context_audit.py \
         scripts/context_update_hash.py scripts/context_bootstrap.py \
         scripts/context_check_watches.py scripts/context_for.py \
         scripts/install_hooks.py
   ```

4. **Remove the Context Index** section from CLAUDE.md and AGENTS.md if present.

---

## Script Reference

| Script | Purpose |
|--------|---------|
| `context_lib.py` | Shared module — all scripts import from this |
| `context_audit.py` | Scan all context files, report stale vs current |
| `context_update_hash.py` | Stamp a file's freshness hash after review |
| `context_bootstrap.py` | Add freshness markers to new or existing files |
| `context_check_watches.py` | Fast check if changed files affect any context (for hooks) |
| `context_for.py` | Look up which context file covers a given source file |
| `install_hooks.py` | Install/uninstall git hooks for automatic checks |

## Additional Resources

- For the freshness marker format spec, see [references/freshness-format.md](references/freshness-format.md)
