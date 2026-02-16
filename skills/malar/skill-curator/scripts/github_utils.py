#!/usr/bin/env python3
"""GitHub helpers for skill-curator: clone, push, fork detection, PR creation."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request


def _gh(*args: str, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=capture,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def _git(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run a git command."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def github_request(url: str) -> dict | list:
    """Make an authenticated GitHub API request, return parsed JSON."""
    headers = {"User-Agent": "skill-curator", "Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        try:
            result = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True
            )
            if result.returncode == 0:
                token = result.stdout.strip()
        except FileNotFoundError:
            pass
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def check_auth() -> bool:
    """Check if gh CLI is authenticated."""
    try:
        _gh("auth", "status")
        return True
    except (RuntimeError, FileNotFoundError):
        return False


def check_push_access(repo: str) -> bool:
    """Check if the authenticated user can push directly to repo."""
    try:
        data = github_request(f"https://api.github.com/repos/{repo}")
        permissions = data.get("permissions", {})
        return permissions.get("push", False)
    except (urllib.error.HTTPError, KeyError):
        return False


def fork_repo(repo: str) -> str:
    """Fork the repo and return the fork's full name (owner/repo)."""
    result = _gh("repo", "fork", repo, "--clone=false")
    # gh repo fork prints the fork URL; parse the fork name
    try:
        data = github_request(f"https://api.github.com/repos/{repo}/forks?per_page=1&sort=newest")
        if data:
            return data[0]["full_name"]
    except (urllib.error.HTTPError, KeyError, IndexError):
        pass
    # Fallback: get authenticated user and construct fork name
    user_data = github_request("https://api.github.com/user")
    repo_name = repo.split("/")[-1]
    return f"{user_data['login']}/{repo_name}"


def clone_for_contribution(repo: str, branch: str, dest: str) -> str:
    """Clone repo ready for pushing. Returns the clone directory path."""
    repo_url = f"https://github.com/{repo}.git"
    _git("clone", "--filter=blob:none", "--depth=1", "--single-branch", repo_url, dest)
    _git("checkout", "-b", branch, cwd=dest)
    return dest


def push_branch(dest: str, remote: str = "origin") -> None:
    """Push the current branch to remote."""
    _git("push", "-u", remote, "HEAD", cwd=dest)


def push_to_fork(dest: str, fork_repo: str) -> None:
    """Add fork as remote and push."""
    fork_url = f"https://github.com/{fork_repo}.git"
    try:
        _git("remote", "add", "fork", fork_url, cwd=dest)
    except RuntimeError:
        _git("remote", "set-url", "fork", fork_url, cwd=dest)
    _git("push", "-u", "fork", "HEAD", cwd=dest)


def create_pr(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
    draft: bool = False,
) -> str:
    """Create a PR and return the PR URL."""
    cmd = ["pr", "create", "--repo", repo, "--title", title, "--body", body, "--head", head, "--base", base]
    if draft:
        cmd.append("--draft")
    result = _gh(*cmd)
    return result.stdout.strip()


def merge_pr(repo: str, pr_number: int, method: str = "squash") -> None:
    """Merge a PR via gh CLI."""
    _gh("pr", "merge", str(pr_number), "--repo", repo, f"--{method}", "--delete-branch")


def list_repo_dirs(repo: str, path: str) -> list[str]:
    """List directory names at a path in the repo via GitHub API."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    try:
        data = github_request(url)
        return [item["name"] for item in data if item["type"] == "dir"]
    except urllib.error.HTTPError:
        return []
