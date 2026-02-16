#!/usr/bin/env python3
"""SpecLife Init - configure a project for AI editor slash commands.

Ports the `speclife init` CLI command to a standalone Python script
with zero external dependencies (stdlib only).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Editor registry
# ---------------------------------------------------------------------------

EDITORS = {
    "cursor": {
        "name": "Cursor",
        "config_dir": ".cursor",
        "commands_sub": "commands",
        "dash_prefix": True,
        "detect_dirs": [".cursor"],
    },
    "claude-code": {
        "name": "Claude Code",
        "config_dir": ".claude",
        "commands_sub": "commands",
        "dash_prefix": False,
        "detect_dirs": [".claude"],
    },
    "opencode": {
        "name": "OpenCode",
        "config_dir": ".opencode",
        "commands_sub": "commands",
        "dash_prefix": False,
        "detect_dirs": [".opencode"],
    },
    "vscode": {
        "name": "VS Code",
        "config_dir": ".vscode",
        "commands_sub": None,  # special handling
        "dash_prefix": False,
        "detect_dirs": [".vscode"],
    },
    "windsurf": {
        "name": "Windsurf",
        "config_dir": ".windsurf",
        "commands_sub": "commands",
        "dash_prefix": False,
        "detect_dirs": [".windsurf"],
    },
    "gemini": {
        "name": "Gemini CLI",
        "config_dir": ".gemini",
        "commands_sub": "commands",
        "dash_prefix": False,
        "detect_dirs": [".gemini"],
    },
    "qwen": {
        "name": "Qwen Code",
        "config_dir": ".qwen",
        "commands_sub": "commands",
        "dash_prefix": True,
        "detect_dirs": [".qwen"],
    },
    "antigravity": {
        "name": "Antigravity",
        "config_dir": ".agent",
        "commands_sub": "workflows",  # uses workflows/ not commands/
        "dash_prefix": False,         # flat workflow files are the primary format
        "detect_dirs": [".agent"],
    },
}

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def detect_spec_dir(project_root: Path) -> str:
    """Return the spec directory name (openspec or specs), defaulting to openspec."""
    for name in ("openspec", "specs"):
        if (project_root / name).is_dir():
            return name
    return "openspec"


def detect_base_branch(project_root: Path) -> str:
    """Detect the default branch from the remote HEAD, falling back to 'main'."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        if result.returncode == 0:
            ref = result.stdout.strip()  # e.g. refs/remotes/origin/main
            return ref.rsplit("/", 1)[-1]
    except FileNotFoundError:
        pass
    return "main"


def detect_editors(project_root: Path) -> list[str]:
    """Return a list of editor IDs whose config directories exist in the project."""
    detected: list[str] = []
    for editor_id, info in EDITORS.items():
        for d in info["detect_dirs"]:
            if (project_root / d).exists():
                detected.append(editor_id)
                break
    return detected


def discover_commands(commands_dir: Path) -> list[str]:
    """List command names (without .md) inside a commands directory."""
    if not commands_dir.is_dir():
        return []
    return sorted(p.stem for p in commands_dir.iterdir() if p.suffix == ".md")


# ---------------------------------------------------------------------------
# File creation helpers
# ---------------------------------------------------------------------------


def _write_if_new(path: Path, content: str, force: bool, label: str) -> bool:
    """Write *content* to *path* unless it already exists (unless force).

    Returns True if the file was written.
    """
    if path.exists() and not force:
        print(f"  ⏭  {label} (exists, skipping)")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  ✅ {label}")
    return True


def create_specliferc(
    project_root: Path,
    spec_dir: str,
    base_branch: str,
    templates_dir: Path,
    force: bool,
) -> bool:
    """Create .specliferc.yaml from template or inline default."""
    dest = project_root / ".specliferc.yaml"
    template = templates_dir / "specliferc.yaml.template"

    if template.is_file():
        content = template.read_text()
        content = content.replace("{{specDir}}", spec_dir)
        content = content.replace("{{baseBranch}}", base_branch)
    else:
        content = (
            "# SpecLife Configuration\n"
            "# Minimal settings - most values are auto-detected\n"
            "\n"
            f"specDir: {spec_dir}\n"
            "\n"
            "git:\n"
            f"  baseBranch: {base_branch}\n"
            "  branchPrefix: spec/\n"
            "  worktreeDir: worktrees\n"
        )

    return _write_if_new(dest, content, force, ".specliferc.yaml")


def install_slash_commands(
    project_root: Path,
    spec_dir: str,
    templates_dir: Path,
    force: bool,
) -> int:
    """Copy slash-command .md files from templates into the project.

    Returns the number of files copied.
    """
    src_dir = templates_dir / "commands"
    dest_dir = project_root / spec_dir / "commands" / "speclife"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not src_dir.is_dir():
        print(f"  ⚠  No command templates found at {src_dir}")
        return 0

    copied = 0
    for template_file in sorted(src_dir.iterdir()):
        if template_file.suffix != ".md":
            continue
        dest_file = dest_dir / template_file.name
        if dest_file.exists() and not force:
            continue
        shutil.copy2(template_file, dest_file)
        copied += 1

    return copied


