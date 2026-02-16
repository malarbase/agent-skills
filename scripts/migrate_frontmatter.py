#!/usr/bin/env python3
"""One-shot migration: move author/repo/tags from top-level frontmatter into metadata:.

For skills that lack author/repo/tags entirely, infers them from the directory path.
"""

from __future__ import annotations

import os
import re
import sys

import yaml


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

FIELDS_TO_MIGRATE = {"author", "repo", "tags"}


def _extract_frontmatter(content: str) -> tuple[str, str]:
    """Split SKILL.md into (frontmatter_text, body). Raises if no frontmatter."""
    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        raise ValueError("No YAML frontmatter found")
    return match.group(1), match.group(2)


def _rebuild_file(fm_dict: dict, body: str) -> str:
    """Render frontmatter dict + body back into SKILL.md content."""
    fm_text = yaml.dump(fm_dict, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    return f"---\n{fm_text}\n---\n{body}"


def migrate_skill(skill_dir: str, dry_run: bool = False) -> bool:
    """Migrate a single skill's frontmatter. Returns True if changed."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return False

    with open(skill_md, "r") as f:
        content = f.read()

    fm_text, body = _extract_frontmatter(content)
    fm = yaml.safe_load(fm_text)
    if not isinstance(fm, dict):
        print(f"  SKIP (frontmatter is not a dict): {skill_md}")
        return False

    metadata = fm.get("metadata", {}) or {}
    changed = False

    for field in FIELDS_TO_MIGRATE:
        if field in fm:
            metadata[field] = fm.pop(field)
            changed = True

    # Infer missing fields from directory structure
    parts = skill_dir.replace(SKILLS_DIR + os.sep, "").split(os.sep)
    if len(parts) >= 2:
        dir_author = parts[0]
        skill_name = parts[1]
    else:
        dir_author = "unknown"
        skill_name = os.path.basename(skill_dir)

    if "author" not in metadata:
        metadata["author"] = dir_author
        changed = True
    if "repo" not in metadata:
        metadata["repo"] = "github.com/malarbase/agent-skills"
        changed = True
    if "tags" not in metadata:
        # Derive tags from skill name parts
        name_parts = skill_name.split("-")
        tags = name_parts[:3] if len(name_parts) > 3 else name_parts
        tags.append("curated")
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_tags: list[str] = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                unique_tags.append(t)
        metadata["tags"] = unique_tags
        changed = True

    if not changed:
        return False

    fm["metadata"] = metadata

    new_content = _rebuild_file(fm, body)

    if dry_run:
        print(f"  WOULD CHANGE: {skill_md}")
        return True

    with open(skill_md, "w") as f:
        f.write(new_content)
    return True


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN — no files will be modified\n")

    changed = 0
    total = 0

    for author in sorted(os.listdir(SKILLS_DIR)):
        author_dir = os.path.join(SKILLS_DIR, author)
        if not os.path.isdir(author_dir) or author.startswith("."):
            continue
        for skill_name in sorted(os.listdir(author_dir)):
            skill_dir = os.path.join(author_dir, skill_name)
            if not os.path.isdir(skill_dir) or skill_name.startswith("."):
                continue
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue

            total += 1
            rel = os.path.relpath(skill_dir, REPO_ROOT)
            if migrate_skill(skill_dir, dry_run=dry_run):
                changed += 1
                print(f"  MIGRATED: {rel}")
            else:
                print(f"  NO CHANGE: {rel}")

    print(f"\n{changed}/{total} skills migrated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
