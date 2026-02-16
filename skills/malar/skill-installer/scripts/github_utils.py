#!/usr/bin/env python3
"""Shared GitHub helpers for skill install scripts."""

from __future__ import annotations

import os
import urllib.request


def github_request(url: str, user_agent: str = "skill-installer") -> bytes:
    """
    Make an authenticated request to GitHub.
    
    Uses GITHUB_TOKEN or GH_TOKEN from environment if available.
    
    Args:
        url: The URL to fetch
        user_agent: User-Agent header value
    
    Returns:
        Response body as bytes
    """
    headers = {"User-Agent": user_agent}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def github_api_contents_url(repo: str, path: str, ref: str = "main") -> str:
    """
    Build a GitHub API contents URL.
    
    Args:
        repo: Repository in owner/repo format
        path: Path within the repository
        ref: Git ref (branch, tag, commit)
    
    Returns:
        GitHub API URL for the contents endpoint
    """
    return f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
