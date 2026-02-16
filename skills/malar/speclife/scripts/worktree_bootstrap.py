#!/usr/bin/env python3
"""Bootstrap environment for a SpecLife worktree.

Detects project environments (Node.js, Python, Go, Rust) and sets up
symlinks so the worktree can build without re-installing dependencies.

Usage:
    worktree_bootstrap.py <worktree_path> <source_root> [--skip-bootstrap]
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def detect_environments(project_root: str) -> list[dict]:
    """Detect project environments present in *project_root*."""
    root = Path(project_root)
    envs: list[dict] = []

    # Node.js
    if (root / "package.json").exists():
        if (root / "pnpm-lock.yaml").exists():
            pm = "pnpm"
        elif (root / "yarn.lock").exists():
            pm = "yarn"
        elif (root / "package-lock.json").exists():
            pm = "npm"
        else:
            pm = "npm"
        envs.append({"name": "nodejs", "package_manager": pm})

    # Python
    if (root / "pyproject.toml").exists():
        if (root / "poetry.lock").exists():
            pm = "poetry"
        elif (root / "uv.lock").exists():
            pm = "uv"
        else:
            pm = "pip"
        envs.append({"name": "python", "package_manager": pm})
    elif (root / "requirements.txt").exists():
        envs.append({"name": "python", "package_manager": "pip"})
    elif (root / "Pipfile").exists():
        envs.append({"name": "python", "package_manager": "pipenv"})
    elif (root / "setup.py").exists():
        envs.append({"name": "python", "package_manager": "pip"})

    # Go
    if (root / "go.mod").exists():
        envs.append({"name": "go", "package_manager": "go"})

    # Rust
    if (root / "Cargo.toml").exists():
        envs.append({"name": "rust", "package_manager": "cargo"})

    return envs


# ---------------------------------------------------------------------------
# Node.js bootstrap
# ---------------------------------------------------------------------------

def bootstrap_nodejs(worktree_path: str, source_root: str) -> dict:
    """Symlink node_modules and patch tsconfig for monorepo support."""
    source_modules = os.path.join(source_root, "node_modules")
    target_modules = os.path.join(worktree_path, "node_modules")

    if not os.path.isdir(source_modules):
        return {
            "success": False,
            "message": "Source node_modules not found. Run npm install in the main project first.",
        }

    # Remove existing target (symlink or dir)
    if os.path.islink(target_modules):
        os.remove(target_modules)
    elif os.path.isdir(target_modules):
        shutil.rmtree(target_modules)

    # Absolute symlink so it resolves from any cwd
    os.symlink(source_modules, target_modules, target_is_directory=True)
    msg = f"Symlinked node_modules -> {source_modules}"

    # Monorepo handling
    monorepo = detect_monorepo(source_root)
    patched = False
    if monorepo["is_monorepo"] and monorepo["workspace_packages"]:
        patched = patch_tsconfig(worktree_path, monorepo)
        if patched:
            n = len(monorepo["workspace_packages"])
            msg += f" | Patched tsconfig for {n} local package(s)"

    return {"success": True, "message": msg}


# ---------------------------------------------------------------------------
# Python bootstrap
# ---------------------------------------------------------------------------

def bootstrap_python(worktree_path: str, source_root: str) -> dict:
    """Symlink .venv from source into worktree."""
    source_venv = os.path.join(source_root, ".venv")
    target_venv = os.path.join(worktree_path, ".venv")

    if not os.path.isdir(source_venv):
        return {
            "success": True,
            "message": "No .venv found in source. Python environment not bootstrapped.",
        }

    if os.path.islink(target_venv):
        os.remove(target_venv)
    elif os.path.isdir(target_venv):
        shutil.rmtree(target_venv)

    os.symlink(source_venv, target_venv, target_is_directory=True)
    return {"success": True, "message": f"Symlinked .venv -> {source_venv}"}


# ---------------------------------------------------------------------------
# Monorepo detection
# ---------------------------------------------------------------------------

def detect_monorepo(project_root: str) -> dict:
    """Detect monorepo structure from package.json, pnpm-workspace, or lerna."""
    root = Path(project_root)
    pkg_json_path = root / "package.json"
    base = {"is_monorepo": False, "type": None, "workspace_packages": []}

    if not pkg_json_path.exists():
        return base

    try:
        pkg = json.loads(pkg_json_path.read_text())
    except (json.JSONDecodeError, OSError):
        return base

    # npm/yarn workspaces
    workspaces = pkg.get("workspaces")
    if workspaces:
        patterns = workspaces if isinstance(workspaces, list) else workspaces.get("packages", [])
        packages = resolve_workspace_packages(project_root, patterns)
        return {"is_monorepo": True, "type": "npm-workspaces", "workspace_packages": packages}

    # pnpm workspaces
    pnpm_ws = root / "pnpm-workspace.yaml"
    if pnpm_ws.exists():
        patterns = _parse_pnpm_workspace_yaml(pnpm_ws.read_text())
        packages = resolve_workspace_packages(project_root, patterns)
        return {"is_monorepo": True, "type": "pnpm-workspaces", "workspace_packages": packages}

    # Lerna
    lerna_path = root / "lerna.json"
    if lerna_path.exists():
        try:
            lerna_cfg = json.loads(lerna_path.read_text())
        except (json.JSONDecodeError, OSError):
            return base
        patterns = lerna_cfg.get("packages", ["packages/*"])
        packages = resolve_workspace_packages(project_root, patterns)
        return {"is_monorepo": True, "type": "lerna", "workspace_packages": packages}

    return base


def _parse_pnpm_workspace_yaml(content: str) -> list[str]:
    """Minimal YAML parser for pnpm-workspace.yaml 'packages' list."""
    patterns: list[str] = []
    in_packages = False
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed == "packages:":
            in_packages = True
            continue
        if in_packages:
            if trimmed.startswith("-"):
                pat = trimmed[1:].strip().strip("'\"")
                if pat:
                    patterns.append(pat)
            elif trimmed and not trimmed.startswith("#"):
                break
    return patterns


# ---------------------------------------------------------------------------
# Workspace package resolution
# ---------------------------------------------------------------------------

def resolve_workspace_packages(project_root: str, patterns: list[str]) -> list[dict]:
    """Expand glob patterns into concrete workspace packages."""
    packages: list[dict] = []

    for pattern in patterns:
        if pattern.endswith("/*"):
            base_dir = os.path.join(project_root, pattern[:-2])
            if not os.path.isdir(base_dir):
                continue
            try:
                entries = sorted(os.listdir(base_dir))
            except OSError:
                continue
            for name in entries:
                pkg_dir = os.path.join(base_dir, name)
                if not os.path.isdir(pkg_dir):
                    continue
                _try_add_package(packages, project_root, pkg_dir)
        elif "*" not in pattern:
            pkg_dir = os.path.join(project_root, pattern)
            if os.path.isdir(pkg_dir):
                _try_add_package(packages, project_root, pkg_dir)

    return packages


def _try_add_package(packages: list[dict], project_root: str, pkg_dir: str) -> None:
    """Read package.json from *pkg_dir* and append info to *packages*."""
    pkg_json = os.path.join(pkg_dir, "package.json")
    if not os.path.isfile(pkg_json):
        return
    try:
        data = json.loads(Path(pkg_json).read_text())
    except (json.JSONDecodeError, OSError):
        return
    rel = os.path.relpath(pkg_dir, project_root)
    entry = find_typescript_entry(pkg_dir)
    packages.append({"name": data.get("name", rel), "path": rel, "entry_point": entry})


# ---------------------------------------------------------------------------
# TypeScript entry point
# ---------------------------------------------------------------------------

def find_typescript_entry(package_path: str) -> str | None:
    """Return the first TypeScript entry point found, or None."""
    candidates = ["src/index.ts", "src/index.tsx", "lib/index.ts", "index.ts"]
    for c in candidates:
        if os.path.isfile(os.path.join(package_path, c)):
            return c
    return None


# ---------------------------------------------------------------------------
# tsconfig patching
# ---------------------------------------------------------------------------

def patch_tsconfig(worktree_path: str, monorepo_info: dict) -> bool:
    """Patch all tsconfig.json files with paths for workspace packages."""
    tsconfigs = _find_tsconfig_files(worktree_path)
    patched_any = False
    for tc_path in tsconfigs:
        try:
            if _patch_single_tsconfig(tc_path, worktree_path, monorepo_info):
                patched_any = True
        except Exception:
            pass
    return patched_any


def _find_tsconfig_files(root_path: str, _depth: int = 0) -> list[str]:
    """Recursively find tsconfig.json files (max depth 5, skip node_modules/dot dirs)."""
    if _depth > 5:
        return []
    found: list[str] = []
    try:
        entries = os.scandir(root_path)
    except OSError:
        return found
    with entries:
        for entry in entries:
            if entry.is_file(follow_symlinks=False) and entry.name == "tsconfig.json":
                found.append(entry.path)
            elif entry.is_dir(follow_symlinks=False) and not entry.name.startswith(".") and entry.name != "node_modules":
                found.extend(_find_tsconfig_files(entry.path, _depth + 1))
    return found


def _patch_single_tsconfig(tc_path: str, worktree_path: str, monorepo_info: dict) -> bool:
    """Add compilerOptions.paths entries for each workspace package."""
    raw = Path(tc_path).read_text()
    cleaned = strip_json_comments(raw)
    tsconfig = json.loads(cleaned)

    co = tsconfig.setdefault("compilerOptions", {})
    if "baseUrl" not in co:
        co["baseUrl"] = "."
    paths = co.setdefault("paths", {})

    tc_dir = os.path.dirname(tc_path)
    rel_to_root = os.path.relpath(worktree_path, tc_dir)
    added = 0

    for pkg in monorepo_info["workspace_packages"]:
        name = pkg["name"]
        if name in paths:
            continue
        entry = pkg.get("entry_point") or "src/index.ts"
        mapping = os.path.join(rel_to_root, pkg["path"], entry)
        paths[name] = [mapping]
        added += 1

    if added > 0:
        Path(tc_path).write_text(json.dumps(tsconfig, indent=2) + "\n")
    return added > 0


def strip_json_comments(content: str) -> str:
    """Remove // and /* */ comments from JSON-with-comments content."""
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*[\s\S]*?\*/", "", content)
    return content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a SpecLife worktree environment.")
    parser.add_argument("worktree_path", help="Path to the new worktree")
    parser.add_argument("source_root", help="Path to the source project root")
    parser.add_argument("--skip-bootstrap", action="store_true", help="Skip bootstrapping")
    args = parser.parse_args()

    wt = os.path.abspath(args.worktree_path)
    src = os.path.abspath(args.source_root)

    if args.skip_bootstrap:
        print("  Bootstrap skipped (--skip-bootstrap)")
        return

    envs = detect_environments(src)
    if not envs:
        print("  No recognised environments detected.")
        return

    print(f"  Detected environments: {', '.join(e['name'] for e in envs)}")

    for env in envs:
        name = env["name"]
        pm = env.get("package_manager", "")

        if name == "nodejs":
            res = bootstrap_nodejs(wt, src)
        elif name == "python":
            res = bootstrap_python(wt, src)
        elif name in ("go", "rust"):
            lang = "Go" if name == "go" else "Rust"
            print(f"  {lang} ({pm}): uses global cache, no setup needed.")
            continue
        else:
            continue

        status = "OK" if res.get("success") else "FAIL"
        print(f"  {name} ({pm}): [{status}] {res['message']}")

    print("  Bootstrap complete.")


if __name__ == "__main__":
    main()
