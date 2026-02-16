---
name: maintain-skills
description: Maintain Skills and Agents
metadata:
  tags:
  - skills
  - maintenance
  - inventory
  - meta
  author: malar
  repo: github.com/malar/skills
---

# Maintain Skills

Audit, inventory, and maintain Claude Code skills and agents.

## List Skills by Author

Extract and categorize all installed skills by their `author` metadata field.

```bash
# Scan all SKILL.md files and extract frontmatter
for skill_dir in ~/.claude/skills/*/ .claude/skills/*/; do
  if [ -f "${skill_dir}SKILL.md" ]; then
    name=$(basename "$skill_dir")
    author=$(sed -n '/^---$/,/^---$/p' "${skill_dir}SKILL.md" | grep "^author:" | cut -d: -f2 | tr -d ' ')
    repo=$(sed -n '/^---$/,/^---$/p' "${skill_dir}SKILL.md" | grep "^repo:" | cut -d: -f2- | tr -d ' ')
    tags=$(sed -n '/^---$/,/^---$/p' "${skill_dir}SKILL.md" | grep "^tags:" | cut -d: -f2-)
    echo "$author|$name|$repo|$tags"
  fi
done | sort | column -t -s'|'
```

## Output Format

When listing skills, format output grouped by author:

```
## Skills by Author

### anthropic (3 skills)
- doc-coauthoring - github.com/anthropics/skills
- frontend-design - github.com/anthropics/skills
- skill-creator - github.com/anthropics/skills

### malar (4 skills)
- 3d-rendering - github.com/malar/mermaid-floorplan
- claude-skill-installer - github.com/malar/skills
- mcp-integration - github.com/malar/mermaid-floorplan
- repo-maintenance - github.com/malar/mermaid-floorplan

### obra (14 skills)
- brainstorming - github.com/obra/superpowers
- ...

### (no author) (N skills)
- skill-without-metadata
```

## Audit Skills

Check for skills missing metadata:

```bash
for skill_dir in ~/.claude/skills/*/ .claude/skills/*/; do
  if [ -f "${skill_dir}SKILL.md" ]; then
    name=$(basename "$skill_dir")
    frontmatter=$(sed -n '/^---$/,/^---$/p' "${skill_dir}SKILL.md")

    # Check for missing fields
    missing=""
    echo "$frontmatter" | grep -q "^author:" || missing="$missing author"
    echo "$frontmatter" | grep -q "^repo:" || missing="$missing repo"
    echo "$frontmatter" | grep -q "^tags:" || missing="$missing tags"

    if [ -n "$missing" ]; then
      echo "$name: missing$missing"
    fi
  fi
done
```

## Add Missing Metadata

When skills are missing author metadata, prompt user for values and update the frontmatter:

1. List skills missing metadata
2. For each, ask user for: author, repo, tags
3. Update the SKILL.md frontmatter

## Skill Locations

- **Global skills**: `~/.claude/skills/` - available in all projects
- **Project skills**: `.claude/skills/` - available only in current project
