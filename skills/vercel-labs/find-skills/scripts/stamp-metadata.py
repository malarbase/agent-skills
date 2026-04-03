#!/usr/bin/env python3
"""Stamp missing metadata fields into an installed skill's SKILL.md.

Only populates fields that are absent -- never overwrites existing values.
Also migrates any top-level author/repo/tags fields into the metadata: block,
per the agentskills.io frontmatter spec.

Usage:
    python stamp-metadata.py <skill-path> [--author <author>] [--repo <repo>] [--tags <tag> ...]

Examples:
    python stamp-metadata.py ~/.claude/skills/my-skill --author myorg --repo github.com/myorg/skills
    python stamp-metadata.py ~/.claude/skills/my-skill --author myorg --tags api integration
"""

from __future__ import annotations

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Fields sometimes placed at the top level that belong under metadata:
_FIELDS_TO_MIGRATE = {"author", "repo", "tags", "displayName", "version"}


def stamp_metadata(
    path: str,
    author: str,
    source_repo: str | None = None,
    tags: list[str] | None = None,
) -> bool:
    """Stamp metadata into SKILL.md. Returns True if the file was modified."""
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        print(f"Error: SKILL.md not found in {path}", file=sys.stderr)
        return False

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        print(f"Warning: no YAML frontmatter found in {skill_md}", file=sys.stderr)
        return False

    try:
        fm = yaml.safe_load(match.group(1))
        if not isinstance(fm, dict):
            print(f"Warning: frontmatter is not a mapping in {skill_md}", file=sys.stderr)
            return False
    except yaml.YAMLError as exc:
        print(f"Warning: could not parse frontmatter in {skill_md}: {exc}", file=sys.stderr)
        return False

    body = match.group(2)
    original_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Migrate top-level fields into metadata:
    metadata: dict = fm.get("metadata", {}) or {}
    for field in _FIELDS_TO_MIGRATE:
        if field in fm:
            metadata[field] = fm.pop(field)

    # Populate only missing fields
    if "author" not in metadata:
        metadata["author"] = author
    if source_repo and "repo" not in metadata:
        metadata["repo"] = source_repo
    if "tags" not in metadata:
        if tags:
            metadata["tags"] = tags
        else:
            # Derive minimal tags from the skill directory name
            skill_name = os.path.basename(path.rstrip("/"))
            parts = skill_name.split("-")
            derived = parts[:3] if len(parts) > 3 else parts
            seen: set[str] = set()
            unique: list[str] = []
            for t in derived:
                if t not in seen:
                    seen.add(t)
                    unique.append(t)
            metadata["tags"] = unique

    fm["metadata"] = metadata

    new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    if new_fm == original_fm:
        return False  # nothing changed

    fm_text = new_fm.rstrip()
    new_content = f"---\n{fm_text}\n---\n{body}"

    with open(skill_md, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Stamp missing metadata into an installed skill's SKILL.md.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("path", help="Path to the installed skill directory")
    parser.add_argument("--author", help="Author to stamp (e.g. github username or org)")
    parser.add_argument("--repo", dest="source_repo", help="Source repo (e.g. github.com/owner/repo)")
    parser.add_argument("--tags", nargs="+", help="Tags to stamp (derived from skill name if omitted)")

    args = parser.parse_args(argv)

    # Resolve author: flag > $USER > "unknown"
    author = args.author or os.environ.get("USER") or "unknown"

    modified = stamp_metadata(
        path=args.path,
        author=author,
        source_repo=args.source_repo,
        tags=args.tags,
    )

    if modified:
        print(f"Stamped metadata in {os.path.join(args.path, 'SKILL.md')}")
    else:
        print(f"No changes needed in {os.path.join(args.path, 'SKILL.md')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
