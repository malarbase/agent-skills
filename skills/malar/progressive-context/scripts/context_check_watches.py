#!/usr/bin/env python3
"""Check if modified files affect any freshness-tracked context files.

Takes one or more file paths (files that were modified) and checks if they
match any watch globs in freshness-tracked context files. Designed to be
fast and silent for git hooks — only prints warnings when matches are found.

Usage:
    python3 context_check_watches.py <file1> [file2] ...

Exit code is always 0 (warnings are informational, never block commits).
Requires: git in PATH.
"""

import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path
import glob as globmod

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


def find_git_root() -> Path:
    """Find the git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path(".")


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


def find_tracked_context_files(git_root: Path) -> list[tuple[Path, list[str]]]:
    """Find all context files with freshness markers, return (path, watches) pairs."""
    results = []
    for pattern in CONTEXT_GLOBS:
        matches = globmod.glob(str(git_root / pattern))
        for m in matches:
            fpath = Path(m)
            try:
                content = fpath.read_text(encoding="utf-8")
            except OSError:
                continue
            match = FRESHNESS_PATTERN.search(content)
            if match:
                watches = parse_watches(match.group(1))
                if watches:
                    results.append((fpath, watches))
    return results


def main():
    if len(sys.argv) < 2:
        # No files provided — nothing to check
        sys.exit(0)

    modified_files = sys.argv[1:]
    git_root = find_git_root()
    tracked = find_tracked_context_files(git_root)

    if not tracked:
        sys.exit(0)

    warned = False
    for context_file, watches in tracked:
        for modified in modified_files:
            for glob_pattern in watches:
                if fnmatch(modified, glob_pattern):
                    try:
                        rel_context = context_file.relative_to(git_root)
                    except ValueError:
                        rel_context = context_file
                    print(f"[context] Warning: {rel_context} may be stale "
                          f"(watched file changed: {modified})")
                    warned = True
                    break
            if warned:
                break
        warned = False

    sys.exit(0)


if __name__ == "__main__":
    main()
