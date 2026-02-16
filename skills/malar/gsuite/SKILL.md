---
name: gsuite
description: Standalone Google Workspace CLI for Docs, Drive, Sheets, Calendar, and
  Gmail operations via googleapis. Bypasses MCP context-window limits for large file
  uploads/downloads. Use when performing Google Workspace operations, batch uploads,
  large file transfers, importing data to Sheets, or when the MCP server is unavailable.
metadata:
  author: malar
  tags:
  - google-workspace
  - cli
  - drive
  - docs
  - sheets
  - curated
---

# Google Workspace CLI

Standalone CLI for all Google Workspace operations using the MCP server's existing OAuth credentials. No MCP server needed.

## When to Use This vs MCP

| Scenario | CLI | MCP |
|----------|-----|-----|
| Upload large files (100KB+) | Best | Fails (context limit) |
| Batch upload a directory | Best | Slow (one-by-one) |
| Import large CSV to Sheets | Best | Fails (context limit) |
| Download/export files to disk | Best | Returns in context |
| Quick single-doc read/edit | Either | Simpler |
| Create doc or folder | Either | Simpler |
| MCP server unavailable | Only option | N/A |

## Prerequisites

Run from a directory with `googleapis` installed:

```bash
npm install googleapis
cd /path/to/cb-mcp/packages/google-workspace-mcp  # already has it
```

The script resolves `googleapis` from the **current working directory** via `createRequire`.

## Auth Setup

Reuses the MCP server's OAuth token at `~/.cb-mcp/google-workspace-mcp.json`. If no `credentials.json` file exists, decode from the MCP build config:

```bash
node -e "const c = require('/path/to/cb-mcp/packages/google-workspace-mcp/credentials.config.cjs'); \
  require('fs').writeFileSync('/tmp/gw-credentials.json', Buffer.from(c.GOOGLE_CREDENTIALS_BASE64, 'base64'));"
```

Global flags: `--credentials <path>`, `--token <path>`.

### Credential Resolution Order

The script resolves credentials in this order:
1. `--credentials <path>` flag (explicit)
2. `$GOOGLE_CREDENTIALS_PATH` environment variable
3. `./credentials/credentials.json` **relative to CWD**

**Common pitfall**: If your CWD lacks `credentials/credentials.json`, you'll get `ENOENT`. Either:
- Copy/symlink credentials into your CWD: `mkdir -p credentials && cp /tmp/gw-credentials.json credentials/credentials.json`
- Or always pass `--credentials /tmp/gw-credentials.json` explicitly

Token defaults to `~/.cb-mcp/google-workspace-mcp.json` and rarely needs overriding.

## Command Reference

```bash
node ~/.cursor/skills/gsuite/scripts/gsuite.js <service> <action> [positional-args] [--flags]
```

All commands output JSON to stdout. Status messages go to stderr.

### Invocation Pitfalls

**Do NOT store the full command in a shell variable.** zsh/bash treats `$VAR args` as a single command lookup, not `node` + args:

```bash
# BAD — fails with "no such file or directory"
GSUITE="node ~/.cursor/skills/gsuite/scripts/gsuite.js"
$GSUITE docs read DOC_ID

# GOOD — call node directly
node ~/.cursor/skills/gsuite/scripts/gsuite.js docs read DOC_ID

# GOOD — use an alias or function
gsuite() { node ~/.cursor/skills/gsuite/scripts/gsuite.js "$@"; }
gsuite docs read DOC_ID
```

**Positional args come before flags.** Commands like `add-tab`, `list-tabs`, `read` take `<docId>` as a positional argument, **not** a `--doc-id` flag:

```bash
# BAD — errors with "Usage: docs add-tab <docId> ..."
node gsuite.js docs add-tab --doc-id DOC_ID --title "Tab Name"

# GOOD — docId is positional
node gsuite.js docs add-tab DOC_ID --title "Tab Name"
```

### Google Docs

| Command | Description |
|---------|-------------|
| `docs read <docId> [--structure]` | Read text (or full API structure) |
| `docs create --title <t> [--content <text>] [--folder-id <id>]` | Create document |
| `docs append <docId> --text <t> \| --file <path>` | Append text |
| `docs replace <docId> --old <t> --new <t>` | Find and replace |
| `docs list-tabs <docId>` | List tabs |
| `docs add-tab <docId> --title <t> [--parent-tab <tabId>]` | Add tab to doc |
| `docs write-blocks <docId> --blocks-file <path> [--tab <tabId>] [--clear]` | Write content blocks (JSON) to a tab |
| `docs write-md <docId> --file <path> [--tab <tabId>] [--clear] [--images-dir <path>] [--images-folder-id <id>]` | Write markdown to a tab with image upload |

`--content` supports `@path/to/file.txt` to read from file.

#### Block types for `write-blocks`

The `--blocks-file` JSON is an array of `ContentBlock` objects:

