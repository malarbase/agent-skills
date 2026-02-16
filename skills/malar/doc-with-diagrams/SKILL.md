---
name: doc-with-diagrams
description: Convert markdown documents with ASCII/text diagrams into professional
  Word documents with embedded Mermaid diagrams. Use when converting technical documentation
  to Word format, creating Word docs with flowcharts/sequence diagrams, or when the
  user mentions converting docs with diagrams to docx.
metadata:
  author: malar
  tags:
  - doc
  - with
  - diagrams
  - curated
---

# Document with Diagrams

Convert markdown with ASCII art diagrams into Word documents with rendered Mermaid diagrams.

## Prerequisites

```bash
npm install -g @mermaid-js/mermaid-cli

# If mmdc fails to find Chrome:
PUPPETEER_CACHE_DIR=~/.cache/puppeteer npx puppeteer browsers install chrome-headless-shell
```

## Workflow

The workflow is **stateless** -- every run starts clean. The agent handles all steps including Mermaid conversion.

### Step 1: Isolate Run and Setup

**Always start here.** The script looks for diagram files in a `diagrams/` directory relative to the input file. To avoid stale artifacts from previous runs, move any existing `diagrams/` aside before creating a fresh one.

```bash
# Determine diagrams dir (same parent as input file)
INPUT_DIR="$(dirname input.md)"
DIAGRAMS_DIR="$INPUT_DIR/diagrams"

# Non-destructive: archive previous run's diagrams (if any)
if [ -d "$DIAGRAMS_DIR" ]; then
  mv "$DIAGRAMS_DIR" "${DIAGRAMS_DIR}-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$DIAGRAMS_DIR"

# Copy script and install dependency
cp ~/.cursor/skills/doc-with-diagrams/scripts/md-to-docx.js "$INPUT_DIR/"
npm install docx
```

Old diagrams are preserved in `diagrams-YYYYMMDD-HHMMSS/` and can be deleted manually later.

### Step 2: First Pass -- Identify Diagrams

```bash
node md-to-docx.js input.md output.docx
```

Output reports diagram counts:
```
Found 85 blocks
ASCII diagrams: 3, Mermaid diagrams: 0

To convert ASCII diagrams, create files in ./diagrams/:
  01-diagram-name.mmd
  02-diagram-name.mmd
  03-diagram-name.mmd
```

### Step 3: Create Mermaid Files (Agent-Driven)

**The agent MUST handle this step automatically.** Do NOT ask the user to create `.mmd` files manually.

For each ASCII diagram reported in Step 2:

1. Read the markdown file and locate each ASCII diagram **in sequential order** (the script detects them by box-drawing characters like `┌┐└┘├┤─│`, arrows `──▶`, and ASCII boxes `+--+`)
2. Analyze the ASCII art's meaning, labels, connections, and annotations
3. Write a Mermaid `.mmd` file to `diagrams/0N-descriptive-name.mmd`

**ASCII-to-Mermaid mapping:**

| ASCII Pattern | Mermaid Type |
|---------------|--------------|
| Boxes with arrows, flow routing | `flowchart LR` or `flowchart TD` |
| Sequential steps with `│ ▼` arrows | `flowchart TD` or `sequenceDiagram` |
| Actor-to-actor interactions | `sequenceDiagram` |
| Entity relationships | `erDiagram` |
| State transitions | `stateDiagram-v2` |

**Rules:**
- Preserve ALL labels, annotations, and semantic meaning from the original ASCII art
- **Always use `flowchart`, never `graph`** — `graph` is a legacy alias that does not enable HTML labels, causing `<br/>` to render as literal text in `mmdc` PNG output
- Use `flowchart` for most structural/routing diagrams
- Use `sequenceDiagram` when the diagram shows message passing between actors
- For line breaks in node labels, use `<br/>` inside quoted labels: `A["Line 1<br/>Line 2"]`
- Quote node labels containing special characters: `A["Label with (parens)"]`
- For detailed syntax, read the mermaid-diagrams skill

### Step 4: Render to PNG

