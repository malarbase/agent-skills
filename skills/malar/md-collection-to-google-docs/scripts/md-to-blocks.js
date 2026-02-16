#!/usr/bin/env node
/**
 * Convert a markdown file to write_google_doc_content blocks JSON.
 * Usage: node md-to-blocks.js <input.md>
 * Outputs JSON array of blocks to stdout.
 */

const fs = require('fs');
const path = require('path');

function parseMarkdown(content) {
  const lines = content.split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Skip empty lines
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      let text = headingMatch[2].trim();
      // Remove trailing anchor {#...}
      text = text.replace(/\s*\{#[^}]+\}\s*$/, '');
      blocks.push({ type: 'heading', level, text });
      i++;
      continue;
    }

    // Horizontal rule
    if (/^---+\s*$/.test(line.trim())) {
      i++;
      continue;
    }

    // Blockquote - collect all lines starting with >
    if (line.trimStart().startsWith('>')) {
      let quoteText = '';
      while (i < lines.length && lines[i].trimStart().startsWith('>')) {
        const qLine = lines[i].trimStart().replace(/^>\s?/, '');
        quoteText += (quoteText ? '\n' : '') + qLine;
        i++;
      }
      blocks.push({ type: 'paragraph', text: quoteText.trim() });
      continue;
    }

    // Fenced code block
    const codeMatch = line.match(/^```(\w*)/);
    if (codeMatch) {
      const language = codeMatch[1] || '';
      i++;
      let codeContent = '';
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeContent += (codeContent ? '\n' : '') + lines[i];
        i++;
      }
      if (i < lines.length) i++; // skip closing ```
      blocks.push({ type: 'code', language: language || undefined, text: codeContent });
      continue;
    }

    // Table
    if (line.includes('|') && line.trim().startsWith('|')) {
      const tableLines = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      if (tableLines.length >= 2) {
        const parseRow = (row) => {
          return row.split('|')
            .slice(1, -1) // remove first and last empty cells
            .map(cell => cell.trim());
        };
        const headers = parseRow(tableLines[0]);
        // Skip separator line (index 1)
        const rows = tableLines.slice(2).map(parseRow);
        // Clean up headers and rows - remove empty
        if (headers.length > 0) {
          blocks.push({ type: 'table', headers, rows });
        }
      }
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        let item = lines[i].replace(/^\s*[-*]\s+/, '');
        i++;
        // Collect continuation lines (indented, not a new list item)
        while (i < lines.length && lines[i].match(/^\s{2,}/) && !/^\s*[-*]\s+/.test(lines[i]) && !/^\s*\d+\.\s+/.test(lines[i])) {
          item += ' ' + lines[i].trim();
          i++;
        }
        items.push(item.trim());
      }
      blocks.push({ type: 'list', items, ordered: false });
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        let item = lines[i].replace(/^\s*\d+\.\s+/, '');
        i++;
        while (i < lines.length && lines[i].match(/^\s{2,}/) && !/^\s*[-*]\s+/.test(lines[i]) && !/^\s*\d+\.\s+/.test(lines[i])) {
          item += ' ' + lines[i].trim();
          i++;
        }
        items.push(item.trim());
      }
      blocks.push({ type: 'list', items, ordered: true });
      continue;
    }

    // Paragraph - collect until empty line or structural element
    let paraText = '';
    while (i < lines.length) {
      const l = lines[i];
      if (l.trim() === '') break;
      if (/^#{1,6}\s/.test(l)) break;
      if (/^```/.test(l)) break;
      if (/^---+\s*$/.test(l.trim())) break;
      if (l.trimStart().startsWith('>') && !paraText) break;
      if (/^\s*[-*]\s+/.test(l) && !paraText) break;
      if (/^\s*\d+\.\s+/.test(l) && !paraText) break;
      if (l.includes('|') && l.trim().startsWith('|') && !paraText) break;
      paraText += (paraText ? ' ' : '') + l.trim();
      i++;
    }
    if (paraText) {
      blocks.push({ type: 'paragraph', text: paraText });
    }
  }

  return blocks;
}

// Main
const inputFile = process.argv[2];
if (!inputFile) {
  console.error('Usage: node md-to-blocks.js <input.md>');
  process.exit(1);
}

const content = fs.readFileSync(inputFile, 'utf-8');
const blocks = parseMarkdown(content);
console.log(JSON.stringify(blocks));
