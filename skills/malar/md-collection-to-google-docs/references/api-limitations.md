# Direct API Write Limitations

Details on why the Google Docs API is unsuitable as the primary content writing path.

## Known Issues with `gsuite write-md` / `docs write-blocks`

| Issue | Impact |
|-------|--------|
| `insertInlineImage` requires a publicly accessible URL | Fails under Workspace domain policies that block external sharing |
| Tables render as pipe-delimited text, not native table objects | No borders, no column widths, no cell styling |
| Hyperlinks in tables are stripped or rendered as plain text | Links not clickable after copy/paste |
| Index math errors compound across structural elements | Batch updates can fail mid-document, leaving partial content |
| `write-md` does not convert `[links](url)` or `` `code` `` | Literal markdown syntax in output |

Use direct API writes only for incremental single-block updates to existing docs (e.g., updating a heading or appending a paragraph).

## Inline Formatting Gaps (Both Paths)

Neither the DOCX path nor the API path converts all inline markdown. See the comparison table in the main SKILL.md under "Known Inline Formatting Gaps". After any content migration, run a post-upload artifact scan (Step 9b) to catch and fix surviving markdown syntax.

## Programmatic Content Replay (Last Resort)

Reading a source doc's structure and replaying it into a target doc/tab via `batchUpdate` (`insertText` + `insertTable` + `updateTextStyle` per element) is technically possible but should be treated as a **last resort**.

Compared to DOCX upload:

- **Partial failure risk**: an error mid-batch leaves the doc half-written with no rollback; DOCX upload is atomic
- **Table index math is fragile**: `insertTable` + per-cell `insertText` requires reverse-order filling to avoid index drift; any miscalculation corrupts the table
- **Image insertion may fail**: `insertInlineImage` requires a publicly accessible URL even when copying from another Google Doc's `contentUri`
- **Per-tab targeting adds complexity**: every `location` and `range` object needs an explicit `tabId`, compounding the index math burden
- **More code, worse output**: hundreds of API requests to reconstruct what a single DOCX upload handles natively

If you find yourself writing a "read doc A → replay into doc B" script, stop and convert the source to DOCX instead.

## Workspace Domain Restrictions

Google Workspace orgs may block `drive.permissions.create` with `type: 'anyone'`, preventing `insertInlineImage` from working (the image URL must be publicly accessible for the Docs API server to fetch it). DOCX upload bypasses this entirely because image bytes are embedded in the DOCX binary.
