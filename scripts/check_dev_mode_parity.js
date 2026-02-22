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

function discoverMainPages() {
  const pages = new Set();

  function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const abs = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        if (entry.name.startsWith('.')) continue;
        if (entry.name === 'dev-mode') continue;
        walk(abs);
        continue;
      }

      if (!entry.isFile()) continue;
      if (!HTML_FILE_RE.test(entry.name)) continue;

      const rel = path.relative(APP_DIR, abs).replace(/\\/g, '/');
      const slug = normalizeSlugFromHtmlRel(rel);
      pages.add(slug);
    }
  }

  if (!fs.existsSync(APP_DIR)) return [];
  walk(APP_DIR);
  return Array.from(pages).sort();
}

function discoverDevModePages() {
  const pages = new Set();

  function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const abs = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        if (entry.name.startsWith('.')) continue;
        walk(abs);
        continue;
      }

      if (!entry.isFile()) continue;
      if (!HTML_FILE_RE.test(entry.name)) continue;

      const rel = path.relative(DEV_MODE_DIR, abs).replace(/\\/g, '/');
      const slug = normalizeSlugFromHtmlRel(rel);
      pages.add(slug);
    }
  }

  if (!fs.existsSync(DEV_MODE_DIR)) return [];
  walk(DEV_MODE_DIR);
  return Array.from(pages).sort();
}

function label(slug) {
  return slug || 'home';
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

  const mainPages = discoverMainPages();
  const devPages = discoverDevModePages();

  const mainSet = new Set(mainPages);
  const devSet = new Set(devPages);

  const missingInDev = mainPages.filter((slug) => !devSet.has(slug));
  const extraInDev = devPages.filter((slug) => !mainSet.has(slug));

  console.log('\nDev-Mode Parity Check');
  console.log(`  Main pages   : ${mainPages.length}`);
  console.log(`  Dev pages    : ${devPages.length}`);
  console.log(`  Missing in dev-mode : ${missingInDev.length}`);
  console.log(`  Extra in dev-mode   : ${extraInDev.length}`);

  if (missingInDev.length > 0) {
    console.log('\nMissing in dev-mode:');
    for (const slug of missingInDev) console.log(`  - ${label(slug)}`);
  }

  if (extraInDev.length > 0) {
    console.log('\nExtra in dev-mode (no matching main page):');
    for (const slug of extraInDev) console.log(`  - ${label(slug)}`);
  }

  const failForMissing = missingInDev.length > 0;
  const failForExtra = !opts.allowExtraDev && extraInDev.length > 0;
  const failed = failForMissing || failForExtra;

  if (failed) {
    console.log('\nParity status: FAIL');
    if (failForExtra) console.log('Reason: extra dev-mode pages are not allowed in strict mode.');
  } else {
    console.log('\nParity status: PASS');
  }

  console.log('');
  if (failed) process.exit(1);
}

main();
