#!/usr/bin/env python3
"""One-shot migration: move author/repo/tags from top-level frontmatter into metadata:.

Uses text surgery to preserve original formatting (no yaml.dump re-serialization).
For skills that lack author/repo/tags entirely, infers and adds them.
"""

from __future__ import annotations

import os
import re
import sys

import yaml


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

FIELDS_TO_MIGRATE = {"author", "repo", "tags"}


def _split_frontmatter(content: str) -> tuple[str, str] | None:
    """Split SKILL.md into (frontmatter_text, rest_including_closing_delim).

    Returns None if no valid frontmatter found.
    """
    match = re.match(r"^---\n(.*?)\n(---\n.*)", content, re.DOTALL)
    if not match:
        return None
    return match.group(1), match.group(2)


def _parse_fm_lines(fm_text: str) -> list[tuple[str | None, str]]:
    """Parse frontmatter into [(key_or_None, raw_line), ...].

    For lines like 'author: foo', key is 'author'.
    For continuation lines (indented under a key), key is None.
    For metadata: block lines, key is 'metadata' or None for children.
    """
    result: list[tuple[str | None, str]] = []
    for line in fm_text.splitlines():
        if line and not line[0].isspace() and ":" in line:
            key = line.split(":", 1)[0].strip()
            result.append((key, line))
        else:
            result.append((None, line))
    return result


def migrate_skill(skill_dir: str, dry_run: bool = False) -> bool:
    """Migrate a single skill's frontmatter. Returns True if changed."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return False

    with open(skill_md, "r") as f:
        content = f.read()

    split = _split_frontmatter(content)
    if split is None:
        print(f"  SKIP (no frontmatter): {skill_md}")
        return False

    fm_text, rest = split

    # Parse to understand structure
    try:
        fm_dict = yaml.safe_load(fm_text)
        if not isinstance(fm_dict, dict):
            print(f"  SKIP (frontmatter is not a dict): {skill_md}")
            return False
    except yaml.YAMLError:
        print(f"  SKIP (invalid YAML): {skill_md}")
        return False

    parsed = _parse_fm_lines(fm_text)
    changed = False

    # Phase 1: Extract lines for fields to migrate
    extracted_lines: dict[str, list[str]] = {}
    keep_lines: list[str] = []
    skip_continuation = False
    current_extract_key: str | None = None

    for key, line in parsed:
        if key in FIELDS_TO_MIGRATE:
            extracted_lines.setdefault(key, []).append(line)
            current_extract_key = key
            skip_continuation = True
            changed = True
        elif skip_continuation and key is None:
            # Continuation line of extracted field
            extracted_lines[current_extract_key].append(line)  # type: ignore[index]
        else:
            skip_continuation = False
            current_extract_key = None
            keep_lines.append(line)

    # Phase 2: Determine what to infer
    parts = skill_dir.replace(SKILLS_DIR + os.sep, "").split(os.sep)
    if len(parts) >= 2:
        dir_author = parts[0]
        skill_name = parts[1]
    else:
        dir_author = "unknown"
        skill_name = os.path.basename(skill_dir)

    existing_metadata = fm_dict.get("metadata", {}) or {}

    # Collect values from extracted fields
    extracted_author = fm_dict.get("author")
    extracted_repo = fm_dict.get("repo")
    extracted_tags = fm_dict.get("tags")

    inferred_lines: list[str] = []

    # Author
    if "author" not in extracted_lines and "author" not in existing_metadata:
        inferred_lines.append(f"  author: {dir_author}")
        changed = True
    # Repo
    if "repo" not in extracted_lines and "repo" not in existing_metadata:
        inferred_lines.append("  repo: github.com/malarbase/agent-skills")
        changed = True
    # Tags
    if "tags" not in extracted_lines and "tags" not in existing_metadata:
        name_parts = skill_name.split("-")
        tag_list = name_parts[:3] if len(name_parts) > 3 else name_parts
        tag_list.append("curated")
        seen: set[str] = set()
        unique: list[str] = []
        for t in tag_list:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        inferred_lines.append(f"  tags: [{', '.join(unique)}]")
        changed = True

    if not changed:
        return False

    # Phase 3: Build new metadata: block lines
    # Check if metadata: already exists in keep_lines
    has_metadata_key = any(k == "metadata" for k, _ in parsed if k is not None and k not in FIELDS_TO_MIGRATE)

    meta_block_lines: list[str] = []
    if not has_metadata_key:
        meta_block_lines.append("metadata:")

    # Add extracted fields (indented under metadata:)
    for field in ("author", "repo", "tags"):
        if field in extracted_lines:
            raw_lines = extracted_lines[field]
            # Re-indent: original is "field: value", needs to be "  field: value"
            for i, raw in enumerate(raw_lines):
                meta_block_lines.append(f"  {raw}")

    # Add inferred fields
    meta_block_lines.extend(inferred_lines)

    # Phase 4: Reassemble frontmatter
    if has_metadata_key:
        # Insert extracted + inferred lines at the end of the existing metadata: block
        # Find where metadata block ends in keep_lines
        new_keep: list[str] = []
        in_metadata = False
        metadata_done = False
        for line in keep_lines:
            if not metadata_done:
                if line.startswith("metadata:"):
                    in_metadata = True
                    new_keep.append(line)
                    continue
                elif in_metadata:
                    if line and line[0].isspace():
                        new_keep.append(line)
                        continue
                    else:
                        # End of metadata block; inject here
                        for ml in meta_block_lines:
                            new_keep.append(ml)
                        in_metadata = False
                        metadata_done = True
                        new_keep.append(line)
                        continue
            new_keep.append(line)

        if in_metadata and not metadata_done:
            # metadata was the last block
            for ml in meta_block_lines:
                new_keep.append(ml)

        keep_lines = new_keep
    else:
        # Append metadata block at end
        keep_lines.extend(meta_block_lines)

    new_fm_text = "\n".join(keep_lines)
    new_content = f"---\n{new_fm_text}\n{rest}"

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
