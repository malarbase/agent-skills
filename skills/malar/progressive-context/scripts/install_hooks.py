#!/usr/bin/env python3
"""Install or uninstall git hooks for automatic context freshness checking.

Auto-detects the project's hook system and installs appropriately:
  1. Husky (.husky/ + "prepare": "husky" in package.json)
  2. pre-commit (.pre-commit-config.yaml)
  3. Plain git hooks (.githooks/ with core.hooksPath)

Hooks installed:
  - post-commit: check if committed files affect any context watches
  - post-merge: run full context audit

Idempotent: won't overwrite existing hooks.

Usage:
    python3 install_hooks.py [--root <git-root>]
    python3 install_hooks.py --uninstall [--root <git-root>]
"""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
HOOK_TEMPLATES_DIR = SKILL_DIR / "references" / "githooks"

# Inline hook content — used when template files aren't available
# (e.g., when this script is copied to a project's scripts/ directory).
_POST_COMMIT_HOOK = """\
#!/bin/sh
# Context freshness check — warns if committed files affect context
SCRIPTS_DIR="$(git rev-parse --show-toplevel)/scripts"
if command -v python3 >/dev/null 2>&1 && [ -f "$SCRIPTS_DIR/context_check_watches.py" ]; then
  git diff-tree --no-commit-id --name-only -r HEAD | xargs python3 "$SCRIPTS_DIR/context_check_watches.py" 2>/dev/null
fi
"""

_POST_MERGE_HOOK = """\
#!/bin/sh
# Context freshness audit after merge/pull
SCRIPTS_DIR="$(git rev-parse --show-toplevel)/scripts"
if command -v python3 >/dev/null 2>&1 && [ -f "$SCRIPTS_DIR/context_audit.py" ]; then
  python3 "$SCRIPTS_DIR/context_audit.py" 2>/dev/null
fi
"""

_INLINE_HOOKS = {
    "post-commit": _POST_COMMIT_HOOK,
    "post-merge": _POST_MERGE_HOOK,
}


def find_git_root(start: str = ".") -> Path:
    """Find the git repository root."""
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


def read_template(name: str) -> str:
    """Read a hook template, falling back to inline content."""
    template_path = HOOK_TEMPLATES_DIR / name
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    if name in _INLINE_HOOKS:
        return _INLINE_HOOKS[name]
    print(f"Error: hook template not found: {template_path}", file=sys.stderr)
    sys.exit(1)


def make_executable(path: Path) -> None:
    """Make a file executable (chmod +x)."""
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def write_hook(hook_path: Path, content: str, hook_name: str) -> bool:
    """Write a hook file if it doesn't exist. Returns True if written."""
    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if "context_check_watches" in existing or "context_audit" in existing:
            print(f"  Skipped {hook_name}: already contains context hooks")
            return False
        # Append to existing hook
        print(f"  Appended to existing {hook_name}")
        with open(hook_path, "a", encoding="utf-8") as f:
            f.write(f"\n# --- progressive-context hooks ---\n")
            # Extract just the body (skip shebang if appending)
            lines = content.splitlines()
            body_start = 0
            for i, line in enumerate(lines):
                if line.startswith("#!"):
                    body_start = i + 1
                    continue
                if line.startswith("#") and i == body_start:
                    body_start = i + 1
                    continue
                break
            f.write("\n".join(lines[body_start:]) + "\n")
        make_executable(hook_path)
        return True

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(content, encoding="utf-8")
    make_executable(hook_path)
    print(f"  Created {hook_name}")
    return True


def detect_husky(git_root: Path) -> bool:
    """Check if project uses Husky."""
    husky_dir = git_root / ".husky"
    pkg_json = git_root / "package.json"
    if not husky_dir.is_dir() or not pkg_json.exists():
        return False
    try:
        pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        return "husky" in scripts.get("prepare", "")
    except (json.JSONDecodeError, OSError):
        return False


def detect_precommit(git_root: Path) -> bool:
    """Check if project uses pre-commit framework."""
    return (git_root / ".pre-commit-config.yaml").exists()


