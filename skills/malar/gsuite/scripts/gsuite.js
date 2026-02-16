#!/usr/bin/env node
/**
 * gsuite.js — Standalone Google Workspace CLI.
 *
 * Usage: node gsuite.js <service> <action> [args] [--flags]
 *
 * Services: docs, drive, sheets, calendar, gmail
 * Run with --help or no args for command list.
 *
 * Reuses the Google Workspace MCP server's OAuth credentials.
 * Only dependency: googleapis (resolve from cwd via createRequire).
 */

import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve, basename, join, extname } from 'node:path';
import { homedir } from 'node:os';
import { createRequire } from 'node:module';
import { Readable } from 'node:stream';

// Resolve googleapis from caller's cwd, not this script's location
const _require = createRequire(resolve(process.cwd(), '__placeholder.js'));
let google;
try {
  ({ google } = _require('googleapis'));
} catch {
  console.error('Error: googleapis not found. Run: npm install googleapis');
  console.error('The script resolves modules from the current working directory.');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function die(msg) { console.error(`Error: ${msg}`); process.exit(1); }
function log(msg) { console.error(msg); }
function out(data) { console.log(JSON.stringify(data, null, 2)); }

function parseArgs(argv) {
  // Extract service and action from first two non-flag args
  const flags = {};
  const raw = [];
  for (let i = 2; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
        flags[key] = argv[++i];
      } else {
        flags[key] = true;
      }
    } else {
      raw.push(argv[i]);
    }
  }
  const service = raw[0] || null;
  const action = raw[1] || null;
  const positionals = raw.slice(2);
  return { service, action, flags, positionals };
}

const MIME_MAP = {
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.csv': 'text/csv',
  '.json': 'application/json',
  '.txt': 'text/plain',
  '.html': 'text/html',
  '.md': 'text/markdown',
};

const GOOGLE_MIME_MAP = {
  '.docx': 'application/vnd.google-apps.document',
  '.xlsx': 'application/vnd.google-apps.spreadsheet',
  '.pptx': 'application/vnd.google-apps.presentation',
  '.csv': 'application/vnd.google-apps.spreadsheet',
};

function resolveDate(input) {
  if (!input) return undefined;
  const now = new Date();
  const sod = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const eod = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);
  const add = (d, n) => { const r = new Date(d); r.setDate(r.getDate() + n); return r; };
  switch (input.toLowerCase().trim()) {
    case 'now': return now.toISOString();
    case 'today': return sod(now).toISOString();
    case 'tomorrow': return sod(add(now, 1)).toISOString();
    case 'yesterday': return sod(add(now, -1)).toISOString();
    case 'end-of-today': return eod(now).toISOString();
    case 'end-of-tomorrow': return eod(add(now, 1)).toISOString();
    case 'next-week': return sod(add(now, 7)).toISOString();
    default: {
      const d = new Date(input);
      if (isNaN(d.getTime())) die(`Invalid date: ${input}`);
      return d.toISOString();
    }
  }
}

function parseCSV(text) {
  const rows = [];
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    const cells = [];
    let cur = '', inQ = false;
    for (const ch of line) {
      if (ch === '"') { inQ = !inQ; }
      else if (ch === ',' && !inQ) { cells.push(cur); cur = ''; }
      else { cur += ch; }
    }
    cells.push(cur);
    rows.push(cells);
  }
  return rows;
}

function extractDocText(body) {
  let text = '';
  for (const el of body?.content || []) {
    if (el.paragraph) {
      for (const pe of el.paragraph.elements || []) {
        if (pe.textRun) text += pe.textRun.content;
      }
    }
    if (el.table) {
      for (const row of el.table.tableRows || []) {
        const cells = [];
        for (const cell of row.tableCells || []) {
          let ct = '';
          for (const ce of cell.content || []) {
            if (ce.paragraph) {
              for (const pe of ce.paragraph.elements || []) {
                if (pe.textRun) ct += pe.textRun.content;
              }
            }
          }
          cells.push(ct.trim());
        }
        text += cells.join('\t') + '\n';
      }
    }
  }
  return text;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

async function createAuth(credPath, tokenPath) {
  const credRaw = await readFile(credPath, 'utf-8');
  const credJson = JSON.parse(credRaw);
  const { client_id, client_secret } = credJson.installed || credJson.web || {};
  if (!client_id || !client_secret) die(`Invalid credentials at ${credPath}`);

  const tokenRaw = await readFile(tokenPath, 'utf-8');
  const tokens = JSON.parse(tokenRaw);
  if (!tokens.access_token) die(`Invalid token at ${tokenPath}`);

  const auth = new google.auth.OAuth2(client_id, client_secret, 'http://localhost:3737');
  auth.setCredentials(tokens);
  auth.on('tokens', async (newTokens) => {
    await writeFile(tokenPath, JSON.stringify({ ...tokens, ...newTokens }, null, 2), 'utf-8');
    log('[auth] Token refreshed and saved');
  });
  return auth;
}

function makeClients(auth) {
  let _docs, _drive, _sheets, _cal, _gmail;
  return {
    get docs() { return _docs ??= google.docs({ version: 'v1', auth }); },
    get drive() { return _drive ??= google.drive({ version: 'v3', auth }); },
    get sheets() { return _sheets ??= google.sheets({ version: 'v4', auth }); },
    get calendar() { return _cal ??= google.calendar({ version: 'v3', auth }); },
    get gmail() { return _gmail ??= google.gmail({ version: 'v1', auth }); },
  };
}

// ===========================================================================
// DOCS — block writing helpers (ported from MCP docs-batch-write.ts)
// ===========================================================================

const HEADING_STYLES = { 1: 'HEADING_1', 2: 'HEADING_2', 3: 'HEADING_3', 4: 'HEADING_4', 5: 'HEADING_5', 6: 'HEADING_6' };

function makeLoc(index, tabId) { const l = { index }; if (tabId) l.tabId = tabId; return l; }
function makeRange(s, e, tabId) { const r = { startIndex: s, endIndex: e }; if (tabId) r.tabId = tabId; return r; }

function parseInlineFormatting(text) {
  const segments = [];
  const pattern = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*)/g;
  let last = 0, m;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) segments.push({ text: text.slice(last, m.index) });
    if (m[2]) segments.push({ text: m[2], bold: true, italic: true });
    else if (m[3]) segments.push({ text: m[3], bold: true });
    else if (m[4]) segments.push({ text: m[4], italic: true });
    last = m.index + m[0].length;
  }
  if (last < text.length) segments.push({ text: text.slice(last) });
  return segments;
}

