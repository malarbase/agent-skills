#!/usr/bin/env node
/**
 * Markdown to DOCX converter with Mermaid diagram support
 * 
 * Usage: node md-to-docx.js <input.md> <output.docx>
 * 
 * This script:
 * 1. Parses markdown to extract structure (headings, paragraphs, tables, code, lists)
 * 2. Identifies ASCII art diagrams and converts them to Mermaid
 * 3. Renders Mermaid diagrams to PNG images
 * 4. Generates a complete DOCX with all content and embedded images
 * 
 * Prerequisites:
 * - npm install docx (in the working directory)
 * - npm install -g @mermaid-js/mermaid-cli
 * - sips (macOS built-in for image dimensions)
 */

const { Document, Packer, Paragraph, TextRun, ImageRun, HeadingLevel, AlignmentType, 
        Header, Footer, PageNumber, BorderStyle, Table, TableRow, TableCell, 
        WidthType, ShadingType, VerticalAlign, ExternalHyperlink, PageBreak,
        LevelFormat } = require('docx');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Parse command line args
const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile || !outputFile) {
  console.error('Usage: node md-to-docx.js <input.md> <output.docx>');
  console.error('');
  console.error('Prerequisites:');
  console.error('  npm install docx');
  console.error('  npm install -g @mermaid-js/mermaid-cli');
  process.exit(1);
}

const markdown = fs.readFileSync(inputFile, 'utf-8');
const workDir = path.dirname(path.resolve(inputFile));
const diagramsDir = path.join(workDir, 'diagrams');

// Ensure diagrams directory exists
if (!fs.existsSync(diagramsDir)) {
  fs.mkdirSync(diagramsDir, { recursive: true });
}

// Track diagram count for naming
let diagramCount = 0;
const diagramImages = {};

/**
 * Detect if a code block contains ASCII art diagram
 */
function isAsciiDiagram(code) {
  const diagramPatterns = [
    /[┌┐└┘├┤┬┴┼─│]/,  // Box drawing characters
    /[═║╔╗╚╝╠╣╦╩╬]/,  // Double box drawing
    /──▶|◀──/,         // Arrows
    /\+-+\+/,          // ASCII boxes +--+
    /\|.*\|.*\|/,      // Vertical bars in pattern
  ];
  return diagramPatterns.some(p => p.test(code));
}

/**
 * Get image dimensions using sips (macOS) or identify (ImageMagick)
 */
function getImageDimensions(pngPath) {
  try {
    // Try sips first (macOS)
    const sipsOutput = execSync(`sips -g pixelWidth -g pixelHeight "${pngPath}"`, { encoding: 'utf-8' });
    const widthMatch = sipsOutput.match(/pixelWidth:\s*(\d+)/);
    const heightMatch = sipsOutput.match(/pixelHeight:\s*(\d+)/);
    if (widthMatch && heightMatch) {
      return { width: parseInt(widthMatch[1]), height: parseInt(heightMatch[1]) };
    }
  } catch (e) {
    // Try identify (ImageMagick) as fallback
    try {
      const identifyOutput = execSync(`identify -format "%w %h" "${pngPath}"`, { encoding: 'utf-8' });
      const [width, height] = identifyOutput.trim().split(' ').map(Number);
      return { width, height };
    } catch (e2) {
      console.error(`Warning: Could not get dimensions for ${pngPath}`);
    }
  }
  return null;
}

/**
 * Render Mermaid to PNG and return image info with correct aspect ratio
 */
function renderMermaid(mermaidCode, name) {
  const mmdFile = path.join(diagramsDir, `${name}.mmd`);
  const pngFile = path.join(diagramsDir, `${name}.png`);
  
  fs.writeFileSync(mmdFile, mermaidCode);
  
  try {
    execSync(`mmdc -i "${mmdFile}" -o "${pngFile}" -w 1200 --scale 2 -b white`, {
      stdio: 'pipe'
    });
    
    const dims = getImageDimensions(pngFile);
    if (!dims) return null;
    
    const aspectRatio = dims.width / dims.height;
    
    // Calculate doc dimensions (max width 560, preserve aspect ratio)
    const docWidth = Math.min(560, dims.width / 2);
    const docHeight = Math.round(docWidth / aspectRatio);
    
    return { path: pngFile, width: docWidth, height: docHeight };
  } catch (err) {
    console.error(`Failed to render ${name}:`, err.message);
    return null;
  }
}

