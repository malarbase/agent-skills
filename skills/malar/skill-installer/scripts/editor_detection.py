#!/usr/bin/env python3
"""Editor detection utilities for cross-editor skill installation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class EditorConfig:
    """Configuration for a detected editor."""
    name: str
    display_name: str
    home_dir: str
    skills_dir: str
    is_project: bool = False  # True if this is a project-local skills directory


# Editor configurations in priority order
# Note: Global home directories for each editor
EDITOR_CONFIGS = [
    {
        "name": "claude",
        "display_name": "Claude Code",
        "env_var": "CLAUDE_HOME",
        "default_home": "~/.claude",
    },
    {
        "name": "opencode",
        "display_name": "OpenCode",
        "env_var": "OPENCODE_HOME",
        "default_home": "~/.config/opencode",  # OpenCode uses XDG-style config path
    },
    {
        "name": "antigravity",
        "display_name": "Antigravity",
        "env_var": "GEMINI_HOME",  # Antigravity uses GEMINI_HOME for global config
        "default_home": "~/.gemini",  # But project-local uses .agent
    },
    {
        "name": "gemini-cli",
        "display_name": "Gemini CLI",
        "env_var": "GEMINI_CLI_HOME",
        "default_home": "~/.gemini",
    },
    {
        "name": "cursor",
        "display_name": "Cursor",
        "env_var": "CURSOR_HOME",
        "default_home": "~/.cursor",
    },
    {
        "name": "windsurf",
        "display_name": "Windsurf",
        "env_var": "WINDSURF_HOME",
        "default_home": "~/.windsurf",
    },
    {
        "name": "agent",
        "display_name": "Generic Agent",
        "env_var": "AGENT_HOME",
        "default_home": "~/.agent",
    },
    {
        "name": "agents",
        "display_name": "Agent-Compatible",
        "env_var": "AGENTS_HOME",
        "default_home": "~/.agents",
    },
]


def find_git_root(start_path: Optional[str] = None) -> Optional[str]:
    """
    Find the git repository root from a starting path.
    
    Args:
        start_path: Directory to start searching from (defaults to cwd)
    
    Returns:
        Absolute path to git root, or None if not in a git repo
    """
    path = os.path.abspath(start_path or os.getcwd())
    while path != os.path.dirname(path):  # Stop at filesystem root
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return None


# Project-local directory names for each editor (in priority order)
# Note: Antigravity uses .agent for project config, NOT .gemini
# .gemini is used by Gemini CLI which is a different product
PROJECT_DIRS = [
    {"name": "claude", "display_name": "Claude Code", "project_dir": ".claude"},
    {"name": "opencode", "display_name": "OpenCode", "project_dir": ".opencode"},
    {"name": "antigravity", "display_name": "Antigravity", "project_dir": ".agent"},  # Antigravity uses .agent
    {"name": "gemini-cli", "display_name": "Gemini CLI", "project_dir": ".gemini"},  # Gemini CLI uses .gemini
    {"name": "cursor", "display_name": "Cursor", "project_dir": ".cursor"},
    {"name": "windsurf", "display_name": "Windsurf", "project_dir": ".windsurf"},
    {"name": "agent", "display_name": "Generic Agent", "project_dir": ".agent"},
    {"name": "agents", "display_name": "Agent-Compatible", "project_dir": ".agents"},  # OpenCode/Claude also read .agents/skills/
]


@dataclass
class ProjectSkillsInfo:
    """Information about a detected project-local skills directory."""
    editor_name: str
    display_name: str
    project_dir: str  # e.g., ".claude"
    home_dir: str     # e.g., "/path/to/repo/.claude"
    skills_dir: str   # e.g., "/path/to/repo/.claude/skills"


def detect_project_skills_dir(
    start_path: Optional[str] = None,
    force_editor: Optional[str] = None,
) -> Optional[ProjectSkillsInfo]:
    """
    Detect a project-local skills directory.
    
    Searches for editor-specific project directories at the git root:
    - .claude/skills (Claude Code)
    - .opencode/skills (OpenCode)
    - .gemini/skills (Antigravity)
    - .cursor/skills (Cursor)
    - .windsurf/skills (Windsurf)
    - .agent/skills (Generic)
    
    Args:
        start_path: Directory to start searching from (defaults to cwd)
        force_editor: Force a specific editor's project directory
    
    Returns:
        ProjectSkillsInfo with detected project skills info, or None if not found
    """
    start = start_path or os.getcwd()
    git_root = find_git_root(start)
    base_dir = git_root or os.getcwd()
    
    # If force_editor is specified, look for that specific project dir
    if force_editor:
        for proj in PROJECT_DIRS:
            if proj["name"] == force_editor.lower():
                home_dir = os.path.join(base_dir, proj["project_dir"])
                skills_dir = os.path.join(home_dir, "skills")
                # Return even if it doesn't exist yet (will be created)
                return ProjectSkillsInfo(
                    editor_name=proj["name"],
                    display_name=proj["display_name"],
                    project_dir=proj["project_dir"],
                    home_dir=home_dir,
                    skills_dir=skills_dir,
                )
        # Unknown editor, use custom project dir
        project_dir = f".{force_editor}"
        home_dir = os.path.join(base_dir, project_dir)
        return ProjectSkillsInfo(
            editor_name=force_editor,
            display_name=force_editor.title(),
            project_dir=project_dir,
            home_dir=home_dir,
            skills_dir=os.path.join(home_dir, "skills"),
        )
    
    # Auto-detect: check each editor's project directory
    for proj in PROJECT_DIRS:
        home_dir = os.path.join(base_dir, proj["project_dir"])
        skills_dir = os.path.join(home_dir, "skills")
        
        # Check if skills dir exists, or at least the home dir exists
        if os.path.isdir(skills_dir) or os.path.isdir(home_dir):
            return ProjectSkillsInfo(
                editor_name=proj["name"],
                display_name=proj["display_name"],
                project_dir=proj["project_dir"],
                home_dir=home_dir,
                skills_dir=skills_dir,
            )
    
    return None


def detect_running_editor() -> Optional[str]:
    """
    Detect which editor is currently running by checking runtime indicators.
    
    Returns:
        Editor name (e.g., "cursor", "claude") or None if not detected
    """
    # Check for editor-specific environment variables that indicate runtime
    # OpenCode sets OPENCODE=1 or AGENT=1
    if os.environ.get("OPENCODE") == "1":
        return "opencode"
    
    # Claude Code detection
    if os.environ.get("CLAUDE") == "1" or "CLAUDE_CODE" in os.environ:
        return "claude"
    
    # Cursor detection
    if os.environ.get("CURSOR_AGENT") == "1" or "CURSOR_CLI" in os.environ:
        return "cursor"
    
    # Check for project directory in current workspace
    git_root = find_git_root()
    if git_root:
        for proj in PROJECT_DIRS:
            proj_dir = os.path.join(git_root, proj["project_dir"])
            if os.path.isdir(proj_dir):
                return proj["name"]
    
    return None


def detect_editor(
    force_editor: Optional[str] = None,
    prefer_project: bool = False,
    project_editor: Optional[str] = None,
) -> EditorConfig:
    """
    Detect the active AI coding editor or project skills directory.
    
    Detection priority:
    1. If prefer_project=True, check for project-local skills first
    2. Force-specified editor via parameter
    3. Runtime detection (CURSOR_AGENT, etc.)
    4. Environment variables (CLAUDE_HOME, OPENCODE_HOME, etc.)
    5. Existing home directories on disk
    6. Fallback to generic .agent
    
    Args:
        force_editor: Force a specific editor by name (claude, opencode, project, etc.)
        prefer_project: If True, prefer project-local skills over global
        project_editor: When using project mode, specify which editor's project dir to use
                        (e.g., "claude" for .claude/skills, "gemini" for .gemini/skills)
    
    Returns:
        EditorConfig with detected editor settings
    """
    # Check for project-local skills if preferred or forced
    if prefer_project or force_editor == "project":
        # Use project_editor if specified, otherwise auto-detect
        project_info = detect_project_skills_dir(force_editor=project_editor)
        if project_info:
            return EditorConfig(
                name=project_info.editor_name,
                display_name=f"{project_info.display_name} (Project)",
                home_dir=project_info.home_dir,
                skills_dir=project_info.skills_dir,
                is_project=True,
            )
        # No project dir found, but user requested project mode
        # Default to .agent in git root or cwd
        if force_editor == "project":
            git_root = find_git_root()
            base = git_root or os.getcwd()
            editor_name = project_editor or "agent"
            # Find the project_dir name
            project_dir = ".agent"
            display_name = "Generic Agent"
            for proj in PROJECT_DIRS:
                if proj["name"] == editor_name:
                    project_dir = proj["project_dir"]
                    display_name = proj["display_name"]
                    break
            return EditorConfig(
                name=editor_name,
                display_name=f"{display_name} (Project)",
                home_dir=os.path.join(base, project_dir),
                skills_dir=os.path.join(base, project_dir, "skills"),
                is_project=True,
            )
    
    # If force_editor specified (not "project"), use that
    if force_editor and force_editor != "project":
        for config in EDITOR_CONFIGS:
            if config["name"] == force_editor.lower():
                home = os.environ.get(
                    config["env_var"],
                    os.path.expanduser(config["default_home"])
                )
                return EditorConfig(
                    name=config["name"],
                    display_name=config["display_name"],
                    home_dir=home,
                    skills_dir=os.path.join(home, "skills"),
                )
        # Unknown editor, treat as custom path
        home = os.path.expanduser(f"~/.{force_editor}")
        return EditorConfig(
            name=force_editor,
            display_name=force_editor.title(),
            home_dir=home,
            skills_dir=os.path.join(home, "skills"),
        )
    
    # Check for running editor first
    running = detect_running_editor()
    if running:
        for config in EDITOR_CONFIGS:
            if config["name"] == running:
                home = os.environ.get(
                    config["env_var"],
                    os.path.expanduser(config["default_home"])
                )
                return EditorConfig(
                    name=config["name"],
                    display_name=config["display_name"],
                    home_dir=home,
                    skills_dir=os.path.join(home, "skills"),
                )
    
    # Check environment variables
    for config in EDITOR_CONFIGS:
        env_val = os.environ.get(config["env_var"])
        if env_val:
            home = env_val
            return EditorConfig(
                name=config["name"],
                display_name=config["display_name"],
                home_dir=home,
                skills_dir=os.path.join(home, "skills"),
            )
    
    # Check for existing home directories
    for config in EDITOR_CONFIGS:
        home = os.path.expanduser(config["default_home"])
        if os.path.isdir(home):
            return EditorConfig(
                name=config["name"],
                display_name=config["display_name"],
                home_dir=home,
                skills_dir=os.path.join(home, "skills"),
            )
    
    # Fallback to generic agent
    fallback = EDITOR_CONFIGS[-1]  # "agent" config
    home = os.path.expanduser(fallback["default_home"])
    return EditorConfig(
        name=fallback["name"],
        display_name=fallback["display_name"],
        home_dir=home,
        skills_dir=os.path.join(home, "skills"),
    )


def get_installed_skills(editor: Optional[EditorConfig] = None) -> set[str]:
    """
    Get the set of installed skill names for an editor.
    
    Args:
        editor: EditorConfig to check, or auto-detect if None
    
    Returns:
        Set of installed skill directory names
    """
    if editor is None:
        editor = detect_editor()
    
    skills_dir = editor.skills_dir
    if not os.path.isdir(skills_dir):
        return set()
    
    entries = set()
    for name in os.listdir(skills_dir):
        path = os.path.join(skills_dir, name)
        if os.path.isdir(path):
            entries.add(name)
    return entries


def list_all_editors() -> list[dict]:
    """
    List all known editors with their detection status.
    
    Returns:
        List of dicts with editor info and whether they're detected/installed
    """
    results = []
    for config in EDITOR_CONFIGS:
        home = os.environ.get(
            config["env_var"],
            os.path.expanduser(config["default_home"])
        )
        env_set = config["env_var"] in os.environ
        dir_exists = os.path.isdir(home)
        skills_dir = os.path.join(home, "skills")
        skills_exist = os.path.isdir(skills_dir)
        
        results.append({
            "name": config["name"],
            "display_name": config["display_name"],
            "env_var": config["env_var"],
            "home_dir": home,
            "skills_dir": skills_dir,
            "env_set": env_set,
            "dir_exists": dir_exists,
            "skills_exist": skills_exist,
        })
    
    return results


if __name__ == "__main__":
    import json
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print(json.dumps(list_all_editors(), indent=2))
    else:
        editor = detect_editor(sys.argv[1] if len(sys.argv) > 1 else None)
        print(f"Detected: {editor.display_name}")
        print(f"Home: {editor.home_dir}")
        print(f"Skills: {editor.skills_dir}")
        print(f"Installed: {get_installed_skills(editor)}")
