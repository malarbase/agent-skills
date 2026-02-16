# Agentic Flow (5+ files)

Parallelizes diagram conversion and DOCX generation across sub-agents.

All scripts: `$SCRIPTS=~/.cursor/skills/md-collection-to-google-docs/scripts/`

## Step 1: Setup

```bash
INPUT_DIR="path/to/markdown/files"
OUTPUT_DIR="$INPUT_DIR/_docx"
mkdir -p "$OUTPUT_DIR"
cp ~/.cursor/skills/doc-with-diagrams/scripts/md-to-docx.js "$INPUT_DIR/"
cd "$INPUT_DIR" && npm install docx
```

## Step 2: Create Drive Folder + Tabbed Root Doc

```bash
cd "$GOOGLEAPIS_DIR"
node $SCRIPTS/create-drive-folder.mjs --name "Project Documentation"
# Save FOLDER_ID from output

node $SCRIPTS/create-tabbed-doc.mjs \
  --title "Project Documentation" \
  --folder-id "$FOLDER_ID" \
  --input-dir "$INPUT_DIR" \
  --tabs-out "$INPUT_DIR/tab-mapping.json"
```

## Step 3: Resolve Cross-References

```bash
node $SCRIPTS/build-tab-url-mapping.js "$INPUT_DIR/tab-mapping.json"
node $SCRIPTS/resolve-crossrefs.js "$INPUT_DIR" "$INPUT_DIR/_resolved" "$INPUT_DIR/tab-url-mapping.json"
```

## Step 4: Parallel Diagram Conversion

Dispatch 3-4 sub-agents to create Mermaid diagrams from ASCII art:

```
Task(subagent_type: "generalPurpose", description: "Create Mermaid diagrams batch N", prompt: """
Read each file, find ASCII diagrams, create .mmd files in diagrams-{name}/.
Files: {batch of files}
""")
```

Then render (can also parallelize):

```bash
for dir in diagrams-*; do
  for f in "$dir"/*.mmd; do
    mmdc -i "$f" -o "${f%.mmd}.png" -w 1200 --scale 2 -b white
  done
done
```

## Step 5: Generate DOCX

Single script handles all files with proper work-dir isolation:

```bash
node $SCRIPTS/generate-docx-with-diagrams.js \
  --input-dir "$INPUT_DIR/_resolved" \
  --output-dir "$OUTPUT_DIR" \
  --script "$INPUT_DIR/md-to-docx.js" \
  --diagrams-dir "$INPUT_DIR"
```

## Step 6: Upload + Update Placeholders

```bash
cd "$GOOGLEAPIS_DIR"
node ~/.cursor/skills/drive-upload-docx/scripts/upload-to-drive.js \
  --input-dir "$OUTPUT_DIR" --folder-id "$FOLDER_ID" --convert \
  --credentials /tmp/gw-credentials.json \
  --mapping-out "$INPUT_DIR/mapping.json"

node $SCRIPTS/update-tab-placeholders.mjs \
  --doc-id "$DOC_ID" \
  --tab-mapping "$INPUT_DIR/tab-mapping.json" \
  --standalone-mapping "$INPUT_DIR/mapping.json"
```

## Step 7: Manual Merge + Cleanup

Click links in tabs → Select All → Copy → Paste. Validate, then cleanup:

```bash
node $SCRIPTS/cleanup.js "$INPUT_DIR" --trash-drive
```
