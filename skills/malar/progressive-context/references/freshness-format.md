# Freshness Marker Format

## Syntax

A freshness marker is an HTML comment embedded in a markdown context file:

```markdown
<!-- freshness
watches_hash: a3f2b1c
last_verified: 2026-02-16
watches:
  - src/renderer/**
  - src/styles.ts
-->
```

The marker must appear anywhere in the file. Convention is to place it at the
**end** of the file so it doesn't interfere with the primary content.

## Fields

### `watches_hash` (required)

A 7-character git hash representing the current state of all watched files.

**How it's computed (content-aware):**

1. Run `git ls-files -s` to get all tracked files with their blob hashes
2. Filter by matching file paths against each watch glob using `fnmatch`
3. Sort matched entries by file path for determinism
4. Build a string of `"<blob_hash> <filepath>\n"` lines
5. Pipe through `git hash-object --stdin`
6. Truncate to the first 7 characters

The hash changes when:
- A watched file's **content** is modified (blob hash changes)
- A watched file is added, removed, or renamed
- The set of files matching the globs changes

### `last_verified` (required)

ISO 8601 date (`YYYY-MM-DD`) of when a human or agent last reviewed the context
file and confirmed it accurately reflects the source code.

Updated automatically by `context_update_hash.py`.

### `watches` (required)

A YAML-style list of glob patterns. Each pattern is matched against file paths
relative to the git root using Python's `fnmatch`.

**Important:** `fnmatch` does not treat `/` as special. Both `*` and `**` match
across directory boundaries. We standardize on `**` by convention so that intent
is clear if the matching engine ever changes.

Common patterns:

| Pattern | Matches |
|---------|---------|
| `src/renderer/**` | All files under src/renderer/ (any depth) |
| `src/renderer/*.ts` | TypeScript files directly in src/renderer/ |
| `*.config.js` | Config files in root |
| `my-pkg/src/**/*.langium` | All .langium files under my-pkg/src/ |

## Placement

Recommended: append to the end of the file.

```markdown
# My Context Rule

This rule describes the rendering pipeline...

(content here)

<!-- freshness
watches_hash: a3f2b1c
last_verified: 2026-02-16
watches:
  - src/renderer/**
  - src/styles.ts
-->
```

## Lifecycle

1. **Bootstrap** — `context_bootstrap.py` adds the initial marker
2. **Detect** — Git hooks call `context_check_watches.py` on commit
3. **Audit** — `context_audit.py` produces a full freshness report
4. **Stamp** — After human review, `context_update_hash.py` updates the hash
