#!/usr/bin/env python3
"""Metadata utilities for filtering skills by frontmatter fields."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error

import yaml

from github_utils import github_api_contents_url, github_request


class MetadataError(Exception):
    pass


def _is_agent_skills_repo(path: str | None = None) -> bool:
    """Check if we're inside the agent-skills repository.
    
    Searches upward from the given path (or cwd) to find the repo root.
    """
    check_path = path or os.getcwd()
    
    # Search upward for the git root
    current = os.path.abspath(check_path)
    while current != os.path.dirname(current):  # Stop at filesystem root
        # Look for .git and skills/ directory
        if os.path.isdir(os.path.join(current, ".git")) and \
           os.path.isdir(os.path.join(current, "skills")):
            # Verify it's actually agent-skills by checking for known structure
            installer_path = os.path.join(current, "skills", "malar", "skill-installer")
            if os.path.isdir(installer_path):
                return True
        current = os.path.dirname(current)
    
    return False


def _get_agent_skills_repo_root() -> str | None:
    """Get the root path of the agent-skills repository if we're inside it."""
    current = os.path.abspath(os.getcwd())
    while current != os.path.dirname(current):  # Stop at filesystem root
        if os.path.isdir(os.path.join(current, ".git")) and \
           os.path.isdir(os.path.join(current, "skills")):
            installer_path = os.path.join(current, "skills", "malar", "skill-installer")
            if os.path.isdir(installer_path):
                return current
        current = os.path.dirname(current)
    return None


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from file content and flatten metadata fields."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    
    try:
        fm = yaml.safe_load(match.group(1))
        if not isinstance(fm, dict):
            return {}
    except yaml.YAMLError:
        return {}
    
    # Flatten metadata.* fields into result dict
    result: dict = {}
    for key, value in fm.items():
        if key == "metadata" and isinstance(value, dict):
            # Flatten metadata.* fields
            for mk, mv in value.items():
                result[mk] = mv
        else:
            result[key] = value
    
    return result


def fetch_local_skill_metadata(skill_path: str, repo_root: str | None = None) -> dict:
    """Fetch metadata from local filesystem.
    
    Args:
        skill_path: Path to skill directory (e.g., "skills/waynesutton/convex")
        repo_root: Root of the repository (auto-detected if None)
    
    Returns:
        Dict with flattened metadata fields
    """
    if repo_root is None:
        repo_root = _get_agent_skills_repo_root()
        if repo_root is None:
            return {}
    
    skill_md_path = os.path.join(repo_root, skill_path, "SKILL.md")
    
    if not os.path.exists(skill_md_path):
        return {}
    
    try:
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return {}
    
    return _parse_frontmatter(content)


def fetch_skill_metadata(repo: str, skill_path: str, ref: str) -> dict:
    """Fetch SKILL.md and parse frontmatter metadata.
    
    Automatically uses local filesystem if inside agent-skills repo,
    otherwise uses GitHub API.
    
    Returns flat dict with both top-level and metadata.* fields.
    Example: {name, description, author, tags, repo, ...}
    
    Args:
        repo: GitHub repo in owner/repo format
        skill_path: Path to skill directory (e.g., "skills/waynesutton/convex")
        ref: Git ref (branch/tag)
    
    Returns:
        Dict with flattened metadata fields
    """
    # Check if we're in the local agent-skills repo
    if _is_agent_skills_repo():
        return fetch_local_skill_metadata(skill_path)
    
    # Otherwise use GitHub API
    skill_md_path = f"{skill_path}/SKILL.md"
    api_url = github_api_contents_url(repo, skill_md_path, ref)
    
    try:
        payload = github_request(api_url)
    except urllib.error.HTTPError as exc:
        # Skill might not have SKILL.md or path is wrong
        return {}
    
    try:
        data = json.loads(payload.decode("utf-8"))
        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8")
        else:
            content = data.get("content", "")
    except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
        return {}
    
    return _parse_frontmatter(content)


