# Skill Curator Troubleshooting

Common issues and solutions when using the skill-curator.

## Working in agent-skills repo

**Scenario**: You're developing skills directly in the agent-skills repository.

**Behavior**: When running from within the agent-skills repo, the curator:
- Uses your local repo directly (no cloning to cache)
- Creates a branch from your current position
- Requires a clean working tree (no uncommitted changes)
- Returns to your original branch after pushing

**Benefits**:
- Review changes with `git diff` before shipping
- No cache directory management
- Faster workflow

**Tip**: Stage and commit any unrelated changes before running `ship`.

## Skill doesn't appear in PR

**Symptom**: You staged a skill, but it's not in the created PR.

**Causes**:
1. The skill already exists in the remote repo with identical content (no changes to commit)
2. Multiple skills were staged, but only one was ready/valid at ship time
3. The staging area was cleaned from a previous successful ship

**Resolution**:
```bash
# Check if skill is already in remote
gh pr view <PR#> --repo malarbase/agent-skills --json files --jq '.files[].path'

# Or check the remote branch directly
git ls-remote --heads origin | grep curate/

# Re-stage if needed
python scripts/curator.py import <source> --author <author>
python scripts/curator.py status
python scripts/curator.py ship
```

## Local changes not included

**Symptom**: Your local edits to a skill aren't appearing when staged.

**Causes**:
1. Changes are stashed: `git stash list`
2. Changes were committed but not in the working tree
3. Importing from wrong directory

**Resolution**:
```bash
# Check for stashed changes
git stash list
git stash show -p stash@{0}  # Preview stash contents
git stash pop               # Apply if needed

# Verify working directory changes
git status
git diff

# Re-import from correct location after applying changes
python scripts/curator.py import ./path/to/skill --author <author>
```

## Ship fails with "nothing to commit"

**Symptom**: `ship` command fails with git commit error.

**Causes**:
1. Skill already exists in remote with identical content
2. Changes were already merged to main

**Resolution**:
```bash
# Check if skill exists in remote
ls -la ~/.cache/skill-curator/repo/agent-skills/skills/<author>/<skill>/

# Compare local vs remote
diff -r /path/to/local/skill ~/.cache/skill-curator/repo/agent-skills/skills/<author>/<skill>/

# If truly different, try cleaning clone cache
rm -rf ~/.cache/skill-curator/repo
python scripts/curator.py import <source> --author <author>
python scripts/curator.py ship
```

## Working directory has uncommitted changes

**Symptom**: Ship fails with "Working directory has uncommitted changes."

**Causes**:
When running from within the agent-skills repo, the curator requires a clean working tree.

**Resolution**:
```bash
# Option 1: Commit the changes
git add .
git commit -m "your message"

# Option 2: Stash the changes
git stash push -m "WIP changes"

# Then retry ship
python scripts/curator.py ship

# After shipping, restore stashed changes if needed
git stash pop
```

## Authentication failures

**Symptom**: Push or PR creation fails with authentication errors.

**Causes**:
1. Not authenticated with GitHub CLI
2. Insufficient permissions on the repository

**Resolution**:
```bash
# Check authentication status
gh auth status

# Login if needed
gh auth login

# Verify you have push access
gh api repos/malarbase/agent-skills --jq '.permissions'

# If no push access, the curator will automatically fork and create PR from fork
```
