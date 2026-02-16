#!/usr/bin/env node
/**
 * cleanup.js — Remove temporary artifacts from a md-collection-to-google-docs workflow.
 *
 * Usage:
 *   node cleanup.js <input-dir> [--trash-drive] [--dry-run]
 *
 * What it removes (local):
 *   - _docx/              Generated DOCX output directory
 *   - _resolved/          Cross-ref resolved markdown directory
 *   - diagrams-{name}/    Diagram build artifact directories
 *   - {name}.docx         Any stray DOCX files in the input dir
 *   - mapping.json        Upload mapping file
 *   - md-to-docx.js       Copied skill script
 *   - _*.md               Preprocessed markdown files (e.g. _README-gdoc.md)
 *   - _*.js               Temporary workflow scripts (e.g. _resolve-refs.js, _fix-blocks.js)
 *   - *.sh                Shell helper scripts (e.g. docx-gen.sh)
 *   - test-write.txt      Test artifacts
 *   - cleanup.sh          Hardcoded cleanup scripts
 *
 * What it keeps:
 *   - Source markdown files (*.md without _ prefix)
 *   - Subdirectories that aren't build artifacts (e.g. internal/)
 *
 * Options:
 *   --trash-drive   Also trash standalone Google Docs listed in mapping.json
 *                   (requires gsuite CLI; files go to Drive Trash, recoverable 30 days)
 *   --dry-run       Show what would be removed without actually deleting anything
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const args = process.argv.slice(2);
const inputDir = args.find(a => !a.startsWith('--'));
const trashDrive = args.includes('--trash-drive');
const dryRun = args.includes('--dry-run');

if (!inputDir) {
  console.error('Usage: node cleanup.js <input-dir> [--trash-drive] [--dry-run]');
  process.exit(1);
}

const absDir = path.resolve(inputDir);
if (!fs.existsSync(absDir)) {
  console.error(`Directory not found: ${absDir}`);
  process.exit(1);
}

const prefix = dryRun ? '[dry-run] would remove' : 'removing';

// Read mapping.json upfront (before local cleanup deletes it)
const mappingPath = path.join(absDir, 'mapping.json');
let mapping = null;
if (fs.existsSync(mappingPath)) {
  try { mapping = JSON.parse(fs.readFileSync(mappingPath, 'utf8')); } catch {}
}

// --- Helpers ---

function rmFile(filePath) {
  if (fs.existsSync(filePath)) {
    console.log(`  ${prefix}: ${path.relative(absDir, filePath)}`);
    if (!dryRun) fs.unlinkSync(filePath);
  }
}

function rmDir(dirPath) {
  if (fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory()) {
    console.log(`  ${prefix}: ${path.relative(absDir, dirPath)}/`);
    if (!dryRun) fs.rmSync(dirPath, { recursive: true, force: true });
  }
}

// --- Local cleanup ---

console.log(`\n=== Local cleanup (${absDir}) ===\n`);

// Known temp directories
rmDir(path.join(absDir, '_docx'));
rmDir(path.join(absDir, '_resolved'));

// diagrams-* directories (build artifacts)
const entries = fs.readdirSync(absDir, { withFileTypes: true });
for (const entry of entries) {
  if (entry.isDirectory() && entry.name.startsWith('diagrams-')) {
    rmDir(path.join(absDir, entry.name));
  }
}

// Known temp files by exact name
const knownTempFiles = [
  'mapping.json',
  'md-to-docx.js',
  'test-write.txt',
  'cleanup.sh',
];
for (const name of knownTempFiles) {
  rmFile(path.join(absDir, name));
}

// Pattern-based removal
for (const entry of entries) {
  if (!entry.isFile()) continue;
  const name = entry.name;
  const fullPath = path.join(absDir, name);

  // _prefixed .md files (preprocessed, e.g. _README-gdoc.md, _prompt-*.md)
  if (name.startsWith('_') && name.endsWith('.md')) {
    rmFile(fullPath);
    continue;
  }

  // _prefixed .js files (temp workflow scripts)
  if (name.startsWith('_') && name.endsWith('.js')) {
    rmFile(fullPath);
    continue;
  }

  // .docx files (generated intermediates)
  if (name.endsWith('.docx')) {
    rmFile(fullPath);
    continue;
  }

  // .sh files (shell helpers)
  if (name.endsWith('.sh')) {
    rmFile(fullPath);
    continue;
  }

  // Non-prefixed .js files that are known workflow scripts (not source code)
  // These are scripts copied in or created during the workflow
  const workflowScripts = [
    'update-crossref-links.js',
    'preprocess-ascii-to-images.js',
    'readme-to-docx.js',
  ];
  if (workflowScripts.includes(name)) {
    rmFile(fullPath);
  }
}

console.log('\nLocal cleanup complete.\n');

// --- Drive cleanup ---

if (trashDrive) {
  if (mapping && Object.keys(mapping).length > 0) {
    const hasGsuite = (() => {
      try { execSync('which gsuite', { stdio: 'pipe' }); return true; } catch { return false; }
    })();

    console.log(`=== Drive cleanup (${Object.keys(mapping).length} docs) ===\n`);

    if (!hasGsuite) {
      console.log('gsuite CLI not found. Trash these manually in Google Drive:\n');
      for (const [name, info] of Object.entries(mapping)) {
        console.log(`  ${name}: ${info.url}`);
      }
    } else {
      for (const [name, info] of Object.entries(mapping)) {
        const fileId = info.fileId;
        console.log(`  ${prefix}: ${name} (${fileId})`);
        if (!dryRun) {
          try {
            execSync(`gsuite drive trash "${fileId}"`, { stdio: 'pipe' });
          } catch (e) {
            console.log(`    (failed or already trashed)`);
          }
        }
      }
    }
    console.log('\nDrive cleanup complete (files in Trash, recoverable 30 days).\n');
  } else {
    console.log('No mapping.json found — skipping Drive cleanup.\n');
  }
}

// --- Summary ---
console.log('Remaining files are source markdown only.');
if (!trashDrive) {
  console.log('Tip: re-run with --trash-drive to also trash standalone Google Docs.');
}
if (dryRun) {
  console.log('\n(Dry run — nothing was actually deleted.)');
}
