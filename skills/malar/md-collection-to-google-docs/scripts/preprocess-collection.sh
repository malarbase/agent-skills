#!/bin/bash
# preprocess-collection.sh
#
# Batch-convert all markdown files in a directory to Google Doc blocks JSON.
# Optionally resolves cross-references if a mapping.json is provided.
#
# Usage:
#   preprocess-collection.sh <input-dir> [mapping.json]
#
# Output:
#   <input-dir>/_blocks/<name>.json   — one blocks JSON file per markdown file
#   If mapping.json provided, cross-references are resolved first, then converted.
#
# Subdirectory files are flattened with "__" separator:
#   internal/experiments.md → _blocks/internal__experiments.json

set -euo pipefail

INPUT_DIR="${1:?Usage: preprocess-collection.sh <input-dir> [mapping.json]}"
MAPPING="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BLOCKS_DIR="$INPUT_DIR/_blocks"

mkdir -p "$BLOCKS_DIR"

# Determine source directory: if mapping provided, resolve cross-refs first
if [ -n "$MAPPING" ]; then
  RESOLVED_DIR="$INPUT_DIR/_resolved"
  echo "Resolving cross-references using $MAPPING..."
  node "$SCRIPT_DIR/resolve-crossrefs.js" "$INPUT_DIR" "$RESOLVED_DIR" "$MAPPING" || true
  SOURCE_DIR="$RESOLVED_DIR"
  echo ""
else
  SOURCE_DIR="$INPUT_DIR"
fi

echo "Converting markdown files to blocks JSON..."
echo "Source: $SOURCE_DIR"
echo "Output: $BLOCKS_DIR"
echo ""

COUNT=0
ERRORS=0

# Find all .md files, skipping hidden dirs, node_modules, _blocks, _resolved, diagrams-*
while IFS= read -r md_file; do
  # Compute relative path from source dir
  rel_path="${md_file#$SOURCE_DIR/}"

  # Skip files starting with _ (like _md-to-blocks.js companion files)
  base_name="$(basename "$rel_path")"
  if [[ "$base_name" == _* ]]; then
    continue
  fi

  # Flatten subdirectory path: internal/experiments.md → internal__experiments
  safe_name="${rel_path%.md}"
  safe_name="${safe_name//\//__}"

  out_file="$BLOCKS_DIR/$safe_name.json"

  if node "$SCRIPT_DIR/md-to-blocks.js" "$md_file" > "$out_file" 2>/dev/null; then
    # Validate JSON is non-empty array
    if [ -s "$out_file" ] && node -e "const b=JSON.parse(require('fs').readFileSync('$out_file','utf-8')); process.exit(Array.isArray(b) && b.length > 0 ? 0 : 1)" 2>/dev/null; then
      block_count=$(node -e "console.log(JSON.parse(require('fs').readFileSync('$out_file','utf-8')).length)")
      echo "  OK: $rel_path → $safe_name.json ($block_count blocks)"
      COUNT=$((COUNT + 1))
    else
      echo "  WARN: $rel_path → empty or invalid blocks (skipped)"
      rm -f "$out_file"
      ERRORS=$((ERRORS + 1))
    fi
  else
    echo "  ERROR: $rel_path → conversion failed"
    rm -f "$out_file"
    ERRORS=$((ERRORS + 1))
  fi
done < <(find "$SOURCE_DIR" -name '*.md' \
  -not -path '*/.git/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/_blocks/*' \
  -not -path '*/_resolved/*' \
  -not -path '*/diagrams-*/*' \
  | sort)

echo ""
echo "Done. Converted: $COUNT files, Errors: $ERRORS"
echo "Blocks directory: $BLOCKS_DIR"

# Write a manifest for the agent to consume
MANIFEST="$BLOCKS_DIR/_manifest.json"
node -e "
const fs = require('fs');
const dir = '$BLOCKS_DIR';
const files = fs.readdirSync(dir)
  .filter(f => f.endsWith('.json') && !f.startsWith('_'))
  .map(f => {
    const blocks = JSON.parse(fs.readFileSync(dir + '/' + f, 'utf-8'));
    const mdName = f.replace(/.json$/, '').replace(/__/g, '/') + '.md';
    const h1 = blocks.find(b => b.type === 'heading' && b.level === 1);
    return {
      jsonFile: f,
      markdownFile: mdName,
      title: h1 ? h1.text : mdName.replace('.md', ''),
      blockCount: blocks.length
    };
  });
console.log(JSON.stringify(files, null, 2));
" > "$MANIFEST"

echo "Manifest: $MANIFEST"