def install_husky(git_root: Path) -> None:
    """Install hooks via Husky."""
    print("Detected: Husky")
    husky_dir = git_root / ".husky"

    post_commit = read_template("post-commit")
    post_merge = read_template("post-merge")

    write_hook(husky_dir / "post-commit", post_commit, ".husky/post-commit")
    write_hook(husky_dir / "post-merge", post_merge, ".husky/post-merge")


def install_precommit(git_root: Path) -> None:
    """Install hooks via pre-commit config.

    Appends local hook entries to .pre-commit-config.yaml.
    """
    print("Detected: pre-commit")
    config_path = git_root / ".pre-commit-config.yaml"
    content = config_path.read_text(encoding="utf-8")

    if "context_check_watches" in content:
        print("  Skipped: context hooks already in .pre-commit-config.yaml")
        return

    # Find the scripts directory relative to the config
    scripts_dir = SKILL_DIR / "scripts"

    hook_entry = f"""
# --- progressive-context hooks ---
- repo: local
  hooks:
    - id: context-check-watches
      name: Check context freshness
      entry: python3 {scripts_dir}/context_check_watches.py
      language: system
      stages: [post-commit]
      always_run: true
    - id: context-audit
      name: Context audit (post-merge)
      entry: python3 {scripts_dir}/context_audit.py
      language: system
      stages: [post-merge]
      always_run: true
"""

    with open(config_path, "a", encoding="utf-8") as f:
        f.write(hook_entry)

    print("  Added local hooks to .pre-commit-config.yaml")
    print("  Run: pre-commit install --hook-type post-commit --hook-type post-merge")


def install_plain_git(git_root: Path) -> None:
    """Install hooks via plain .githooks/ directory."""
    print("Detected: plain git hooks")
    hooks_dir = git_root / ".githooks"
    hooks_dir.mkdir(exist_ok=True)

    post_commit = read_template("post-commit")
    post_merge = read_template("post-merge")

    wrote_any = False
    wrote_any |= write_hook(hooks_dir / "post-commit", post_commit,
                            ".githooks/post-commit")
    wrote_any |= write_hook(hooks_dir / "post-merge", post_merge,
                            ".githooks/post-merge")

    # Configure git to use .githooks
    try:
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True, text=True, check=False,
            cwd=git_root,
        )
        current_path = result.stdout.strip()
        if current_path != ".githooks":
            subprocess.run(
                ["git", "config", "core.hooksPath", ".githooks"],
                check=True, cwd=git_root,
            )
            print("  Set git config core.hooksPath = .githooks")
        else:
            print("  core.hooksPath already set to .githooks")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  Warning: could not set core.hooksPath: {e}", file=sys.stderr)


CONTEXT_HOOK_MARKER = "progressive-context"
CONTEXT_HOOK_SIGNATURES = ("context_check_watches", "context_audit")


def _remove_hook_file(hook_path: Path, hook_name: str) -> bool:
    """Remove a hook file or clean progressive-context lines from it.

    If the entire file is a progressive-context hook, delete it.
    If progressive-context was appended to an existing hook, remove only that section.
    Returns True if something was removed.
    """
    if not hook_path.exists():
        return False

    content = hook_path.read_text(encoding="utf-8")

    # Check if this file contains our hooks at all
    if not any(sig in content for sig in CONTEXT_HOOK_SIGNATURES):
        return False

    # Determine if the file is entirely ours or has other meaningful content.
    # "Ours" = empty, shebang, comments, shell scaffolding (if/fi/then/else),
    # variable assignments for SCRIPTS_DIR, and lines with context-hook signatures.
    SHELL_SCAFFOLDING = {"if", "fi", "then", "else", "elif", "done", "do"}

    def _is_ours(line: str) -> bool:
        s = line.strip()
        if not s or s.startswith("#") or line.startswith("#!/"):
            return True
        if any(sig in line for sig in CONTEXT_HOOK_SIGNATURES):
            return True
        if CONTEXT_HOOK_MARKER in line:
            return True
        if "SCRIPTS_DIR=" in line or "command -v python3" in line:
            return True
        if "xargs python3" in line or "git diff-tree" in line:
            return True
        if s.rstrip(";") in SHELL_SCAFFOLDING:
            return True
        return False

    foreign_lines = [l for l in content.splitlines() if not _is_ours(l)]

    if not foreign_lines:
        hook_path.unlink()
        print(f"  Removed {hook_name}")
        return True

    # Other content exists — remove our marker-delimited section and any
    # standalone context-hook lines, keeping everything else.
    cleaned = []
    skip_block = False
    for line in content.splitlines():
        if CONTEXT_HOOK_MARKER in line:
            skip_block = True
            continue
        if skip_block:
            if any(sig in line for sig in CONTEXT_HOOK_SIGNATURES):
                continue
            if not line.strip():
                continue
            skip_block = False
        if _is_ours(line) and not line.startswith("#!/"):
            # Only drop non-shebang "ours" lines if they're isolated
            # (surrounded by other ours lines). Keep if adjacent to foreign.
            continue
        cleaned.append(line)

    hook_path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    print(f"  Cleaned context hooks from {hook_name}")
    return True


