#!/usr/bin/env node
/**
 * Count ASCII diagram blocks that md-to-docx.js will detect in a markdown file.
 *
 * Uses the SAME regex heuristics as md-to-docx.js, so the count matches exactly.
 * Run this BEFORE creating .mmd files to know how many are needed.
 *
 * Usage: node count-ascii-diagrams.js <markdown-file>
 *
 * Output: one line per detected block (numbered, with context), then total count.
 * Exit code: 0 if any diagrams found, 1 if none.
 */

const fs = require('fs');
const path = require('path');

const file = process.argv[2];
if (!file) {
  console.error('Usage: node count-ascii-diagrams.js <markdown-file>');
  process.exit(2);
}

const md = fs.readFileSync(file, 'utf-8');

// Must match md-to-docx.js isAsciiDiagram exactly
function isAsciiDiagram(code) {
  const patterns = [
    /[┌┐└┘├┤┬┴┼─│]/,   // Box-drawing characters
    /[═║╔╗╚╝╠╣╦╩╬]/,   // Double box-drawing
    /──▶|◀──/,          // Arrows
    /\+-+\+/,           // ASCII boxes +--+
    /\|.*\|.*\|/,       // Vertical bars in pattern (⚠️ false positive source)
  ];
  return patterns.some(p => p.test(code));
}

const lines = md.split('\n');
let inCode = false, content = '', start = 0, n = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (/^```/.test(line) && !inCode) {
    inCode = true;
    start = i;
    content = '';
  } else if (/^```/.test(line) && inCode) {
    inCode = false;
    if (isAsciiDiagram(content)) {
      n++;
      // Show context: nearest heading or previous non-empty line
      let ctx = '';
      for (let j = start - 1; j >= Math.max(0, start - 5); j--) {
        if (lines[j].trim()) { ctx = lines[j].trim(); break; }
      }
      const patterns = [];
      if (/[┌┐└┘├┤┬┴┼─│]/.test(content)) patterns.push('box-drawing');
      if (/[═║╔╗╚╝╠╣╦╩╬]/.test(content)) patterns.push('double-box');
      if (/──▶|◀──/.test(content)) patterns.push('arrows');
      if (/\+-+\+/.test(content)) patterns.push('ascii-boxes');
      if (/\|.*\|.*\|/.test(content)) patterns.push('vertical-bars');
      
      console.log(
        `  ${String(n).padStart(2, '0')} (line ${String(start).padStart(4)}) [${patterns.join(',')}] ${ctx}`
      );
    }
  } else if (inCode) {
    content += line + '\n';
  }
}

console.log(`\nTotal: ${n} ASCII diagram blocks in ${path.basename(file)}`);
if (n === 0) {
  console.log('No diagrams to convert.');
  process.exit(1);
}
console.log(`Create ${n} numbered .mmd files (01-name.mmd through ${String(n).padStart(2,'0')}-name.mmd)`);
