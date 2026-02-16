#!/usr/bin/env python3
"""Audit freshness of all AI context files in a repository.

Scans for context files (.cursor/rules/*.md, CLAUDE.md, AGENTS.md, etc.),
reads their freshness markers, computes current hashes from watched files,
and reports which context files are stale.

Usage:
    python3 context_audit.py [--root <git-root>]

Exit code is always 0 (report is informational).
Requires: git in PATH.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Patterns to scan for context files (relative to git root)
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


def find_git_root(start: str = ".") -> Path:
    """Find the git repository root from a starting directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
            cwd=start,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: not inside a git repository", file=sys.stderr)
        sys.exit(1)


def find_context_files(git_root: Path) -> list[Path]:
    """Find all context files matching known patterns."""
    import glob as globmod
    files = []
    for pattern in CONTEXT_GLOBS:
        matches = globmod.glob(str(git_root / pattern))
        files.extend(Path(m) for m in matches)
    return sorted(set(files))


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
                in_watches = False
    data["watches"] = watches

    return data if data.get("watches_hash") else None


def compute_hash(git_root: Path, watch_globs: list[str]) -> str:
    """Compute a deterministic hash from git-tracked files matching watch globs.

    Pipes sorted matching filenames through git hash-object --stdin.
    Returns first 7 characters of the hash.
    """
    try:
        # Get all git-tracked files
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, check=True,
            cwd=git_root,
        )
        all_files = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        return "ERROR"

    # Filter by watch globs using fnmatch
    from fnmatch import fnmatch
    matched = set()
    for f in all_files:
        for glob_pattern in watch_globs:
            if fnmatch(f, glob_pattern):
                matched.add(f)
                break

    if not matched:
        return "0000000"

    # Sort for determinism and hash the file list
    sorted_files = "\n".join(sorted(matched)) + "\n"
    try:
        result = subprocess.run(
            ["git", "hash-object", "--stdin"],
            input=sorted_files, capture_output=True, text=True, check=True,
            cwd=git_root,
        )
        return result.stdout.strip()[:7]
    except subprocess.CalledProcessError:
        return "ERROR"


def get_changed_files(git_root: Path, watch_globs: list[str],
                      stored_hash: str) -> list[str]:
    """Get list of watched files that have changed recently (for diffstat)."""
    from fnmatch import fnmatch
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~5..HEAD", "--"],
            capture_output=True, text=True, check=False,
            cwd=git_root,
        )
        if result.returncode != 0:
            return []
        changed = result.stdout.strip().splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    matched = []
    for f in changed:
        for glob_pattern in watch_globs:
            if fnmatch(f, glob_pattern):
                matched.append(f)
                break
    return matched


def main():
    root_arg = None
    args = sys.argv[1:]
    if "--root" in args:
        idx = args.index("--root")
        if idx + 1 < len(args):
            root_arg = args[idx + 1]

    git_root = find_git_root(root_arg or ".")
    context_files = find_context_files(git_root)

    if not context_files:
        print("No context files found matching known patterns.")
        return

    stale_count = 0
    ok_count = 0
    missing_count = 0

    print("CONTEXT FRESHNESS REPORT")
    print("========================")

    for filepath in context_files:
        rel_path = filepath.relative_to(git_root)

        try:
            content = filepath.read_text(encoding="utf-8")
        except OSError as e:
            print(f"ERROR  {rel_path}")
            print(f"       could not read: {e}")
            continue

        marker = parse_freshness_marker(content)

        if marker is None:
            missing_count += 1
            print(f"NONE   {rel_path}")
            print("       no freshness marker found")
            print()
            continue

        stored_hash = marker["watches_hash"]
        current_hash = compute_hash(git_root, marker["watches"])
        last_verified = marker.get("last_verified", "unknown")

        if stored_hash != current_hash:
            stale_count += 1
            print(f"STALE  {rel_path}")
            print(f"       watches_hash: {stored_hash} -> {current_hash} (changed)")
            print(f"       last_verified: {last_verified}")
            changed = get_changed_files(git_root, marker["watches"], stored_hash)
            if changed:
                print(f"       changed files:")
                for cf in changed[:10]:
                    print(f"         - {cf}")
                if len(changed) > 10:
                    print(f"         ... and {len(changed) - 10} more")
        else:
            ok_count += 1
            print(f"OK     {rel_path}")
            print(f"       watches_hash: {stored_hash} (unchanged)")
            print(f"       last_verified: {last_verified}")

        print()

    print(f"Summary: {stale_count} stale, {ok_count} current, {missing_count} missing markers")


if __name__ == "__main__":
    main()
