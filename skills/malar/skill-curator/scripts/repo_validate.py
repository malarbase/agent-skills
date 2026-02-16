#!/usr/bin/env python3
"""Repo-specific skill validation for malarbase/agent-skills.

Standalone script that validates skills against both the agentskills.io spec
and repo-specific conventions. When quick_validate.py is available (in-repo),
delegates spec checks to it. Otherwise, uses built-in spec checks as fallback.

Usage:
    repo_validate.py <skill_dir> [--repo-root <path>]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

QUICK_VALIDATE_REL = os.path.join(
    "skills", "anthropic", "skill-creator", "scripts", "quick_validate.py"
)

# Spec-level allowed top-level properties (fallback validation)
ALLOWED_PROPERTIES = {
    "name", "description", "license", "allowed-tools", "metadata", "compatibility"
}


def _find_quick_validate(repo_root: str | None) -> str | None:
    """Try to locate quick_validate.py from repo root."""
    if repo_root:
        candidate = os.path.join(repo_root, QUICK_VALIDATE_REL)
        if os.path.isfile(candidate):
            return candidate

    # Try inferring repo root: this script is at skills/malar/skill-curator/scripts/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    inferred_root = os.path.normpath(os.path.join(script_dir, "..", "..", "..", ".."))
    candidate = os.path.join(inferred_root, QUICK_VALIDATE_REL)
    if os.path.isfile(candidate):
        return candidate

    return None


def _run_quick_validate(script_path: str, skill_dir: str) -> tuple[bool, str]:
    """Run quick_validate.py via subprocess. Returns (passed, message)."""
    result = subprocess.run(
        [sys.executable, script_path, skill_dir],
        capture_output=True, text=True,
    )
    output = result.stdout.strip()
    if result.returncode != 0:
        return False, output or result.stderr.strip()
    return True, output


def _builtin_spec_validate(skill_dir: str) -> tuple[bool, str]:
    """Fallback spec validation when quick_validate.py is not available."""
    if yaml is None:
        return False, "pyyaml not installed; cannot validate YAML frontmatter"

    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return False, "SKILL.md not found"

    with open(skill_md, "r") as f:
        content = f.read()

    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    unexpected = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected:
        return False, (
            f"Unexpected key(s): {', '.join(sorted(unexpected))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        if not re.match(r"^[a-z0-9-]+$", name):
            return False, f"Name '{name}' must be kebab-case"
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        if len(name) > 64:
            return False, f"Name too long ({len(name)} chars, max 64)"

    desc = frontmatter.get("description", "")
    if not isinstance(desc, str):
        return False, f"Description must be a string, got {type(desc).__name__}"
    desc = desc.strip()
    if desc:
        if "<" in desc or ">" in desc:
            return False, "Description cannot contain angle brackets"
        if len(desc) > 1024:
            return False, f"Description too long ({len(desc)} chars, max 1024)"

    return True, "Spec checks passed"


def _parse_frontmatter(skill_dir: str) -> dict | None:
    """Parse and return frontmatter dict, or None on failure."""
    if yaml is None:
        return None
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return None
    with open(skill_md, "r") as f:
        content = f.read()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1))
        return fm if isinstance(fm, dict) else None
    except yaml.YAMLError:
        return None


def repo_validate(skill_dir: str) -> list[str]:
    """Run repo-specific checks. Returns list of errors (empty = valid)."""
    errors: list[str] = []

    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return ["SKILL.md not found"]

    # Name must match parent directory
    fm = _parse_frontmatter(skill_dir)
    if fm:
        name = fm.get("name", "")
        dir_name = os.path.basename(os.path.normpath(skill_dir))
        if name and name != dir_name:
            errors.append(
                f"name '{name}' does not match directory name '{dir_name}'"
            )

    # SKILL.md line limit (recommendation, not blocking)
    with open(skill_md, "r") as f:
        line_count = sum(1 for _ in f)
    if line_count > 500:
        print(f"WARNING: SKILL.md is {line_count} lines (recommended max 500)", file=sys.stderr)

    # metadata.tags validation
    if fm:
        metadata = fm.get("metadata")
        if isinstance(metadata, dict):
            tags = metadata.get("tags")
            if tags is not None:
                if not isinstance(tags, list):
                    errors.append("metadata.tags must be a list")
                elif not all(isinstance(t, str) for t in tags):
                    errors.append("All metadata.tags must be strings")

            author = metadata.get("author")
            if author is not None:
                if not isinstance(author, str) or not author.strip():
                    errors.append("metadata.author must be a non-empty string")

    return errors


def validate(skill_dir: str, repo_root: str | None = None) -> tuple[bool, list[str]]:
    """Full validation: spec checks + repo checks. Returns (passed, messages)."""
    messages: list[str] = []

    # Layer 1: Spec checks
    qv_path = _find_quick_validate(repo_root)
    if qv_path:
        passed, msg = _run_quick_validate(qv_path, skill_dir)
        if not passed:
            return False, [f"Spec: {msg}"]
        messages.append(f"Spec: {msg} (via quick_validate.py)")
    else:
        passed, msg = _builtin_spec_validate(skill_dir)
        if not passed:
            return False, [f"Spec: {msg}"]
        messages.append(f"Spec: {msg} (built-in fallback)")

    # Layer 2: Repo-specific checks
    repo_errors = repo_validate(skill_dir)
    if repo_errors:
        for e in repo_errors:
            messages.append(f"Repo: {e}")
        return False, messages

    messages.append("Repo: All checks passed")
    return True, messages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo_validate.py",
        description="Validate skill against spec and repo conventions.",
    )
    parser.add_argument("skill_dir", help="Path to skill directory")
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Path to agent-skills repo root (for locating quick_validate.py)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output on failure",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    skill_dir = os.path.abspath(args.skill_dir)
    passed, messages = validate(skill_dir, args.repo_root)

    if not args.quiet or not passed:
        for msg in messages:
            print(msg)

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
