#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const APPENDIX_ROOT = path.join(ROOT, 'appendix');
const SCAN_ROOT = path.join(APPENDIX_ROOT, 'scans_outputs');
const LEGACY_SCAN_ROOT = path.join(APPENDIX_ROOT, 'scans');
const RUNS_DIR = path.join(SCAN_ROOT, 'runs');
const CURRENT_DIR = path.join(SCAN_ROOT, 'current');
const ARCHIVE_DIR = path.join(SCAN_ROOT, 'archive');

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function parseLegacyArtifact(fileName) {
  const scanOrDiff = fileName.match(/^(\d{8}-\d{4})-(.+)-(scan|diff)\.json$/);
  if (scanOrDiff) {
    return {
      timestamp: scanOrDiff[1],
      targetName: `${scanOrDiff[2]}-${scanOrDiff[3]}.json`,
      kind: scanOrDiff[3],
    };
  }

  const coverage = fileName.match(/^(\d{8}-\d{4})-scan-coverage-report\.json$/);
  if (coverage) {
    return {
      timestamp: coverage[1],
      targetName: 'scan-coverage-report.json',
      kind: 'coverage',
    };
  }
  return null;
}

function sameContent(fileA, fileB) {
  try {
    const a = fs.readFileSync(fileA);
    const b = fs.readFileSync(fileB);
    return a.equals(b);
  } catch {
    return false;
  }
}

function collectLegacyCandidates(dirPath) {
  if (!fs.existsSync(dirPath)) return [];
  return fs.readdirSync(dirPath, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .map((name) => ({
      sourceDir: dirPath,
      fileName: name,
      parsed: parseLegacyArtifact(name),
    }))
    .filter((row) => row.parsed);
}

function collectLegacyCurrent(dirPath) {
  if (!fs.existsSync(dirPath)) return [];
  const currentDir = path.join(dirPath, 'current');
  if (!fs.existsSync(currentDir)) return [];
  return fs.readdirSync(currentDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && /\.json$/i.test(entry.name))
    .map((entry) => ({
      sourceDir: currentDir,
      fileName: entry.name,
      parsed: null,
      isCurrentSnapshot: true,
    }));
}

function refreshCurrentFromRuns() {
  ensureDir(CURRENT_DIR);
  if (!fs.existsSync(RUNS_DIR)) return 0;

  const runDirs = fs.readdirSync(RUNS_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();

  const latestByName = new Map();
  for (const runName of runDirs) {
    const runPath = path.join(RUNS_DIR, runName);
    const files = fs.readdirSync(runPath, { withFileTypes: true })
      .filter((entry) => entry.isFile())
      .map((entry) => entry.name)
      .filter((name) => /\.json$/i.test(name));
    for (const fileName of files) {
      latestByName.set(fileName, path.join(runPath, fileName));
    }
  }

  for (const [fileName, srcPath] of latestByName.entries()) {
    fs.copyFileSync(srcPath, path.join(CURRENT_DIR, fileName));
  }
  return latestByName.size;
}

function main() {
  if (!fs.existsSync(APPENDIX_ROOT)) {
    console.error('appendix/ directory not found.');
    process.exit(1);
  }

  ensureDir(SCAN_ROOT);
  ensureDir(RUNS_DIR);
  ensureDir(CURRENT_DIR);
  ensureDir(ARCHIVE_DIR);

  const candidates = [
    ...collectLegacyCandidates(APPENDIX_ROOT),
    ...collectLegacyCandidates(SCAN_ROOT),
    ...collectLegacyCandidates(LEGACY_SCAN_ROOT),
    ...collectLegacyCurrent(LEGACY_SCAN_ROOT),
  ];

  if (candidates.length === 0) {
    const currentCount = refreshCurrentFromRuns();
    console.log(`No legacy scan artifacts to move. Refreshed ${currentCount} current snapshot file(s).`);
    return;
  }

  const conflictDir = path.join(ARCHIVE_DIR, `conflicts-${nowStamp()}`);
  let movedToRuns = 0;
  let removedDuplicates = 0;
  let movedConflicts = 0;

  for (const row of candidates) {
    const src = path.join(row.sourceDir, row.fileName);
    const dst = row.isCurrentSnapshot
      ? path.join(CURRENT_DIR, row.fileName)
      : path.join(RUNS_DIR, row.parsed.timestamp, row.parsed.targetName);
    ensureDir(path.dirname(dst));

    if (!fs.existsSync(dst)) {
      fs.renameSync(src, dst);
      movedToRuns += 1;
      continue;
    }

    if (sameContent(src, dst)) {
      fs.unlinkSync(src);
      removedDuplicates += 1;
      continue;
    }

    ensureDir(conflictDir);
    let conflictName = row.fileName;
    let counter = 1;
    while (fs.existsSync(path.join(conflictDir, conflictName))) {
      const ext = path.extname(row.fileName);
      const base = row.fileName.slice(0, row.fileName.length - ext.length);
      conflictName = `${base}-conflict${counter}${ext}`;
      counter += 1;
    }
    fs.renameSync(src, path.join(conflictDir, conflictName));
    movedConflicts += 1;
  }

  const currentCount = refreshCurrentFromRuns();

  console.log('Scan output organization complete.');
  console.log(`  Migrated to runs/: ${movedToRuns}`);
  console.log(`  Removed duplicates: ${removedDuplicates}`);
  console.log(`  Moved conflicts   : ${movedConflicts}`);
  console.log(`  Current snapshots : ${currentCount}`);
  console.log(`  Runs dir          : ${path.relative(ROOT, RUNS_DIR)}`);
  console.log(`  Current dir       : ${path.relative(ROOT, CURRENT_DIR)}`);
  if (movedConflicts > 0) console.log(`  Conflict archive  : ${path.relative(ROOT, conflictDir)}`);
}

main();
