#!/usr/bin/env python3
"""Skill validation and metadata utilities."""

from __future__ import annotations

import os
import re

SENSITIVE_PATTERNS = [".env", "credentials", ".key", ".pem", ".p12", ".secret"]
MAX_SKILL_LINES = 500
REQUIRED_FIELDS = ["name", "description"]


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML frontmatter from markdown text as a flat dict."""
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def validate_skill(path: str) -> list[str]:
    """Return a list of validation errors. Empty list means valid."""
    errors: list[str] = []

    if not os.path.isdir(path):
        return [f"Not a directory: {path}"]

    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        errors.append("SKILL.md not found")
        return errors

    with open(skill_md, "r") as f:
        content = f.read()

    line_count = content.count("\n") + 1
    if line_count > MAX_SKILL_LINES:
        errors.append(f"SKILL.md is {line_count} lines (max {MAX_SKILL_LINES})")

    fm = parse_frontmatter(content)
    if not fm:
        errors.append("No YAML frontmatter found")
    else:
        for field in REQUIRED_FIELDS:
            if not fm.get(field):
                errors.append(f"Missing required frontmatter field: {field}")

        name = fm.get("name", "")
        if name and not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
            errors.append(f"Invalid skill name '{name}': use lowercase letters, numbers, hyphens")
        if name and len(name) > 64:
            errors.append(f"Skill name too long ({len(name)} chars, max 64)")

        desc = fm.get("description", "")
        if desc and len(desc) > 1024:
            errors.append(f"Description too long ({len(desc)} chars, max 1024)")

    for root, _dirs, files in os.walk(path):
        for fname in files:
            for pattern in SENSITIVE_PATTERNS:
                if pattern in fname.lower():
                    rel = os.path.relpath(os.path.join(root, fname), path)
                    errors.append(f"Potentially sensitive file: {rel}")

    return errors


def extract_metadata(path: str) -> dict[str, str]:
    """Parse SKILL.md frontmatter and return metadata dict."""
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        return {}
    with open(skill_md, "r") as f:
        return parse_frontmatter(f.read())


def ensure_metadata(path: str, author: str, source_repo: str | None = None) -> None:
    """Add or update author/repo fields in SKILL.md frontmatter."""
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        return

    with open(skill_md, "r") as f:
        content = f.read()

    fm = parse_frontmatter(content)
    updates: dict[str, str] = {}
    if not fm.get("author"):
        updates["author"] = author
    if source_repo and not fm.get("repo"):
        updates["repo"] = source_repo

    if not updates:
        return

    match = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
    if not match:
        return

    fm_block = match.group(2)
    for key, value in updates.items():
        fm_block += f"\n{key}: {value}"

    new_content = match.group(1) + fm_block + match.group(3) + content[match.end():]
    with open(skill_md, "w") as f:
        f.write(new_content)
