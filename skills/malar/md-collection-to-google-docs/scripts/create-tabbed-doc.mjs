#!/usr/bin/env node
/**
 * Create a tabbed Google Doc skeleton with one tab per markdown file.
 * Deletes the auto-created default "Tab 1" so all tabs have proper names.
 *
 * Usage (from mapping):
 *   node create-tabbed-doc.mjs \
 *     --title "Doc Title" --folder-id <id> --mapping <mapping.json> \
 *     [--tabs-out <tab-mapping.json>]
 *
 * Usage (from input directory):
 *   node create-tabbed-doc.mjs \
 *     --title "Doc Title" --folder-id <id> --input-dir <dir> \
 *     [--tabs-out <tab-mapping.json>]
 *
 * Run from a directory with `googleapis` in node_modules.
 * OAuth credentials: --credentials (default /tmp/gw-credentials.json)
 * OAuth token: --token (default ~/.cb-mcp/google-workspace-mcp.json)
 *
 * Output: tab-mapping.json with { "file.md": { "tabId", "tabUrl", "title" } }
 */
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { homedir } from 'node:os';
import { createRequire } from 'node:module';

const require = createRequire(resolve(process.cwd(), '__placeholder.js'));
const { google } = require('googleapis');

function parseArgs(argv) {
  const args = {
    title: null, folderId: null, mappingPath: null, inputDir: null, tabsOut: null,
    credentials: process.env.GOOGLE_CREDENTIALS_PATH || '/tmp/gw-credentials.json',
    token: resolve(homedir(), '.cb-mcp', 'google-workspace-mcp.json'),
  };
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case '--title':       args.title = argv[++i]; break;
      case '--folder-id':   args.folderId = argv[++i]; break;
      case '--mapping':     args.mappingPath = argv[++i]; break;
      case '--input-dir':   args.inputDir = argv[++i]; break;
      case '--tabs-out':    args.tabsOut = argv[++i]; break;
      case '--credentials': args.credentials = argv[++i]; break;
      case '--token':       args.token = argv[++i]; break;
    }
  }
  if (!args.title || !args.folderId || (!args.mappingPath && !args.inputDir)) {
    console.error('Usage: node create-tabbed-doc.mjs --title "Title" --folder-id <id> (--mapping <json> | --input-dir <dir>)');
    process.exit(1);
  }
  return args;
}

function titleFromFilename(md) {
  return md.replace(/^internal\//, '').replace(/\.md$/, '')
    .split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

async function discoverFiles(inputDir) {
  const files = [];
  async function scan(dir, prefix) {
    const entries = await readdir(dir, { withFileTypes: true });
    for (const e of entries) {
      if (e.isFile() && e.name.endsWith('.md') && !e.name.startsWith('_')) {
        files.push(prefix ? prefix + '/' + e.name : e.name);
      } else if (e.isDirectory() && !e.name.startsWith('_') && !e.name.startsWith('.')) {
        await scan(join(dir, e.name), prefix ? prefix + '/' + e.name : e.name);
      }
    }
  }
  await scan(inputDir, '');
  // Sort: README first, then alphabetical
  files.sort((a, b) => {
    if (a.toLowerCase().startsWith('readme')) return -1;
    if (b.toLowerCase().startsWith('readme')) return 1;
    return a.localeCompare(b);
  });
  return files;
}

async function main() {
  const args = parseArgs(process.argv);

  const credRaw = await readFile(args.credentials, 'utf-8');
  const credJson = JSON.parse(credRaw);
  const { client_id, client_secret } = credJson.installed || credJson.web || {};
  const tokenRaw = await readFile(args.token, 'utf-8');
  const tokens = JSON.parse(tokenRaw);
  const oauth2Client = new google.auth.OAuth2(client_id, client_secret, 'http://localhost:3737');
  oauth2Client.setCredentials(tokens);
  oauth2Client.on('tokens', async (nt) => {
    await writeFile(args.token, JSON.stringify({ ...tokens, ...nt }, null, 2), 'utf-8');
  });

  const docs = google.docs({ version: 'v1', auth: oauth2Client });
  const drive = google.drive({ version: 'v3', auth: oauth2Client });

  // Discover files — from mapping or input directory
  let mdFiles, mapping;
  if (args.mappingPath) {
    mapping = JSON.parse(await readFile(args.mappingPath, 'utf-8'));
    mdFiles = Object.keys(mapping).filter(k => !k.includes('/'));
    for (const k of Object.keys(mapping)) {
      if (k.includes('/') && !mdFiles.includes(k.split('/').pop())) mdFiles.push(k);
    }
  } else {
    mdFiles = await discoverFiles(args.inputDir);
    mapping = {};
  }

  console.log('Creating root doc: "' + args.title + '"...');
  console.log('  Files: ' + mdFiles.length);

  // Create root document
  const createRes = await docs.documents.create({ requestBody: { title: args.title } });
  const docId = createRes.data.documentId;
  console.log('  Document ID: ' + docId);

  // Move into Drive folder
  const fileRes = await drive.files.get({ fileId: docId, fields: 'parents' });
  await drive.files.update({
    fileId: docId, addParents: args.folderId,
    removeParents: (fileRes.data.parents || []).join(','), fields: 'id',
  });

  // Get default tab ID (to delete later)
  const docData = await docs.documents.get({ documentId: docId, includeTabsContent: true });
  const defaultTabId = docData.data.tabs[0].tabProperties.tabId;

  const tabMapping = {};
  const rootUrl = 'https://docs.google.com/document/d/' + docId + '/edit';

  // Add ALL tabs as named tabs
  for (const md of mdFiles) {
    const title = titleFromFilename(md);
    console.log('  Adding tab: "' + title + '"...');
    const tabRes = await docs.documents.batchUpdate({
      documentId: docId,
      requestBody: { requests: [{ addDocumentTab: { tabProperties: { title } } }] },
    });
    const newTabId = tabRes.data.replies?.[0]?.addDocumentTab?.tabProperties?.tabId;
    if (!newTabId) { console.error('    WARN: no tab ID for "' + title + '"'); continue; }
    tabMapping[md] = {
      tabId: newTabId,
      tabUrl: rootUrl + '?tab=' + newTabId,
      title,
      standaloneUrl: mapping[md]?.url || null,
    };
  }

  // Delete the default "Tab 1" — API field is "deleteTab" (NOT "deleteDocumentTab")
  console.log('  Deleting default tab "' + defaultTabId + '"...');
  try {
    await docs.documents.batchUpdate({
      documentId: docId,
      requestBody: { requests: [{ deleteTab: { tabId: defaultTabId } }] },
    });
    console.log('  Default tab deleted.');
  } catch (err) {
    console.error('  WARN: Could not delete default tab: ' + err.message);
    console.error('  Manually delete "Tab 1" from the Google Docs UI.');
  }

  // Write tab mapping
  const tabsOutPath = args.tabsOut || (args.inputDir ? join(args.inputDir, 'tab-mapping.json') : 'tab-mapping.json');
  await writeFile(tabsOutPath, JSON.stringify(tabMapping, null, 2));

  console.log('\nRoot doc: ' + rootUrl);
  console.log('Tabs: ' + Object.keys(tabMapping).length);
  console.log('Tab mapping: ' + tabsOutPath);
}

main().catch(err => { console.error('Fatal:', err.message || err); process.exit(1); });
