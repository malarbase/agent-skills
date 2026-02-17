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
    tags: list[str] | None
    author: str | None
    curator: str | None
    from_repo: str | None
    filter: list[str] | None
    match_all_tags: bool


def _list_curated(repo: str, path: str, ref: str) -> list[str]:
    """Fetch the list of curated skills from GitHub or local filesystem."""
    # Check if we're in the local agent-skills repo
    from metadata_utils import _is_agent_skills_repo, _get_agent_skills_repo_root
    
    if _is_agent_skills_repo():
        # Use local filesystem
        import os
        repo_root = _get_agent_skills_repo_root()
        if not repo_root:
            raise ListError("Could not find agent-skills repo root")
        
        skills_path = os.path.join(repo_root, path)
        
        if not os.path.isdir(skills_path):
            raise ListError(f"Skills path not found: {skills_path}")
        
        try:
            skills = [d for d in os.listdir(skills_path) 
                     if os.path.isdir(os.path.join(skills_path, d)) and not d.startswith('.')]
            return sorted(skills)
        except OSError as exc:
            raise ListError(f"Failed to list local skills: {exc}") from exc
    
    # Use GitHub API
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
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Filter skills by tag(s). Shows skills matching any tag by default.",
    )
    parser.add_argument(
        "--author",
        help="Filter skills by content author (metadata.author field).",
    )
    parser.add_argument(
        "--curator",
        help="Filter skills by curator/contributor (directory name in repo structure).",
    )
    parser.add_argument(
        "--from-repo",
        dest="from_repo",
        help="Filter skills by source repository (metadata.repo field).",
    )
    parser.add_argument(
        "--filter",
        action="append",
        help="Filter by metadata field (format: key=value). Can be specified multiple times.",
    )
    parser.add_argument(
        "--match-all-tags",
        action="store_true",
        help="Require skills to match all specified tags (AND logic instead of OR).",
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
        
        # Filter by metadata if requested
        if args.tags or args.author or args.curator or args.from_repo or args.filter:
            from metadata_utils import filter_skills_by_metadata
            
            # Parse custom filters
            custom_filters = {}
            if args.filter:
                for f in args.filter:
                    if "=" not in f:
                        print(f"Warning: Invalid filter format '{f}', expected key=value", file=sys.stderr)
                        continue
                    key, value = f.split("=", 1)
                    custom_filters[key.strip()] = value.strip()
            
            skills = filter_skills_by_metadata(
                args.repo,
                skills,
                args.ref,
                tags=args.tags,
                author=args.author,
                curator=args.curator,
                from_repo=args.from_repo,
                filters=custom_filters if custom_filters else None,
                match_all_tags=args.match_all_tags,
            )
            
            if not skills:
                criteria = []
                if args.tags:
                    criteria.append(f"tags: {', '.join(args.tags)}")
                if args.author:
                    criteria.append(f"author: {args.author}")
                if args.curator:
                    criteria.append(f"curator: {args.curator}")
                if args.from_repo:
                    criteria.append(f"from-repo: {args.from_repo}")
                if custom_filters:
                    criteria.extend(f"{k}={v}" for k, v in custom_filters.items())
                print(f"No skills found matching {' AND '.join(criteria)}")
                return 0
        
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
            
            # Show active filters
            filters_applied = []
            if args.tags:
                filters_applied.append(f"tags: {', '.join(args.tags)}")
            if args.author:
                filters_applied.append(f"author: {args.author}")
            if args.curator:
                filters_applied.append(f"curator: {args.curator}")
            if args.from_repo:
                filters_applied.append(f"from-repo: {args.from_repo}")
            if args.filter:
                filters_applied.extend(args.filter)
            
            if filters_applied:
                print(f"Filtered by {' AND '.join(filters_applied)}\n")
            
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