/**
 * Parse markdown into structured blocks
 */
function parseMarkdown(md) {
  const blocks = [];
  const lines = md.split('\n');
  let i = 0;
  
  while (i < lines.length) {
    const line = lines[i];
    
    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({ type: 'heading', level: headingMatch[1].length, text: headingMatch[2] });
      i++;
      continue;
    }

    // Images: ![alt](path)
    const imgMatch = line.match(/^!\[([^\]]*)\]\(([^)]+)\)/);
    if (imgMatch) {
      blocks.push({ type: 'image', alt: imgMatch[1], src: imgMatch[2] });
      i++;
      continue;
    }
    
    // Code blocks
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      const code = codeLines.join('\n');
      
      if (lang === 'mermaid') {
        blocks.push({ type: 'mermaid', code });
      } else if (isAsciiDiagram(code)) {
        blocks.push({ type: 'ascii-diagram', code, lang });
      } else {
        blocks.push({ type: 'code', code, lang });
      }
      i++;
      continue;
    }
    
    // Tables
    if (line.includes('|') && lines[i + 1]?.match(/^\|[-:\s|]+\|$/)) {
      const tableLines = [line];
      i++;
      while (i < lines.length && lines[i].includes('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      blocks.push({ type: 'table', lines: tableLines });
      continue;
    }
    
    // Blockquotes
    if (line.startsWith('>')) {
      const quoteLines = [];
      while (i < lines.length && (lines[i].startsWith('>') || lines[i].trim() === '')) {
        if (lines[i].startsWith('>')) {
          quoteLines.push(lines[i].replace(/^>\s?/, ''));
        }
        i++;
        if (lines[i]?.trim() === '' && !lines[i + 1]?.startsWith('>')) break;
      }
      blocks.push({ type: 'blockquote', text: quoteLines.join('\n') });
      continue;
    }
    
    // Horizontal rule
    if (line.match(/^-{3,}$/) || line.match(/^\*{3,}$/)) {
      blocks.push({ type: 'hr' });
      i++;
      continue;
    }
    
    // List items
    if (line.match(/^[-*]\s/) || line.match(/^\d+\.\s/)) {
      const listItems = [];
      const isOrdered = /^\d+\./.test(line);
      while (i < lines.length && (lines[i].match(/^[-*]\s/) || lines[i].match(/^\d+\.\s/) || (lines[i].startsWith('  ') && listItems.length > 0))) {
        const itemMatch = lines[i].match(/^[-*\d.]+\s+(.+)$/);
        if (itemMatch) {
          listItems.push(itemMatch[1]);
        } else if (lines[i].trim()) {
          if (listItems.length > 0) {
            listItems[listItems.length - 1] += ' ' + lines[i].trim();
          }
        }
        i++;
      }
      blocks.push({ type: 'list', items: listItems, ordered: isOrdered });
      continue;
    }
    
    // Empty lines
    if (line.trim() === '') {
      i++;
      continue;
    }
    
    // Regular paragraph
    const paraLines = [];
    while (i < lines.length && lines[i].trim() !== '' && 
           !lines[i].startsWith('#') && !lines[i].startsWith('```') &&
           !lines[i].startsWith('>') && !lines[i].match(/^[-*]\s/) &&
           !lines[i].match(/^\d+\.\s/) && !lines[i].match(/^!\[/) &&
           !lines[i].match(/^-{3,}$/) && !lines[i].match(/^\*{3,}$/) &&
           !(lines[i].includes('|') && lines[i + 1]?.match(/^\|[-:\s|]+\|$/))) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: 'paragraph', text: paraLines.join(' ') });
    }
  }
  
  return blocks;
}

