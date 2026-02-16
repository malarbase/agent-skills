#!/usr/bin/env bash
set -euo pipefail

# SpecLife Init - configures a project for AI editor slash commands
# Usage: init.sh [--force] [--tools <editors>] [--yes] [project_dir]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: init.sh [OPTIONS] [PROJECT_DIR]

Configure a project for SpecLife AI editor slash commands.

Options:
  --force            Overwrite existing configuration files
  --tools EDITORS    Comma-separated editor IDs to configure
                     (cursor,claude-code,vscode,windsurf,gemini,qwen,antigravity,opencode)
  --yes              Accept all defaults (non-interactive)
  -h, --help         Show this help message

Examples:
  init.sh                          # Configure current directory interactively
  init.sh --yes                    # Configure with auto-detected editors
  init.sh --tools cursor,claude-code --yes /path/to/project
EOF
  exit 0
fi

if command -v uv &>/dev/null; then
  exec uv run "$SCRIPT_DIR/speclife_init.py" --templates "$TEMPLATES_DIR" "$@"
else
  exec python3 "$SCRIPT_DIR/speclife_init.py" --templates "$TEMPLATES_DIR" "$@"
fi
