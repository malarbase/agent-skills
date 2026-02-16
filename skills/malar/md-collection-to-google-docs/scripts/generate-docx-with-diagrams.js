#!/usr/bin/env node
/**
 * Generate DOCX files from resolved markdown, handling per-file diagram directories.
 *
 * Usage:
 *   node generate-docx-with-diagrams.js \
 *     --input-dir <resolved-markdown-dir> \
 *     --output-dir <docx-output-dir> \
 *     --script <path-to-md-to-docx.js> \
 *     [--diagrams-dir <base-dir-for-diagrams>]
 *
 * For each .md file in input-dir:
 *   1. Creates a temp work directory
 *   2. Copies the markdown file and its diagram PNGs (from diagrams-{name}/)
 *   3. Runs md-to-docx.js to generate the DOCX
 *   4. Cleans up the temp directory
 *
 * Diagram directories are expected at: {diagrams-dir}/diagrams-{name}/*.png
 * If --diagrams-dir is omitted, looks in the parent of input-dir.
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function parseArgs(argv) {
  const args = { inputDir: null, outputDir: null, script: null, diagramsDir: null };
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case '--input-dir':    args.inputDir = argv[++i]; break;
      case '--output-dir':   args.outputDir = argv[++i]; break;
      case '--script':       args.script = argv[++i]; break;
      case '--diagrams-dir': args.diagramsDir = argv[++i]; break;
    }
  }
  if (!args.inputDir || !args.outputDir || !args.script) {
    console.error('Usage: node generate-docx-with-diagrams.js --input-dir <dir> --output-dir <dir> --script <md-to-docx.js>');
    process.exit(1);
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv);
  const diagramsBase = args.diagramsDir || path.dirname(args.inputDir);

  // Ensure output dir exists
  fs.mkdirSync(args.outputDir, { recursive: true });

  // Find all .md files (including subdirectories like internal/)
  const files = [];
  function scanDir(dir, prefix) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isFile() && entry.name.endsWith('.md') && !entry.name.startsWith('_')) {
        files.push({ rel: prefix ? prefix + '/' + entry.name : entry.name, abs: path.join(dir, entry.name) });
      } else if (entry.isDirectory() && !entry.name.startsWith('_') && !entry.name.startsWith('.')) {
        scanDir(path.join(dir, entry.name), prefix ? prefix + '/' + entry.name : entry.name);
      }
    }
  }
  scanDir(args.inputDir, '');

  console.log(`Processing ${files.length} markdown files...\n`);

  let success = 0, failed = 0;
  for (const file of files) {
    const name = path.basename(file.rel, '.md');
    const outName = name + '.docx';
    const diagDir = path.join(diagramsBase, 'diagrams-' + name);
    const hasDiagrams = fs.existsSync(diagDir);

    // Create temp work directory
    const workDir = path.join(args.inputDir, '_work-' + name);
    fs.mkdirSync(path.join(workDir, 'diagrams'), { recursive: true });

    // Copy markdown
    fs.copyFileSync(file.abs, path.join(workDir, name + '.md'));

    // Copy diagram PNGs if they exist
    if (hasDiagrams) {
      const pngs = fs.readdirSync(diagDir).filter(f => f.endsWith('.png'));
      for (const png of pngs) {
        fs.copyFileSync(path.join(diagDir, png), path.join(workDir, 'diagrams', png));
      }
    }

    // Run md-to-docx.js
    const inputPath = path.join(workDir, name + '.md');
    const outputPath = path.join(args.outputDir, outName);
    try {
      execSync(`node "${args.script}" "${inputPath}" "${outputPath}"`, { stdio: 'pipe' });
      const size = (fs.statSync(outputPath).size / 1024).toFixed(1);
      const diagCount = hasDiagrams ? fs.readdirSync(diagDir).filter(f => f.endsWith('.png')).length : 0;
      console.log(`  OK  ${outName} (${size} KB${diagCount ? ', ' + diagCount + ' diagrams' : ''})`);
      success++;
    } catch (err) {
      console.error(`  FAIL  ${outName}: ${err.stderr?.toString()?.trim() || err.message}`);
      failed++;
    }

    // Cleanup work dir
    fs.rmSync(workDir, { recursive: true, force: true });
  }

  console.log(`\nDone: ${success} succeeded, ${failed} failed.`);
  if (failed > 0) process.exit(1);
}

main();