/**
 * Parse inline markdown formatting into TextRun / ExternalHyperlink objects.
 * Handles: [label](url) → hyperlinks, **bold** → bold runs, `code` → monospace runs.
 */
function parseInlineFormatting(text) {
  const runs = [];
  // Match hyperlinks, bold, or inline code — in order of appearance
  const regex = /(\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|`(.+?)`)/g;
  let lastIdx = 0;
  let m;
  while ((m = regex.exec(text)) !== null) {
    // Plain text before this match
    if (m.index > lastIdx) {
      runs.push(new TextRun({ text: text.slice(lastIdx, m.index), size: 22 }));
    }
    if (m[2] && m[3]) {
      // Hyperlink [label](url)
      runs.push(new ExternalHyperlink({
        link: m[3],
        children: [new TextRun({ text: m[2], style: "Hyperlink", size: 22, color: "1155CC", underline: {} })]
      }));
    } else if (m[4]) {
      // Bold **text**
      runs.push(new TextRun({ text: m[4], bold: true, size: 22 }));
    } else if (m[5]) {
      // Inline code `text`
      runs.push(new TextRun({ text: m[5], font: "Courier New", size: 20 }));
    }
    lastIdx = m.index + m[0].length;
  }
  // Trailing plain text
  if (lastIdx < text.length) {
    runs.push(new TextRun({ text: text.slice(lastIdx), size: 22 }));
  }
  return runs.length ? runs : [new TextRun({ text, size: 22 })];
}

/**
 * Parse table from markdown lines
 */
function parseTable(tableLines) {
  const rows = [];
  for (let i = 0; i < tableLines.length; i++) {
    if (i === 1 && tableLines[i].match(/^\|[-:\s|]+\|$/)) continue;
    const cells = tableLines[i].split('|').filter((c, idx, arr) => idx > 0 && idx < arr.length - 1).map(c => c.trim());
    rows.push({ cells, isHeader: i === 0 });
  }
  return rows;
}

/**
 * Create docx table from parsed rows
 */
function createDocxTable(rows) {
  if (rows.length === 0) return null;
  
  const numCols = rows[0].cells.length;
  const colWidth = Math.floor(9360 / numCols);
  const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
  const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };
  
  return new Table({
    columnWidths: Array(numCols).fill(colWidth),
    rows: rows.map((row) => new TableRow({
      tableHeader: row.isHeader,
      children: row.cells.map(cell => new TableCell({
        borders: cellBorders,
        width: { size: colWidth, type: WidthType.DXA },
        shading: row.isHeader ? { fill: "1976d2", type: ShadingType.CLEAR } : undefined,
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({
          children: row.isHeader
            ? [new TextRun({ text: cell.replace(/\*\*/g, ''), bold: true, color: "FFFFFF", size: 22 })]
            : parseInlineFormatting(cell)
        })]
      }))
    }))
  });
}

/**
 * Convert blocks to docx elements
 */