| Type | Fields | Notes |
|------|--------|-------|
| `heading` | `text`, `level` (1-6) | |
| `paragraph` | `text` | Supports `**bold**`, `*italic*`, `***both***` |
| `code` | `text`, `language` | Courier New + gray background |
| `table` | `headers`, `rows` | Pipe-delimited text, bold headers |
| `image` | `uri`, `width`, `height` | URI must be a Drive or public URL |
| `list` | `items`, `ordered` | Bullets or numbered |

#### `write-md` image handling

Local image paths (`![alt](./path.png)`) are auto-uploaded to Drive:
- Looks in `--images-dir` first, then relative to the markdown file
- Uploads to `--images-folder-id` (optional) and inserts the Drive URI
- URLs (`http://...`) are passed through unchanged

### Google Drive

| Command | Description |
|---------|-------------|
| `drive search [--query <q>] [--type <t>] [--folder <id>]` | Search files |
| `drive ls [--folder-id <id>] [--max <n>]` | List folder |
| `drive get <fileId> [--permissions]` | File metadata |
| `drive read <fileId> [--format text\|html\|csv\|pdf] [--output <path>]` | Download/export |
| `drive mkdir --name <n> [--parent-id <id>]` | Create folder |
| `drive upload --file <path> [--folder-id <id>] [--convert]` | Upload file |
| `drive upload-dir --input-dir <path> --folder-id <id> [--convert] [--mapping-out <p>]` | Batch upload |
| `drive share <fileId> --email <e> --role <r> [--notify]` | Share file |
| `drive delete <fileId> [--permanent]` | Trash (or delete) |

`--type` options: document, spreadsheet, presentation, folder, pdf, image.
`--format` for read: text, html, csv, pdf, docx, xlsx.
`--convert` converts to Google format on upload (DOCX→Doc, XLSX→Sheet, etc.).

### Google Sheets

| Command | Description |
|---------|-------------|
| `sheets read <id> [--range <r>] [--metadata]` | Read data or metadata |
| `sheets create --title <t> [--sheets s1,s2] [--folder-id <id>]` | Create spreadsheet |
| `sheets write <id> --range <r> (--values <json> \| --values-file <path>)` | Write values |
| `sheets append <id> --range <r> (--values <json> \| --values-file <path>)` | Append rows |
| `sheets clear <id> --range <r>` | Clear range |
| `sheets import <id> --file <path> --range <r>` | Import CSV/JSON |

Values format: `'[["a","b"],["c","d"]]'`. Use `--raw` for RAW input (default: USER_ENTERED).

### Calendar (read-only)

| Command | Description |
|---------|-------------|
| `calendar list --from <d> --to <d> [--calendar <id>]` | List events |
| `calendar get <eventId> [--calendar <id>]` | Event details |
| `calendar search --query <q> [--from <d>] [--to <d>]` | Search events |
| `calendar calendars` | List all calendars |
| `calendar freebusy --from <d> --to <d> [--calendars id1,id2]` | Check availability |

Date values: ISO 8601, or `today`, `tomorrow`, `yesterday`, `now`, `end-of-today`, `next-week`.

### Gmail (read-only)

| Command | Description |
|---------|-------------|
| `gmail list [--query <q>] [--labels l1,l2] [--max <n>]` | List messages |
| `gmail read <messageId> [--format full\|metadata\|minimal]` | Read message |
| `gmail search --query <q> [--max <n>]` | Search messages |

## Examples

### Batch upload DOCX, convert to Google Docs

```bash
node gsuite.js drive upload-dir \
  --input-dir ./docs/_docx \
  --folder-id FOLDER_ID \
  --credentials /tmp/gw-credentials.json \
  --convert \
  --mapping-out ./docs/mapping.json
```

### Import CSV into Sheets

```bash
node gsuite.js sheets import SPREADSHEET_ID \
  --file ./data/sales.csv \
  --range "Sheet1!A1" \
  --credentials /tmp/gw-credentials.json
```

### Download a Google Doc as HTML

```bash
node gsuite.js drive read DOC_ID --format html --output ./doc.html
```

### Today's calendar events

```bash
node gsuite.js calendar list --from today --to end-of-today
```

### Publish markdown collection as a single tabbed Google Doc

```bash
# Create the doc
DOC=$(node gsuite.js docs create --title "My Documentation" --folder-id FOLDER_ID | jq -r '.documentId')

# Write README.md to the default (first) tab
node gsuite.js docs write-md $DOC --file ./README.md --clear \
  --images-dir ./diagrams-README --images-folder-id $IMG_FOLDER

# Add tabs for each additional file and write content
for name in architecture-overview troubleshooting api-reference; do
  TAB=$(node gsuite.js docs add-tab $DOC --title "$name" | jq -r '.tabId')
  node gsuite.js docs write-md $DOC --file "./$name.md" --tab $TAB --clear \
    --images-dir "./diagrams-$name" --images-folder-id $IMG_FOLDER
done
```

