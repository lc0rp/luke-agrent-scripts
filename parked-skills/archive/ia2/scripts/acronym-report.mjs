#!/usr/bin/env node
import fs from 'fs';
import path from 'path';

const root = process.cwd();
const docsRoot = path.join(root, 'docs');

const ignoredDirs = new Set([
  '.git',
  'node_modules',
  'dist',
  'build',
  'out',
  'coverage',
  'templates',
  '99-archive'
]);

const ignoredFiles = new Set([
  path.join('docs', 'README.md')
]);

const ignoreAcronyms = new Set(['README', 'TODO', 'FIXME', 'YYYY', 'MM', 'DD']);

function exists(p) {
  try { fs.accessSync(p); return true; } catch { return false; }
}

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.name.startsWith('.') && entry.name !== '.github') continue;
    if (ignoredDirs.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...walk(full));
    else if (entry.isFile()) files.push(full);
  }
  return files;
}

function resolveOutputPath() {
  const preferred = path.join(docsRoot, '00-foundation', 'reference');
  if (exists(preferred)) return path.join(preferred, 'acronym-report.md');
  const fallbackDocs = path.join(docsRoot, 'acronym-report.md');
  if (exists(docsRoot)) return fallbackDocs;
  return path.join(root, 'acronym-report.md');
}

function isGlossaryFile(filePath) {
  const base = path.basename(filePath).toLowerCase();
  if (base === 'glossary.md') return true;
  const dir = path.basename(path.dirname(filePath)).toLowerCase();
  return dir === 'glossary' && base === 'index.md';
}

function stripInlineCode(line) {
  return line.replace(/`[^`]*`/g, '');
}

function iterateContentLines(content, cb) {
  let inFence = false;
  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim();
    if (line.startsWith('```')) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    cb(stripInlineCode(rawLine));
  }
}

function extractGlossaryTerms(content) {
  const terms = new Set();
  iterateContentLines(content, (line) => {
    const cleaned = line.replace(/^\s*[-*]\s+/, '').replace(/^\s*\d+\.\s+/, '');
    const match = cleaned.match(/^([A-Z][A-Z0-9]{1,})\s*(?:-|—|:)/);
    if (match) terms.add(match[1]);
  });
  return terms;
}

function normalize(value) {
  return value.trim();
}

function collectDefinitions(content) {
  const defs = new Map();
  let lineNum = 0;
  iterateContentLines(content, (line) => {
    lineNum += 1;
    const patterns = [
      /\b([A-Za-z][A-Za-z0-9 ,\/-]{2,})\s*\(([A-Z][A-Z0-9]{1,})\)\b/g,
      /\b([A-Z][A-Z0-9]{1,})\s*\(([^)]+)\)/g
    ];
    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(line)) !== null) {
        const acronym = pattern === patterns[0] ? match[2] : match[1];
        if (!defs.has(acronym)) defs.set(acronym, lineNum);
      }
    }
  });
  return defs;
}

function collectOccurrences(content) {
  const occ = new Map();
  let lineNum = 0;
  iterateContentLines(content, (line) => {
    lineNum += 1;
    const matches = line.match(/\b[A-Z][A-Z0-9]{1,}\b/g) || [];
    for (const raw of matches) {
      const acronym = normalize(raw);
      if (ignoreAcronyms.has(acronym)) continue;
      if (!occ.has(acronym)) occ.set(acronym, []);
      occ.get(acronym).push(lineNum);
    }
  });
  return occ;
}

if (!exists(docsRoot)) {
  console.error('docs/ directory missing.');
  process.exit(1);
}

const mdFiles = walk(docsRoot).filter((f) => f.endsWith('.md'));
const glossaryFiles = mdFiles.filter((f) => isGlossaryFile(f));
const glossaryTerms = new Set();

for (const file of glossaryFiles) {
  const content = fs.readFileSync(file, 'utf8');
  const terms = extractGlossaryTerms(content);
  for (const term of terms) glossaryTerms.add(term);
}

const findings = [];
let filesScanned = 0;
let totalAcronyms = 0;
let undefinedCount = 0;
let lateDefCount = 0;

for (const file of mdFiles) {
  const rel = path.relative(root, file);
  if (ignoredFiles.has(rel)) continue;
  if (path.basename(file) === 'index.md') continue;
  if (isGlossaryFile(file)) continue;

  filesScanned += 1;
  const content = fs.readFileSync(file, 'utf8');
  const defs = collectDefinitions(content);
  const occ = collectOccurrences(content);

  const fileIssues = [];
  for (const [acronym, lines] of occ.entries()) {
    const firstLine = lines[0];
    totalAcronyms += 1;
    if (glossaryTerms.has(acronym)) continue;
    const defLine = defs.get(acronym);
    if (!defLine) {
      undefinedCount += 1;
      fileIssues.push(`- ${acronym} (line ${firstLine}): no definition found`);
    } else if (defLine > firstLine) {
      lateDefCount += 1;
      fileIssues.push(`- ${acronym} (line ${firstLine}): definition after first use (line ${defLine})`);
    }
  }

  if (fileIssues.length) {
    findings.push(`## ${rel}\n\n${fileIssues.join('\n')}`);
  }
}

const outPath = resolveOutputPath();
const outDir = path.dirname(outPath);
if (!exists(outDir)) fs.mkdirSync(outDir, { recursive: true });

const date = new Date().toISOString().replace('T', ' ').replace(/\..+/, '');
const glossaryList = glossaryFiles.length
  ? glossaryFiles.map((f) => `- ${path.relative(root, f)}`).join('\n')
  : '- (none found)';

const report = [
  '# Acronym Report',
  '',
  `Generated: ${date}`,
  `Root: ${root}`,
  `Docs root: ${docsRoot}`,
  '',
  '## Summary',
  `- Files scanned: ${filesScanned}`,
  `- Acronyms found: ${totalAcronyms}`,
  `- Undefined acronyms: ${undefinedCount}`,
  `- Definition after first use: ${lateDefCount}`,
  '',
  '## Glossary sources',
  glossaryList,
  '',
  '## Findings',
  findings.length ? findings.join('\n\n') : 'No issues found.'
].join('\n');

fs.writeFileSync(outPath, report, 'utf8');
console.log(`Acronym report written to ${outPath}`);
