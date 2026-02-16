#!/usr/bin/env python3
"""List curated skills from a GitHub repo path with editor detection."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error

from editor_detection import detect_editor, get_installed_skills
from github_utils import github_api_contents_url, github_request

DEFAULT_REPO = "anthropics/skills"
DEFAULT_PATH = "skills"
DEFAULT_REF = "main"


class ListError(Exception):
    pass


class Args(argparse.Namespace):
    repo: str
    path: str
    ref: str
    format: str
    editor: str | None
    project: bool
    project_editor: str | None


def _list_curated(repo: str, path: str, ref: str) -> list[str]:
    """Fetch the list of curated skills from GitHub."""
    api_url = github_api_contents_url(repo, path, ref)
    try:
        payload = github_request(api_url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ListError(
                "Curated skills path not found: "
                f"https://github.com/{repo}/tree/{ref}/{path}"
            ) from exc
        raise ListError(f"Failed to fetch curated skills: HTTP {exc.code}") from exc
    
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, list):
        raise ListError("Unexpected curated listing response.")
    
    skills = [item["name"] for item in data if item.get("type") == "dir"]
    return sorted(skills)


def _parse_args(argv: list[str]) -> Args:
    parser = argparse.ArgumentParser(
        description="List curated skills from GitHub.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # List skills from anthropics/skills
  %(prog)s --format json          # JSON output
  %(prog)s --repo myorg/skills    # Custom repo
  %(prog)s --editor opencode      # Force OpenCode detection
  %(prog)s --project              # Show install status for project skills
        """,
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"GitHub repo in owner/repo format (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--path",
        default=DEFAULT_PATH,
        help=f"Path within repo containing skills (default: {DEFAULT_PATH})",
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"Git ref (branch/tag) (default: {DEFAULT_REF})",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--editor",
        help="Force global editor detection (claude, opencode, antigravity, cursor, windsurf, agent)",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        default=False,
        help="Check install status against project-local skills",
    )
    parser.add_argument(
        "--project-editor",
        dest="project_editor",
        default=None,
        help="Which editor's project dir to check: claude (.claude), opencode (.opencode), "
             "antigravity (.gemini), cursor (.cursor), windsurf (.windsurf), agent (.agent)",
    )
    return parser.parse_args(argv, namespace=Args())


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    
    try:
        # Detect editor (project flag enables project-local check)
        if args.project or args.project_editor:
            editor = detect_editor("project", project_editor=args.project_editor)
        else:
            editor = detect_editor(args.editor)
        
        # Fetch skills list
        skills = _list_curated(args.repo, args.path, args.ref)
        installed = get_installed_skills(editor)
        
        if args.format == "json":
            payload = {
                "editor": {
                    "name": editor.name,
                    "display_name": editor.display_name,
                    "skills_dir": editor.skills_dir,
                },
                "repo": args.repo,
                "skills": [
                    {"name": name, "installed": name in installed}
                    for name in skills
                ],
            }
            print(json.dumps(payload, indent=2))
        else:
            print(f"\nAvailable skills from {args.repo}:\n")
            for idx, name in enumerate(skills, start=1):
                suffix = " (already installed)" if name in installed else ""
                print(f"  {idx}. {name}{suffix}")
            print(f"\nDetected editor: {editor.display_name} ({editor.skills_dir})")
            print("\nWhich skills would you like to install?")
        
        return 0
    
    except ListError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
