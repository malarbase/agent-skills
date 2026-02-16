# Tabbed Document Delivery

The tabbed root doc is the **default final deliverable**. Standalone docs are intermediaries for copy/paste.

## Tab-First Workflow

Create the tabbed skeleton **before** generating DOCX so cross-references resolve to tab URLs from the start:

```
1. Create Drive folder             → create-drive-folder.mjs
2. Create tabbed root doc          → create-tabbed-doc.mjs --input-dir
3. Build tab URL mapping           → build-tab-url-mapping.js
4. Resolve cross-refs to tab URLs  → resolve-crossrefs.js
5. Convert diagrams → Mermaid → PNG
6. Generate DOCX with diagrams     → generate-docx-with-diagrams.js
7. Upload DOCX as standalone docs  → upload-to-drive.js
8. Update tab placeholders         → update-tab-placeholders.mjs
9. Manual merge (copy/paste)
10. Cleanup                        → cleanup.js --trash-drive
```

## Known Pitfalls

1. **Default "Tab 1" must be deleted.** `create-tabbed-doc.mjs` handles this automatically using `{ deleteTab: { tabId: 't.0' } }`. The API field is `deleteTab` (NOT `deleteDocumentTab`).

2. **Cross-refs must use tab URLs.** Use `build-tab-url-mapping.js` to convert `tab-mapping.json` to the format `resolve-crossrefs.js` expects.

3. **Diagrams must be converted.** Never skip ASCII→Mermaid→PNG. Use `generate-docx-with-diagrams.js` to handle per-file diagram directories automatically.

4. **Tab placeholders need clickable links.** After uploading standalone docs, run `update-tab-placeholders.mjs` to insert styled titles and clickable links. Without this, the user has no easy way to find the source doc for each tab.

## Construction Modes

Default to **Mode 1**.

| Mode | Reliability | Effort | Best for |
|------|-------------|--------|----------|
| 1. Skeleton + copy/paste | High | Low | Most workflows |
| 2. Incremental blocks | Medium | High | Fine-grained control |
| 3. Browser-assisted | Medium-Low | Medium | Time-boxed migrations |

---

## Mode 1: Tabbed Skeleton + Manual Merge (Default)

All steps use reusable scripts from `~/.cursor/skills/md-collection-to-google-docs/scripts/`.

### T1: Create skeleton

```bash
node $SCRIPTS/create-tabbed-doc.mjs \
  --title "Project Documentation" \
  --folder-id "$FOLDER_ID" \
  --input-dir "$INPUT_DIR" \
  --tabs-out "$INPUT_DIR/tab-mapping.json"
```

The script:
1. Scans `--input-dir` for `.md` files (README first, then alphabetical)
2. Creates one named tab per file
3. Deletes the default "Tab 1"
4. Writes `tab-mapping.json`

### T2: Resolve cross-references

```bash
node $SCRIPTS/build-tab-url-mapping.js "$INPUT_DIR/tab-mapping.json"
node $SCRIPTS/resolve-crossrefs.js "$INPUT_DIR" "$INPUT_DIR/_resolved" "$INPUT_DIR/tab-url-mapping.json"
```

### T3: Convert diagrams + generate DOCX

```bash
# Create .mmd files for ASCII diagrams, render to PNG, then:
node $SCRIPTS/generate-docx-with-diagrams.js \
  --input-dir "$INPUT_DIR/_resolved" \
  --output-dir "$OUTPUT_DIR" \
  --script "$INPUT_DIR/md-to-docx.js" \
  --diagrams-dir "$INPUT_DIR"
```

### T4: Upload standalone docs

```bash
node ~/.cursor/skills/drive-upload-docx/scripts/upload-to-drive.js \
  --input-dir "$OUTPUT_DIR" --folder-id "$FOLDER_ID" --convert \
  --mapping-out "$INPUT_DIR/mapping.json"
```

### T5: Update tab placeholders

```bash
node $SCRIPTS/update-tab-placeholders.mjs \
  --doc-id "$DOC_ID" \
  --tab-mapping "$INPUT_DIR/tab-mapping.json" \
  --standalone-mapping "$INPUT_DIR/mapping.json"
```

### T6: Manual merge

Click the link in each tab → Select All → Copy → Paste into the tab.

### T7: Validation

- Every internal reference opens the correct tab (`?tab=t.*`)
- No visible markdown link literals remain
- Spot-check 3-5 links per tab

### T8: Cleanup

```bash
node $SCRIPTS/cleanup.js "$INPUT_DIR" --trash-drive
```

---

## Mode 2: Incremental Block Insertion

Build tabs programmatically with `docs write-md` or `docs write-blocks`. **Not recommended for docs with tables or images** — tables render as pipe-delimited text, images require public URLs.

## Mode 3: Browser-Assisted Copy/Paste (Experimental)

Use browser automation to transfer content from standalone docs into tabs. Safety: checkpoint every 2-3 tabs, fall back to Mode 1 if unstable.
