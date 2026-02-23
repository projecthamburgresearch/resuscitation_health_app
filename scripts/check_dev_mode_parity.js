#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const APP_DIR = path.join(ROOT, 'app');
const DEV_MODE_DIR = path.join(APP_DIR, 'dev-mode');
const HTML_FILE_RE = /\.html?$/i;

function parseArgs(argv) {
  const out = { allowExtraDev: false };
  for (const arg of argv) {
    if (arg === '--allow-extra-dev') out.allowExtraDev = true;
    else if (arg === '--help' || arg === '-h') {
      console.log(`
Usage:
  node scripts/check_dev_mode_parity.js
  node scripts/check_dev_mode_parity.js --allow-extra-dev

By default parity is strict:
  - main pages missing in dev-mode => fail
  - extra dev-mode pages not in main => fail
`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }
  return out;
}

function normalizeSlugFromHtmlRel(relFile) {
  const rel = String(relFile || '').replace(/\\/g, '/');
  const noExt = rel.replace(/\.html?$/i, '');

  if (rel.toLowerCase() === 'index.html') return '';
  if (rel.toLowerCase() === 'resuscitation_app_complete.html') return '';

  if (/\/index$/i.test(noExt)) {
    return noExt.replace(/\/index$/i, '').replace(/^\/+/, '').replace(/\/+$/, '');
  }

  return noExt.replace(/^\/+/, '').replace(/\/+$/, '');
}

function discoverPages(dir, baseRelDir, fsModule = fs, skipDirs = []) {
  const pages = new Set();

  function walk(currentDir) {
    if (!fsModule.existsSync(currentDir)) return;
    const entries = fsModule.readdirSync(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const abs = path.join(currentDir, entry.name);

      if (entry.isDirectory()) {
        if (entry.name.startsWith('.')) continue;
        if (skipDirs.includes(entry.name)) continue;
        walk(abs);
        continue;
      }

      if (!entry.isFile()) continue;
      if (!HTML_FILE_RE.test(entry.name)) continue;

      const rel = path.relative(baseRelDir, abs).replace(/\\/g, '/');
      const slug = normalizeSlugFromHtmlRel(rel);
      pages.add(slug);
    }
  }

  if (!fsModule.existsSync(dir)) return [];
  walk(dir);
  return Array.from(pages).sort();
}

function calculateParity(mainPages, devPages, opts = { allowExtraDev: false }) {
  const mainSet = new Set(mainPages);
  const devSet = new Set(devPages);

  const missingInDev = mainPages.filter((slug) => !devSet.has(slug));
  const extraInDev = devPages.filter((slug) => !mainSet.has(slug));

  const failForMissing = missingInDev.length > 0;
  const failForExtra = !opts.allowExtraDev && extraInDev.length > 0;
  const failed = failForMissing || failForExtra;

  return {
    success: !failed,
    missingInDev,
    extraInDev,
    failForMissing,
    failForExtra
  };
}

function main() {
  const opts = parseArgs(process.argv.slice(2));

  if (!fs.existsSync(APP_DIR)) {
    console.error('Missing app directory.');
    process.exit(1);
  }
  if (!fs.existsSync(DEV_MODE_DIR)) {
    console.error('Missing app/dev-mode directory.');
    process.exit(1);
  }

  const mainPages = discoverPages(APP_DIR, APP_DIR, fs, ['dev-mode']);
  const devPages = discoverPages(DEV_MODE_DIR, DEV_MODE_DIR, fs, []);

  const result = calculateParity(mainPages, devPages, opts);

  console.log('\nDev-Mode Parity Check');
  console.log(`  Main pages   : ${mainPages.length}`);
  console.log(`  Dev pages    : ${devPages.length}`);
  console.log(`  Missing in dev-mode : ${result.missingInDev.length}`);
  console.log(`  Extra in dev-mode   : ${result.extraInDev.length}`);

  if (result.missingInDev.length > 0) {
    console.log('\nMissing in dev-mode:');
    for (const slug of result.missingInDev) console.log(`  - ${slug || 'home'}`);
  }

  if (result.extraInDev.length > 0) {
    console.log('\nExtra in dev-mode (no matching main page):');
    for (const slug of result.extraInDev) console.log(`  - ${slug || 'home'}`);
  }

  if (!result.success) {
    console.log('\nParity status: FAIL');
    if (result.failForExtra) console.log('Reason: extra dev-mode pages are not allowed in strict mode.');
  } else {
    console.log('\nParity status: PASS');
  }

  console.log('');
  if (!result.success) process.exit(1);
}

if (require.main === module) {
  main();
}

module.exports = {
  normalizeSlugFromHtmlRel,
  discoverPages,
  calculateParity,
  APP_DIR,
  DEV_MODE_DIR
};
