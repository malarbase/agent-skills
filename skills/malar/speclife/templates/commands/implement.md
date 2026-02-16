---
name: /speclife-implement
id: speclife-implement
category: SpecLife
description: Convenience proxy to /openspec-apply for implementing changes.
---
# /speclife implement

Convenience proxy to `/openspec-apply`.

## ⚡ Execution

**When this command is invoked, IMMEDIATELY invoke `/openspec-apply`.**

This is a thin proxy—do not add additional behavior.

## Usage

```
/speclife implement
```

## Behavior

This command exists for users who expect a `/speclife implement` command. It simply proxies to the OpenSpec implementation command.

**Action**: Invoke `/openspec-apply`

## Why This Exists

SpecLife complements OpenSpec rather than duplicating it:

- **OpenSpec** handles spec management (proposals, implementation, archiving)
- **SpecLife** handles git/GitHub automation (worktrees, branches, PRs, releases)

For consistency, users should use `/openspec-apply` directly. This proxy exists only for discoverability.

## See Also

- `/openspec-apply` - The actual implementation command
- `/openspec-proposal` - Create a new proposal
- `/speclife start` - Create worktree and optionally scaffold proposal


