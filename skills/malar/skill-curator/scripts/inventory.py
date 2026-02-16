#!/usr/bin/env python3
"""Scan skills directory and update README.md inventory section."""

from __future__ import annotations

import os
import re

from skill_utils import extract_metadata


def scan_skills(repo_root: str) -> dict[str, list[dict[str, str]]]:
    """Scan skills/ dir, return {author: [skill_info, ...]} sorted."""
    skills_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_dir):
        return {}

    result: dict[str, list[dict[str, str]]] = {}
    for author in sorted(os.listdir(skills_dir)):
        author_dir = os.path.join(skills_dir, author)
        if not os.path.isdir(author_dir) or author.startswith("."):
            continue
        skills_list: list[dict[str, str]] = []
        for skill_name in sorted(os.listdir(author_dir)):
            skill_dir = os.path.join(author_dir, skill_name)
            if not os.path.isdir(skill_dir) or skill_name.startswith("."):
                continue
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            meta = extract_metadata(skill_dir)
            desc = meta.get("description", "").split(".")[0]  # First sentence
            skills_list.append({"name": skill_name, "description": desc})
        if skills_list:
            result[author] = skills_list
    return result


def generate_inventory_section(skills: dict[str, list[dict[str, str]]]) -> str:
    """Generate markdown for the Skills Inventory section."""
    lines: list[str] = ["## Skills Inventory", ""]
    for author, skill_list in sorted(skills.items()):
        lines.append(f"### {author} ({len(skill_list)} skill{'s' if len(skill_list) != 1 else ''})")
        for s in skill_list:
            desc = s["description"]
            lines.append(f"- **{s['name']}** - {desc}" if desc else f"- **{s['name']}**")
        lines.append("")
    return "\n".join(lines)


def update_readme(repo_root: str) -> bool:
    """Update README.md inventory section. Return True if changed."""
    readme_path = os.path.join(repo_root, "README.md")
    if not os.path.isfile(readme_path):
        return False

    with open(readme_path, "r") as f:
        content = f.read()

    skills = scan_skills(repo_root)
    new_section = generate_inventory_section(skills)

    # Replace existing inventory section (from ## Skills Inventory to next ## or end)
    pattern = r"## Skills Inventory\n.*?(?=\n## (?!Skills Inventory)|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        new_content = content[: match.start()] + new_section + content[match.end():]
    else:
        # Append after first heading block
        new_content = content.rstrip() + "\n\n" + new_section + "\n"

    if new_content == content:
        return False

    with open(readme_path, "w") as f:
        f.write(new_content)
    return True


if __name__ == "__main__":
    import sys

    repo_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    changed = update_readme(repo_root)
    if changed:
        print("README.md inventory updated.")
    else:
        print("README.md inventory already up to date.")
