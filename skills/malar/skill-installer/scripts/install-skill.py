#!/usr/bin/env python3
"""Install a skill from GitHub into the detected editor's skills directory."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import zipfile
from dataclasses import dataclass

from editor_detection import detect_editor, EditorConfig
from github_utils import github_request

DEFAULT_REF = "main"
DEFAULT_REPO = "anthropics/skills"
DEFAULT_PATH = "skills"


@dataclass
class Args:
    skill: str | None = None
    tags: list[str] | None = None     # NEW
    author: str | None = None          # NEW
    curator: str | None = None         # NEW
    from_repo: str | None = None       # NEW
    filter: list[str] | None = None    # NEW (key=value pairs)
    match_all_tags: bool = False       # NEW
    url: str | None = None
    repo: str | None = None
    path: list[str] | None = None
    ref: str = DEFAULT_REF
    dest: str | None = None
    name: str | None = None
    method: str = "auto"
    editor: str | None = None
    project: bool = False  # Install to project-local skills
    project_editor: str | None = None  # Which editor's project dir to use


@dataclass
class Source:
    owner: str
    repo: str
    ref: str
    paths: list[str]
    repo_url: str | None = None


class InstallError(Exception):
    pass


def _tmp_root() -> str:
    """Get a temp directory for downloads."""
    base = os.path.join(tempfile.gettempdir(), "skill-installer")
    os.makedirs(base, exist_ok=True)
    return base


def _parse_github_url(url: str, default_ref: str) -> tuple[str, str, str, str | None]:
    """Parse a GitHub URL into components."""
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "github.com":
        raise InstallError("Only GitHub URLs are supported for download mode.")
    
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise InstallError("Invalid GitHub URL.")
    
    owner, repo = parts[0], parts[1]
    ref = default_ref
    subpath = ""
    
    if len(parts) > 2:
        if parts[2] in ("tree", "blob"):
            if len(parts) < 4:
                raise InstallError("GitHub URL missing ref or path.")
            ref = parts[3]
            subpath = "/".join(parts[4:])
        else:
            subpath = "/".join(parts[2:])
    
    return owner, repo, ref, subpath or None


def _download_repo_zip(owner: str, repo: str, ref: str, dest_dir: str) -> str:
    """Download and extract a repo zip archive."""
    zip_url = f"https://codeload.github.com/{owner}/{repo}/zip/{ref}"
    zip_path = os.path.join(dest_dir, "repo.zip")
    
    try:
        payload = github_request(zip_url)
    except urllib.error.HTTPError as exc:
        raise InstallError(f"Download failed: HTTP {exc.code}") from exc
    
    with open(zip_path, "wb") as f:
        f.write(payload)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        _safe_extract_zip(zf, dest_dir)
        top_levels = {name.split("/")[0] for name in zf.namelist() if name}
    
    if not top_levels:
        raise InstallError("Downloaded archive was empty.")
    if len(top_levels) != 1:
        raise InstallError("Unexpected archive layout.")
    
    return os.path.join(dest_dir, next(iter(top_levels)))


def _safe_extract_zip(zf: zipfile.ZipFile, dest_dir: str) -> None:
    """Safely extract a zip file, preventing path traversal."""
    dest_root = os.path.realpath(dest_dir)
    for info in zf.infolist():
        extracted_path = os.path.realpath(os.path.join(dest_dir, info.filename))
        if extracted_path == dest_root or extracted_path.startswith(dest_root + os.sep):
            continue
        raise InstallError("Archive contains files outside the destination.")
    zf.extractall(dest_dir)


def _run_git(args: list[str]) -> None:
    """Run a git command and raise on failure."""
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise InstallError(result.stderr.strip() or "Git command failed.")


def _git_sparse_checkout(repo_url: str, ref: str, paths: list[str], dest_dir: str) -> str:
    """Clone a repo with sparse checkout for specific paths."""
    repo_dir = os.path.join(dest_dir, "repo")
    clone_cmd = [
        "git", "clone",
        "--filter=blob:none",
        "--depth", "1",
        "--sparse",
        "--single-branch",
        "--branch", ref,
        repo_url,
        repo_dir,
    ]
    
    try:
        _run_git(clone_cmd)
    except InstallError:
        # Try without --branch (some refs need checkout after clone)
        _run_git([
            "git", "clone",
            "--filter=blob:none",
            "--depth", "1",
            "--sparse",
            "--single-branch",
            repo_url,
            repo_dir,
        ])
    
    _run_git(["git", "-C", repo_dir, "sparse-checkout", "set", *paths])
    _run_git(["git", "-C", repo_dir, "checkout", ref])
    return repo_dir


def _validate_relative_path(path: str) -> None:
    """Ensure a path is relative and doesn't escape."""
    if os.path.isabs(path) or os.path.normpath(path).startswith(".."):
        raise InstallError("Skill path must be a relative path inside the repo.")


