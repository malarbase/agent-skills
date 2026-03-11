---
name: tea-cli
description: CLI tool for interacting with Gitea repositories. Use when users need to manage pull requests, issues, releases, branches, or other Gitea entities via command line. Triggers on requests to create/merge/list/view PRs, manage Gitea issues, create releases, or interact with the Gitea API.
metadata:
  author: malar
  repo: github.com/malarbase/agent-skills
  tags: [gitea, cli, pr, issues, releases, git]
---

# Tea CLI Skill

## Overview

Tea is a productivity helper for Gitea that provides command-line access to repository entities and local helpers like `tea pr checkout`. This skill provides workflows and commands for common Gitea operations.

## Quick Start

```bash
# List all PRs (use --login if multiple accounts configured)
tea pr list --login <login-name>

# Create a new PR
tea pr create --title "feat: description" --base main --login <login-name>

# Merge a PR
tea pr merge <pr-number> --login <login-name>
```

## Configuration

### Login to Gitea Server

First-time setup:

```bash
tea login
# Follow prompts to enter:
# - Server URL (e.g., https://code.whiteblossom.xyz)
# - Username
# - API token (generate in Gitea settings → Applications)
```

### Manage Logins

```bash
# List configured logins
tea logins

# Logout from a server
tea logout <login-name>
```

### Environment Variables

For CI/CD or script usage, set `GITEA_TOKEN`:

```bash
export GITEA_TOKEN=your-api-token
```

## Pull Request Workflows

### List PRs

```bash
# All PRs
tea pr list --login <login-name>

# Filter by state
tea pr list --state open --login <login-name>
tea pr list --state closed --login <login-name>
```

### View PR Details

```bash
tea pr view <pr-number> --login <login-name>
```

### Create PR

```bash
tea pr create --title "feat: description" --base main --login <login-name>
```

### Merge PR

```bash
tea pr merge <pr-number> --login <login-name>
```

### Checkout PR Locally

```bash
tea pr checkout <pr-number> --login <login-name>
```

### Comment on PR

```bash
tea comment <pr-number> "Your comment here" --login <login-name>
```

## Issue Management

```bash
# List issues
tea issue list --login <login-name>

# Create issue
tea issue create --title "Bug: description" --login <login-name>

# View issue
tea issue view <issue-number> --login <login-name>

# Edit issue (add labels, assignees, etc.)
tea issue edit <issue-number> --add-labels <label-name> --login <login-name>
tea issue edit <issue-number> --remove-labels <label-name> --login <login-name>
tea issue edit <issue-number> --add-assignees <username> --login <login-name>
```

## Label Management

```bash
# List all labels
tea labels --login <login-name>

# Create label
tea label create "<label-name>" --color "#0075ca" --login <login-name>

# Add label to issue/PR (use issue edit, not "issue label add" which doesn't exist)
tea issue edit <issue-or-pr-number> --add-labels <label-name> --login <login-name>
```

## Releases

```bash
# List releases
tea release list --login <login-name>

# Create release
tea release create v1.0.0 --login <login-name>
```

## Branches

```bash
# List branches
tea branch list --login <login-name>

# Create branch
tea branch create feature/new-feature --login <login-name>
```

## Repository Operations

```bash
# Show repo info
tea repo info --login <login-name>
```

## Command Reference

Get help on any command:

```bash
tea --help
tea <command> --help
tea <command> <subcommand> --help
```

## Best Practices

1. **Always specify `--login`** when multiple logins are configured
2. **Place `--login` at the END** of the command: `tea pr list --login malarinv` (not `tea --login malarinv pr list`)
3. **Use conventional commit prefixes** in PR titles: `feat:`, `fix:`, `chore:`, `docs:`
4. **Verify PR status** before merging with `tea pr view`
5. **Keep local branches updated** before tea operations
6. **Use `--login malarinv`** for the primary work account

## Troubleshooting

### "Error: not found"

- Verify login name: `tea logins`
- Ensure `--login <name>` flag is at the **end** of the command
- Check Gitea token is valid and not expired

### Label Operations Not Working

Some tea commands (especially label management) may report success but silently fail if the API token lacks required scopes:

- `read:issue` scope required for viewing/adding issue or PR labels
- `write:issue` scope required for creating/modifying labels
- If label operations fail, verify token scopes in Gitea settings → Applications → Edit Token
- Token must have both `read:issue` and `write:issue` for full label management

**Important:** The command `tea issue label add` does not exist. Use `tea issue edit <idx> --add-labels <label> --login <name>` instead.

### Command Reports Success But Nothing Changed

This typically indicates a token scope limitation:

1. Check current token scopes in Gitea: Settings → Applications → Edit Token
2. Required scopes for common operations:
   - PR/Issue management: `read:issue`, `write:issue`
   - Label operations: `read:issue`, `write:issue`
   - Repository operations: `read:repository`, `write:repository`
3. If scopes are missing, create a new token with all required scopes

### PR Checkout Fails

- Ensure branch exists on remote
- Check local git state is clean
- Try `git fetch origin` first
