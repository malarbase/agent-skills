#!/usr/bin/env node

/**
 * resolve-crossrefs.js
 *
 * Resolves relative markdown cross-references to Google Docs URLs.
 *
 * Usage:
 *   node resolve-crossrefs.js <input-dir> <output-dir> <mapping-json>
 *
 * mapping-json format:
 *   {
 *     "README.md": { "docId": "1abc...", "url": "https://docs.google.com/document/d/1abc.../edit" },
 *     "architecture-overview.md": { "docId": "2def...", "url": "https://docs.google.com/document/d/2def.../edit?tab=t.xxx" },
 *     "internal/experiments.md": { "docId": "3ghi...", "url": "https://docs.google.com/document/d/3ghi.../edit?tab=t.yyy" }
 *   }
 *
 * Supports both separate-doc URLs and tab URLs. When the URL already contains
 * a tab param (?tab=...), anchors from the source link are appended as additional
 * query parameters rather than conflicting with the tab parameter.
 *
 * What it does:
 *   1. Reads all .md files from input-dir (recursively)
 *   2. Replaces relative links: [text](./file.md) → [text](google-docs-url)
 *   3. Handles anchors: [text](./file.md#section) → [text](google-docs-url#section)
 *   4. Preserves external links (http://, https://) unchanged
 *   5. Reports unresolved references
 *   6. Writes processed files to output-dir (preserving directory structure)
 */

const fs = require("fs");
const path = require("path");

function findMarkdownFiles(dir, baseDir = dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // Skip hidden dirs, node_modules, diagrams dirs
      if (
        entry.name.startsWith(".") ||
        entry.name === "node_modules" ||
        entry.name.startsWith("diagrams")
      ) {
        continue;
      }
      files.push(...findMarkdownFiles(fullPath, baseDir));
    } else if (entry.name.endsWith(".md")) {
      files.push({
        fullPath,
        relativePath: path.relative(baseDir, fullPath),
      });
    }
  }
  return files;
}

function resolveLink(linkTarget, currentFileRelDir, mapping) {
  // Split off anchor
  const [filePart, anchor] = linkTarget.split("#", 2);

  // Normalize: remove leading ./
  const cleanFile = filePart.replace(/^\.\//, "");

  // Resolve relative to the current file's directory
  const resolvedPath = path.normalize(
    path.join(currentFileRelDir, cleanFile)
  );

  // Look up in mapping (try several variants)
  const candidates = [
    resolvedPath,
    cleanFile,
    resolvedPath.replace(/\\/g, "/"),
    cleanFile.replace(/\\/g, "/"),
  ];

  for (const candidate of candidates) {
    if (mapping[candidate]) {
      let url = mapping[candidate].url;
      if (anchor) {
        // If URL already has query params (e.g., ?tab=t.xxx), append anchor as additional param
        if (url.includes("?")) {
          // For tab URLs, we can't deep-link to a heading within a tab via URL alone.
          // Append as a query param hint; the agent can later use add-link with headingId.
          url += `&heading=${anchor}`;
        } else {
          url += `?heading=${anchor}`;
        }
      }
      return { resolved: true, url };
    }
  }

  return { resolved: false, original: linkTarget };
}

function processMarkdown(content, currentFileRelDir, mapping) {
  const unresolved = [];
  let resolvedCount = 0;

  // Match markdown links: [text](target)
  // Negative lookbehind for ! to skip image links
  const linkPattern = /(?<!!)\[([^\]]*)\]\(([^)]+)\)/g;

  const processed = content.replace(linkPattern, (match, text, target) => {
    // Skip external links
    if (target.startsWith("http://") || target.startsWith("https://")) {
      return match;
    }

    // Skip non-.md links (anchors within same doc, images, etc.)
    const filePart = target.split("#")[0];
    if (filePart && !filePart.endsWith(".md")) {
      return match;
    }

    // Handle same-file anchors (#section)
    if (!filePart && target.startsWith("#")) {
      return match; // Keep as-is
    }

    const result = resolveLink(target, currentFileRelDir, mapping);
    if (result.resolved) {
      resolvedCount++;
      return `[${text}](${result.url})`;
    } else {
      unresolved.push({ text, target });
      return match; // Keep original if not in mapping
    }
  });

  return { processed, resolvedCount, unresolved };
}

function main() {
  const args = process.argv.slice(2);
  if (args.length < 3) {
    console.error(
      "Usage: node resolve-crossrefs.js <input-dir> <output-dir> <mapping-json>"
    );
    console.error("");
    console.error("mapping-json can be a JSON file path or inline JSON string");
    process.exit(1);
  }

  const [inputDir, outputDir, mappingArg] = args;

  // Load mapping
  let mapping;
  try {
    if (fs.existsSync(mappingArg)) {
      mapping = JSON.parse(fs.readFileSync(mappingArg, "utf-8"));
    } else {
      mapping = JSON.parse(mappingArg);
    }
  } catch (e) {
    console.error(`Error loading mapping: ${e.message}`);
    process.exit(1);
  }

  // Validate input dir
  if (!fs.existsSync(inputDir)) {
    console.error(`Input directory not found: ${inputDir}`);
    process.exit(1);
  }

  // Find all markdown files
  const mdFiles = findMarkdownFiles(inputDir);
  console.log(`Found ${mdFiles.length} markdown files in ${inputDir}`);
  console.log(`Mapping has ${Object.keys(mapping).length} entries`);
  console.log("");

  // Create output dir
  fs.mkdirSync(outputDir, { recursive: true });

  let totalResolved = 0;
  let totalUnresolved = 0;

  for (const file of mdFiles) {
    const content = fs.readFileSync(file.fullPath, "utf-8");
    const currentDir = path.dirname(file.relativePath);

    const { processed, resolvedCount, unresolved } = processMarkdown(
      content,
      currentDir,
      mapping
    );

    totalResolved += resolvedCount;
    totalUnresolved += unresolved.length;

    // Write to output dir (preserving structure)
    const outPath = path.join(outputDir, file.relativePath);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, processed, "utf-8");

    // Report
    const status =
      unresolved.length > 0 ? `(${unresolved.length} unresolved)` : "";
    console.log(
      `  ${file.relativePath}: ${resolvedCount} links resolved ${status}`
    );

    if (unresolved.length > 0) {
      for (const u of unresolved) {
        console.log(`    WARNING: unresolved [${u.text}](${u.target})`);
      }
    }
  }

  console.log("");
  console.log(
    `Done. Resolved: ${totalResolved}, Unresolved: ${totalUnresolved}`
  );
  console.log(`Output written to: ${outputDir}`);

  // Also write mapping for reference
  const mappingOutPath = path.join(outputDir, "_crossref-mapping.json");
  fs.writeFileSync(mappingOutPath, JSON.stringify(mapping, null, 2), "utf-8");
  console.log(`Mapping saved to: ${mappingOutPath}`);

  if (totalUnresolved > 0) {
    console.log(
      `\nWARNING: ${totalUnresolved} unresolved references. Add missing entries to mapping.json.`
    );
    process.exit(2); // Non-zero but distinct from error
  }
}

main();
