---
name: md-collection-to-google-docs
description: Convert a collection of interlinked markdown files into Google Docs with
  rendered diagrams, tables, and cross-references. Uses DOCX as an intermediary for
  reliable formatting. Use when the user wants to publish markdown documentation to
  Google Docs, write docs to Google Drive, convert a docs folder to Google Docs, or
  prepare a tabbed final document.
metadata:
  author: malar
  tags:
  - documentation
  - google-docs
  - markdown
  - workflow
  - curated
---

# Markdown Collection to Google Docs

Convert markdown documentation into Google Docs via DOCX intermediary. The final deliverable is a **single tabbed Google Doc** with one tab per file, native tables, embedded diagrams, and clickable cross-references between tabs.

## Why DOCX Intermediary

Always use **md → DOCX → upload**. Direct Google Docs API writes are a last resort — see [references/api-limitations.md](references/api-limitations.md).

DOCX upload gives native tables, embedded images (no public URL needed), native hyperlinks, and atomic uploads with zero index math bugs.

## Prerequisites

- Google Workspace MCP authenticated (`drive` + `docs` scopes)
- `doc-with-diagrams` skill (provides `md-to-docx.js`)
- `mmdc`: `npm install -g @mermaid-js/mermaid-cli`
- `docx` npm package: `npm install docx`
- `googleapis` npm package (available in the MCP server's node_modules)

All scripts below must run from a directory that has `googleapis` in `node_modules` (e.g., the cb-mcp monorepo root). The scripts path is `~/.cursor/skills/md-collection-to-google-docs/scripts/`.

## Execution Mode

| Collection Size | Mode |
|-----------------|------|
| 1-4 files | **Direct** — main agent handles all steps sequentially |
| 5+ files | **Agentic** — parallel sub-agents; see [references/agentic-flow.md](references/agentic-flow.md) |

## Delivery Shape

The **primary deliverable is a tabbed Google Doc**. Standalone docs are intermediaries for copy/paste.

**Always create the tabbed root doc** unless the user explicitly asks for standalone docs only.

---

## Common Mistakes (Must Avoid)

1. **Never skip diagram conversion.** ASCII diagrams → Mermaid `.mmd` → PNG → embed in DOCX. Skipping produces ugly placeholder blocks.
2. **Always resolve cross-refs to tab URLs**, not standalone doc URLs. Create tab skeleton FIRST.
3. **Delete the default "Tab 1".** After adding named tabs, delete via `{ deleteTab: { tabId: 't.0' } }`. API field is `deleteTab`, NOT `deleteDocumentTab`. The `create-tabbed-doc.mjs` script handles this automatically.
4. **Per-file diagram directories.** `md-to-docx.js` expects `{workDir}/diagrams/`. Don't share one dir across files. The `generate-docx-with-diagrams.js` script handles this automatically.
5. **Add clickable links to tab placeholders.** After uploading standalone docs, run `update-tab-placeholders.mjs` so each tab has a clickable link for manual copy/paste.
6. **Verify diagram count before creating `.mmd` files.** The detection regex has false positives (table schemas, code with `|` chars). A count mismatch shifts all subsequent diagram images. Run `count-ascii-diagrams.js` first — see Step 5a.
7. **Use flat Mermaid layouts.** Never use `direction TB` inside subgraphs — causes tall/narrow renders. Use flat `graph LR` or `graph TD`.
8. **Run post-upload artifact scan (Step 9b).** `md-to-docx.js` does not convert `*italic*` to DOCX italic formatting, and `gsuite write-md` does not convert `[links](url)` or `` `code` `` to native formatting. These pass through as literal markdown text into the Google Doc. Always run the verification scan after merging — see Step 9b.

---

## Workflow Overview

```
1.  Setup
2.  Create Drive folder
3.  Create tabbed root doc → tab-mapping.json (with tab URLs)
4.  Resolve cross-refs to tab URLs
5.  Convert ASCII diagrams → Mermaid → PNG
6.  Generate DOCX (with tab-URL cross-refs + embedded diagrams)
7.  Upload DOCX as standalone docs → mapping.json
8.  Update tab placeholders with clickable links
9.  Manual merge: copy from standalone → paste into tabs
9b. Post-merge artifact scan: fix surviving markdown syntax
10. Cleanup
```

---

## Step 1: Setup

```bash
INPUT_DIR="path/to/markdown/files"
OUTPUT_DIR="$INPUT_DIR/_docx"
SCRIPTS=~/.cursor/skills/md-collection-to-google-docs/scripts
GOOGLEAPIS_DIR="/path/to/dir-with-googleapis"   # e.g. cb-mcp monorepo root

mkdir -p "$OUTPUT_DIR"
cp ~/.cursor/skills/doc-with-diagrams/scripts/md-to-docx.js "$INPUT_DIR/"
cd "$INPUT_DIR" && npm install docx
```

## Step 2: Create Drive Folder

```bash
cd "$GOOGLEAPIS_DIR" && \
node "$SCRIPTS/create-drive-folder.mjs" --name "Project Documentation"
```

Outputs JSON with `id` and `webViewLink`. Save the folder ID: `FOLDER_ID=...`

## Step 3: Create Tabbed Root Doc

```bash
cd "$GOOGLEAPIS_DIR" && \
node "$SCRIPTS/create-tabbed-doc.mjs" \
  --title "Project Documentation" \
  --folder-id "$FOLDER_ID" \
  --input-dir "$INPUT_DIR" \
  --tabs-out "$INPUT_DIR/tab-mapping.json"
```

Scans `$INPUT_DIR` for `.md` files, creates one named tab per file (README first), deletes the default "Tab 1", writes `tab-mapping.json`:

```json
{ "README.md": { "tabId": "t.abc", "tabUrl": "https://docs.google.com/.../edit?tab=t.abc", "title": "Overview" } }
```

## Step 4: Resolve Cross-References

```bash
node "$SCRIPTS/build-tab-url-mapping.js" "$INPUT_DIR/tab-mapping.json" "$INPUT_DIR/tab-url-mapping.json"

node "$SCRIPTS/resolve-crossrefs.js" \
  "$INPUT_DIR" "$INPUT_DIR/_resolved" "$INPUT_DIR/tab-url-mapping.json"
```

Cross-references now point to `?tab=t.xxx` URLs. When pasted into tabs, links navigate between tabs natively.

## Step 5: Convert Diagrams

**Mandatory — do NOT skip.** For each file with ASCII diagrams:

### 5a. Count detected diagram blocks (CRITICAL)

```bash
node "$SCRIPTS/count-ascii-diagrams.js" "$INPUT_DIR/FILE.md"
```

Shows each detected block with line number, matched patterns, and context. Create one `.mmd` per detected block — including false positives (table schemas → ER diagrams, etc.).

### 5b. Create and render `.mmd` files

1. Create exactly N `.mmd` files in `$INPUT_DIR/diagrams-{basename}/`, numbered `01-name.mmd` through `NN-name.mmd`
2. Render to PNG: `PUPPETEER_CACHE_DIR=~/.cache/puppeteer mmdc -i file.mmd -o file.png -w 1600 --scale 2 -b white`
3. **Verify:** `ls diagrams-{name}/*.png | wc -l` must equal the count from step 5a

For 5+ files, dispatch parallel sub-agents to create Mermaid files (3-4 agents, batched by file).

## Step 6: Generate DOCX

```bash
node "$SCRIPTS/generate-docx-with-diagrams.js" \
  --input-dir "$INPUT_DIR/_resolved" \
  --output-dir "$OUTPUT_DIR" \
  --script "$INPUT_DIR/md-to-docx.js" \
  --diagrams-dir "$INPUT_DIR"
```

Handles per-file work directories and diagram copying automatically.

## Step 7: Upload Standalone Docs

```bash
cd "$GOOGLEAPIS_DIR" && \
node ~/.cursor/skills/drive-upload-docx/scripts/upload-to-drive.js \
  --input-dir "$OUTPUT_DIR" \
  --folder-id "$FOLDER_ID" \
  --credentials /tmp/gw-credentials.json \
  --convert \
  --mapping-out "$INPUT_DIR/mapping.json"
```

## Step 8: Update Tab Placeholders

```bash
cd "$GOOGLEAPIS_DIR" && \
DOC_ID=$(node -e "const m=require('$INPUT_DIR/tab-mapping.json');const u=Object.values(m)[0].tabUrl;console.log(u.split('/d/')[1].split('/')[0])") && \
node "$SCRIPTS/update-tab-placeholders.mjs" \
  --doc-id "$DOC_ID" \
  --tab-mapping "$INPUT_DIR/tab-mapping.json" \
  --standalone-mapping "$INPUT_DIR/mapping.json"
```

Each tab now has a bold title, copy/paste instructions, and a **clickable link** to the standalone doc.

## Step 9: Manual Merge

For each tab in the root doc:
1. Click the link to open the standalone Google Doc
2. Select All (Cmd+A) → Copy (Cmd+C)
3. Switch to the tabbed root doc → navigate to the matching tab
4. Paste (Cmd+V)

**Validation**: Every internal reference opens the correct tab (`?tab=t.*`). Spot-check 3-5 links per tab.

### Step 9b: Post-Merge Artifact Scan (CRITICAL)

After merging all tabs, scan the entire document for markdown formatting that survived as literal text. This happens because `md-to-docx.js` has incomplete inline formatting support — see [Known Inline Formatting Gaps](#known-inline-formatting-gaps).

Use a single script via the Google Docs API (`includeTabsContent: true`) to scan all tabs:

```javascript
// For each tab, walk all textRun elements and regex-match:
//   /\*\*\*(.+?)\*\*\*/g   — bold-italic artifacts
//   /\*\*(.+?)\*\*/g       — bold artifacts
//   /\*(.+?)\*/g           — italic artifacts
//   /`([^`]+)`/g           — inline code artifacts
//   /\[([^\]]+)\]\(([^)]+)\)/g — markdown link artifacts
```

For each match found, use `batchUpdate` to:
1. `deleteContentRange` the literal markdown text
2. `insertText` with just the inner text
3. `updateTextStyle` to apply native bold/italic/code/hyperlink formatting

**Process from end-to-start within each tab** to avoid index drift. All tabs can be fixed in a single `batchUpdate` call since tab indices are independent.

**Important caveats when fixing artifacts programmatically:**
- **Overlapping regex matches**: When bold markers are adjacent (e.g., `**Label:** value**Next:**`), a `*italic*` regex can match text *between* bold markers, consuming characters from both. Deduplicate matches by checking for index overlap, keeping the wider match.
- **Same-line metadata fields**: Lines like `**Type:** value**Audience:** value` with no line breaks between fields are especially fragile. If the fix corrupts them (truncated labels, lost spacing), delete the entire damaged paragraph and reinsert with correct text and formatting.

## Step 10: Cleanup

```bash
node "$SCRIPTS/cleanup.js" "$INPUT_DIR" --dry-run     # preview
node "$SCRIPTS/cleanup.js" "$INPUT_DIR"                # remove local temp files
node "$SCRIPTS/cleanup.js" "$INPUT_DIR" --trash-drive  # trash standalone docs on Drive
```

**Share the tabbed root doc URL with the user** — this is the final deliverable.

---

## Scripts Reference

All scripts are in `~/.cursor/skills/md-collection-to-google-docs/scripts/`.

| Script | Purpose |
|--------|---------|
| `create-drive-folder.mjs` | Create a Google Drive folder. `--name "Name" [--parent-id <id>]` |
| `create-tabbed-doc.mjs` | Create tabbed Google Doc skeleton. `--title "T" --folder-id <id> (--input-dir <dir> \| --mapping <json>)` |
| `build-tab-url-mapping.js` | Convert tab-mapping.json → resolve-crossrefs format. `<input> [output]` |
| `count-ascii-diagrams.js` | Count diagram blocks md-to-docx.js will detect. Run before creating `.mmd` files. `<markdown-file>` |
| `resolve-crossrefs.js` | Replace relative `.md` links with Google Docs/tab URLs. `<input-dir> <output-dir> <mapping>` |
| `generate-docx-with-diagrams.js` | Generate DOCX with per-file diagram handling. `--input-dir <dir> --output-dir <dir> --script <js>` |
| `upload-to-drive.js` | Upload DOCX → Google Docs. Lives in `drive-upload-docx` skill. `--input-dir <dir> --folder-id <id> --convert` |
| `update-tab-placeholders.mjs` | Add clickable links to tab placeholder text. `--doc-id <id> --tab-mapping <json> --standalone-mapping <json>` |
| `cleanup.js` | Remove temp files + optionally trash Drive docs. `<dir> [--trash-drive] [--dry-run]` |
| `md-to-docx.js` | MD → DOCX converter. Lives in `doc-with-diagrams` skill. Copy to INPUT_DIR before use. |

## Tips

- **No inline code generation.** Every step uses a reusable script. Don't generate ad-hoc Node.js snippets.
- **Create the tabbed skeleton early.** Tab URLs enable cross-refs to point to tabs from the start.
- **Diagrams are mandatory.** Convert ASCII art → Mermaid → PNG before DOCX generation.
- **The tabbed doc is the final deliverable**, not the standalone docs.
- **Keep `tab-mapping.json`** for repeatable updates and re-publishing.

## Known Inline Formatting Gaps

The two markdown-to-Google-Docs paths have complementary gaps in inline formatting:

| Markdown syntax | `md-to-docx.js` (DOCX path) | `gsuite write-md` (API path) |
|-----------------|------------------------------|-------------------------------|
| `**bold**` | Converted | Converted |
| `*italic*` | **NOT converted** — passes as literal `*text*` | Converted |
| `***bold-italic***` | **NOT converted** | Converted |
| `` `code` `` | Converted (Courier New) | **NOT converted** — passes as literal `` `text` `` |
| `[text](url)` | Converted (hyperlink) | **NOT converted** — passes as literal `[text](url)` |

**Impact**: Any markdown syntax not handled by the converter appears as literal asterisks, backticks, or bracket notation in the final Google Doc. The DOCX path (used by this workflow) leaves `*italic*` and `***bold-italic***` as literal text. The API path leaves `` `code` `` and `[links](url)` as literal text.

**Mitigation**: Step 9b (post-merge artifact scan) catches and fixes all of these programmatically after content is in the Google Doc.

## Additional References

- [Tabbed document delivery](references/tabbed-delivery.md) — construction modes, manual merge details
- [Agentic flow for 5+ files](references/agentic-flow.md) — parallel DOCX generation with sub-agents
- [API write limitations](references/api-limitations.md) — why direct Docs API writes fail for tables/images
