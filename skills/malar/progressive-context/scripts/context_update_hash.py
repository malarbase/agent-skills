#!/usr/bin/env python3
"""Update the freshness hash of a context file after manual review.

Reads the file's watches globs, recomputes the hash from current git state,
and updates the watches_hash and last_verified fields in-place.

Usage:
    python3 context_update_hash.py <file-path>

Requires: git in PATH.
"""

import re
import subprocess
import sys
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

FRESHNESS_PATTERN = re.compile(
    r"(<!--\s*freshness\s*\n)(.*?)(\n\s*-->)",
    re.DOTALL,
)


def find_git_root() -> Path:
    """Find the git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: not inside a git repository", file=sys.stderr)
        sys.exit(1)


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


def compute_hash(git_root: Path, watch_globs: list[str]) -> str:
    """Compute hash from git-tracked files matching watch globs."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, check=True,
            cwd=git_root,
        )
        all_files = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        print("Error: git ls-files failed", file=sys.stderr)
        sys.exit(1)

    matched = set()
    for f in all_files:
        for glob_pattern in watch_globs:
            if fnmatch(f, glob_pattern):
                matched.add(f)
                break

    if not matched:
        return "0000000"

    sorted_files = "\n".join(sorted(matched)) + "\n"
    try:
        result = subprocess.run(
            ["git", "hash-object", "--stdin"],
            input=sorted_files, capture_output=True, text=True, check=True,
            cwd=git_root,
        )
        return result.stdout.strip()[:7]
    except subprocess.CalledProcessError:
        print("Error: git hash-object failed", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: context_update_hash.py <file-path>", file=sys.stderr)
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    content = filepath.read_text(encoding="utf-8")
    match = FRESHNESS_PATTERN.search(content)

    if not match:
        print(f"Error: no freshness marker found in {filepath}", file=sys.stderr)
        sys.exit(1)

    block = match.group(2)
    watches = parse_watches(block)

    if not watches:
        print(f"Error: no watches found in freshness marker of {filepath}",
              file=sys.stderr)
        sys.exit(1)

    git_root = find_git_root()
    new_hash = compute_hash(git_root, watches)
    today = date.today().isoformat()

    # Update watches_hash
    new_block = re.sub(
        r"watches_hash:\s*\S+",
        f"watches_hash: {new_hash}",
        block,
    )
    # Update last_verified
    new_block = re.sub(
        r"last_verified:\s*\S+",
        f"last_verified: {today}",
        new_block,
    )

    new_content = content[:match.start(2)] + new_block + content[match.end(2):]
    filepath.write_text(new_content, encoding="utf-8")

    print(f"Updated {filepath}")
    print(f"  watches_hash: {new_hash}")
    print(f"  last_verified: {today}")
    print(f"  watches: {', '.join(watches)}")


if __name__ == "__main__":
    main()
