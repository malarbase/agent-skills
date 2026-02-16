# Command Reference

Detailed documentation for each `curator.py` subcommand.

## import

Fetch a skill from a source and stage it locally for review.

```bash
python scripts/curator.py import <source> [--author <author>] [--ref <ref>]
```

**Steps performed:**
1. Parse source (GitHub URL, `owner/repo:path`, or local path)
2. Fetch skill to a temp directory
3. Validate basic structure (SKILL.md exists, has frontmatter)
4. Copy to staging: `~/.cache/skill-curator/staging/<author>/<skill-name>/`
5. Report what was staged

**Arguments:**
- `source` — GitHub URL, `owner/repo:path/to/skill`, or local filesystem path
- `--author` — Author namespace in the target repo (default: inferred from source or `$USER`)
- `--ref` — Git ref for GitHub sources (default: `main`)

**Examples:**
```bash
# From GitHub URL
curator.py import https://github.com/user/repo/tree/main/skills/my-skill --author malar

# From repo:path shorthand
curator.py import user/repo:skills/my-skill --author malar

# From local directory
curator.py import ./my-local-skill --author malar
```

---

## validate

Check a skill's structure and metadata for correctness.

```bash
python scripts/curator.py validate [<path>]
```

**Steps performed:**
1. If no path given, validate all staged skills
2. Check SKILL.md exists
3. Parse and validate frontmatter (`name`, `description` required)
4. Check SKILL.md is under 500 lines
5. Scan for sensitive files (`.env`, `credentials.*`, `*.key`)
6. Report errors or "OK"

**Arguments:**
- `path` — Optional path to a specific skill directory. If omitted, validates all staged skills.

---

## ship

Create a branch, commit staged skills, push, and open a PR.

```bash
python scripts/curator.py ship [--draft] [--dry-run]
```

**Steps performed:**
1. Verify staged skills exist and pass validation
2. Clone target repo (sparse checkout for speed)
3. Create branch: `curate/add-<skill-name>` or `curate/add-batch-<timestamp>`
4. Copy staged skills to `skills/<author>/<skill-name>/`
5. Commit with conventional message: `feat(skills): add <author>/<skill-name>`
6. Check push access; fork if needed
7. Push branch
8. Create PR via `gh pr create`
9. Clean up local clone and staging
10. Print PR URL

**Options:**
- `--draft` — Create a draft PR
- `--dry-run` — Run through steps without pushing or creating PR

---

## land

Merge an approved PR and update the inventory.

```bash
python scripts/curator.py land <pr-number>
```

**Steps performed:**
1. Merge PR via `gh pr merge --squash <pr-number>`
2. Clone/pull updated main
3. Run inventory scan and update README.md
4. If README changed, commit and push: `chore(inventory): update skills inventory`
5. Report success

**Arguments:**
- `pr-number` — The GitHub PR number to merge

---

## update

Update an existing skill in the repo from a new source.

```bash
python scripts/curator.py update <skill> --from <source> [--author <author>]
```

**Steps performed:**
1. Parse `<skill>` as `<author>/<skill-name>` or just `<skill-name>` (uses `--author`)
2. Verify the skill exists in the target repo
3. Import updated version to staging
4. Stage as replacement (overwrites existing staging for that skill)
5. Report ready for `ship`

**Arguments:**
- `skill` — Skill identifier, e.g. `malar/my-skill` or just `my-skill`
- `--from` — Source to fetch the update from (same formats as `import`)
- `--author` — Author namespace (if not included in `skill`)

---

## list

Show the current skills inventory from the remote repo.

```bash
python scripts/curator.py list [--author <author>]
```

**Steps performed:**
1. Fetch directory listing from GitHub API: `repos/malarbase/agent-skills/contents/skills`
2. For each author, fetch skill directories
3. Print formatted inventory table

**Options:**
- `--author` — Filter to a specific author

---

## status

Show skills currently staged and ready to ship.

```bash
python scripts/curator.py status
```

**Steps performed:**
1. Scan staging directory (`~/.cache/skill-curator/staging/`)
2. For each staged skill, show: author, name, validation status
3. Print summary

---

## Branch and Commit Conventions

| Scenario | Branch | Commit |
|----------|--------|--------|
| New skill | `curate/add-<skill-name>` | `feat(skills): add <author>/<skill-name>` |
| Update skill | `curate/update-<skill-name>` | `fix(skills): update <author>/<skill-name>` |
| Batch add | `curate/add-batch-<timestamp>` | `feat(skills): add <count> skills` |
| Inventory update | (direct to main) | `chore(inventory): update skills inventory` |