function buildFormattedText(text, startIndex, requests, tabId) {
  const segments = parseInlineFormatting(text);
  if (segments.length === 0) segments.push({ text });
  const plain = segments.map(s => s.text).join('');
  requests.push({ insertText: { location: makeLoc(startIndex, tabId), text: plain } });
  let off = startIndex;
  for (const seg of segments) {
    if (seg.bold || seg.italic) {
      const style = {}, fields = [];
      if (seg.bold) { style.bold = true; fields.push('bold'); }
      if (seg.italic) { style.italic = true; fields.push('italic'); }
      requests.push({ updateTextStyle: { range: makeRange(off, off + seg.text.length, tabId), textStyle: style, fields: fields.join(',') } });
    }
    off += seg.text.length;
  }
  return startIndex + plain.length;
}

function buildBlockRequests(blocks, startIndex, tabId) {
  const requests = [];
  let idx = startIndex;
  for (const block of blocks) {
    switch (block.type) {
      case 'heading': {
        const t = (block.text || '') + '\n';
        const style = HEADING_STYLES[Math.min(Math.max(block.level || 1, 1), 6)] || 'HEADING_1';
        requests.push({ insertText: { location: makeLoc(idx, tabId), text: t } });
        requests.push({ updateParagraphStyle: { range: makeRange(idx, idx + t.length, tabId), paragraphStyle: { namedStyleType: style }, fields: 'namedStyleType' } });
        idx += t.length;
        break;
      }
      case 'paragraph': {
        idx = buildFormattedText((block.text || '') + '\n', idx, requests, tabId);
        break;
      }
      case 'code': {
        const t = (block.text || '') + '\n';
        requests.push({ insertText: { location: makeLoc(idx, tabId), text: t } });
        requests.push({ updateTextStyle: { range: makeRange(idx, idx + t.length, tabId), textStyle: { weightedFontFamily: { fontFamily: 'Courier New' }, fontSize: { magnitude: 10, unit: 'PT' } }, fields: 'weightedFontFamily,fontSize' } });
        requests.push({ updateParagraphStyle: { range: makeRange(idx, idx + t.length, tabId), paragraphStyle: { shading: { backgroundColor: { color: { rgbColor: { red: 0.95, green: 0.95, blue: 0.95 } } } } }, fields: 'shading' } });
        idx += t.length;
        break;
      }
      case 'table': {
        const headers = block.headers || [], rows = block.rows || [];
        if (headers.length === 0 && rows.length === 0) break;
        if (headers.length > 0) {
          const ht = headers.join('  |  ') + '\n';
          requests.push({ insertText: { location: makeLoc(idx, tabId), text: ht } });
          requests.push({ updateTextStyle: { range: makeRange(idx, idx + ht.length, tabId), textStyle: { bold: true }, fields: 'bold' } });
          idx += ht.length;
        }
        for (const row of rows) {
          const rt = (row || []).join('  |  ') + '\n';
          requests.push({ insertText: { location: makeLoc(idx, tabId), text: rt } });
          idx += rt.length;
        }
        break;
      }
      case 'image': {
        if (!block.uri) break;
        const imgReq = { uri: block.uri, location: makeLoc(idx, tabId) };
        if (block.width || block.height) {
          imgReq.objectSize = {};
          if (block.width) imgReq.objectSize.width = { magnitude: block.width, unit: 'PT' };
          if (block.height) imgReq.objectSize.height = { magnitude: block.height, unit: 'PT' };
        }
        requests.push({ insertInlineImage: imgReq });
        idx += 1;
        requests.push({ insertText: { location: makeLoc(idx, tabId), text: '\n' } });
        idx += 1;
        break;
      }
      case 'list': {
        const items = block.items || [];
        if (items.length === 0) break;
        const lt = items.map(i => i + '\n').join('');
        const ls = idx;
        requests.push({ insertText: { location: makeLoc(idx, tabId), text: lt } });
        idx += lt.length;
        requests.push({ createParagraphBullets: { range: makeRange(ls, idx, tabId), bulletPreset: block.ordered ? 'NUMBERED_DECIMAL_ALPHA_ROMAN' : 'BULLET_DISC_CIRCLE_SQUARE' } });
        break;
      }
    }
  }
  return { requests, endIndex: idx };
}