function blocksToDocx(blocks) {
  const children = [];
  
  for (const block of blocks) {
    switch (block.type) {
      case 'heading':
        const headingLevel = block.level === 1 ? HeadingLevel.HEADING_1 :
                            block.level === 2 ? HeadingLevel.HEADING_2 :
                            block.level === 3 ? HeadingLevel.HEADING_3 :
                            HeadingLevel.HEADING_4;
        children.push(new Paragraph({
          heading: headingLevel,
          children: [new TextRun(block.text.replace(/\*\*/g, ''))]
        }));
        break;
        
      case 'paragraph':
        children.push(new Paragraph({
          spacing: { after: 200 },
          children: parseInlineFormatting(block.text)
        }));
        break;

      case 'image': {
        const imgPath = path.resolve(workDir, block.src);
        if (!fs.existsSync(imgPath)) {
          console.error(`Warning: Image not found: ${imgPath}`);
          children.push(new Paragraph({
            spacing: { after: 200 },
            children: [new TextRun({ text: `[Image not found: ${block.src}]`, italics: true, color: "999999" })]
          }));
          break;
        }
        const dims = getImageDimensions(imgPath);
        if (dims) {
          const aspectRatio = dims.width / dims.height;
          const docWidth = Math.min(560, dims.width / 2);
          const docHeight = Math.round(docWidth / aspectRatio);
          children.push(new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 200, after: 200 },
            children: [new ImageRun({
              type: path.extname(imgPath).replace('.', '') === 'jpg' ? 'jpg' : 'png',
              data: fs.readFileSync(imgPath),
              transformation: { width: docWidth, height: docHeight },
              altText: { title: block.alt || 'Image', description: block.alt || 'Image', name: path.basename(imgPath) }
            })]
          }));
        }
        break;
      }
        
      case 'code':
        const codeLines = block.code.split('\n');
        children.push(new Paragraph({
          spacing: { before: 120, after: 120 },
          shading: { fill: "f5f5f5", type: ShadingType.CLEAR },
          children: [new TextRun({ text: block.lang ? `[${block.lang}]` : '[code]', bold: true, size: 20, color: "666666" })]
        }));
        for (const codeLine of codeLines) {
          children.push(new Paragraph({
            spacing: { after: 0 },
            indent: { left: 360 },
            children: [new TextRun({ text: codeLine || ' ', font: "Courier New", size: 20 })]
          }));
        }
        children.push(new Paragraph({ spacing: { after: 200 }, children: [] }));
        break;
        
      case 'mermaid':
        diagramCount++;
        const imgInfo = renderMermaid(block.code, `diagram-${diagramCount}`);
        if (imgInfo) {
          children.push(new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 200, after: 120 },
            children: [new ImageRun({
              type: "png",
              data: fs.readFileSync(imgInfo.path),
              transformation: { width: imgInfo.width, height: imgInfo.height },
              altText: { title: `Diagram ${diagramCount}`, description: "Mermaid diagram", name: `diagram-${diagramCount}` }
            })]
          }));
          children.push(new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { after: 200 },
            children: [new TextRun({ text: `Figure ${diagramCount}`, italics: true, color: "666666", size: 22 })]
          }));
        }
        break;
        
      case 'ascii-diagram':
        diagramCount++;
        const paddedNum = diagramCount.toString().padStart(2, '0');
        
        // Check for existing PNG files
        let existingPng = null;
        let existingMmd = null;
        
        try {
          const files = fs.readdirSync(diagramsDir);
          existingPng = files.find(f => f.startsWith(`${paddedNum}-`) && f.endsWith('.png'));
          existingMmd = files.find(f => f.startsWith(`${paddedNum}-`) && f.endsWith('.mmd'));
        } catch (e) {
          // diagrams dir may not exist yet
        }
        
        if (existingPng) {
          const pngPath = path.join(diagramsDir, existingPng);
          const dims = getImageDimensions(pngPath);
          if (dims) {
            const aspectRatio = dims.width / dims.height;
            const docWidth = Math.min(560, dims.width / 2);
            const docHeight = Math.round(docWidth / aspectRatio);
            
            children.push(new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { before: 200, after: 120 },
              children: [new ImageRun({
                type: "png",
                data: fs.readFileSync(pngPath),
                transformation: { width: docWidth, height: docHeight },
                altText: { title: `Diagram ${diagramCount}`, description: "Converted ASCII diagram", name: `diagram-${diagramCount}` }
              })]
            }));
            children.push(new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 200 },
              children: [new TextRun({ text: `Figure ${diagramCount}`, italics: true, color: "666666", size: 22 })]
            }));
          }
        } else if (existingMmd) {
          const mermaidCode = fs.readFileSync(path.join(diagramsDir, existingMmd), 'utf-8');
          const imgInfo = renderMermaid(mermaidCode, existingMmd.replace('.mmd', ''));
          if (imgInfo) {
            children.push(new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { before: 200, after: 120 },
              children: [new ImageRun({
                type: "png",
                data: fs.readFileSync(imgInfo.path),
                transformation: { width: imgInfo.width, height: imgInfo.height },
                altText: { title: `Diagram ${diagramCount}`, description: "Converted ASCII diagram", name: `diagram-${diagramCount}` }
              })]
            }));
            children.push(new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 200 },
              children: [new TextRun({ text: `Figure ${diagramCount}`, italics: true, color: "666666", size: 22 })]
            }));
          }
        } else {
          // Fall back to code block display with warning
          children.push(new Paragraph({
            spacing: { before: 120, after: 120 },
            shading: { fill: "fff3e0", type: ShadingType.CLEAR },
            children: [new TextRun({ text: `[ASCII Diagram ${diagramCount} - create ${paddedNum}-name.mmd to convert]`, bold: true, size: 20, color: "e65100" })]
          }));
          for (const codeLine of block.code.split('\n')) {
            children.push(new Paragraph({
              spacing: { after: 0 },
              children: [new TextRun({ text: codeLine || ' ', font: "Courier New", size: 18 })]
            }));
          }
          children.push(new Paragraph({ spacing: { after: 200 }, children: [] }));
        }
        break;
        
      case 'table':
        const rows = parseTable(block.lines);
        const table = createDocxTable(rows);
        if (table) {
          children.push(table);
          children.push(new Paragraph({ spacing: { after: 200 }, children: [] }));
        }
        break;
        
      case 'list':
        for (let li = 0; li < block.items.length; li++) {
          const prefix = block.ordered ? `${li + 1}. ` : '• ';
          children.push(new Paragraph({
            spacing: { after: 60 },
            children: [new TextRun({ text: prefix, size: 22 }), ...parseInlineFormatting(block.items[li])]
          }));
        }
        children.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
        break;
        
      case 'blockquote':
        children.push(new Paragraph({
          spacing: { before: 120, after: 120 },
          indent: { left: 720 },
          shading: { fill: "e3f2fd", type: ShadingType.CLEAR },
          children: [new TextRun({ text: block.text, italics: true, color: "1565c0" })]
        }));
        break;
        
      case 'hr':
        children.push(new Paragraph({
          spacing: { before: 240, after: 240 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC" } },
          children: []
        }));
        break;
    }
  }
  
  return children;
}