### Create a skeleton tabbed doc with links (lightweight alternative)

When full content migration is complex (many diagrams, large files), create a skeleton with tabs linking to standalone docs instead. Then copy-paste manually at your own pace.

```bash
DOC=$(node gsuite.js docs create --title "My Documentation" --folder-id FOLDER_ID | jq -r '.documentId')

# The default first tab has id "t.0" — rename it
# (No CLI command for rename; use batchUpdate directly — see "Direct API" section)

# Add tabs
for name in "Architecture" "Troubleshooting" "API Reference"; do
  node gsuite.js docs add-tab $DOC --title "$name"
done

# Write a title + link into each tab using write-md with a temp markdown file
```

### Rename a tab (direct API — no CLI command)

There is no `docs rename-tab` CLI command. Use `googleapis` directly:

```javascript
// updateDocumentTabProperties — note tabId goes INSIDE tabProperties
await docs.documents.batchUpdate({
  documentId: DOC_ID,
  requestBody: {
    requests: [{
      updateDocumentTabProperties: {
        tabProperties: { tabId: 't.0', title: 'New Title' },
        fields: 'title'
      }
    }]
  }
});
```

**Critical**: `tabId` must be **inside** `tabProperties`, not a sibling field. The API returns `"Unknown name 'tabId'"` if placed incorrectly.

### Write content to a specific tab (direct API)

When using `insertText` or `updateTextStyle` against a specific tab, include `tabId` in every `location` and `range` object:

```javascript
// Insert text at beginning of a specific tab
{
  insertText: {
    text: 'Hello World\n',
    location: { index: 1, tabId: 't.abc123' }  // tabId required!
  }
}

// Style text in a specific tab
{
  updateTextStyle: {
    range: { startIndex: 1, endIndex: 12, tabId: 't.abc123' },  // tabId required!
    textStyle: { bold: true },
    fields: 'bold'
  }
}
```

Without `tabId`, requests default to the first tab (`t.0`).

### Pipe-friendly: get file IDs from search

```bash
node gsuite.js drive search --query "quarterly" --type document | jq '.files[].id'
```

## Relationship to Other Skills

- **drive-upload-docx**: Specialized for the `md-collection-to-google-docs` workflow (maps .docx → .md keys). Use that skill for that specific pipeline.
- **google-workspace-mcp**: MCP-based tool reference. Use MCP for quick interactive operations where context-window size isn't an issue.
- **This skill (gsuite)**: General-purpose CLI for all operations, especially large files and batch work.

## `write-md` Inline Formatting Gaps

`docs write-md` converts `**bold**`, `*italic*`, and `***bold-italic***` to native Google Docs formatting via `parseInlineFormatting()`. However, it does **NOT** handle:

| Syntax | Status | Result in Google Doc |
|--------|--------|----------------------|
| `[text](url)` | Not converted | Literal `[text](url)` text, no hyperlink |
| `` `code` `` | Not converted | Literal backtick-wrapped text, no monospace |

**Workaround**: After `write-md`, use the Google Docs API directly to scan for `[text](url)` and `` `code` `` patterns and replace them with native links/code formatting via `batchUpdate`. Or use the DOCX upload path (`md-to-docx.js` + `drive upload --convert`) which handles links and code but not italic — see `md-collection-to-google-docs` skill for the full comparison table.

## Known Gotchas

| Problem | Cause | Fix |
|---------|-------|-----|
| `no such file or directory: node /path/gsuite.js` | Stored full command in shell variable, zsh treats as single path | Call `node /path/gsuite.js` directly or use a shell function |
| `ENOENT: credentials/credentials.json` | CWD lacks the default credentials path | Pass `--credentials /path` or copy to `./credentials/` |
| `Usage: docs add-tab <docId> ...` | Used `--doc-id` flag instead of positional arg | Put docId before flags: `docs add-tab DOC_ID --title "..."` |
| `Unknown name "tabId" at update_document_tab_properties` | `tabId` placed as sibling of `tabProperties` | Nest `tabId` **inside** `tabProperties: { tabId, title }` |
| `Unknown name "updateDocumentTab"` | Wrong request type name | Use `updateDocumentTabProperties` (not `updateDocumentTab`) |
| Content goes to wrong tab | Missing `tabId` in `location`/`range` objects | Always include `tabId` in every `location` and `range` for multi-tab docs |
| SSL error on upload (intermittent) | Transient network/TLS issue | Retry the upload command; usually succeeds on second attempt |

## Design Notes

- `createRequire(cwd)` resolves `googleapis` from working directory
- Token auto-refresh with persistence to disk
- Sequential uploads to respect Drive API rate limits
- JSON to stdout, status to stderr — pipe-friendly
- Non-zero exit on any failure
- Default tab in new docs has id `t.0`
