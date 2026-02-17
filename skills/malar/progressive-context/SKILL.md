---
name: progressive-context
description: Manages AI context files (CLAUDE.md, AGENTS.md, .cursor/rules/, skills)
  with progressive disclosure layers and hash-based freshness tracking. Bootstraps
  context structure in new projects, audits existing context for staleness via git
  hooks, and stamps files after review. Use when setting up context management, auditing
  freshness, restructuring CLAUDE.md for progressive disclosure, or when git hooks
  report stale context. Triggers on "context audit", "setup context", "progressive
  disclosure", "slim CLAUDE.md", "freshness check", "context freshness".
metadata:
  author: malar
  tags:
  - progressive
  - context
  - curated
---

# Progressive Context

Manage AI context files (CLAUDE.md, AGENTS.md, .cursor/rules/, skill files) with
progressive disclosure and automatic freshness tracking. Context files watch the
source code they document — when source changes, stale context surfaces
automatically via git hooks.

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

When watched files change, the stored hash becomes stale. Git hooks surface
warnings at commit time so context stays current.

See `references/freshness-format.md` for the full format specification.

---

## Workflows

### Workflow A: `setup` — Bootstrap Progressive Context in a New Project

Use this when starting fresh or adding context management to an existing project.

**Steps:**

1. **Scan existing context files** — Run `context_bootstrap.py --scan` on the
   project root to find all `.md` files that could benefit from freshness tracking.

2. **Analyze project structure** — Examine the codebase to understand which source
   directories each context file documents. Propose watch globs for each.

3. **Propose disclosure layers** — Categorize context files into the four layers
   (Always / Path-triggered / On-demand / Reference). Suggest moving verbose
   sections from CLAUDE.md into path-triggered or reference files.

4. **Copy scripts to the project**:
   ```bash
   cp ~/.cursor/skills/progressive-context/scripts/*.py scripts/
   chmod +x scripts/context_*.py scripts/install_hooks.py
   ```

5. **Add freshness markers** — For each context file, run:
   ```bash
   python3 scripts/context_bootstrap.py <context-file> "src/relevant/**" "other/glob.ts"
   ```

6. **Build a Context Index** — Add a `## Context Index` section to CLAUDE.md
   mapping directory globs to context files. This enables `context_for.py` routing.

   **Important:** Globs must match real directory names on disk (run `ls -d */` to
   verify). Monorepos often use prefixed names (e.g., `my-app-language/` not
   `language/`). Wrong globs cause silent routing failures.

   ```markdown
   ## Context Index

   | Directory | Context File |
   |-----------|-------------|
   | `my-app-language/**` | `docs/context/language.md` |
   | `my-app-server/**` | `docs/context/server.md` |
   ```

7. **Install git hooks** — Run:
   ```bash
   python3 scripts/install_hooks.py
   ```

8. **Run initial audit** to confirm everything is `OK`:
   ```bash
   python3 scripts/context_audit.py
   ```

9. **Report token savings** — Compare the token count of the original monolithic
   CLAUDE.md against the new always-loaded subset. Report the reduction.

### Workflow B: `audit` — Check Context Freshness

Use this periodically or when context might be stale.

**Steps:**

1. Run the audit script:
   ```bash
   python3 scripts/context_audit.py
   ```

2. Read the report. For each `STALE` file:
   - Open the context file and its watched source files
   - Determine what changed and whether the context file needs updating
   - Update the prose if needed

3. After reviewing/updating, stamp the file (see Workflow C).

### Workflow C: `verify-and-stamp` — Update Freshness After Review

Use this after manually reviewing a context file to confirm it's current.

**Steps:**

1. Verify the context file is accurate (read it, compare with source).

2. Stamp it:
   ```bash
   python3 scripts/context_update_hash.py <context-file>
   ```

3. Commit the updated hash so future audits use the new baseline.

### Workflow D: `teardown` — Remove Progressive Context from a Project

Use this to cleanly remove everything the skill installed.

**Steps:**

1. **Remove git hooks**:
   ```bash
   python3 scripts/install_hooks.py --uninstall
   ```

2. **Strip freshness markers** from context files (optional — markers are inert
   HTML comments, safe to leave). Run this **before** deleting context files:
   ```bash
   python3 -c "
   import re, sys, pathlib, glob as g
   files = g.glob('docs/context/*.md') + g.glob('.cursor/rules/*.md')
   for f in files:
       p = pathlib.Path(f)
       text = p.read_text()
       cleaned = re.sub(r'\n?<!-- freshness\n.*?-->\n?', '', text, flags=re.DOTALL)
       if cleaned != text:
           p.write_text(cleaned)
           print(f'Stripped marker from {f}')
   "
   ```

3. **Remove context files** (optional — only if reverting to monolithic CLAUDE.md):
   ```bash
   rm -rf docs/context/
   # Remove only the rules this skill created (check contents first)
   ls .cursor/rules/
   rm -f .cursor/rules/<your-rule-files>.md
   ```

4. **Remove context scripts** from the project:
   ```bash
   rm -f scripts/context_audit.py scripts/context_update_hash.py \
         scripts/context_bootstrap.py scripts/context_check_watches.py \
         scripts/context_for.py scripts/install_hooks.py
   ```

5. **Remove the Context Index** section from CLAUDE.md and AGENTS.md if present.

The `docs/context/` files and `.cursor/rules/` are useful independently of the
freshness system — consider keeping them even after removing the automation.

---

## Quick Start for Any Agent

After running Workflow A (`setup`), scripts live in the project's `scripts/` directory.
If scripts haven't been copied yet, use the skill directory as the source.

```bash
# Use project-local scripts (preferred — after setup)
python3 scripts/context_audit.py
python3 scripts/context_update_hash.py .cursor/rules/my-rule.md
python3 scripts/context_for.py --auto

# Or use the skill directory directly (before setup / bootstrapping)
SKILL_DIR="$HOME/.cursor/skills/progressive-context/scripts"
python3 "$SKILL_DIR/context_bootstrap.py" --scan .
python3 "$SKILL_DIR/context_bootstrap.py" CLAUDE.md "src/**/*.ts" "package.json"
python3 "$SKILL_DIR/install_hooks.py"
```

---

## Script Reference

| Script | Purpose |
|--------|---------|
| `context_audit.py` | Scan all context files, report stale vs current |
| `context_update_hash.py` | Stamp a file's freshness hash after review |
| `context_bootstrap.py` | Add freshness markers to new or existing files |
| `context_check_watches.py` | Fast check if changed files affect any context (for hooks) |
| `context_for.py` | Look up which context file covers a given source file |
| `install_hooks.py` | Install (`--uninstall` to remove) git hooks for automatic checks |
