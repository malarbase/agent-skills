#!/usr/bin/env python3
"""Shared utilities for context freshness tracking scripts.

All context_* scripts import from this module to avoid duplication.
Python 3 stdlib-only — no external dependencies.
"""

import glob as globmod
import re
import subprocess
import sys
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

CONTEXT_GLOBS = [
    ".cursor/rules/*.md",
    ".cursor/skills/*/SKILL.md",
    ".claude/skills/*/SKILL.md",
    "docs/context/*.md",
    "CLAUDE.md",
    "AGENTS.md",
]

FRESHNESS_PATTERN = re.compile(
    r"<!--\s*freshness\s*\n(.*?)\n\s*-->",
    re.DOTALL,
)

FRESHNESS_PATTERN_GROUPS = re.compile(
    r"(<!--\s*freshness\s*\n)(.*?)(\n\s*-->)",
    re.DOTALL,
)


def find_git_root(start: str = ".", *, exit_on_error: bool = True) -> Path:
    """Find the git repository root from a starting directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
            cwd=start,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        if exit_on_error:
            print("Error: not inside a git repository", file=sys.stderr)
            sys.exit(1)
        return Path(".")


def find_context_files(git_root: Path) -> list[Path]:
    """Find all context files matching CONTEXT_GLOBS."""
    files = []
    for pattern in CONTEXT_GLOBS:
        matches = globmod.glob(str(git_root / pattern))
        files.extend(Path(m) for m in matches)
    return sorted(set(files))


def compute_hash(git_root: Path, watch_globs: list[str]) -> str:
    """Compute a content-aware hash from git-tracked files matching watch_globs.

    Uses ``git ls-files -s`` to obtain per-file blob hashes (which change
    when file content changes), filters by watch_globs via fnmatch, then
    hashes the sorted "blob_hash path" pairs.  Returns the first 7 hex chars.

    Note: fnmatch does not treat '/' specially, so both '*' and '**' match
    across directory boundaries.  We standardize on '**' by convention.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "-s"],
            capture_output=True, text=True, check=True,
            cwd=git_root,
        )
    except subprocess.CalledProcessError:
        return "ERROR"

    matched = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        filepath = parts[1]
        blob_hash = parts[0].split()[1]
        for glob_pattern in watch_globs:
            if fnmatch(filepath, glob_pattern):
                matched.append((filepath, blob_hash))
                break

    if not matched:
        return "0000000"

    matched.sort(key=lambda x: x[0])
    hash_input = "\n".join(f"{h} {p}" for p, h in matched) + "\n"
    try:
        result = subprocess.run(
            ["git", "hash-object", "--stdin"],
            input=hash_input, capture_output=True, text=True, check=True,
            cwd=git_root,
        )
        return result.stdout.strip()[:7]
    except subprocess.CalledProcessError:
        return "ERROR"


def parse_freshness_marker(content: str) -> dict | None:
    """Extract freshness marker data from file content.

    Returns dict with keys: watches_hash, last_verified, watches
    or None if no marker found.
    """
    match = FRESHNESS_PATTERN.search(content)
    if not match:
        return None

    block = match.group(1)
    data = {}

    hash_match = re.search(r"watches_hash:\s*(\S+)", block)
    if hash_match:
        data["watches_hash"] = hash_match.group(1)

    date_match = re.search(r"last_verified:\s*(\S+)", block)
    if date_match:
        data["last_verified"] = date_match.group(1)

    data["watches"] = parse_watches(block)

    return data if data.get("watches_hash") else None


def parse_watches(block: str) -> list[str]:
    """Extract watch glob patterns from a freshness marker block."""
    watches = []
    in_watches = False
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("watches:"):
            in_watches = True
            continue
        if in_watches:
            if stripped.startswith("- "):
                watches.append(stripped[2:].strip())
            elif stripped and not stripped.startswith("-"):
                break
    return watches


def has_freshness_marker(content: str) -> bool:
    """Check if content contains a freshness marker."""
    return bool(FRESHNESS_PATTERN.search(content))


def build_marker(watches_hash: str, watch_globs: list[str]) -> str:
    """Build a freshness marker HTML comment."""
    today = date.today().isoformat()
    watches_lines = "\n".join(f"  - {g}" for g in watch_globs)
    return (
        f"\n<!-- freshness\n"
        f"watches_hash: {watches_hash}\n"
        f"last_verified: {today}\n"
        f"watches:\n"
        f"{watches_lines}\n"
        f"-->\n"
    )
