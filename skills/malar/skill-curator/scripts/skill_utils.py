#!/usr/bin/env python3
"""Skill validation and metadata utilities.

Validation delegates to repo_validate.py (same directory), which chains
quick_validate.py when available. Sensitive file scanning is a separate
curator-specific concern.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

import yaml

SENSITIVE_PATTERNS = [".env", "credentials", ".key", ".pem", ".p12", ".secret"]

FIELDS_TO_MIGRATE = {"author", "repo", "tags", "displayName", "version"}


def validate_skill(path: str, repo_root: str | None = None) -> list[str]:
    """Validate a skill via repo_validate.py. Returns list of errors."""
    errors: list[str] = []

    if not os.path.isdir(path):
        return [f"Not a directory: {path}"]

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repo_validate.py")
    cmd = [sys.executable, script, path]
    if repo_root:
        cmd.extend(["--repo-root", repo_root])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        output = result.stdout.strip()
        if output:
            errors.extend(output.splitlines())
        else:
            errors.append(result.stderr.strip() or "Validation failed")

    # Sensitive file scan (curator-specific)
    errors.extend(check_sensitive_files(path))

    return errors


def check_sensitive_files(path: str) -> list[str]:
    """Scan for potentially sensitive files. Returns list of warnings."""
    errors: list[str] = []
    for root, _dirs, files in os.walk(path):
        for fname in files:
            for pattern in SENSITIVE_PATTERNS:
                if pattern in fname.lower():
                    rel = os.path.relpath(os.path.join(root, fname), path)
                    errors.append(f"Potentially sensitive file: {rel}")
    return errors


def extract_metadata(path: str) -> dict[str, str]:
    """Parse SKILL.md frontmatter and return a flat metadata dict.

    Top-level fields (name, description, etc.) are returned directly.
    Fields under metadata: are flattened with their original keys.
    """
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        return {}

    with open(skill_md, "r") as f:
        content = f.read()

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    try:
        fm = yaml.safe_load(match.group(1))
        if not isinstance(fm, dict):
            return {}
    except yaml.YAMLError:
        return {}

    result: dict[str, str] = {}
    for key, value in fm.items():
        if key == "metadata" and isinstance(value, dict):
            for mk, mv in value.items():
                result[mk] = mv
        else:
            result[key] = value
    return result


def ensure_metadata(
    path: str,
    author: str,
    source_repo: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """Ensure metadata.author, metadata.repo, metadata.tags are present in SKILL.md.

    Also migrates any top-level author/repo/tags into metadata: block.
    """
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        return

    with open(skill_md, "r") as f:
        content = f.read()

    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        return

    try:
        fm = yaml.safe_load(match.group(1))
        if not isinstance(fm, dict):
            return
    except yaml.YAMLError:
        return

    body = match.group(2)

    # Migrate top-level fields into metadata
    metadata = fm.get("metadata", {}) or {}
    for field in FIELDS_TO_MIGRATE:
        if field in fm:
            metadata[field] = fm.pop(field)

    # Populate missing fields
    if "author" not in metadata:
        metadata["author"] = author
    if source_repo and "repo" not in metadata:
        metadata["repo"] = source_repo
    if "tags" not in metadata:
        if tags:
            metadata["tags"] = tags
        else:
            skill_name = os.path.basename(path.rstrip("/"))
            name_parts = skill_name.split("-")
            derived = name_parts[:3] if len(name_parts) > 3 else name_parts
            derived.append("curated")
            seen: set[str] = set()
            unique: list[str] = []
            for t in derived:
                if t not in seen:
                    seen.add(t)
                    unique.append(t)
            metadata["tags"] = unique

    fm["metadata"] = metadata

    # Write back
    fm_text = yaml.dump(
        fm, default_flow_style=False, sort_keys=False, allow_unicode=True
    ).rstrip()
    new_content = f"---\n{fm_text}\n---\n{body}"

    with open(skill_md, "w") as f:
        f.write(new_content)
