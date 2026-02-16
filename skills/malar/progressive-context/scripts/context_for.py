#!/usr/bin/env python3
"""Deterministic context lookup by file path.

Reads a routing table from CLAUDE.md's `## Context Index` markdown table
and maps source file paths to context files.

Three modes:
  1. python3 context_for.py <filepath>   — output contents of matching context file
  2. python3 context_for.py --auto       — detect modified/staged files via git status,
                                            output combined relevant context
  3. python3 context_for.py --list       — list all glob-to-file mappings

Falls back gracefully if CLAUDE.md doesn't have a Context Index table.

Requires: git in PATH (for --auto mode).
"""

import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path


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


def parse_context_index(git_root: Path) -> list[tuple[str, str]]:
    """Parse the Context Index table from CLAUDE.md.

    Returns list of (glob_pattern, context_file_path) tuples.
    """
    claude_md = git_root / "CLAUDE.md"
    if not claude_md.exists():
        return []

    try:
        content = claude_md.read_text(encoding="utf-8")
    except OSError:
        return []

    # Find the ## Context Index section
    section_match = re.search(
        r"##\s+Context Index\s*\n(.*?)(?=\n##\s|\Z)",
        content,
        re.DOTALL,
    )
    if not section_match:
        return []

    section = section_match.group(1)

    # Parse markdown table rows: | glob | file | description |
    mappings = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        glob_cell = cells[0]
        file_cell = cells[1]
        if glob_cell.lower() in ("directory", "glob", "---", "----") or "-" * 3 in glob_cell:
            continue
        context_file = file_cell.strip("`")
        if not context_file:
            continue
        # Handle multiple globs in one cell: `a/**`, `b/**`, `c/**`
        raw_globs = [g.strip().strip("`") for g in glob_cell.split(",")]
        for glob_pattern in raw_globs:
            glob_pattern = glob_pattern.strip()
            if glob_pattern:
                mappings.append((glob_pattern, context_file))

    return mappings


def find_context_for_file(filepath: str,
                          mappings: list[tuple[str, str]]) -> list[str]:
    """Find context files that match a given source file path."""
    matches = []
    for glob_pattern, context_file in mappings:
        if fnmatch(filepath, glob_pattern):
            matches.append(context_file)
    return matches


def get_modified_files(git_root: Path) -> list[str]:
    """Get list of modified/staged files from git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--no-renames"],
            capture_output=True, text=True, check=True,
            cwd=git_root,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    files = []
    for line in result.stdout.strip().splitlines():
        if len(line) < 4:
            continue
        # Status is first 2 chars, then space, then filename
        filename = line[3:].strip()
        if filename:
            files.append(filename)
    return files


def output_context_file(git_root: Path, context_path: str) -> bool:
    """Read and print a context file. Returns True if successful."""
    full_path = git_root / context_path
    if not full_path.exists():
        print(f"# Warning: context file not found: {context_path}",
              file=sys.stderr)
        return False

    try:
        content = full_path.read_text(encoding="utf-8")
        print(f"# === {context_path} ===")
        print(content)
        print()
        return True
    except OSError as e:
        print(f"# Warning: could not read {context_path}: {e}",
              file=sys.stderr)
        return False


def mode_lookup(filepath: str, git_root: Path,
                mappings: list[tuple[str, str]]) -> None:
    """Look up and output context for a single file."""
    matches = find_context_for_file(filepath, mappings)
    if not matches:
        print(f"No context mapping found for: {filepath}", file=sys.stderr)
        sys.exit(0)

    for context_file in matches:
        output_context_file(git_root, context_file)


def mode_auto(git_root: Path, mappings: list[tuple[str, str]]) -> None:
    """Detect modified/staged files and output combined relevant context."""
    modified = get_modified_files(git_root)
    if not modified:
        print("No modified or staged files detected.", file=sys.stderr)
        sys.exit(0)

    # Collect unique context files
    seen = set()
    context_files = []
    for filepath in modified:
        for context_file in find_context_for_file(filepath, mappings):
            if context_file not in seen:
                seen.add(context_file)
                context_files.append(context_file)

    if not context_files:
        print("No context mappings match the modified files.", file=sys.stderr)
        sys.exit(0)

    for cf in context_files:
        output_context_file(git_root, cf)


def mode_list(mappings: list[tuple[str, str]]) -> None:
    """List all glob-to-file mappings."""
    if not mappings:
        print("No Context Index table found in CLAUDE.md")
        return

    max_glob = max(len(g) for g, _ in mappings)
    print(f"{'Glob':<{max_glob + 2}} Context File")
    print(f"{'-' * (max_glob + 2)} {'-' * 40}")
    for glob_pattern, context_file in mappings:
        print(f"{glob_pattern:<{max_glob + 2}} {context_file}")


def main():
    git_root = find_git_root()
    mappings = parse_context_index(git_root)

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  context_for.py <filepath>  — output matching context\n"
            "  context_for.py --auto      — context for modified/staged files\n"
            "  context_for.py --list      — list all mappings",
            file=sys.stderr,
        )
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--auto":
        if not mappings:
            print("No Context Index table found in CLAUDE.md", file=sys.stderr)
            sys.exit(0)
        mode_auto(git_root, mappings)
    elif arg == "--list":
        mode_list(mappings)
    else:
        if not mappings:
            print("No Context Index table found in CLAUDE.md", file=sys.stderr)
            sys.exit(0)
        mode_lookup(arg, git_root, mappings)


if __name__ == "__main__":
    main()