/** Get the body of a specific tab (or default tab). */
async function getTabBody(docsClient, documentId, tabId) {
  if (!tabId) {
    const doc = await docsClient.documents.get({ documentId });
    return doc.data.body;
  }
  const doc = await docsClient.documents.get({ documentId, includeTabsContent: true });
  for (const tab of doc.data.tabs || []) {
    if (tab.tabProperties?.tabId === tabId) return tab.documentTab?.body;
    // Check child tabs
    for (const child of tab.childTabs || []) {
      if (child.tabProperties?.tabId === tabId) return child.documentTab?.body;
    }
  }
  return undefined;
}

function getBodyEndIndex(body) {
  const content = body?.content;
  if (!content || content.length === 0) return 1;
  return content[content.length - 1]?.endIndex ?? 1;
}

/** Parse markdown to content blocks (inline version of _md-to-blocks.js with image support). */
function parseMarkdownToBlocks(content) {
  const lines = content.split('\n');
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === '') { i++; continue; }

    // Headings
    const hm = line.match(/^(#{1,6})\s+(.+)/);
    if (hm) { blocks.push({ type: 'heading', level: hm[1].length, text: hm[2].trim().replace(/\s*\{#[^}]+\}\s*$/, '') }); i++; continue; }

    // HR
    if (/^---+\s*$/.test(line.trim())) { i++; continue; }

    // Image (standalone line)
    const imgMatch = line.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (imgMatch) { blocks.push({ type: 'image', text: imgMatch[1], uri: imgMatch[2] }); i++; continue; }

    // Blockquote
    if (line.trimStart().startsWith('>')) {
      let qt = '';
      while (i < lines.length && lines[i].trimStart().startsWith('>')) { qt += (qt ? '\n' : '') + lines[i].trimStart().replace(/^>\s?/, ''); i++; }
      blocks.push({ type: 'paragraph', text: qt.trim() });
      continue;
    }

    // Fenced code
    const cm = line.match(/^```(\w*)/);
    if (cm) {
      const lang = cm[1] || undefined; i++;
      let code = '';
      while (i < lines.length && !lines[i].startsWith('```')) { code += (code ? '\n' : '') + lines[i]; i++; }
      if (i < lines.length) i++;
      blocks.push({ type: 'code', language: lang, text: code });
      continue;
    }

    // Table
    if (line.includes('|') && line.trim().startsWith('|')) {
      const tl = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim().startsWith('|')) { tl.push(lines[i]); i++; }
      if (tl.length >= 2) {
        const pr = r => r.split('|').slice(1, -1).map(c => c.trim());
        const headers = pr(tl[0]), rows = tl.slice(2).map(pr);
        if (headers.length > 0) blocks.push({ type: 'table', headers, rows });
      }
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        let item = lines[i].replace(/^\s*[-*]\s+/, ''); i++;
        while (i < lines.length && lines[i].match(/^\s{2,}/) && !/^\s*[-*]\s+/.test(lines[i]) && !/^\s*\d+\.\s+/.test(lines[i])) { item += ' ' + lines[i].trim(); i++; }
        items.push(item.trim());
      }
      blocks.push({ type: 'list', items, ordered: false });
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        let item = lines[i].replace(/^\s*\d+\.\s+/, ''); i++;
        while (i < lines.length && lines[i].match(/^\s{2,}/) && !/^\s*[-*]\s+/.test(lines[i]) && !/^\s*\d+\.\s+/.test(lines[i])) { item += ' ' + lines[i].trim(); i++; }
        items.push(item.trim());
      }
      blocks.push({ type: 'list', items, ordered: true });
      continue;
    }

    // Paragraph
    let pt = '';
    while (i < lines.length) {
      const l = lines[i];
      if (l.trim() === '' || /^#{1,6}\s/.test(l) || /^```/.test(l) || /^---+\s*$/.test(l.trim())) break;
      if ((l.trimStart().startsWith('>') || /^\s*[-*]\s+/.test(l) || /^\s*\d+\.\s+/.test(l) || (l.includes('|') && l.trim().startsWith('|'))) && !pt) break;
      // Inline image within paragraph text: extract as separate image block
      const inlineImg = l.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (inlineImg && !pt) { blocks.push({ type: 'image', text: inlineImg[1], uri: inlineImg[2] }); i++; break; }
      pt += (pt ? ' ' : '') + l.trim();
      i++;
    }
    if (pt) blocks.push({ type: 'paragraph', text: pt });
  }
  return blocks;
}

// ===========================================================================
// DOCS — commands
// ===========================================================================

const docsCmd = {
  async read(c, pos, f) {
    const docId = pos[0];
    if (!docId) die('Usage: docs read <docId> [--structure]');
    const res = await c.docs.documents.get({ documentId: docId });
    if (f.structure) return res.data;
    return { title: res.data.title, documentId: docId, text: extractDocText(res.data.body) };
  },

  async create(c, pos, f) {
    if (!f.title) die('Usage: docs create --title <title> [--content <text>] [--folder-id <id>]');
    const res = await c.docs.documents.create({ requestBody: { title: f.title } });
    const docId = res.data.documentId;
    if (f['folder-id']) {
      await c.drive.files.update({ fileId: docId, addParents: f['folder-id'] });
    }
    if (f.content) {
      const text = f.content.startsWith('@') ? await readFile(f.content.slice(1), 'utf-8') : f.content;
      await c.docs.documents.batchUpdate({
        documentId: docId,
        requestBody: { requests: [{ insertText: { location: { index: 1 }, text } }] },
      });
    }
    log(`Created: ${f.title}`);
    return { documentId: docId, title: f.title, url: `https://docs.google.com/document/d/${docId}/edit` };
  },

  async append(c, pos, f) {
    const docId = pos[0];
    if (!docId || (!f.text && !f.file)) die('Usage: docs append <docId> --text <text> | --file <path>');
    const text = f.file ? await readFile(f.file, 'utf-8') : f.text;
    const doc = await c.docs.documents.get({ documentId: docId });
    const endIdx = doc.data.body.content.at(-1).endIndex;
    await c.docs.documents.batchUpdate({
      documentId: docId,
      requestBody: { requests: [{ insertText: { location: { index: endIdx - 1 }, text } }] },
    });
    log(`Appended ${text.length} chars to ${docId}`);
    return { documentId: docId, appended: text.length };
  },

  async replace(c, pos, f) {
    const docId = pos[0];
    if (!docId || !f.old || !f.new) die('Usage: docs replace <docId> --old <text> --new <text>');
    await c.docs.documents.batchUpdate({
      documentId: docId,
      requestBody: {
        requests: [{
          replaceAllText: { containsText: { text: f.old, matchCase: true }, replaceText: f.new },
        }],
      },
    });
    return { documentId: docId, replaced: f.old, with: f.new };
  },

  async 'list-tabs'(c, pos, f) {
    const docId = pos[0];
    if (!docId) die('Usage: docs list-tabs <docId>');
    const res = await c.docs.documents.get({ documentId: docId, includeTabsContent: true });
    return (res.data.tabs || []).map(t => ({
      id: t.tabProperties?.tabId,
      title: t.tabProperties?.title,
      index: t.tabProperties?.index,
    }));
  },

  async 'add-tab'(c, pos, f) {
    const docId = pos[0];
    if (!docId || !f.title) die('Usage: docs add-tab <docId> --title <title> [--parent-tab <tabId>]');
    const tabProps = { title: f.title };
    if (f['parent-tab']) tabProps.parentTabId = f['parent-tab'];
    const res = await c.docs.documents.batchUpdate({
      documentId: docId,
      requestBody: { requests: [{ addDocumentTab: { tabProperties: tabProps } }] },
    });
    const added = res.data.replies?.[0]?.addDocumentTab;
    const tabId = added?.tabProperties?.tabId || '';
    log(`Added tab "${f.title}" → ${tabId}`);
    return { documentId: docId, tabId, title: added?.tabProperties?.title || f.title };
  },

  async 'write-blocks'(c, pos, f) {
    const docId = pos[0];
    if (!docId || !f['blocks-file']) die('Usage: docs write-blocks <docId> --blocks-file <path> [--tab <tabId>] [--clear]');
    const blocks = JSON.parse(await readFile(resolve(f['blocks-file']), 'utf-8'));
    const tabId = f.tab || undefined;

    // Get current body for the target tab
    const body = await getTabBody(c.docs, docId, tabId);
    let startIndex = 1;

    if (f.clear) {
      const endIdx = getBodyEndIndex(body);
      if (endIdx > 2) {
        await c.docs.documents.batchUpdate({
          documentId: docId,
          requestBody: { requests: [{ deleteContentRange: { range: makeRange(1, endIdx - 1, tabId) } }] },
        });
      }
    } else {
      startIndex = Math.max(getBodyEndIndex(body) - 1, 1);
    }

    const { requests } = buildBlockRequests(blocks, startIndex, tabId);
    if (requests.length > 0) {
      await c.docs.documents.batchUpdate({ documentId: docId, requestBody: { requests } });
    }
    log(`Wrote ${blocks.length} blocks to ${tabId || 'default tab'}`);
    return { documentId: docId, tabId, blocksWritten: blocks.length };
  },

  async 'write-md'(c, pos, f) {
    const docId = pos[0];
    if (!docId || !f.file) die('Usage: docs write-md <docId> --file <path> [--tab <tabId>] [--clear] [--images-dir <path>] [--images-folder-id <driveFolderId>]');
    const mdContent = await readFile(resolve(f.file), 'utf-8');
    const blocks = parseMarkdownToBlocks(mdContent);
    const tabId = f.tab || undefined;
    const imagesDir = f['images-dir'] ? resolve(f['images-dir']) : null;
    const imagesFolderId = f['images-folder-id'] || null;

    // Upload local images to Drive and replace URIs
    let imagesUploaded = 0;
    for (const block of blocks) {
      if (block.type !== 'image' || !block.uri) continue;
      // Skip URLs (http/https/drive)
      if (/^https?:\/\//.test(block.uri) || block.uri.startsWith('drive:')) continue;
      // Local path — try to find and upload
      const imgName = basename(block.uri);
      const candidates = [
        imagesDir ? join(imagesDir, imgName) : null,
        resolve(join(resolve(f.file, '..'), block.uri)),
      ].filter(Boolean);
      let uploaded = false;
      for (const candidate of candidates) {
        try {
          const buf = await readFile(candidate);
          const ext = extname(imgName).toLowerCase();
          const mimeType = MIME_MAP[ext] || 'image/png';
          const reqBody = { name: imgName };
          if (imagesFolderId) reqBody.parents = [imagesFolderId];
          const uploadRes = await c.drive.files.create({
            requestBody: reqBody,
            media: { mimeType, body: Readable.from(buf) },
            fields: 'id, webContentLink',
          });
          // Use webContentLink for inline image insertion
          block.uri = uploadRes.data.webContentLink || `https://drive.google.com/uc?id=${uploadRes.data.id}&export=download`;
          log(`  Uploaded image: ${imgName} → ${uploadRes.data.id}`);
          imagesUploaded++;
          uploaded = true;
          break;
        } catch { /* try next candidate */ }
      }
      if (!uploaded) log(`  Warning: image not found: ${block.uri}`);
    }

    // Get current body and handle --clear
    const body = await getTabBody(c.docs, docId, tabId);
    let startIndex = 1;
    if (f.clear) {
      const endIdx = getBodyEndIndex(body);
      if (endIdx > 2) {
        await c.docs.documents.batchUpdate({
          documentId: docId,
          requestBody: { requests: [{ deleteContentRange: { range: makeRange(1, endIdx - 1, tabId) } }] },
        });
      }
    } else {
      startIndex = Math.max(getBodyEndIndex(body) - 1, 1);
    }

    const { requests } = buildBlockRequests(blocks, startIndex, tabId);
    if (requests.length > 0) {
      await c.docs.documents.batchUpdate({ documentId: docId, requestBody: { requests } });
    }
    log(`Wrote ${blocks.length} blocks (${imagesUploaded} images uploaded) to ${tabId || 'default tab'}`);
    return { documentId: docId, tabId, blocksWritten: blocks.length, imagesUploaded };
  },
};

// ===========================================================================
// DRIVE
// ===========================================================================

const driveCmd = {
  async search(c, pos, f) {
    const parts = [];
    if (f.query) parts.push(`name contains '${f.query.replace(/'/g, "\\'")}'`);
    if (f.type) {
      const tm = {
        document: 'application/vnd.google-apps.document',
        spreadsheet: 'application/vnd.google-apps.spreadsheet',
        presentation: 'application/vnd.google-apps.presentation',
        folder: 'application/vnd.google-apps.folder',
        pdf: 'application/pdf',
      };
      if (f.type === 'image') parts.push("(mimeType contains 'image/')");
      else if (tm[f.type]) parts.push(`mimeType = '${tm[f.type]}'`);
    }
    if (f.folder) parts.push(`'${f.folder}' in parents`);
    parts.push('trashed = false');
    const q = parts.join(' and ');
    const res = await c.drive.files.list({
      q,
      pageSize: parseInt(f.max) || 20,
      fields: 'files(id, name, mimeType, webViewLink, modifiedTime, size)',
      orderBy: 'modifiedTime desc',
    });
    return { files: res.data.files || [], query: q };
  },

  async ls(c, pos, f) {
    const folderId = f['folder-id'] || pos[0] || 'root';
    const res = await c.drive.files.list({
      q: `'${folderId}' in parents and trashed = false`,
      pageSize: parseInt(f.max) || 50,
      fields: 'files(id, name, mimeType, webViewLink, modifiedTime, size)',
      orderBy: f['order-by'] || 'name',
    });
    return { folderId, files: res.data.files || [] };
  },

  async get(c, pos, f) {
    const fileId = pos[0];
    if (!fileId) die('Usage: drive get <fileId> [--permissions]');
    const fields = 'id, name, mimeType, webViewLink, createdTime, modifiedTime, size, owners, parents';
    const res = await c.drive.files.get({ fileId, fields: f.permissions ? fields + ', permissions' : fields });
    return res.data;
  },

  async read(c, pos, f) {
    const fileId = pos[0];
    if (!fileId) die('Usage: drive read <fileId> [--format text|html|csv|pdf|docx|xlsx] [--output <path>]');
    const meta = await c.drive.files.get({ fileId, fields: 'mimeType, name' });
    const mime = meta.data.mimeType;
    const name = meta.data.name;
    const isGoogle = mime.startsWith('application/vnd.google-apps.');

    if (isGoogle) {
      const format = f.format || 'text';
      const exportMimes = {
        text: 'text/plain', html: 'text/html', pdf: 'application/pdf', csv: 'text/csv',
        docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      };
      const eMime = exportMimes[format];
      if (!eMime) die(`Unknown format: ${format}. Options: ${Object.keys(exportMimes).join(', ')}`);
      const isBin = ['pdf', 'docx', 'xlsx'].includes(format);
      const res = await c.drive.files.export({ fileId, mimeType: eMime }, { responseType: isBin ? 'arraybuffer' : 'text' });
      if (f.output) {
        await writeFile(f.output, isBin ? Buffer.from(res.data) : res.data);
        log(`Saved to ${f.output}`);
        return { saved: f.output, name, format };
      }
      if (isBin) return { name, format, content_base64: Buffer.from(res.data).toString('base64') };
      return { name, format, content: res.data };
    }
    // Regular file download
    const res = await c.drive.files.get({ fileId, alt: 'media' }, { responseType: 'arraybuffer' });
    const buf = Buffer.from(res.data);
    if (f.output) {
      await writeFile(f.output, buf);
      log(`Saved to ${f.output} (${buf.length} bytes)`);
      return { saved: f.output, name, size: buf.length };
    }
    if (mime.startsWith('text/') || mime === 'application/json') return { name, content: buf.toString('utf-8') };
    return { name, mimeType: mime, size: buf.length, content_base64: buf.toString('base64') };
  },

  async mkdir(c, pos, f) {
    const name = f.name || pos[0];
    if (!name) die('Usage: drive mkdir --name <name> [--parent-id <id>]');
    const res = await c.drive.files.create({
      requestBody: {
        name,
        mimeType: 'application/vnd.google-apps.folder',
        ...(f['parent-id'] && { parents: [f['parent-id']] }),
      },
      fields: 'id, name, webViewLink',
    });
    log(`Created folder: ${name}`);
    return { folderId: res.data.id, name: res.data.name, url: res.data.webViewLink };
  },

  async upload(c, pos, f) {
    const filePath = f.file || pos[0];
    if (!filePath) die('Usage: drive upload --file <path> [--folder-id <id>] [--convert] [--name <name>]');
    const buffer = await readFile(filePath);
    const fileName = f.name || basename(filePath);
    const ext = extname(fileName).toLowerCase();
    const mimeType = MIME_MAP[ext] || 'application/octet-stream';
    const requestBody = {
      name: fileName,
      ...(f['folder-id'] && { parents: [f['folder-id']] }),
    };
    if (f.convert && GOOGLE_MIME_MAP[ext]) requestBody.mimeType = GOOGLE_MIME_MAP[ext];
    const res = await c.drive.files.create({
      requestBody,
      media: { mimeType, body: Readable.from(buffer) },
      fields: 'id, name, webViewLink, mimeType',
    });
    const sizeKB = (buffer.length / 1024).toFixed(1);
    log(`Uploaded: ${fileName} (${sizeKB} KB) → ${res.data.id}`);
    return { fileId: res.data.id, name: res.data.name, url: res.data.webViewLink, mimeType: res.data.mimeType, size: buffer.length };
  },

  async 'upload-dir'(c, pos, f) {
    const inputDir = f['input-dir'] || pos[0];
    const folderId = f['folder-id'];
    if (!inputDir || !folderId) die('Usage: drive upload-dir --input-dir <path> --folder-id <id> [--convert] [--pattern <glob>] [--mapping-out <path>]');
    const dir = resolve(inputDir);
    const entries = await readdir(dir);
    const pattern = f.pattern ? new RegExp(f.pattern.replace(/\*/g, '.*'), 'i') : null;
    const files = entries.filter(e => !e.startsWith('.') && (!pattern || pattern.test(e))).sort();
    if (files.length === 0) die(`No files found in ${dir}`);
    log(`Uploading ${files.length} file(s) from ${dir}\n`);
    const mapping = {};
    for (const file of files) {
      const filePath = join(dir, file);
      const buffer = await readFile(filePath);
      const ext = extname(file).toLowerCase();
      const mimeType = MIME_MAP[ext] || 'application/octet-stream';
      const requestBody = { name: file, parents: [folderId] };
      if (f.convert && GOOGLE_MIME_MAP[ext]) requestBody.mimeType = GOOGLE_MIME_MAP[ext];
      const res = await c.drive.files.create({
        requestBody,
        media: { mimeType, body: Readable.from(buffer) },
        fields: 'id, name, webViewLink',
      });
      const url = res.data.webViewLink || `https://drive.google.com/file/d/${res.data.id}/view`;
      const sizeKB = (buffer.length / 1024).toFixed(1);
      log(`  ✓ ${file} (${sizeKB} KB) → ${res.data.id}`);
      mapping[file] = { fileId: res.data.id, url };
    }
    const mappingOut = f['mapping-out'] ? resolve(f['mapping-out']) : join(dir, 'mapping.json');
    await writeFile(mappingOut, JSON.stringify(mapping, null, 2), 'utf-8');
    log(`\nMapping written to ${mappingOut}`);
    return { uploaded: files.length, mapping, mappingFile: mappingOut };
  },

  async share(c, pos, f) {
    const fileId = pos[0];
    if (!fileId) die('Usage: drive share <fileId> --email <email> --role <reader|writer|commenter> [--notify]');
    const type = f.type || (f.email ? 'user' : 'anyone');
    const body = { type, role: f.role || 'reader' };
    if (f.email) body.emailAddress = f.email;
    if (f.domain) body.domain = f.domain;
    const res = await c.drive.permissions.create({
      fileId,
      requestBody: body,
      sendNotificationEmail: f.notify === true || f.notify === 'true',
      fields: 'id, type, role, emailAddress',
    });
    log(`Shared ${fileId} with ${f.email || type}`);
    return res.data;
  },

  async delete(c, pos, f) {
    const fileId = pos[0];
    if (!fileId) die('Usage: drive delete <fileId> [--permanent]');
    if (f.permanent) {
      await c.drive.files.delete({ fileId });
      log(`Permanently deleted ${fileId}`);
    } else {
      await c.drive.files.update({ fileId, requestBody: { trashed: true } });
      log(`Trashed ${fileId}`);
    }
    return { fileId, action: f.permanent ? 'deleted' : 'trashed' };
  },
};

// ===========================================================================
// SHEETS
// ===========================================================================

const sheetsCmd = {
  async read(c, pos, f) {
    const id = pos[0];
    if (!id) die('Usage: sheets read <spreadsheetId> [--range <range>] [--metadata]');
    if (f.metadata) {
      const res = await c.sheets.spreadsheets.get({ spreadsheetId: id });
      return { title: res.data.properties.title, sheets: res.data.sheets.map(s => ({ id: s.properties.sheetId, title: s.properties.title, rows: s.properties.gridProperties.rowCount, cols: s.properties.gridProperties.columnCount })) };
    }
    const range = f.range || 'Sheet1';
    const res = await c.sheets.spreadsheets.values.get({ spreadsheetId: id, range });
    return { range: res.data.range, values: res.data.values || [] };
  },

  async create(c, pos, f) {
    if (!f.title) die('Usage: sheets create --title <title> [--sheets s1,s2] [--folder-id <id>]');
    const sheetTitles = f.sheets ? f.sheets.split(',') : ['Sheet1'];
    const res = await c.sheets.spreadsheets.create({
      requestBody: {
        properties: { title: f.title },
        sheets: sheetTitles.map(t => ({ properties: { title: t.trim() } })),
      },
    });
    const ssId = res.data.spreadsheetId;
    if (f['folder-id']) {
      await c.drive.files.update({ fileId: ssId, addParents: f['folder-id'] });
    }
    log(`Created spreadsheet: ${f.title}`);
    return { spreadsheetId: ssId, title: f.title, url: res.data.spreadsheetUrl };
  },

  async write(c, pos, f) {
    const id = pos[0];
    if (!id || !f.range) die('Usage: sheets write <id> --range <range> (--values <json> | --values-file <path>)');
    let values;
    if (f['values-file']) values = JSON.parse(await readFile(f['values-file'], 'utf-8'));
    else if (f.values) values = JSON.parse(f.values);
    else die('Provide --values <json> or --values-file <path>');
    const res = await c.sheets.spreadsheets.values.update({
      spreadsheetId: id, range: f.range,
      valueInputOption: f.raw ? 'RAW' : 'USER_ENTERED',
      requestBody: { values },
    });
    return { updatedRange: res.data.updatedRange, updatedCells: res.data.updatedCells };
  },

  async append(c, pos, f) {
    const id = pos[0];
    if (!id || !f.range) die('Usage: sheets append <id> --range <range> (--values <json> | --values-file <path>)');
    let values;
    if (f['values-file']) values = JSON.parse(await readFile(f['values-file'], 'utf-8'));
    else if (f.values) values = JSON.parse(f.values);
    else die('Provide --values <json> or --values-file <path>');
    const res = await c.sheets.spreadsheets.values.append({
      spreadsheetId: id, range: f.range,
      valueInputOption: f.raw ? 'RAW' : 'USER_ENTERED',
      requestBody: { values },
    });
    return { updatedRange: res.data.updates?.updatedRange, updatedCells: res.data.updates?.updatedCells };
  },

  async clear(c, pos, f) {
    const id = pos[0];
    if (!id || !f.range) die('Usage: sheets clear <id> --range <range>');
    const res = await c.sheets.spreadsheets.values.clear({
      spreadsheetId: id, range: f.range, requestBody: {},
    });
    return { clearedRange: res.data.clearedRange };
  },

  async import(c, pos, f) {
    const id = pos[0];
    if (!id || !f.file || !f.range) die('Usage: sheets import <id> --file <path> --range <range>');
    const filePath = resolve(f.file);
    const ext = extname(filePath).toLowerCase();
    let values;
    if (ext === '.csv') {
      values = parseCSV(await readFile(filePath, 'utf-8'));
    } else if (ext === '.json') {
      const data = JSON.parse(await readFile(filePath, 'utf-8'));
      values = Array.isArray(data) ? data : data.values;
      if (!Array.isArray(values)) die('JSON must be an array of arrays or { "values": [[...]] }');
    } else {
      die(`Unsupported file type: ${ext}. Use .csv or .json`);
    }
    const res = await c.sheets.spreadsheets.values.update({
      spreadsheetId: id, range: f.range,
      valueInputOption: f.raw ? 'RAW' : 'USER_ENTERED',
      requestBody: { values },
    });
    log(`Imported ${values.length} rows from ${basename(filePath)}`);
    return { updatedRange: res.data.updatedRange, updatedCells: res.data.updatedCells, rows: values.length };
  },
};

// ===========================================================================
// CALENDAR
// ===========================================================================

const calendarCmd = {
  async list(c, pos, f) {
    if (!f.from || !f.to) die('Usage: calendar list --from <date> --to <date> [--calendar <id>] [--max <n>]');
    const res = await c.calendar.events.list({
      calendarId: f.calendar || 'primary',
      timeMin: resolveDate(f.from),
      timeMax: resolveDate(f.to),
      maxResults: parseInt(f.max) || 50,
      singleEvents: true,
      orderBy: 'startTime',
    });
    return {
      events: (res.data.items || []).map(e => ({
        id: e.id, summary: e.summary,
        start: e.start?.dateTime || e.start?.date,
        end: e.end?.dateTime || e.end?.date,
        location: e.location, status: e.status,
        organizer: e.organizer?.email,
        attendees: (e.attendees || []).map(a => ({ email: a.email, status: a.responseStatus })),
      })),
    };
  },

  async get(c, pos, f) {
    const eventId = pos[0];
    if (!eventId) die('Usage: calendar get <eventId> [--calendar <id>]');
    const res = await c.calendar.events.get({
      calendarId: f.calendar || 'primary', eventId,
    });
    return res.data;
  },

  async search(c, pos, f) {
    if (!f.query) die('Usage: calendar search --query <text> [--from <date>] [--to <date>] [--max <n>]');
    const params = {
      calendarId: f.calendar || 'primary',
      q: f.query,
      maxResults: parseInt(f.max) || 25,
      singleEvents: true,
      orderBy: 'startTime',
    };
    if (f.from) params.timeMin = resolveDate(f.from);
    if (f.to) params.timeMax = resolveDate(f.to);
    const res = await c.calendar.events.list(params);
    return {
      events: (res.data.items || []).map(e => ({
        id: e.id, summary: e.summary,
        start: e.start?.dateTime || e.start?.date,
        end: e.end?.dateTime || e.end?.date,
      })),
    };
  },

  async calendars(c, pos, f) {
    const res = await c.calendar.calendarList.list({ showHidden: f.hidden === true });
    return (res.data.items || []).map(cal => ({
      id: cal.id, summary: cal.summary, primary: cal.primary || false,
      accessRole: cal.accessRole, timeZone: cal.timeZone,
    }));
  },

  async freebusy(c, pos, f) {
    if (!f.from || !f.to) die('Usage: calendar freebusy --from <date> --to <date> [--calendars id1,id2]');
    const calIds = f.calendars ? f.calendars.split(',') : ['primary'];
    const res = await c.calendar.freebusy.query({
      requestBody: {
        timeMin: resolveDate(f.from),
        timeMax: resolveDate(f.to),
        items: calIds.map(id => ({ id: id.trim() })),
      },
    });
    return res.data.calendars;
  },
};

// ===========================================================================
// GMAIL
// ===========================================================================

function decodeBase64url(str) {
  return Buffer.from(str.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf-8');
}

const gmailCmd = {
  async list(c, pos, f) {
    const res = await c.gmail.users.messages.list({
      userId: 'me',
      q: f.query,
      labelIds: f.labels ? f.labels.split(',') : undefined,
      maxResults: parseInt(f.max) || 10,
    });
    const messages = [];
    for (const msg of res.data.messages || []) {
      const full = await c.gmail.users.messages.get({
        userId: 'me', id: msg.id, format: 'metadata',
        metadataHeaders: ['From', 'Subject', 'Date'],
      });
      const hdrs = {};
      for (const h of full.data.payload?.headers || []) hdrs[h.name.toLowerCase()] = h.value;
      messages.push({ id: msg.id, threadId: msg.threadId, ...hdrs, snippet: full.data.snippet, labels: full.data.labelIds });
    }
    return { messages, resultSizeEstimate: res.data.resultSizeEstimate };
  },

  async read(c, pos, f) {
    const msgId = pos[0];
    if (!msgId) die('Usage: gmail read <messageId> [--format full|metadata|minimal]');
    const res = await c.gmail.users.messages.get({
      userId: 'me', id: msgId, format: f.format || 'full',
    });
    const msg = res.data;
    if (f.format === 'minimal' || f.format === 'metadata') return msg;
    // Extract headers and body
    const headers = {};
    for (const h of msg.payload?.headers || []) {
      const k = h.name.toLowerCase();
      if (['from', 'to', 'subject', 'date', 'cc', 'bcc'].includes(k)) headers[k] = h.value;
    }
    let body = '';
    function extractBody(parts) {
      for (const p of parts || []) {
        if (p.mimeType === 'text/plain' && p.body?.data) body += decodeBase64url(p.body.data);
        if (p.parts) extractBody(p.parts);
      }
    }
    if (msg.payload?.body?.data) body = decodeBase64url(msg.payload.body.data);
    else extractBody(msg.payload?.parts);
    return { id: msg.id, threadId: msg.threadId, ...headers, body, labels: msg.labelIds };
  },

  async search(c, pos, f) {
    if (!f.query) die('Usage: gmail search --query <text> [--max <n>]');
    const res = await c.gmail.users.messages.list({
      userId: 'me', q: f.query, maxResults: parseInt(f.max) || 10,
    });
    const messages = [];
    for (const msg of res.data.messages || []) {
      const full = await c.gmail.users.messages.get({
        userId: 'me', id: msg.id, format: 'metadata',
        metadataHeaders: ['From', 'Subject', 'Date'],
      });
      const hdrs = {};
      for (const h of full.data.payload?.headers || []) hdrs[h.name.toLowerCase()] = h.value;
      messages.push({ id: msg.id, threadId: msg.threadId, ...hdrs, snippet: full.data.snippet });
    }
    return { messages, resultSizeEstimate: res.data.resultSizeEstimate };
  },
};

// ===========================================================================
// ROUTER & HELP
// ===========================================================================

const COMMANDS = {
  docs: docsCmd,
  drive: driveCmd,
  sheets: sheetsCmd,
  calendar: calendarCmd,
  gmail: gmailCmd,
};

function showHelp() {
  console.error(`
gsuite.js — Standalone Google Workspace CLI

Usage: node gsuite.js <service> <action> [args] [--flags]

Services:
  docs       read, create, append, replace, list-tabs, add-tab, write-blocks, write-md
  drive      search, ls, get, read, mkdir, upload, upload-dir, share, delete
  sheets     read, create, write, append, clear, import
  calendar   list, get, search, calendars, freebusy
  gmail      list, read, search

Global flags:
  --credentials <path>   OAuth credentials (default: $GOOGLE_CREDENTIALS_PATH or ./credentials/credentials.json)
  --token <path>         OAuth token (default: ~/.cb-mcp/google-workspace-mcp.json)

Run "gsuite.js <service> help" for per-service usage.
`.trim());
}

async function main() {
  const { service, action, flags, positionals } = parseArgs(process.argv);

  if (!service || service === 'help' || flags.help) { showHelp(); process.exit(0); }

  const svc = COMMANDS[service];
  if (!svc) die(`Unknown service: ${service}. Available: ${Object.keys(COMMANDS).join(', ')}`);

  if (!action || action === 'help') {
    console.error(`${service} actions: ${Object.keys(svc).join(', ')}`);
    process.exit(0);
  }

  const handler = svc[action];
  if (!handler) die(`Unknown action: ${service} ${action}. Available: ${Object.keys(svc).join(', ')}`);

  const credPath = flags.credentials
    || process.env.GOOGLE_CREDENTIALS_PATH
    || resolve(process.cwd(), 'credentials/credentials.json');
  const tokenPath = flags.token
    || resolve(homedir(), '.cb-mcp', 'google-workspace-mcp.json');

  const auth = await createAuth(resolve(credPath), resolve(tokenPath));
  const clients = makeClients(auth);

  const result = await handler(clients, positionals, flags);
  out(result);
}

main().catch(err => {
  console.error(`\nError: ${err.message || err}`);
  process.exit(1);
});
