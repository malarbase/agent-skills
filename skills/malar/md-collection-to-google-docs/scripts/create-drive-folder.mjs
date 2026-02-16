#!/usr/bin/env node
/**
 * Create a Google Drive folder.
 *
 * Usage:
 *   node create-drive-folder.mjs --name "Folder Name" [--parent-id <id>] \
 *     [--credentials <path>] [--token <path>]
 *
 * Run from a directory with `googleapis` in node_modules.
 * Outputs JSON: { "id": "...", "name": "...", "webViewLink": "..." }
 */
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { homedir } from 'node:os';
import { createRequire } from 'node:module';

const require = createRequire(resolve(process.cwd(), '__placeholder.js'));
const { google } = require('googleapis');

function parseArgs(argv) {
  const args = {
    name: null, parentId: null,
    credentials: process.env.GOOGLE_CREDENTIALS_PATH || '/tmp/gw-credentials.json',
    token: resolve(homedir(), '.cb-mcp', 'google-workspace-mcp.json'),
  };
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case '--name':        args.name = argv[++i]; break;
      case '--parent-id':   args.parentId = argv[++i]; break;
      case '--credentials': args.credentials = argv[++i]; break;
      case '--token':       args.token = argv[++i]; break;
    }
  }
  if (!args.name) {
    console.error('Usage: node create-drive-folder.mjs --name "Folder Name" [--parent-id <id>]');
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

  const drive = google.drive({ version: 'v3', auth: o });
  const requestBody = { name: args.name, mimeType: 'application/vnd.google-apps.folder' };
  if (args.parentId) requestBody.parents = [args.parentId];

  const res = await drive.files.create({ requestBody, fields: 'id, name, webViewLink' });
  console.log(JSON.stringify(res.data, null, 2));
}

main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