// Main execution
console.log(`Parsing ${inputFile}...`);
const blocks = parseMarkdown(markdown);
console.log(`Found ${blocks.length} blocks`);

// Count diagrams
const asciiDiagrams = blocks.filter(b => b.type === 'ascii-diagram');
const mermaidDiagrams = blocks.filter(b => b.type === 'mermaid');
console.log(`ASCII diagrams: ${asciiDiagrams.length}, Mermaid diagrams: ${mermaidDiagrams.length}`);

if (asciiDiagrams.length > 0) {
  console.log(`\nTo convert ASCII diagrams, create files in ${diagramsDir}/:`);
  asciiDiagrams.forEach((_, idx) => {
    const num = (idx + 1).toString().padStart(2, '0');
    console.log(`  ${num}-diagram-name.mmd`);
  });
  console.log(`Then run: mmdc -i file.mmd -o file.png -w 1200 --scale 2 -b white`);
}

// Extract title
const titleBlock = blocks.find(b => b.type === 'heading' && b.level === 1);
const title = titleBlock ? titleBlock.text : 'Document';

// Create document
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, color: "1976d2", font: "Arial" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "333333", font: "Arial" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: "444444", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "555555", font: "Arial" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 3 } }
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({ 
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: title, italics: true, size: 20, color: "666666" })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ 
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "Page ", size: 20 }), 
          new TextRun({ children: [PageNumber.CURRENT], size: 20 }), 
          new TextRun({ text: " of ", size: 20 }), 
          new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 20 })
        ]
      })] })
    },
    children: blocksToDocx(blocks)
  }]
});

// Generate document
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputFile, buffer);
  console.log(`\nDocument created: ${outputFile}`);
}).catch(err => {
  console.error('Failed to create document:', err);
  process.exit(1);
});
