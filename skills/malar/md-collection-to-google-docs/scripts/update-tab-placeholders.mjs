#!/usr/bin/env node
/**
 * Update placeholder text in tabs of a tabbed Google Doc.
 * Adds styled title + clickable link to each standalone source doc.
 *
 * Usage:
 *   node update-tab-placeholders.mjs \
 *     --doc-id <google-doc-id> \
 *     --tab-mapping <tab-mapping.json> \
 *     --standalone-mapping <mapping.json> \
 *     [--credentials <path>] [--token <path>]
 *
 * tab-mapping.json: { "file.md": { "tabId": "t.xxx", "title": "Tab Title" } }
 * mapping.json:     { "file.md": { "fileId": "...", "url": "https://..." } }
 */
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { homedir } from 'node:os';
import { createRequire } from 'node:module';

const require = createRequire(resolve(process.cwd(), '__placeholder.js'));
const { google } = require('googleapis');

function parseArgs(argv) {
  const args = {
    docId: null, tabMappingPath: null, standaloneMappingPath: null,
    credentials: process.env.GOOGLE_CREDENTIALS_PATH || '/tmp/gw-credentials.json',
    token: resolve(homedir(), '.cb-mcp', 'google-workspace-mcp.json'),
  };
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case '--doc-id':              args.docId = argv[++i]; break;
      case '--tab-mapping':         args.tabMappingPath = argv[++i]; break;
      case '--standalone-mapping':  args.standaloneMappingPath = argv[++i]; break;
      case '--credentials':         args.credentials = argv[++i]; break;
      case '--token':               args.token = argv[++i]; break;
    }
  }
  if (!args.docId || !args.tabMappingPath || !args.standaloneMappingPath) {
    console.error('Usage: node update-tab-placeholders.mjs --doc-id <id> --tab-mapping <path> --standalone-mapping <path>');
    process.exit(1);
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);

  const cred = JSON.parse(await readFile(args.credentials, 'utf-8'));
  const { client_id, client_secret } = cred.installed || cred.web || {};
  const tok = JSON.parse(await readFile(args.token, 'utf-8'));
  const o = new google.auth.OAuth2(client_id, client_secret, 'http://localhost:3737');
  o.setCredentials(tok);
  o.on('tokens', async (nt) => {
    await writeFile(args.token, JSON.stringify({ ...tok, ...nt }, null, 2), 'utf-8');
  });

  const docs = google.docs({ version: 'v1', auth: o });
  const tabMapping = JSON.parse(await readFile(args.tabMappingPath, 'utf-8'));
  const standaloneMapping = JSON.parse(await readFile(args.standaloneMappingPath, 'utf-8'));

  // Get current doc to find content extents per tab
  const docData = await docs.documents.get({ documentId: args.docId, includeTabsContent: true });

  for (const [md, tabInfo] of Object.entries(tabMapping)) {
    const tab = docData.data.tabs.find(t => t.tabProperties.tabId === tabInfo.tabId);
    if (!tab) { console.log('SKIP (no tab): ' + md); continue; }

    const standaloneUrl = standaloneMapping[md]?.url
      || standaloneMapping[md.replace(/^internal\//, '')]?.url
      || null;
    if (!standaloneUrl) { console.log('SKIP (no standalone URL): ' + md); continue; }

    const body = tab.documentTab?.body;
    const endIndex = body?.content?.slice(-1)?.[0]?.endIndex || 2;

    // Clear existing content
    if (endIndex > 2) {
      await docs.documents.batchUpdate({
        documentId: args.docId,
        requestBody: { requests: [{ deleteContentRange: { range: { startIndex: 1, endIndex: endIndex - 1, tabId: tabInfo.tabId } } }] },
      });
    }

    const title = tabInfo.title || md.replace(/\.md$/, '');
    const linkText = 'Open standalone doc: ' + title;
    const instrText = 'Copy content from the standalone Google Doc below.\nSelect All (Cmd+A) then Copy (Cmd+C) then Paste (Cmd+V) into this tab.\n\n';
    const fullText = title + '\n\n' + instrText + linkText + '\n';

    // Insert text
    await docs.documents.batchUpdate({
      documentId: args.docId,
      requestBody: { requests: [{ insertText: { text: fullText, location: { index: 1, tabId: tabInfo.tabId } } }] },
    });

    // Style: make link clickable + bold title
    const linkStart = fullText.indexOf(linkText) + 1;
    const linkEnd = linkStart + linkText.length;
    await docs.documents.batchUpdate({
      documentId: args.docId,
      requestBody: {
        requests: [
          { updateTextStyle: {
            textStyle: { link: { url: standaloneUrl } },
            range: { startIndex: linkStart, endIndex: linkEnd, tabId: tabInfo.tabId },
            fields: 'link',
          }},
          { updateTextStyle: {
            textStyle: { bold: true, fontSize: { magnitude: 18, unit: 'PT' } },
            range: { startIndex: 1, endIndex: 1 + title.length, tabId: tabInfo.tabId },
            fields: 'bold,fontSize',
          }},
        ],
      },
    });

    console.log('OK  ' + title + ' -> ' + standaloneUrl);
  }

  console.log('\nDone. Each tab now has a clickable link to its standalone doc.');
}

main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