```bash
cd "$DIAGRAMS_DIR"
for f in *.mmd; do
  PUPPETEER_CACHE_DIR=~/.cache/puppeteer mmdc -i "$f" -o "${f%.mmd}.png" -w 1200 --scale 2 -b white
done
cd -
```

If rendering fails for a diagram, check the `.mmd` syntax and fix it before proceeding.

### Step 5: Generate Final DOCX

```bash
node md-to-docx.js input.md output.docx
```

The script automatically:
- Matches `0N-*.png` files to the Nth ASCII diagram position
- Calculates correct aspect ratios from actual pixel dimensions
- Embeds images without distortion
- Renders any ` ```mermaid ` code blocks directly (no `.mmd` file needed)

## Script Location

```
~/.cursor/skills/doc-with-diagrams/scripts/md-to-docx.js
```

Copy to the input file's directory before use.

## What the Script Handles

- **Headings** -> H1-H4 with styled formatting
- **Paragraphs** -> Normal text with spacing; inline **bold**, `code`, and [hyperlinks](url) preserved
- **Images** -> `![alt](path)` references embedded as inline images with correct aspect ratio
- **Tables** -> Native DOCX tables with colored headers; hyperlinks and bold in cells preserved
- **Code blocks** -> Monospace with gray background
- **Lists** -> Ordered (numbered) and unordered (bullet); inline formatting preserved in items
- **Blockquotes** -> Indented with blue highlight
- **Horizontal rules** -> Border separator
- **ASCII diagrams** -> Replaced with PNG (if `0N-*.png` exists in `diagrams/`)
- **Mermaid blocks** -> Auto-rendered to PNG via mmdc

## Known Inline Formatting Gaps

`parseInlineFormatting()` (line ~252) uses a single regex that handles `[links](url)`, `**bold**`, and `` `code` `` but does **NOT** handle:

| Syntax | Status | Result in DOCX |
|--------|--------|----------------|
| `*italic*` | Not converted | Literal `*text*` in output |
| `***bold-italic***` | Not converted | Literal `***text***` in output |

The regex: `/(\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|`(.+?)`)/g`

To add italic support, the regex would need `\*(.+?)\*` added **after** the `\*\*` branch (order matters to avoid `**bold**` being consumed by `*italic*`). This has not been done yet because single `*` is also used for bullet lists and multiplication, making false positives likely without context-aware parsing.

**Workaround**: When the DOCX is uploaded to Google Docs, run a post-upload artifact scan to fix surviving markdown syntax programmatically — see the `md-collection-to-google-docs` skill, Step 9b.

## CRITICAL: Aspect Ratio

The script auto-calculates dimensions from actual pixel sizes. **NEVER hardcode width/height values.**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Wrong/stale diagrams from previous run | You skipped Step 1 -- archive old `diagrams/` and create a fresh one |
| `[ASCII Diagram N - create 0N-name.mmd]` in output | Agent missed a diagram -- create the missing `.mmd` |
| Diagram numbering mismatch | Ensure `.mmd` files are numbered in the same order the script encounters ASCII diagrams |
| Images look skewed | Ensure you're using the script (not manual dimensions) |
| `Cannot find module 'docx'` | Run `npm install docx` |
| `mmdc: command not found` | Run `npm install -g @mermaid-js/mermaid-cli` |
| `Could not find Chrome` | See Chrome fix below |

### Chrome/Puppeteer Fix

```bash
# Install required Chrome version
PUPPETEER_CACHE_DIR=~/.cache/puppeteer npx puppeteer browsers install chrome-headless-shell

# If a specific version is requested (e.g., 131.0.6778.204):
PUPPETEER_CACHE_DIR=~/.cache/puppeteer npx puppeteer browsers install chrome-headless-shell@131.0.6778.204

# Always use PUPPETEER_CACHE_DIR when running mmdc
PUPPETEER_CACHE_DIR=~/.cache/puppeteer mmdc -i diagram.mmd -o diagram.png -w 1200 --scale 2 -b white
```