def _validate_skill_name(name: str) -> None:
    """Validate a skill name is safe."""
    altsep = os.path.altsep
    if not name or os.path.sep in name or (altsep and altsep in name):
        raise InstallError("Skill name must be a single path segment.")
    if name in (".", ".."):
        raise InstallError("Invalid skill name.")


def _validate_skill(path: str) -> None:
    """Ensure a directory is a valid skill."""
    if not os.path.isdir(path):
        raise InstallError(f"Skill path not found: {path}")
    skill_md = os.path.join(path, "SKILL.md")
    if not os.path.isfile(skill_md):
        raise InstallError("SKILL.md not found in selected skill directory.")


def _copy_skill(src: str, dest_dir: str) -> None:
    """Copy a skill to the destination."""
    os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
    if os.path.exists(dest_dir):
        raise InstallError(f"Destination already exists: {dest_dir}")
    shutil.copytree(src, dest_dir)


def _build_repo_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}.git"


def _build_repo_ssh(owner: str, repo: str) -> str:
    return f"git@github.com:{owner}/{repo}.git"


def _prepare_repo(source: Source, method: str, tmp_dir: str) -> str:
    """Prepare the repo (download or clone) and return the root path."""
    if method in ("download", "auto"):
        try:
            return _download_repo_zip(source.owner, source.repo, source.ref, tmp_dir)
        except InstallError as exc:
            if method == "download":
                raise
            err_msg = str(exc)
            # Auth errors should fall back to git
            if "HTTP 401" in err_msg or "HTTP 403" in err_msg or "HTTP 404" in err_msg:
                pass
            else:
                raise
    
    if method in ("git", "auto"):
        repo_url = source.repo_url or _build_repo_url(source.owner, source.repo)
        try:
            return _git_sparse_checkout(repo_url, source.ref, source.paths, tmp_dir)
        except InstallError:
            # Try SSH fallback
            repo_url = _build_repo_ssh(source.owner, source.repo)
            return _git_sparse_checkout(repo_url, source.ref, source.paths, tmp_dir)
    
    raise InstallError("Unsupported method.")


def _resolve_source(args: Args) -> Source:
    """Resolve arguments into a Source object."""
    # NEW: Handle metadata filtering (--tags, --author, --curator, --from-repo, --filter)
    if args.tags or args.author or args.curator or args.from_repo or args.filter:
        from metadata_utils import filter_skills_by_metadata
        from github_utils import github_api_contents_url, github_request
        import json
        
        # Default to curated repo
        repo = args.repo or DEFAULT_REPO
        path = DEFAULT_PATH
        ref = args.ref
        
        # Fetch all skills
        api_url = github_api_contents_url(repo, path, ref)
        payload = github_request(api_url)
        data = json.loads(payload.decode("utf-8"))
        all_skills = [item["name"] for item in data if item.get("type") == "dir"]
        
        # Parse custom filters
        custom_filters = {}
        if args.filter:
            for f in args.filter:
                if "=" not in f:
                    raise InstallError(f"Invalid filter format '{f}', expected key=value")
                key, value = f.split("=", 1)
                custom_filters[key.strip()] = value.strip()
        
        # Filter by metadata
        matching = filter_skills_by_metadata(
            repo,
            all_skills,
            ref,
            tags=args.tags,
            author=args.author,
            curator=args.curator,
            from_repo=args.from_repo,
            filters=custom_filters if custom_filters else None,
            match_all_tags=args.match_all_tags,
        )
        
        if not matching:
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
            raise InstallError(f"No skills found matching {' AND '.join(criteria)}")
        
        repo_parts = repo.split("/")
        return Source(
            owner=repo_parts[0],
            repo=repo_parts[1],
            ref=ref,
            paths=[f"{path}/{name}" for name in matching],
        )
    
    # Handle --skill (curated skill by name)
    if args.skill:
        return Source(
            owner="anthropics",
            repo="skills",
            ref=args.ref,
            paths=[f"{DEFAULT_PATH}/{args.skill}"],
        )
    
    # Handle --url
    if args.url:
        owner, repo, ref, url_path = _parse_github_url(args.url, args.ref)
        if args.path is not None:
            paths = list(args.path)
        elif url_path:
            paths = [url_path]
        else:
            paths = []
        if not paths:
            raise InstallError("Missing --path for GitHub URL.")
        return Source(owner=owner, repo=repo, ref=ref, paths=paths)
    
    # Handle --repo
    if not args.repo:
        raise InstallError("Provide --skill, --repo, or --url.")
    
    if "://" in args.repo:
        return _resolve_source(
            Args(url=args.repo, repo=None, path=args.path, ref=args.ref)
        )
    
    repo_parts = [p for p in args.repo.split("/") if p]
    if len(repo_parts) != 2:
        raise InstallError("--repo must be in owner/repo format.")
    if not args.path:
        raise InstallError("Missing --path for --repo.")
    
    return Source(
        owner=repo_parts[0],
        repo=repo_parts[1],
        ref=args.ref,
        paths=list(args.path),
    )


