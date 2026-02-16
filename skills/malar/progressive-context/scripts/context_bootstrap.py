#!/usr/bin/env python3
"""Bootstrap freshness tracking for context files.

Two modes:
  1. Add marker:  python3 context_bootstrap.py <file> "glob1" "glob2" ...
     Appends a freshness marker to the file with computed initial hash.

  2. Scan mode:   python3 context_bootstrap.py --scan <directory>
     Finds all .md files in the directory tree that lack freshness markers.

Idempotent: if a marker already exists, prints a message and exits.

Requires: git in PATH.
"""

import os
import re
import subprocess
import sys
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

FRESHNESS_PATTERN = re.compile(
    r"<!--\s*freshness\s*\n.*?\n\s*-->",
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
        return "0000000"

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
        return "0000000"


def has_freshness_marker(content: str) -> bool:
    """Check if content already contains a freshness marker."""
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


def add_marker(filepath: Path, watch_globs: list[str]) -> None:
    """Add a freshness marker to a file."""
    content = filepath.read_text(encoding="utf-8")

    if has_freshness_marker(content):
        print(f"Already tracked: {filepath}")
        return

    git_root = find_git_root()
    watches_hash = compute_hash(git_root, watch_globs)
    marker = build_marker(watches_hash, watch_globs)

    # Append marker to end of file
    if not content.endswith("\n"):
        content += "\n"
    content += marker

    filepath.write_text(content, encoding="utf-8")
    print(f"Added freshness marker to {filepath}")
    print(f"  watches_hash: {watches_hash}")
    print(f"  watches: {', '.join(watch_globs)}")


def scan_directory(directory: Path) -> None:
    """Find all .md files without freshness markers."""
    found = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = Path(root) / fname
            try:
                content = fpath.read_text(encoding="utf-8")
                if not has_freshness_marker(content):
                    found.append(fpath)
            except OSError:
                continue

    if not found:
        print("All .md files already have freshness markers (or none found).")
        return

    print(f"Found {len(found)} .md file(s) without freshness markers:\n")
    for f in sorted(found):
        try:
            rel = f.relative_to(directory)
        except ValueError:
            rel = f
        print(f"  {rel}")

    print(f"\nTo add tracking, run:")
    print(f'  python3 context_bootstrap.py <file> "src/**" "other/glob"')


def main():
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            '  context_bootstrap.py <file> "glob1" "glob2" ...  — add marker\n'
            "  context_bootstrap.py --scan <directory>           — find untracked files",
            file=sys.stderr,
        )
        sys.exit(1)

    if sys.argv[1] == "--scan":
        directory = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        if not directory.is_dir():
            print(f"Error: not a directory: {directory}", file=sys.stderr)
            sys.exit(1)
        scan_directory(directory)
    else:
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"Error: file not found: {filepath}", file=sys.stderr)
            sys.exit(1)
        watch_globs = sys.argv[2:]
        if not watch_globs:
            print("Error: at least one watch glob is required", file=sys.stderr)
            sys.exit(1)
        add_marker(filepath, watch_globs)


if __name__ == "__main__":
    main()
