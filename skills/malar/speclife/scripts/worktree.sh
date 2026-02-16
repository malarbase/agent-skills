#!/usr/bin/env bash
set -euo pipefail

# SpecLife worktree management wrapper
# Usage: worktree.sh create|rm|list <change-id> [-f]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository" >&2; exit 1
}

# --- Config: parse .specliferc.yaml with grep/sed ---
CONFIG_FILE="$PROJECT_ROOT/.specliferc.yaml"
BASE_BRANCH="main"
BRANCH_PREFIX="spec/"
WORKTREE_DIR="worktrees"

if [[ -f "$CONFIG_FILE" ]]; then
  val=$(grep -E '^\s+baseBranch:' "$CONFIG_FILE" 2>/dev/null | sed 's/.*baseBranch:\s*//' | tr -d '[:space:]"'"'" || true)
  [[ -n "$val" ]] && BASE_BRANCH="$val"
  val=$(grep -E '^\s+branchPrefix:' "$CONFIG_FILE" 2>/dev/null | sed 's/.*branchPrefix:\s*//' | tr -d '[:space:]"'"'" || true)
  [[ -n "$val" ]] && BRANCH_PREFIX="$val"
  val=$(grep -E '^\s+worktreeDir:' "$CONFIG_FILE" 2>/dev/null | sed 's/.*worktreeDir:\s*//' | tr -d '[:space:]"'"'" || true)
  [[ -n "$val" ]] && WORKTREE_DIR="$val"
fi

WORKTREE_BASE="$PROJECT_ROOT/$WORKTREE_DIR"

# --- Helpers ---
die()  { echo "Error: $*" >&2; exit 1; }
info() { echo "  * $*"; }

validate_change_id() {
  local id="$1"
  if [[ ! "$id" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    die "Invalid change-id '$id'. Use kebab-case (lowercase letters, numbers, hyphens)."
  fi
}

run_bootstrap() {
  local wt_path="$1"
  if command -v uv &>/dev/null; then
    uv run "$SCRIPT_DIR/worktree_bootstrap.py" "$wt_path" "$PROJECT_ROOT"
  else
    python3 "$SCRIPT_DIR/worktree_bootstrap.py" "$wt_path" "$PROJECT_ROOT"
  fi
}

# --- Subcommands ---
cmd_create() {
  local change_id="$1"
  validate_change_id "$change_id"

  local branch="${BRANCH_PREFIX}${change_id}"
  local worktree_path="${WORKTREE_BASE}/${change_id}"

  [[ -d "$worktree_path" ]] && die "Worktree already exists: $worktree_path"

  echo "Creating worktree for '$change_id'..."
  git fetch origin --quiet
  git branch "$branch" "origin/${BASE_BRANCH}" 2>/dev/null \
    || die "Branch '$branch' already exists or base branch 'origin/${BASE_BRANCH}' not found."
  git worktree add "$worktree_path" "$branch" --quiet

  info "Path:   $worktree_path"
  info "Branch: $branch"

  echo "Bootstrapping environment..."
  run_bootstrap "$worktree_path" || true

  echo ""
  echo "Done! Next steps:"
  echo "  cd $worktree_path"
  echo "  # then run /openspec-proposal to create the spec"
}

cmd_rm() {
  local change_id="$1"
  local force_flag="${2:-}"

  local branch="${BRANCH_PREFIX}${change_id}"
  local worktree_path="${WORKTREE_BASE}/${change_id}"

  echo "Removing worktree for '$change_id'..."
  if [[ "$force_flag" == "-f" ]]; then
    git worktree remove "$worktree_path" --force
  else
    git worktree remove "$worktree_path"
  fi
  git branch -D "$branch" 2>/dev/null || true

  info "Removed: $worktree_path"
  info "Branch:  $branch (deleted)"
}

cmd_list() {
  local found=0
  local wt_path="" wt_branch=""

  while IFS= read -r line; do
    if [[ "$line" =~ ^worktree\ (.+) ]]; then
      wt_path="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^branch\ refs/heads/(.+) ]]; then
      wt_branch="${BASH_REMATCH[1]}"
    elif [[ -z "$line" ]]; then
      if [[ "$wt_path" == "$WORKTREE_BASE"/* && "$wt_branch" == "$BRANCH_PREFIX"* ]]; then
        local cid="${wt_branch#"$BRANCH_PREFIX"}"
        printf "  %-24s %-30s %s\n" "$cid" "$wt_branch" "$wt_path"
        found=1
      fi
      wt_path="" ; wt_branch=""
    fi
  done < <(git worktree list --porcelain)

  if [[ "$found" -eq 0 ]]; then
    echo "No active spec worktrees."
  fi
}

# --- Main dispatch ---
case "${1:-}" in
  create) [[ -z "${2:-}" ]] && die "Usage: worktree.sh create <change-id>"; cmd_create "$2" ;;
  rm)     [[ -z "${2:-}" ]] && die "Usage: worktree.sh rm <change-id> [-f]"; cmd_rm "$2" "${3:-}" ;;
  list)   cmd_list ;;
  *)      echo "Usage: worktree.sh <create|rm|list> [change-id] [-f]" >&2; exit 1 ;;
esac