def create_speclife_md(
    project_root: Path,
    spec_dir: str,
    templates_dir: Path,
) -> bool:
    """Create {spec_dir}/speclife.md with project context hints."""
    dest = project_root / spec_dir / "speclife.md"
    if dest.exists():
        print(f"  ⏭  {spec_dir}/speclife.md (exists, skipping)")
        return False

    template = templates_dir / "speclife.md.template"
    if template.is_file():
        content = template.read_text().replace("{{specDir}}", spec_dir)
    else:
        content = (
            "# SpecLife Configuration\n"
            "\n"
            "This file provides context for AI agents using speclife slash commands.\n"
            "\n"
            "## Commands\n"
            "\n"
            "- **Test:** `npm test`\n"
            "- **Build:** `npm run build`\n"
            "- **Lint:** `npm run lint`\n"
            "\n"
            "## Release Policy\n"
            "\n"
            "- **Auto-release:** patch and minor versions\n"
            "- **Manual release:** major versions (breaking changes)\n"
            "\n"
            "## Context Files\n"
            "\n"
            "When implementing changes, always read:\n"
            f"- `{spec_dir}/project.md` - project context and conventions\n"
            f"- `{spec_dir}/AGENTS.md` - agent guidelines\n"
            "- `README.md` - project overview\n"
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)
    print(f"  ✅ {spec_dir}/speclife.md")
    return True


def create_release_workflow(
    project_root: Path,
    templates_dir: Path,
    base_branch: str,
) -> bool:
    """Copy the release workflow into .github/workflows/.

    Skips if a release workflow already exists.
    """
    workflows_dir = project_root / ".github" / "workflows"
    for existing in ("release.yml", "speclife-release.yml"):
        if (workflows_dir / existing).is_file():
            print(f"  ⏭  .github/workflows/{existing} (exists, skipping)")
            return False

    src = templates_dir / "speclife-release.yml"
    dest = workflows_dir / "speclife-release.yml"

    if src.is_file():
        workflows_dir.mkdir(parents=True, exist_ok=True)
        content = src.read_text()
        # Replace branch reference if the template uses a placeholder
        content = content.replace("{{baseBranch}}", base_branch)
        dest.write_text(content)
    else:
        # Inline fallback matching the CLI's generated workflow
        workflows_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            "# SpecLife Release Workflow\n"
            "name: Create Release\n"
            "\n"
            "on:\n"
            "  push:\n"
            f"    branches: [{base_branch}]\n"
            "\n"
            "jobs:\n"
            "  release:\n"
            "    runs-on: ubuntu-latest\n"
            "    if: startsWith(github.event.head_commit.message, 'chore(release):')\n"
            "    permissions:\n"
            "      contents: write\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Extract version\n"
            "        id: version\n"
            "        run: |\n"
            '          VERSION=$(echo "${{ github.event.head_commit.message }}" '
            "| grep -oP 'v\\\\d+\\\\.\\\\d+\\\\.\\\\d+')\n"
            '          echo "version=$VERSION" >> $GITHUB_OUTPUT\n'
            "      - name: Create tag\n"
            "        run: |\n"
            '          git config user.name "github-actions[bot]"\n'
            '          git config user.email "github-actions[bot]@users.noreply.github.com"\n'
            "          git tag ${{ steps.version.outputs.version }}\n"
            "          git push origin ${{ steps.version.outputs.version }}\n"
            "      - uses: softprops/action-gh-release@v2\n"
            "        with:\n"
            "          tag_name: ${{ steps.version.outputs.version }}\n"
            "          generate_release_notes: true\n"
        )

    print("  ✅ .github/workflows/speclife-release.yml")
    return True


# ---------------------------------------------------------------------------
# Editor configuration
# ---------------------------------------------------------------------------


def _make_relative_symlink(link_path: Path, target_path: Path, force: bool) -> bool:
    """Create a relative symlink at *link_path* pointing to *target_path*.

    Both paths should be absolute. The stored symlink value will be relative
    so the repo is relocatable. Returns True if created/updated.
    """
    rel = os.path.relpath(target_path, link_path.parent)

    if link_path.is_symlink() or link_path.exists():
        if not force:
            return False
        link_path.unlink()

    link_path.symlink_to(rel)
    return True