def _parse_args(argv: list[str]) -> Args:
    parser = argparse.ArgumentParser(
        description="Install skills from GitHub into your editor's skills directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --skill doc-coauthoring          # Install curated skill by name
  %(prog)s --tags convex                    # Install all skills tagged "convex"
  %(prog)s --author Convex                  # Install all skills by content author
  %(prog)s --curator waynesutton            # Install all skills by curator
  %(prog)s --from-repo github.com/waynesutton/convexskills  # Install by source repo
  %(prog)s --tags convex --author Convex    # Install Convex's convex-tagged skills
  %(prog)s --tags convex backend --match-all-tags  # Skills with BOTH tags
  %(prog)s --filter "license=MIT"           # Install skills with MIT license
  %(prog)s --tags backend --filter "repo=github.com/myorg/skills"  # Combined filters
  %(prog)s --repo anthropics/skills --path skills/skill-creator
  %(prog)s --url https://github.com/anthropics/skills/tree/main/skills/docx
  %(prog)s --skill docx --editor opencode   # Force OpenCode global destination
  %(prog)s --skill docx --project           # Install to project (auto-detect editor dir)
        """,
    )
    parser.add_argument(
        "--skill",
        help="Install a curated skill by name (from anthropics/skills)",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repo in owner/repo format",
    )
    parser.add_argument(
        "--url",
        help="Full GitHub URL to skill directory",
    )
    parser.add_argument(
        "--path",
        nargs="+",
        help="Path(s) to skill(s) inside the repo",
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"Git ref (branch/tag) (default: {DEFAULT_REF})",
    )
    parser.add_argument(
        "--dest",
        help="Override destination skills directory",
    )
    parser.add_argument(
        "--name",
        help="Custom skill name (defaults to path basename)",
    )
    parser.add_argument(
        "--method",
        choices=["auto", "download", "git"],
        default="auto",
        help="Download method (default: auto)",
    )
    parser.add_argument(
        "--editor",
        help="Force global editor detection (claude, opencode, antigravity, cursor, windsurf, agent)",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Install to project-local skills directory (in git root)",
    )
    parser.add_argument(
        "--project-editor",
        dest="project_editor",
        help="Which editor's project dir to use: claude (.claude), opencode (.opencode), "
             "antigravity (.gemini), cursor (.cursor), windsurf (.windsurf), agent (.agent)",
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Install all skills matching tag(s) from the curated repo",
    )
    parser.add_argument(
        "--author",
        help="Install all skills by content author (metadata.author field)",
    )
    parser.add_argument(
        "--curator",
        help="Install all skills by curator/contributor (directory name in repo structure)",
    )
    parser.add_argument(
        "--from-repo",
        dest="from_repo",
        help="Install all skills from source repository (metadata.repo field)",
    )
    parser.add_argument(
        "--filter",
        action="append",
        help="Filter by metadata field (format: key=value). Can be specified multiple times for AND logic.",
    )
    parser.add_argument(
        "--match-all-tags",
        action="store_true",
        help="Require skills to match all specified tags (AND logic instead of OR)",
    )
    return parser.parse_args(argv, namespace=Args())


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    
    try:
        # Detect editor (project flag enables project-local installation)
        if args.project or args.project_editor:
            editor = detect_editor("project", project_editor=args.project_editor)
        else:
            editor = detect_editor(args.editor)
        
        # Resolve source
        source = _resolve_source(args)
        source.ref = source.ref or args.ref
        
        if not source.paths:
            raise InstallError("No skill paths provided.")
        
        for path in source.paths:
            _validate_relative_path(path)
        
        # Determine destination
        dest_root = args.dest or editor.skills_dir
        
        # Download/clone and install
        tmp_dir = tempfile.mkdtemp(prefix="skill-install-", dir=_tmp_root())
        try:
            repo_root = _prepare_repo(source, args.method, tmp_dir)
            installed = []
            
            for path in source.paths:
                skill_name = args.name if len(source.paths) == 1 else None
                skill_name = skill_name or os.path.basename(path.rstrip("/"))
                
                _validate_skill_name(skill_name)
                if not skill_name:
                    raise InstallError("Unable to derive skill name.")
                
                dest_dir = os.path.join(dest_root, skill_name)
                if os.path.exists(dest_dir):
                    raise InstallError(f"Destination already exists: {dest_dir}")
                
                skill_src = os.path.join(repo_root, path)
                _validate_skill(skill_src)
                _copy_skill(skill_src, dest_dir)
                installed.append((skill_name, dest_dir))
        finally:
            if os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
        
        # Report results
        print(f"\nInstalled to {editor.display_name} ({dest_root}):\n")
        for skill_name, dest_dir in installed:
            print(f"  ✓ {skill_name} → {dest_dir}")
        
        print(f"\nRestart your editor to pick up new skills.")
        return 0
    
    except InstallError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
