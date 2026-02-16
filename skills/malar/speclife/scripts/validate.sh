#!/usr/bin/env bash
set -euo pipefail

# SpecLife Validate - check spec completeness for a change
# Usage: validate.sh <change-id> [--strict]

die()  { echo "Error: $*" >&2; exit 1; }
warn() { echo "Warning: $*" >&2; WARNINGS=$((WARNINGS + 1)); }

# --- Parse arguments ---
CHANGE_ID=""
STRICT=false

for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=true ;;
    --help|-h)
      echo "Usage: validate.sh <change-id> [--strict]"
      echo ""
      echo "Validate a SpecLife change proposal for completeness."
      echo ""
      echo "Options:"
      echo "  --strict    Fail on any warnings (not just errors)"
      echo "  -h, --help  Show this help message"
      exit 0
      ;;
    -*) die "Unknown flag: $arg" ;;
    *)  CHANGE_ID="$arg" ;;
  esac
done

[[ -z "$CHANGE_ID" ]] && die "Usage: validate.sh <change-id> [--strict]"

# --- Locate project root and spec dir ---
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "Not inside a git repository"
CONFIG_FILE="$PROJECT_ROOT/.specliferc.yaml"
SPEC_DIR="openspec"

if [[ -f "$CONFIG_FILE" ]]; then
  val=$(grep -E '^specDir:' "$CONFIG_FILE" 2>/dev/null | sed 's/specDir:\s*//' | tr -d '[:space:]"'"'" || true)
  [[ -n "$val" ]] && SPEC_DIR="$val"
fi

CHANGE_DIR="$PROJECT_ROOT/$SPEC_DIR/changes/$CHANGE_ID"
ERRORS=0
WARNINGS=0

echo "Validating change: $CHANGE_ID"
echo "  Path: $CHANGE_DIR"
echo ""

# --- Check proposal.md ---
PROPOSAL="$CHANGE_DIR/proposal.md"
if [[ ! -f "$PROPOSAL" ]]; then
  echo "  ✗ proposal.md not found"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✓ proposal.md exists"

  # Check for required sections
  if ! grep -qi '## Summary\|## Description\|## Motivation\|## Problem' "$PROPOSAL"; then
    warn "proposal.md has no recognizable summary/description section"
  fi
fi

# --- Check tasks.md ---
TASKS="$CHANGE_DIR/tasks.md"
if [[ ! -f "$TASKS" ]]; then
  echo "  ✗ tasks.md not found"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✓ tasks.md exists"

  # Count completed vs incomplete tasks
  TOTAL=$(grep -cE '^\s*-\s*\[[ xX]\]' "$TASKS" 2>/dev/null || echo "0")
  DONE=$(grep -cE '^\s*-\s*\[[xX]\]' "$TASKS" 2>/dev/null || echo "0")
  TODO=$((TOTAL - DONE))

  echo "  ✓ Tasks: $DONE/$TOTAL complete ($TODO remaining)"

  if [[ "$TOTAL" -eq 0 ]]; then
    warn "tasks.md has no task items (expected - [ ] or - [x] lines)"
  fi
fi

# --- Check for extra spec files (informational) ---
for f in "$CHANGE_DIR"/*.md; do
  [[ ! -f "$f" ]] && continue
  basename=$(basename "$f")
  case "$basename" in
    proposal.md|tasks.md) ;; # already checked
    *) echo "  ℹ  Additional spec file: $basename" ;;
  esac
done

# --- Summary ---
echo ""
if [[ "$ERRORS" -gt 0 ]]; then
  echo "✗ Validation FAILED ($ERRORS error(s), $WARNINGS warning(s))"
  exit 1
elif [[ "$STRICT" == true && "$WARNINGS" -gt 0 ]]; then
  echo "✗ Validation FAILED in strict mode ($WARNINGS warning(s))"
  exit 1
elif [[ "$WARNINGS" -gt 0 ]]; then
  echo "✓ Validation PASSED with $WARNINGS warning(s)"
  exit 0
else
  echo "✓ Validation PASSED"
  exit 0
fi