def configure_editor(
    editor_id: str,
    project_root: Path,
    spec_dir: str,
    force: bool,
) -> None:
    """Set up symlinks / config for a single editor."""
    info = EDITORS.get(editor_id)
    if info is None:
        print(f"  ⚠  Unknown editor: {editor_id}")
        return

    source_dir = project_root / spec_dir / "commands" / "speclife"

    # --- VS Code: special handling (settings.json, no symlinks) ---
    if editor_id == "vscode":
        _configure_vscode(project_root, spec_dir, force)
        return

    # --- Antigravity: flat workflow symlinks ---
    if editor_id == "antigravity":
        _configure_antigravity(project_root, spec_dir, source_dir, force)
        return

    # --- Standard editors (symlink directory + optional dash-prefix) ---
    config_dir = info["config_dir"]
    commands_base = project_root / config_dir / info["commands_sub"]
    commands_base.mkdir(parents=True, exist_ok=True)

    symlink_dir = commands_base / "speclife"

    try:
        created = _make_relative_symlink(symlink_dir, source_dir, force)
        status = "created" if created else "exists"
        print(f"  ✅ {config_dir}/{info['commands_sub']}/speclife -> .../{spec_dir}/commands/speclife ({status})")
    except OSError as exc:
        print(f"  ⚠  Failed to symlink {symlink_dir}: {exc}")

    # Dash-prefixed symlinks (cursor, qwen)
    if info["dash_prefix"]:
        cmds = discover_commands(source_dir)
        for cmd in cmds:
            dash_file = commands_base / f"speclife-{cmd}.md"
            target_file = commands_base / "speclife" / f"{cmd}.md"
            try:
                created = _make_relative_symlink(dash_file, target_file, force)
                if created:
                    print(f"  ✅ {config_dir}/{info['commands_sub']}/speclife-{cmd}.md")
            except OSError as exc:
                print(f"  ⚠  Failed to create dash symlink for {cmd}: {exc}")


def _configure_vscode(project_root: Path, spec_dir: str, force: bool) -> None:
    """Write VS Code settings.json with speclife markers."""
    vscode_dir = project_root / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    settings_path = vscode_dir / "settings.json"
    settings: dict = {}

    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    if settings.get("speclife.enabled") and not force:
        print("  ⏭  .vscode/settings.json (already configured, skipping)")
        return

    settings["speclife.enabled"] = True
    settings["speclife.specDir"] = spec_dir
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    print("  ✅ .vscode/settings.json")


def _configure_antigravity(
    project_root: Path,
    spec_dir: str,
    source_dir: Path,
    force: bool,
) -> None:
    """Create .agent/workflows/speclife-<cmd>.md symlinks."""
    workflows_dir = project_root / ".agent" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    cmds = discover_commands(source_dir)
    if not cmds:
        print("  ⚠  No commands found to link for Antigravity")
        return

    for cmd in cmds:
        dash_file = workflows_dir / f"speclife-{cmd}.md"
        target_file = source_dir / f"{cmd}.md"
        try:
            created = _make_relative_symlink(dash_file, target_file, force)
            if created:
                print(f"  ✅ .agent/workflows/speclife-{cmd}.md")
        except OSError as exc:
            print(f"  ⚠  Failed to create workflow symlink for {cmd}: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure a project for SpecLife AI editor slash commands.",
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--templates",
        required=True,
        help="Path to the speclife templates directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing configuration files",
    )
    parser.add_argument(
        "--tools",
        default=None,
        help="Comma-separated list of editor IDs to configure",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Accept all defaults (non-interactive)",
    )
    args = parser.parse_args()

    project_root = Path(args.project_dir).resolve()
    templates_dir = Path(args.templates).resolve()

    if not project_root.is_dir():
        print(f"Error: {project_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    if not templates_dir.is_dir():
        print(f"Error: templates directory not found: {templates_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Initializing SpecLife in {project_root}\n")

    # 1. Detect settings
    print("Detecting project settings...")
    spec_dir = detect_spec_dir(project_root)
    base_branch = detect_base_branch(project_root)
    print(f"  • Spec directory: {spec_dir}")
    print(f"  • Base branch:    {base_branch}")
    print()

    # 2. Detect / select editors
    if args.tools:
        selected = [s.strip() for s in args.tools.split(",") if s.strip()]
    else:
        selected = detect_editors(project_root)
        if not selected:
            selected = ["cursor", "claude-code"]
            print(f"  No editors detected — defaulting to: {', '.join(selected)}")
        else:
            print(f"  Detected editors: {', '.join(selected)}")
    print()

    # 3. Create configuration files
    print("Creating configuration files...")
    create_specliferc(project_root, spec_dir, base_branch, templates_dir, args.force)

    copied = install_slash_commands(project_root, spec_dir, templates_dir, args.force)
    if copied:
        print(f"  ✅ Installed {copied} slash command(s) into {spec_dir}/commands/speclife/")
    else:
        print(f"  ⏭  Slash commands already present in {spec_dir}/commands/speclife/")

    create_speclife_md(project_root, spec_dir, templates_dir)
    create_release_workflow(project_root, templates_dir, base_branch)
    print()

    # 4. Configure editors
    print("Configuring editors...")
    for editor_id in selected:
        name = EDITORS.get(editor_id, {}).get("name", editor_id)
        print(f"\n  [{name}]")
        try:
            configure_editor(editor_id, project_root, spec_dir, args.force)
        except Exception as exc:
            print(f"  ⚠  Error configuring {name}: {exc}")
    print()

    # 5. Summary
    print("─" * 50)
    print("✅ SpecLife configured!\n")
    print("Next steps:")
    print("  1. Run /speclife setup to auto-detect project commands")
    print('  2. Use /speclife start "your change" to begin a new change')
    print()


if __name__ == "__main__":
    main()