def uninstall_husky(git_root: Path) -> None:
    """Remove context hooks from Husky."""
    print("Detected: Husky")
    husky_dir = git_root / ".husky"
    _remove_hook_file(husky_dir / "post-commit", ".husky/post-commit")
    _remove_hook_file(husky_dir / "post-merge", ".husky/post-merge")


def uninstall_precommit(git_root: Path) -> None:
    """Remove context hook entries from .pre-commit-config.yaml."""
    print("Detected: pre-commit")
    config_path = git_root / ".pre-commit-config.yaml"
    if not config_path.exists():
        return
    content = config_path.read_text(encoding="utf-8")
    if CONTEXT_HOOK_MARKER not in content:
        print("  No context hooks found in .pre-commit-config.yaml")
        return

    # Remove the block from the marker to the end of our entries
    lines = content.splitlines()
    cleaned = []
    skip = False
    for line in lines:
        if CONTEXT_HOOK_MARKER in line:
            skip = True
            continue
        if skip:
            # Skip until we hit a line that starts a new repo block or EOF
            stripped = line.strip()
            if stripped.startswith("- repo:") and "local" not in stripped:
                skip = False
                cleaned.append(line)
            continue
        cleaned.append(line)

    config_path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    print("  Removed context hooks from .pre-commit-config.yaml")


def uninstall_plain_git(git_root: Path) -> None:
    """Remove context hooks from .githooks/ directory."""
    print("Detected: plain git hooks")
    hooks_dir = git_root / ".githooks"
    removed_any = False
    if hooks_dir.is_dir():
        removed_any |= _remove_hook_file(hooks_dir / "post-commit",
                                          ".githooks/post-commit")
        removed_any |= _remove_hook_file(hooks_dir / "post-merge",
                                          ".githooks/post-merge")
        # If directory is now empty, remove it and reset hooksPath
        remaining = list(hooks_dir.iterdir())
        if not remaining:
            hooks_dir.rmdir()
            print("  Removed empty .githooks/ directory")
            try:
                subprocess.run(
                    ["git", "config", "--unset", "core.hooksPath"],
                    check=False, cwd=git_root, capture_output=True,
                )
                print("  Unset git config core.hooksPath")
            except FileNotFoundError:
                pass


def main():
    root_arg = None
    uninstall = False
    args = sys.argv[1:]
    if "--uninstall" in args:
        uninstall = True
        args.remove("--uninstall")
    if "--root" in args:
        idx = args.index("--root")
        if idx + 1 < len(args):
            root_arg = args[idx + 1]

    git_root = find_git_root(root_arg or ".")

    if uninstall:
        print(f"Uninstalling context hooks from: {git_root}\n")
        if detect_husky(git_root):
            uninstall_husky(git_root)
        elif detect_precommit(git_root):
            uninstall_precommit(git_root)
        else:
            uninstall_plain_git(git_root)
        print("\nDone. Context hooks removed.")
    else:
        print(f"Installing context hooks in: {git_root}\n")
        if detect_husky(git_root):
            install_husky(git_root)
        elif detect_precommit(git_root):
            install_precommit(git_root)
        else:
            install_plain_git(git_root)
        print("\nDone. Context freshness will be checked automatically on commit/merge.")


if __name__ == "__main__":
    main()
