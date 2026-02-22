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

const requiredKeys = [
  'type',
  'primary_audience',
  'owner',
  'last_verified',
  'next_review_by',
  'source_of_truth'
];

const allowedTypes = new Set(['tutorial', 'how-to', 'reference', 'concept']);
const allowedAudiences = new Set([
  'non-users/buyers',
  'admins/operators',
  'end users',
  'developers/partners',
  'sales and marketing',
  'support and operations',
  'engineers',
  'leadership',
  'risk/compliance/audit'
]);

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

function normalize(value) {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function parseFrontmatter(content) {
  if (!content.startsWith('---')) return null;
  const end = content.indexOf('\n---', 3);
  if (end === -1) return null;
  const block = content.slice(3, end).trim();
  const data = new Map();
  for (const line of block.split('\n')) {
    const idx = line.indexOf(':');
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim();
    if (key) data.set(key, value);
  }
  return data;
}

function parseHeaderBlock(content) {
  const lines = content.split('\n').slice(0, 30);
  const data = new Map();
  for (const line of lines) {
    const match = line.match(/^([A-Za-z ]+):\s*(.+)$/);
    if (!match) continue;
    const key = match[1].trim().toLowerCase().replace(/\s+/g, '_');
    const value = match[2].trim();
    data.set(key, value);
  }
  return data.size ? data : null;
}

function validate(filePath, content) {
  const errors = [];
  const frontmatter = parseFrontmatter(content);
  const data = frontmatter || parseHeaderBlock(content);

  if (!data) {
    errors.push('missing metadata block');
    return errors;
  }

  const missing = requiredKeys.filter((k) => !data.has(k) || !String(data.get(k) || '').trim());
  if (missing.length) errors.push(`missing keys: ${missing.join(', ')}`);

  const type = data.get('type');
  if (!type || !allowedTypes.has(normalize(type))) {
    errors.push(`invalid type: ${type || '<empty>'}`);
  }

  const audience = data.get('primary_audience') || data.get('primary audience');
  if (!audience || !allowedAudiences.has(normalize(audience))) {
    errors.push(`invalid primary_audience: ${audience || '<empty>'}`);
  }

  const nextReview = data.get('next_review_by') || data.get('next review by');
  if (nextReview && !/^\d{4}-\d{2}-\d{2}$/.test(nextReview.trim())) {
    errors.push(`next_review_by not YYYY-MM-DD: ${nextReview}`);
  }

  return errors;
}

if (!exists(docsRoot)) {
  console.error('docs/ directory missing.');
  process.exit(1);
}

const mdFiles = walk(docsRoot).filter((f) => f.endsWith('.md'));
const errors = [];

for (const file of mdFiles) {
  const rel = path.relative(root, file);
  if (ignoredFiles.has(rel)) continue;
  if (path.basename(file) === 'index.md') continue;
  const content = fs.readFileSync(file, 'utf8');
  const fileErrors = validate(file, content);
  if (fileErrors.length) {
    errors.push(`${rel}: ${fileErrors.join('; ')}`);
  }
}

if (errors.length) {
  console.error('Doc metadata validation failed:\n' + errors.map((e) => `- ${e}`).join('\n'));
  process.exit(1);
}

console.log('Doc metadata validation passed.');
