#!/usr/bin/env python3
"""Skill Curator CLI — publish and maintain skills in agent-skills repo."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse

import github_utils as gh
import skill_utils
from inventory import update_readme

TARGET_REPO = os.environ.get("SKILL_CURATOR_REPO", "malarbase/agent-skills")
STAGING_DIR = os.path.expanduser(
    os.environ.get("SKILL_CURATOR_STAGING", "~/.cache/skill-curator/staging")
)
CLONE_DIR = os.path.expanduser(
    os.environ.get("SKILL_CURATOR_CLONE", "~/.cache/skill-curator/repo")
)


class CuratorError(Exception):
    pass


# ── Source parsing ──────────────────────────────────────────────────────


def _parse_source(source: str) -> dict:
    """Parse a source string into {type, owner, repo, ref, path} or {type, local_path}."""
    # Local path
    if os.path.exists(source) or source.startswith(("./", "/", "~/")):
        return {"type": "local", "local_path": os.path.expanduser(source)}

    # GitHub URL
    if source.startswith("https://github.com/"):
        parsed = urllib.parse.urlparse(source)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            raise CuratorError(f"Invalid GitHub URL: {source}")
        owner, repo = parts[0], parts[1]
        ref = "main"
        path = ""
        if len(parts) > 2 and parts[2] in ("tree", "blob"):
            ref = parts[3] if len(parts) > 3 else "main"
            path = "/".join(parts[4:])
        elif len(parts) > 2:
            path = "/".join(parts[2:])
        return {"type": "github", "owner": owner, "repo": repo, "ref": ref, "path": path}

    # Repo:path shorthand (owner/repo:path/to/skill)
    if ":" in source and "/" in source.split(":")[0]:
        repo_part, path = source.split(":", 1)
        repo_parts = repo_part.split("/")
        if len(repo_parts) == 2:
            return {
                "type": "github",
                "owner": repo_parts[0],
                "repo": repo_parts[1],
                "ref": "main",
                "path": path,
            }

    raise CuratorError(
        f"Cannot parse source: {source}\n"
        "Expected: GitHub URL, owner/repo:path, or local path"
    )


def _fetch_from_github(source: dict, dest: str) -> str:
    """Clone a skill from GitHub to dest. Returns path to skill directory."""
    repo = f"{source['owner']}/{source['repo']}"
    ref = source["ref"]
    skill_path = source["path"]

    repo_url = f"https://github.com/{repo}.git"
    repo_dir = os.path.join(dest, "repo")

    subprocess.run(
        [
            "git", "clone", "--filter=blob:none", "--depth=1",
            "--sparse", "--single-branch", "--branch", ref,
            repo_url, repo_dir,
        ],
        capture_output=True, text=True, check=True,
    )
    if skill_path:
        subprocess.run(
            ["git", "-C", repo_dir, "sparse-checkout", "set", skill_path],
            capture_output=True, text=True, check=True,
        )

    return os.path.join(repo_dir, skill_path) if skill_path else repo_dir


def _skill_name_from_path(path: str) -> str:
    """Derive skill name from a path."""
    return os.path.basename(path.rstrip("/"))


def _is_agent_skills_repo(path: str) -> bool:
    """Check if the given path is the agent-skills repository."""
    if not os.path.isdir(os.path.join(path, ".git")):
        return False
    
    try:
        result = subprocess.run(
            ["git", "-C", path, "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        )
        remote_url = result.stdout.strip()
        return "agent-skills" in remote_url and TARGET_REPO.split("/")[0] in remote_url
    except subprocess.CalledProcessError:
        return False


# ── Commands ────────────────────────────────────────────────────────────


def cmd_import(
    source: str,
    author: str | None,
    ref: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """Fetch skill from source and stage locally."""
    parsed = _parse_source(source)
    if ref and parsed["type"] == "github":
        parsed["ref"] = ref

    author = author or os.environ.get("USER", "unknown")

    with tempfile.TemporaryDirectory(prefix="skill-curator-") as tmp:
        if parsed["type"] == "local":
            skill_dir = parsed["local_path"]
        else:
            skill_dir = _fetch_from_github(parsed, tmp)

        errors = skill_utils.validate_skill(skill_dir)
        if errors:
            print("Validation warnings:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)

        skill_name = _skill_name_from_path(skill_dir)
        stage_dest = os.path.join(STAGING_DIR, author, skill_name)

        if os.path.exists(stage_dest):
            shutil.rmtree(stage_dest)

        os.makedirs(os.path.dirname(stage_dest), exist_ok=True)
        shutil.copytree(skill_dir, stage_dest)

        # Ensure metadata (author, repo, tags under metadata:)
        source_repo = f"github.com/{parsed['owner']}/{parsed['repo']}" if parsed["type"] == "github" else None
        skill_utils.ensure_metadata(stage_dest, author, source_repo, tags=tags)

    print(f"Staged: {author}/{skill_name} → {stage_dest}")
    print("Run 'curator.py validate' to check, then 'curator.py ship' to publish.")


def cmd_validate(path: str | None) -> None:
    """Validate staged skills or a specific path."""
    targets: list[tuple[str, str]] = []

    if path:
        targets.append((_skill_name_from_path(path), path))
    else:
        if not os.path.isdir(STAGING_DIR):
            print("No staged skills found.")
            return
        for author in sorted(os.listdir(STAGING_DIR)):
            author_dir = os.path.join(STAGING_DIR, author)
            if not os.path.isdir(author_dir):
                continue
            for skill_name in sorted(os.listdir(author_dir)):
                skill_dir = os.path.join(author_dir, skill_name)
                if os.path.isdir(skill_dir):
                    targets.append((f"{author}/{skill_name}", skill_dir))

    if not targets:
        print("Nothing to validate.")
        return

    all_ok = True
    for label, skill_dir in targets:
        errors = skill_utils.validate_skill(skill_dir)
        if errors:
            all_ok = False
            print(f"✗ {label}:")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"✓ {label}: OK")

    if not all_ok:
        sys.exit(1)


def cmd_ship(draft: bool = False, dry_run: bool = False) -> None:
    """Create branch, commit staged skills, push, and open PR."""
    if not gh.check_auth():
        raise CuratorError("Not authenticated. Run: gh auth login")

    # Collect staged skills
    staged: list[tuple[str, str, str]] = []  # (author, name, path)
    if not os.path.isdir(STAGING_DIR):
        raise CuratorError("No staged skills. Run 'curator.py import' first.")

    for author in sorted(os.listdir(STAGING_DIR)):
        author_dir = os.path.join(STAGING_DIR, author)
        if not os.path.isdir(author_dir):
            continue
        for skill_name in sorted(os.listdir(author_dir)):
            skill_dir = os.path.join(author_dir, skill_name)
            if os.path.isdir(skill_dir):
                errors = skill_utils.validate_skill(skill_dir)
                if errors:
                    raise CuratorError(
                        f"Validation failed for {author}/{skill_name}:\n"
                        + "\n".join(f"  - {e}" for e in errors)
                    )
                staged.append((author, skill_name, skill_dir))

    if not staged:
        raise CuratorError("No staged skills found.")

    # Determine branch name and commit message
    if len(staged) == 1:
        author, name, _ = staged[0]
        branch = f"curate/add-{name}"
        commit_msg = f"feat(skills): add {author}/{name}"
        pr_title = commit_msg
    else:
        branch = f"curate/add-batch-{int(time.time())}"
        names = ", ".join(f"{a}/{n}" for a, n, _ in staged)
        commit_msg = f"feat(skills): add {len(staged)} skills\n\nSkills: {names}"
        pr_title = f"feat(skills): add {len(staged)} skills"

    if dry_run:
        print(f"[dry-run] Would create branch: {branch}")
        print(f"[dry-run] Would commit: {commit_msg}")
        for a, n, p in staged:
            print(f"[dry-run] Would copy: {p} → skills/{a}/{n}/")
        return

    # Check if we're already in the agent-skills repo
    cwd = os.getcwd()
    using_local_repo = _is_agent_skills_repo(cwd)
    original_branch = None
    
    if using_local_repo:
        print(f"Detected agent-skills repo at {cwd}")
        clone_dest = cwd
        
        # Save current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=clone_dest, capture_output=True, text=True, check=True,
        )
        original_branch = result.stdout.strip()
        
        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=clone_dest, capture_output=True, text=True, check=True,
        )
        if result.stdout.strip():
            raise CuratorError(
                "Working directory has uncommitted changes. "
                "Commit or stash them before shipping."
            )
        
        # Create and checkout branch
        subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=clone_dest, check=True, capture_output=True,
        )
    else:
        # Clone and prepare (original behavior)
        if os.path.exists(CLONE_DIR):
            shutil.rmtree(CLONE_DIR)
        os.makedirs(CLONE_DIR, exist_ok=True)

        clone_dest = os.path.join(CLONE_DIR, "agent-skills")
        gh.clone_for_contribution(TARGET_REPO, branch, clone_dest)

    # Copy skills
    for author, name, skill_dir in staged:
        dest = os.path.join(clone_dest, "skills", author, name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)

    # Commit
    subprocess.run(["git", "add", "."], cwd=clone_dest, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=clone_dest, check=True, capture_output=True,
    )

    # Push (fork if needed)
    can_push = gh.check_push_access(TARGET_REPO)
    fork_name = None
    if can_push:
        gh.push_branch(clone_dest)
        head = branch
    else:
        fork_name = gh.fork_repo(TARGET_REPO)
        gh.push_to_fork(clone_dest, fork_name)
        fork_owner = fork_name.split("/")[0]
        head = f"{fork_owner}:{branch}"

    # Build PR body from template if available
    pr_template_path = os.path.join(clone_dest, ".github", "pull_request_template.md")
    skills_lines = []
    for author, name, _ in staged:
        meta = skill_utils.extract_metadata(os.path.join(clone_dest, "skills", author, name))
        desc = meta.get("description", "No description")
        skills_lines.append(f"- **{author}/{name}**: {desc}")
    skills_section = "\n".join(skills_lines)

    if os.path.isfile(pr_template_path):
        with open(pr_template_path, "r") as f:
            body = f.read()
        body = body.replace("<!-- What skills are being added/updated? -->", pr_title)
        body = body.replace("<!-- List of skills with descriptions -->", skills_section)
    else:
        body = f"## Summary\n\n{pr_title}\n\n## Skills\n\n{skills_section}\n"

    pr_url = gh.create_pr(
        repo=TARGET_REPO,
        title=pr_title,
        body=body,
        head=head,
        draft=draft,
    )

    # Return to original branch if using local repo
    if using_local_repo and original_branch:
        subprocess.run(
            ["git", "checkout", original_branch],
            cwd=clone_dest, check=True, capture_output=True,
        )
        print(f"Returned to branch: {original_branch}")

    # Cleanup staging
    for _, _, skill_dir in staged:
        shutil.rmtree(skill_dir, ignore_errors=True)

    # Cleanup empty author dirs
    if os.path.isdir(STAGING_DIR):
        for d in os.listdir(STAGING_DIR):
            dpath = os.path.join(STAGING_DIR, d)
            if os.path.isdir(dpath) and not os.listdir(dpath):
                os.rmdir(dpath)

    print(f"PR created: {pr_url}")


def cmd_land(pr_number: int) -> None:
    """Merge PR and update inventory."""
    if not gh.check_auth():
        raise CuratorError("Not authenticated. Run: gh auth login")

    gh.merge_pr(TARGET_REPO, pr_number)
    print(f"PR #{pr_number} merged.")

    # Update inventory
    if os.path.exists(CLONE_DIR):
        shutil.rmtree(CLONE_DIR)
    os.makedirs(CLONE_DIR, exist_ok=True)
    clone_dest = os.path.join(CLONE_DIR, "agent-skills")
    gh.clone_for_contribution(TARGET_REPO, "chore/update-inventory", clone_dest)

    changed = update_readme(clone_dest)
    if changed:
        subprocess.run(["git", "add", "README.md"], cwd=clone_dest, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "chore(inventory): update skills inventory"],
            cwd=clone_dest, check=True, capture_output=True,
        )
        if gh.check_push_access(TARGET_REPO):
            gh.push_branch(clone_dest)
            # Push directly to main for inventory updates
            subprocess.run(
                ["git", "push", "origin", "chore/update-inventory:main"],
                cwd=clone_dest, check=True, capture_output=True,
            )
        print("Inventory updated and pushed.")
    else:
        print("Inventory already up to date.")

    shutil.rmtree(CLONE_DIR, ignore_errors=True)


def cmd_update(skill: str, source: str, author: str | None) -> None:
    """Update an existing skill from a new source."""
    # Parse skill identifier
    if "/" in skill:
        author_name, skill_name = skill.split("/", 1)
    else:
        author_name = author or os.environ.get("USER", "unknown")
        skill_name = skill

    print(f"Updating {author_name}/{skill_name} from {source}...")
    cmd_import(source, author=author_name)
    print(f"Staged update for {author_name}/{skill_name}. Run 'curator.py ship' to publish.")


def cmd_list(author_filter: str | None = None) -> None:
    """Show current skills inventory from the remote repo."""
    authors = gh.list_repo_dirs(TARGET_REPO, "skills")
    if not authors:
        print("No skills found or could not access repo.")
        return

    for author in sorted(authors):
        if author_filter and author != author_filter:
            continue
        skills = gh.list_repo_dirs(TARGET_REPO, f"skills/{author}")
        if skills:
            print(f"\n{author} ({len(skills)} skills):")
            for s in sorted(skills):
                print(f"  - {s}")

    print()


def cmd_status() -> None:
    """Show skills currently staged and ready to ship."""
    if not os.path.isdir(STAGING_DIR):
        print("No staged skills.")
        return

    found = False
    for author in sorted(os.listdir(STAGING_DIR)):
        author_dir = os.path.join(STAGING_DIR, author)
        if not os.path.isdir(author_dir):
            continue
        for skill_name in sorted(os.listdir(author_dir)):
            skill_dir = os.path.join(author_dir, skill_name)
            if not os.path.isdir(skill_dir):
                continue
            found = True
            errors = skill_utils.validate_skill(skill_dir)
            status = "✓ valid" if not errors else f"✗ {len(errors)} error(s)"
            print(f"  {author}/{skill_name}  [{status}]")

    if not found:
        print("No staged skills.")


# ── CLI ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="curator.py",
        description="Publish and maintain skills in the agent-skills repo.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # import
    p_import = sub.add_parser("import", help="Fetch skill from source, stage locally")
    p_import.add_argument("source", help="GitHub URL, owner/repo:path, or local path")
    p_import.add_argument("--author", help="Author namespace (default: $USER)")
    p_import.add_argument("--ref", help="Git ref for GitHub sources (default: main)")
    p_import.add_argument("--tags", help="Comma-separated tags (default: derived from skill name)")

    # validate
    p_validate = sub.add_parser("validate", help="Check skill structure and metadata")
    p_validate.add_argument("path", nargs="?", help="Path to skill dir (default: all staged)")

    # ship
    p_ship = sub.add_parser("ship", help="Push staged skills and create PR")
    p_ship.add_argument("--draft", action="store_true", help="Create draft PR")
    p_ship.add_argument("--dry-run", action="store_true", help="Show what would happen")

    # land
    p_land = sub.add_parser("land", help="Merge PR and update inventory")
    p_land.add_argument("pr_number", type=int, help="PR number to merge")

    # update
    p_update = sub.add_parser("update", help="Update existing skill from new source")
    p_update.add_argument("skill", help="Skill to update (author/name or name)")
    p_update.add_argument("--from", dest="source", required=True, help="Source to fetch update from")
    p_update.add_argument("--author", help="Author namespace")

    # list
    p_list = sub.add_parser("list", help="Show current inventory")
    p_list.add_argument("--author", help="Filter by author")

    # status
    sub.add_parser("status", help="Show staged skills")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "import":
            tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
            cmd_import(args.source, args.author, args.ref, tags=tags)
        elif args.command == "validate":
            cmd_validate(args.path)
        elif args.command == "ship":
            cmd_ship(draft=args.draft, dry_run=args.dry_run)
        elif args.command == "land":
            cmd_land(args.pr_number)
        elif args.command == "update":
            cmd_update(args.skill, args.source, args.author)
        elif args.command == "list":
            cmd_list(args.author)
        elif args.command == "status":
            cmd_status()
        return 0
    except CuratorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
