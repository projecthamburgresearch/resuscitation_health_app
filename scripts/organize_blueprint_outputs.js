#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const BLUEPRINT_ROOT = path.join(ROOT, 'appendix/blueprint_outputs');
const LEGACY_BLUEPRINT_ROOT = path.join(ROOT, 'appendix/blueprint_legacy');
const CURRENT_DIR = path.join(BLUEPRINT_ROOT, 'current');
const ARCHIVE_ROOT = path.join(BLUEPRINT_ROOT, 'archive');

const FILE_RE = /\.(?:json|ya?ml|md)$/i;

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function sameContent(a, b) {
  try {
    const aBuf = fs.readFileSync(a);
    const bBuf = fs.readFileSync(b);
    return aBuf.equals(bBuf);
  } catch {
    return false;
  }
}

function parseArgs(argv) {
  const out = { dryRun: false };
  for (const arg of argv) {
    if (arg === '--dry-run') out.dryRun = true;
    else if (arg === '--help' || arg === '-h') {
      console.log(`
Usage:
  node scripts/organize_blueprint_outputs.js
  node scripts/organize_blueprint_outputs.js --dry-run

Behavior:
  - moves top-level artifact files from appendix/blueprint_outputs/ into canonical folders
  - canonical location is appendix/blueprint_outputs/current/
  - conflicting files are archived under appendix/blueprint_outputs/archive/<timestamp>/
  - also migrates legacy appendix/blueprint_legacy top-level artifacts
`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }
  return out;
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (!fs.existsSync(BLUEPRINT_ROOT)) {
    if (!fs.existsSync(LEGACY_BLUEPRINT_ROOT)) {
      console.error('appendix/blueprint_outputs/ directory not found.');
      process.exit(1);
    }
    ensureDir(BLUEPRINT_ROOT);
  }

  ensureDir(CURRENT_DIR);
  ensureDir(ARCHIVE_ROOT);

  const roots = [BLUEPRINT_ROOT];
  if (fs.existsSync(LEGACY_BLUEPRINT_ROOT)) roots.push(LEGACY_BLUEPRINT_ROOT);

  const candidates = [];
  for (const root of roots) {
    const files = fs.readdirSync(root, { withFileTypes: true })
      .filter((entry) => entry.isFile())
      .map((entry) => entry.name)
      .filter((name) => FILE_RE.test(name))
      .sort();
    for (const file of files) {
      candidates.push({ file, root });
    }
  }

  if (candidates.length === 0) {
    console.log('No top-level blueprint artifact files to organize.');
    return;
  }

  const archiveDir = path.join(ARCHIVE_ROOT, `top-level-${nowStamp()}`);
  let movedToCurrent = 0;
  let movedToArchive = 0;

  for (const candidate of candidates) {
    const src = path.join(candidate.root, candidate.file);
    const dstCurrent = path.join(CURRENT_DIR, candidate.file);

    if (!fs.existsSync(dstCurrent)) {
      if (opts.dryRun) {
        console.log(`[dry-run] move ${path.relative(ROOT, src)} -> ${path.relative(ROOT, dstCurrent)}`);
      } else {
        fs.renameSync(src, dstCurrent);
      }
      movedToCurrent += 1;
      continue;
    }

    if (sameContent(src, dstCurrent)) {
      if (opts.dryRun) {
        console.log(`[dry-run] remove duplicate ${path.relative(ROOT, src)} (already in current/)`);
      } else {
        fs.unlinkSync(src);
      }
      continue;
    }

    const dstArchive = path.join(archiveDir, candidate.file);
    if (opts.dryRun) {
      console.log(`[dry-run] move conflict ${path.relative(ROOT, src)} -> ${path.relative(ROOT, dstArchive)}`);
    } else {
      ensureDir(archiveDir);
      fs.renameSync(src, dstArchive);
    }
    movedToArchive += 1;
  }

  console.log(`Organized ${candidates.length} top-level artifact file(s).`);
  console.log(`  Moved to current/: ${movedToCurrent}`);
  console.log(`  Moved to archive/: ${movedToArchive}`);
  if (opts.dryRun) console.log('  No files were changed (--dry-run).');
}

main();