def filter_skills_by_metadata(
    repo: str,
    skills: list[str],
    ref: str,
    tags: list[str] | None = None,
    author: str | None = None,
    curator: str | None = None,
    from_repo: str | None = None,
    filters: dict[str, str] | None = None,
    match_all_tags: bool = False,
) -> list[str]:
    """Filter skills by any combination of metadata criteria.
    
    Automatically uses local filesystem if inside agent-skills repo,
    otherwise uses GitHub API.
    
    Args:
        repo: GitHub repo in owner/repo format
        skills: List of skill names to filter (may be author dirs or skill dirs)
        ref: Git ref (branch/tag)
        tags: Filter by tag(s) - OR logic by default, AND if match_all_tags=True
        author: Filter by metadata.author field (content creator)
        curator: Filter by curator (directory name - first path segment)
        from_repo: Filter by metadata.repo field (source repository)
        filters: Dict of key=value pairs for custom metadata filtering
        match_all_tags: If True, require ALL tags (AND logic)
    
    Returns:
        List of skill names matching ALL specified filters
    """
    matching = []
    base_path = "skills"
    
    # Check if we're in local repo
    is_local = _is_agent_skills_repo()
    repo_root = _get_agent_skills_repo_root() if is_local else None
    
    # Enumerate all skill paths
    all_skill_paths = []
    
    if is_local and repo_root:
        # Use local filesystem
        for item in skills:
            item_path = os.path.join(repo_root, base_path, item)
            if os.path.isdir(item_path):
                # Check if it's an author directory with subdirectories
                try:
                    subdirs = [d for d in os.listdir(item_path) 
                              if os.path.isdir(os.path.join(item_path, d)) and not d.startswith('.')]
                    if subdirs:
                        # It's an author directory
                        for skill_name in subdirs:
                            all_skill_paths.append((f"{item}/{skill_name}", skill_name))
                    else:
                        # Direct skill directory
                        all_skill_paths.append((item, item))
                except OSError:
                    all_skill_paths.append((item, item))
    else:
        # Use GitHub API
        import json
        for item in skills:
            try:
                api_url = github_api_contents_url(repo, f"{base_path}/{item}", ref)
                payload = github_request(api_url)
                data = json.loads(payload.decode("utf-8"))
                if isinstance(data, list):
                    # It's an author directory, get the skills inside
                    for skill_item in data:
                        if skill_item.get("type") == "dir":
                            skill_name = skill_item["name"]
                            all_skill_paths.append((f"{item}/{skill_name}", skill_name))
            except (urllib.error.HTTPError, json.JSONDecodeError):
                # Not an author dir, treat as direct skill
                all_skill_paths.append((item, item))
    
    # Now filter the skills
    for skill_path, skill_name in all_skill_paths:
        # Extract curator from path (first segment before /)
        path_curator = skill_path.split("/")[0] if "/" in skill_path else None
        
        # Apply curator filter first (path-based, no API call needed)
        if curator and path_curator:
            if path_curator.lower() != curator.lower():
                continue
        
        # Fetch metadata for this skill
        full_path = f"{base_path}/{skill_path}"
        metadata = fetch_skill_metadata(repo, full_path, ref)
        
        if not metadata:
            # Skip skills without valid metadata
            continue
        
        # Apply filters (AND logic between different filter types)
        matches = True
        
        # 1. Filter by tags
        if tags and matches:
            skill_tags = metadata.get("tags", [])
            if not isinstance(skill_tags, list):
                # Handle case where tags might be a string or other type
                skill_tags = [skill_tags] if skill_tags else []
            
            if match_all_tags:
                # AND logic: skill must have ALL specified tags
                matches = all(tag in skill_tags for tag in tags)
            else:
                # OR logic: skill must have AT LEAST ONE specified tag
                matches = any(tag in skill_tags for tag in tags)
        
        # 2. Filter by author (content creator)
        if author and matches:
            matches = metadata.get("author", "").lower() == author.lower()
        
        # 3. Filter by source repo
        if from_repo and matches:
            skill_repo = metadata.get("repo", "")
            matches = from_repo.lower() in skill_repo.lower()
        
        # 4. Filter by custom metadata fields
        if filters and matches:
            for key, value in filters.items():
                metadata_value = metadata.get(key, "")
                # Convert to string for comparison
                if str(metadata_value).lower() != value.lower():
                    matches = False
                    break
        
        if matches:
            matching.append(skill_name)
    
    return matching
