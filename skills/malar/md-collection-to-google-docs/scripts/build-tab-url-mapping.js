#!/usr/bin/env node
/**
 * Convert tab-mapping.json to the format resolve-crossrefs.js expects.
 *
 * Usage:
 *   node build-tab-url-mapping.js <tab-mapping.json> [output.json]
 *
 * Input:  { "file.md": { "tabUrl": "https://..." } }
 * Output: { "file.md": { "url": "https://..." } }
 *
 * If output path is omitted, writes to tab-url-mapping.json in the same directory.
 */
const fs = require('fs');
const path = require('path');

const inputPath = process.argv[2];
if (!inputPath) {
  console.error('Usage: node build-tab-url-mapping.js <tab-mapping.json> [output.json]');
  process.exit(1);
}

const outputPath = process.argv[3] || path.join(path.dirname(inputPath), 'tab-url-mapping.json');

const tabMapping = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
const out = {};
for (const [k, v] of Object.entries(tabMapping)) {
  out[k] = { url: v.tabUrl };
}

fs.writeFileSync(outputPath, JSON.stringify(out, null, 2));
console.log(`Written ${Object.keys(out).length} entries to ${outputPath}`);
