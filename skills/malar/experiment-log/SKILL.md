---
name: experiment-log
description: Proactively log infrastructure, performance, and integration experiments
  to a structured experiments.md file. Triggers when the session involves testing
  hypotheses, benchmarking, comparing approaches, trying configurations, debugging
  with trial-and-error, or any work where the outcome is uncertain and worth recording.
  Detects experiment patterns and appends entries without being asked.
metadata:
  author: malar
  tags:
  - documentation
  - experiments
  - logging
  - curated
---

# Experiment Log

Maintain a structured decision trail across LLM sessions so experiments are never re-run blindly and outcomes inform future decisions.

## When to Activate

Log an experiment when the session involves ANY of:
- Testing a hypothesis ("will X improve Y?")
- Benchmarking or timing comparisons
- Trying a configuration change to see if it works
- Debugging through trial-and-error with measurable outcomes
- Comparing two approaches (A vs B)
- Infrastructure changes with uncertain outcomes (deploy modes, image sizes, timeouts)

Do NOT log routine tasks like "fix this lint error" or "add a field to this struct."

## Locating the Experiment Log

1. Search the workspace for an existing `experiments.md`:
   - Check `docs/**/experiments.md`, `**/experiments.md`
2. If found, append to it (newest entry at top, below the header)
3. If not found, ask the user where to create one

## Entry Format

Each entry follows this template. Use the next sequential `EXP-NNN` ID.

```markdown
## EXP-NNN: [Short descriptive title] (YYYY-MM-DD)

**Goal**: What we're trying to achieve or prove.

**Method**: What we did — commands, config changes, code changes.

**Result**: `PASS` | `FAIL` | `PARTIAL` | `PENDING`
[Concrete data: timings, sizes, status codes, error messages.]

**Decision**: What this means for next steps. Link to follow-up experiments if any.

**Commit**: `abc1234` on `branch-name` (if applicable)
```

### Status Key

| Status | Meaning |
|--------|---------|
| `PASS` | Confirmed hypothesis, merged/applied |
| `FAIL` | Did not work, documented why |
| `PARTIAL` | Partially successful, needs follow-up |
| `PENDING` | Awaiting deployment, external action, or next session |
| `BLOCKED` | Waiting on external dependency |

## Workflow

### During the Session

1. **Detect**: Recognize when work becomes experimental (uncertain outcome)
2. **Track mentally**: Note the goal, method, and measurements as you go
3. **Capture data**: Save exact timings, sizes, error messages, status codes — not approximations

### Before Ending an Experiment

1. **Read** the existing `experiments.md` to get the last EXP number
2. **Append** a new entry at the top (below the header/intro section)
3. **Update** the "Pending Experiments" section if the entry creates or resolves a pending item
4. **Update** reference tables (timings, sizes, resource IDs) if new measurements were taken

### Multiple Experiments in One Session

Log each separately with its own EXP entry. Order them chronologically (earliest experiment gets the lower number).

## What Makes a Good Entry

- **Concrete data over prose**: `8.6s` not "slow", `199MB` not "smaller"
- **Include the negative**: Failed experiments are as valuable as successes — they prevent reruns
- **Link cause and effect**: "EXP-007 session reuse (1.3s) + EXP-008 smaller image → total should fit under 10s timeout"
- **Capture resource IDs**: Runtime IDs, target IDs, commit hashes — anything a future session would need to look up
- **Note gotchas**: Side effects, things that broke unexpectedly, undocumented behaviors

## Anti-Patterns

- Logging routine code changes as experiments
- Vague results: "it didn't work" (always include the error or measurement)
- Skipping failed experiments (they're the most valuable)
- Duplicating documentation — the experiment log captures the *journey*, docs capture the *destination*
