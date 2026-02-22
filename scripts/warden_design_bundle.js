#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const { URL } = require('url');
const { spawn } = require('child_process');
let chromium = null;

const ROOT = process.cwd();
const APP_DIR = path.join(ROOT, 'app');
const PAGE_FILE_RE = /\.html?$/i;

const DESIGN_ROOT = path.resolve(ROOT, process.env.WARDEN_DESIGN_ROOT || 'appendix/guidance/warden/design');
const DESIGN_RUNS_DIR = path.join(DESIGN_ROOT, 'runs');
const BLUEPRINT_RUNS_DIR = path.resolve(
  ROOT,
  process.env.WARDEN_BLUEPRINT_RUNS_DIR || 'appendix/guidance/warden/blueprint_outputs/runs',
);
const SCAN_RUNS_DIR = path.resolve(
  ROOT,
  process.env.WARDEN_SCAN_RUNS_DIR || 'appendix/guidance/warden/scans_outputs/runs',
);

const DEFAULT_BASE_URL = process.env.WARDEN_DESIGN_BASE_URL || 'http://127.0.0.1:3000';
const DEFAULT_MODE = 'main';
const DEFAULT_TIMEOUT_SECONDS = 180;
const DEFAULT_VIEWPORT = { width: 390, height: 844 };
const DEFAULT_CAPTURE_ATTEMPTS = Number(process.env.WARDEN_CAPTURE_ATTEMPTS || 3);
const DEFAULT_STABILIZE_MS = Number(process.env.WARDEN_STABILIZE_MS || 1800);
const DEFAULT_WARMUP_ROUNDS = Number(process.env.WARDEN_WARMUP_ROUNDS || 2);
const DEFAULT_SPLIT_SUBCOLUMNS = Number(process.env.WARDEN_SPLIT_SUBCOLUMNS || 3);
const DEFAULT_DYNAMIC_MAIN = process.env.WARDEN_DYNAMIC_MAIN === '0' ? false : true;
const DEFAULT_DYNAMIC_MAX_TRANSITIONS = Number(process.env.WARDEN_DYNAMIC_MAX_TRANSITIONS || 80);
const DEFAULT_DYNAMIC_SETTLE_MS = Number(process.env.WARDEN_DYNAMIC_SETTLE_MS || 220);
const MAX_PAGE_HEIGHT_FOR_CLIPS = 12000;
const ERROR_PATTERNS = [
  'runtime chunkloaderror',
  'failed to load chunk',
  'chunkloaderror',
  'application error:',
  'a client-side exception has occurred',
  'nextjs 16.1.6',
];

function ensurePlaywrightChromium() {
  if (chromium) return chromium;
  try {
    ({ chromium } = require('playwright'));
    return chromium;
  } catch (err) {
    const detail = err && err.message ? err.message : String(err);
    throw new Error(`Missing Playwright dependency. Run "npm install" in this repo. (${detail})`);
  }
}

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function rel(filePath) {
  return path.relative(ROOT, filePath) || '.';
}

function slugify(input) {
  return String(input || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'item';
}

function parseViewport(spec) {
  const text = String(spec || '').trim().toLowerCase();
  const match = text.match(/^(\d{2,5})x(\d{2,5})$/);
  if (!match) throw new Error(`Invalid viewport "${spec}". Use WIDTHxHEIGHT (example: 1440x900).`);
  const width = Number(match[1]);
  const height = Number(match[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width < 200 || height < 200) {
    throw new Error(`Invalid viewport "${spec}". Width/height must be >= 200.`);
  }
  return { width, height };
}

function viewportKey(vp) {
  return `${vp.width}x${vp.height}`;
}

function parseArgs(argv) {
  const out = {
    blueprintRun: null,
    scanRun: null,
    baseUrl: DEFAULT_BASE_URL,
    mode: DEFAULT_MODE,
    pagesSpec: null,
    viewportSpecs: [],
    keepDev: false,
    devTimeoutSeconds: DEFAULT_TIMEOUT_SECONDS,
    outputDir: null,
    captureAttempts: DEFAULT_CAPTURE_ATTEMPTS,
    stabilizeMs: DEFAULT_STABILIZE_MS,
    warmupRounds: DEFAULT_WARMUP_ROUNDS,
    splitMain: true,
    splitSubcolumns: DEFAULT_SPLIT_SUBCOLUMNS,
    dynamicMain: DEFAULT_DYNAMIC_MAIN,
    dynamicMaxTransitions: DEFAULT_DYNAMIC_MAX_TRANSITIONS,
    dynamicSettleMs: DEFAULT_DYNAMIC_SETTLE_MS,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];

    if (arg === '--blueprint-run') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --blueprint-run');
      out.blueprintRun = next;
      i += 1;
    } else if (arg.startsWith('--blueprint-run=')) {
      out.blueprintRun = arg.split('=', 2)[1];
    } else if (arg === '--scan-run') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --scan-run');
      out.scanRun = next;
      i += 1;
    } else if (arg.startsWith('--scan-run=')) {
      out.scanRun = arg.split('=', 2)[1];
    } else if (arg === '--base-url') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --base-url');
      out.baseUrl = next;
      i += 1;
    } else if (arg.startsWith('--base-url=')) {
      out.baseUrl = arg.split('=', 2)[1];
    } else if (arg === '--mode') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --mode');
      out.mode = next;
      i += 1;
    } else if (arg.startsWith('--mode=')) {
      out.mode = arg.split('=', 2)[1];
    } else if (arg === '--pages') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --pages');
      out.pagesSpec = next;
      i += 1;
    } else if (arg.startsWith('--pages=')) {
      out.pagesSpec = arg.split('=', 2)[1];
    } else if (arg === '--viewport') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --viewport');
      out.viewportSpecs.push(next);
      i += 1;
    } else if (arg.startsWith('--viewport=')) {
      out.viewportSpecs.push(arg.split('=', 2)[1]);
    } else if (arg === '--keep-dev') {
      out.keepDev = true;
    } else if (arg === '--dev-timeout') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --dev-timeout');
      out.devTimeoutSeconds = Number(next);
      i += 1;
    } else if (arg.startsWith('--dev-timeout=')) {
      out.devTimeoutSeconds = Number(arg.split('=', 2)[1]);
    } else if (arg === '--capture-attempts') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --capture-attempts');
      out.captureAttempts = Number(next);
      i += 1;
    } else if (arg.startsWith('--capture-attempts=')) {
      out.captureAttempts = Number(arg.split('=', 2)[1]);
    } else if (arg === '--stabilize-ms') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --stabilize-ms');
      out.stabilizeMs = Number(next);
      i += 1;
    } else if (arg.startsWith('--stabilize-ms=')) {
      out.stabilizeMs = Number(arg.split('=', 2)[1]);
    } else if (arg === '--warmup-rounds') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --warmup-rounds');
      out.warmupRounds = Number(next);
      i += 1;
    } else if (arg.startsWith('--warmup-rounds=')) {
      out.warmupRounds = Number(arg.split('=', 2)[1]);
    } else if (arg === '--split-main') {
      out.splitMain = true;
    } else if (arg === '--no-split-main') {
      out.splitMain = false;
    } else if (arg === '--dynamic-main') {
      out.dynamicMain = true;
    } else if (arg === '--no-dynamic-main') {
      out.dynamicMain = false;
    } else if (arg === '--split-subcolumns') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --split-subcolumns');
      out.splitSubcolumns = Number(next);
      i += 1;
    } else if (arg.startsWith('--split-subcolumns=')) {
      out.splitSubcolumns = Number(arg.split('=', 2)[1]);
    } else if (arg === '--dynamic-max-transitions') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --dynamic-max-transitions');
      out.dynamicMaxTransitions = Number(next);
      i += 1;
    } else if (arg.startsWith('--dynamic-max-transitions=')) {
      out.dynamicMaxTransitions = Number(arg.split('=', 2)[1]);
    } else if (arg === '--dynamic-settle-ms') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --dynamic-settle-ms');
      out.dynamicSettleMs = Number(next);
      i += 1;
    } else if (arg.startsWith('--dynamic-settle-ms=')) {
      out.dynamicSettleMs = Number(arg.split('=', 2)[1]);
    } else if (arg === '--output-dir') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --output-dir');
      out.outputDir = next;
      i += 1;
    } else if (arg.startsWith('--output-dir=')) {
      out.outputDir = arg.split('=', 2)[1];
    } else if (arg === '--help' || arg === '-h') {
      console.log(`
Usage:
  node scripts/warden_design_bundle.js
  node scripts/warden_design_bundle.js --blueprint-run 20260221-084935-warden --scan-run 20260221-085017
  node scripts/warden_design_bundle.js --mode main --pages home
  node scripts/warden_design_bundle.js --mode main --viewport 390x844 --viewport 844x390

Flags:
  --blueprint-run ID|PATH   Blueprint run folder name or path (default: latest)
  --scan-run ID|PATH        Scan run folder name or path (default: latest)
  --mode MODE               main | both (both aliases to main)
  --pages LIST              all or comma-separated slugs (home/about/events)
  --viewport WxH            Repeatable screenshot viewport(s), default 390x844
  --base-url URL            App URL (default: ${DEFAULT_BASE_URL})
  --keep-dev                Keep dev server running if script started it
  --dev-timeout SEC         Dev readiness timeout (default: ${DEFAULT_TIMEOUT_SECONDS})
  --capture-attempts N      Per-route screenshot retries (default: ${DEFAULT_CAPTURE_ATTEMPTS})
  --stabilize-ms MS         Settling wait after page-ready (default: ${DEFAULT_STABILIZE_MS})
  --warmup-rounds N         Route warmup rounds before capture (default: ${DEFAULT_WARMUP_ROUNDS})
  --split-main              Enable section/column split screenshots for main mode (default)
  --no-split-main           Disable split screenshots
  --dynamic-main            Enable dynamic transition capture for home/main (default)
  --no-dynamic-main         Disable dynamic transition capture
  --dynamic-max-transitions Max dynamic transitions to capture per viewport (default: ${DEFAULT_DYNAMIC_MAX_TRANSITIONS})
  --dynamic-settle-ms MS    Wait after dynamic transition before shot (default: ${DEFAULT_DYNAMIC_SETTLE_MS})
  --split-subcolumns N      Max section crops per detected content column (default: ${DEFAULT_SPLIT_SUBCOLUMNS})
  --output-dir PATH         Override bundle output directory

Output:
  ${rel(path.join(DESIGN_ROOT, 'runs'))}/<timestamp>/
    - bundle_manifest.json
    - bundle_summary.md
    - linked/blueprint_run (symlink)
    - linked/scan_run (symlink)
    - screenshots/static/main/*.png
    - screenshots/dynamic/main/*.png
    - splits/static/main/<page>-<viewport>/* (when split-main enabled)
    - splits/dynamic/main/<transition>-<viewport>/* (when split-main enabled)
`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }

  const normalizedMode = String(out.mode || '').toLowerCase().trim();
  if (!['main', 'both'].includes(normalizedMode)) {
    throw new Error(`Invalid --mode "${out.mode}". Use main or both.`);
  }
  out.mode = normalizedMode === 'both' ? 'main' : normalizedMode;

  if (!Number.isFinite(out.devTimeoutSeconds) || out.devTimeoutSeconds <= 0) {
    throw new Error('Invalid --dev-timeout value. Must be a positive number.');
  }
  if (!Number.isFinite(out.captureAttempts) || out.captureAttempts < 1) {
    throw new Error('Invalid --capture-attempts value. Must be >= 1.');
  }
  if (!Number.isFinite(out.stabilizeMs) || out.stabilizeMs < 0) {
    throw new Error('Invalid --stabilize-ms value. Must be >= 0.');
  }
  if (!Number.isFinite(out.warmupRounds) || out.warmupRounds < 0) {
    throw new Error('Invalid --warmup-rounds value. Must be >= 0.');
  }
  if (!Number.isFinite(out.splitSubcolumns) || out.splitSubcolumns < 0) {
    throw new Error('Invalid --split-subcolumns value. Must be >= 0.');
  }
  if (!Number.isFinite(out.dynamicMaxTransitions) || out.dynamicMaxTransitions < 1) {
    throw new Error('Invalid --dynamic-max-transitions value. Must be >= 1.');
  }
  if (!Number.isFinite(out.dynamicSettleMs) || out.dynamicSettleMs < 0) {
    throw new Error('Invalid --dynamic-settle-ms value. Must be >= 0.');
  }

  const vps = out.viewportSpecs.length > 0
    ? out.viewportSpecs.map(parseViewport)
    : [DEFAULT_VIEWPORT];
  const dedup = new Map();
  for (const vp of vps) dedup.set(viewportKey(vp), vp);
  out.viewports = Array.from(dedup.values());

  return out;
}

function latestDirectory(dirPath) {
  if (!fs.existsSync(dirPath)) return null;
  const dirs = fs.readdirSync(dirPath, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(dirPath, entry.name));
  if (dirs.length === 0) return null;
  dirs.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return dirs[0];
}

function resolveRunDir(baseDir, arg, label) {
  let candidate;
  if (arg) {
    const treatAsPath = arg.includes('/') || arg.includes('\\') || path.isAbsolute(arg);
    candidate = treatAsPath ? path.resolve(ROOT, arg) : path.join(baseDir, arg);
  } else {
    candidate = latestDirectory(baseDir);
  }
  if (!candidate || !fs.existsSync(candidate) || !fs.statSync(candidate).isDirectory()) {
    throw new Error(`${label} run directory not found: ${arg || '(latest)'} under ${rel(baseDir)}`);
  }
  return candidate;
}

function safeReadJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function discoverPages(baseDir) {
  const pages = [];

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
      if (!PAGE_FILE_RE.test(entry.name)) continue;

      const relFile = path.relative(baseDir, abs).replace(/\\/g, '/');
      const noExt = relFile.replace(/\.html?$/i, '');
      let slug = '';
      if (relFile.toLowerCase() === 'index.html' || relFile.toLowerCase() === 'resuscitation_app_complete.html') {
        slug = '';
      } else if (/\/index$/i.test(noExt)) {
        slug = noExt.replace(/\/index$/i, '');
      } else {
        slug = noExt;
      }
      slug = slug.replace(/^\/+/, '').replace(/\/+$/, '');
      if (slug.toLowerCase() === 'home') slug = '';
      pages.push(slug);
    }
  }

  walk(baseDir);
  return Array.from(new Set(pages)).sort();
}

function normalizePageSlug(input) {
  let value = String(input || '').trim();
  if (!value) return '';
  value = value.replace(/^\/+/, '').replace(/\/+$/, '');
  if (value === '' || value === 'home') return '';
  return value;
}

function pageLabel(slug) {
  return slug || 'home';
}

function routePath(slug, mode) {
  if (!slug) return '/';
  return `/${slug}`;
}

function pagesFromScanRun(scanRunDir) {
  const runManifest = safeReadJson(path.join(scanRunDir, 'run_manifest.json'));
  if (runManifest && Array.isArray(runManifest.scans)) {
    return Array.from(new Set(runManifest.scans.map((s) => normalizePageSlug(s.page)).filter((s) => s !== undefined))).sort();
  }

  const rows = fs.readdirSync(scanRunDir, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .filter((name) => /-scan\.json$/i.test(name));

  const pages = [];
  for (const name of rows) {
    const match = name.match(/^(.*?)(?:-\d{2,5}x\d{2,5})?-scan\.json$/i);
    if (!match) continue;
    pages.push(normalizePageSlug(match[1]));
  }
  return Array.from(new Set(pages)).sort();
}

function resolvePages(opts, scanRunDir) {
  const scanPages = pagesFromScanRun(scanRunDir);
  const mainPages = discoverPages(APP_DIR);

  let selected;
  if (!opts.pagesSpec || opts.pagesSpec.trim().toLowerCase() === 'all') {
    selected = scanPages.length > 0 ? scanPages : mainPages;
  } else {
    selected = opts.pagesSpec
      .split(',')
      .map((v) => normalizePageSlug(v))
      .filter((v, idx, arr) => v !== null && arr.indexOf(v) === idx);
  }

  if (selected.length === 0) selected = [''];
  return selected;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function requestUrl(urlStr, timeoutMs = 6000) {
  return new Promise((resolve) => {
    const parsed = new URL(urlStr);
    const lib = parsed.protocol === 'https:' ? https : http;
    const req = lib.request(
      parsed,
      { method: 'GET', timeout: timeoutMs },
      (res) => {
        const status = Number(res.statusCode || 0);
        res.resume();
        resolve({ ok: status >= 200 && status < 400, status });
      },
    );
    req.on('timeout', () => {
      req.destroy(new Error('timeout'));
    });
    req.on('error', () => resolve({ ok: false, status: 0 }));
    req.end();
  });
}

async function isReady(baseUrl, mode) {
  const root = baseUrl.replace(/\/+$/, '');
  const checks = [`${root}/`];

  for (const url of checks) {
    const res = await requestUrl(url);
    if (!res.ok) return false;
  }
  return true;
}

function parsePort(baseUrl) {
  const parsed = new URL(baseUrl);
  if (parsed.port) return Number(parsed.port);
  return parsed.protocol === 'https:' ? 443 : 80;
}

function waitForChildExit(child, timeoutMs) {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      resolve();
    };
    child.once('exit', finish);
    setTimeout(finish, timeoutMs);
  });
}

async function stopDevServer(child) {
  if (!child || child.killed) return;
  child.kill('SIGTERM');
  await waitForChildExit(child, 8000);
  if (!child.killed) {
    try {
      child.kill('SIGKILL');
    } catch {
      // best effort
    }
  }
}

async function ensureDevServer(baseUrl, mode, timeoutSeconds) {
  if (await isReady(baseUrl, mode)) {
    console.log('[Info] Dev server already running; reusing existing process.');
    return { started: false, child: null };
  }

  const port = parsePort(baseUrl);
  console.log(`[Step] Start Dev Server on port ${port}`);
  const child = spawn('npm', ['run', 'dev', '--', '--port', String(port)], {
    cwd: ROOT,
    stdio: 'inherit',
    env: { ...process.env, PORT: String(port) },
  });

  const deadline = Date.now() + timeoutSeconds * 1000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Dev server exited early with code ${child.exitCode}`);
    }
    if (await isReady(baseUrl, mode)) {
      console.log('[Info] Dev server is ready.');
      return { started: true, child };
    }
    await sleep(1000);
  }

  await stopDevServer(child);
  throw new Error(`Dev server not ready within ${timeoutSeconds}s`);
}

function ensureSymlink(targetPath, linkPath) {
  ensureDir(path.dirname(linkPath));
  try {
    if (fs.existsSync(linkPath)) fs.rmSync(linkPath, { recursive: true, force: true });
    const relativeTarget = path.relative(path.dirname(linkPath), targetPath);
    fs.symlinkSync(relativeTarget, linkPath, 'dir');
    return { ok: true, fallbackFile: null };
  } catch {
    const fallbackFile = `${linkPath}.txt`;
    fs.writeFileSync(fallbackFile, `${targetPath}\n`, 'utf8');
    return { ok: false, fallbackFile };
  }
}

function buildRunDir(opts, blueprintRunDir, scanRunDir) {
  if (opts.outputDir) return path.resolve(ROOT, opts.outputDir);
  const stamp = nowStamp();
  const bpName = path.basename(blueprintRunDir);
  const scanName = path.basename(scanRunDir);
  return path.join(DESIGN_RUNS_DIR, `${stamp}__bp-${bpName}__scan-${scanName}`);
}

function summarizeBlueprint(blueprintRunDir) {
  const runMeta = safeReadJson(path.join(blueprintRunDir, 'run_meta.json'));
  const files = fs.readdirSync(blueprintRunDir, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .sort();

  return {
    runDir: rel(blueprintRunDir),
    runName: path.basename(blueprintRunDir),
    runMeta,
    fileCount: files.length,
    files,
  };
}

function summarizeScan(scanRunDir) {
  const runManifest = safeReadJson(path.join(scanRunDir, 'run_manifest.json'));
  const coverageReport = safeReadJson(path.join(scanRunDir, 'scan-coverage-report.json'));
  const files = fs.readdirSync(scanRunDir, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .sort();

  return {
    runDir: rel(scanRunDir),
    runName: path.basename(scanRunDir),
    runManifest,
    coverageReport,
    fileCount: files.length,
    files,
  };
}

function routeUrl(baseUrl, slug, mode) {
  return `${baseUrl.replace(/\/+$/, '')}${routePath(slug, mode)}`;
}

async function warmupRoutes(baseUrl, mode, pages, rounds) {
  if (rounds <= 0) return;
  const modes = ['main'];
  console.log(`[Step] Warmup Routes (${rounds} round${rounds === 1 ? '' : 's'})`);

  for (let round = 1; round <= rounds; round++) {
    for (const currentMode of modes) {
      for (const slug of pages) {
        const url = routeUrl(baseUrl, slug, currentMode);
        const result = await requestUrl(url, 20_000);
        const label = pageLabel(slug);
        if (!result.ok) {
          console.log(`  [warmup] round ${round} ${currentMode} ${label} -> HTTP ${result.status || 'ERR'}`);
        }
        await sleep(80);
      }
    }
  }
}

async function detectRuntimeOverlay(page) {
  const text = await page.evaluate(() => {
    const portal = document.querySelector('nextjs-portal');
    const portalText = portal ? portal.textContent || '' : '';
    const bodyText = document.body ? document.body.innerText || '' : '';
    return `${portalText}\n${bodyText}`.toLowerCase();
  });

  for (const pattern of ERROR_PATTERNS) {
    if (text.includes(pattern)) return pattern;
  }
  return null;
}

async function waitForPageStable(page, mode, stabilizeMs) {
  await page.waitForLoadState('domcontentloaded', { timeout: 45_000 });
  await page.waitForLoadState('networkidle', { timeout: 45_000 }).catch(() => null);

  // Static pages might not include semantic landmarks; require only body readiness.
  await page.waitForSelector('body', { timeout: 45_000 });

  await page.waitForFunction(() => document.readyState === 'complete', null, { timeout: 30_000 }).catch(() => null);
  await page.evaluate(() => (document.fonts && document.fonts.ready ? document.fonts.ready.then(() => true) : true)).catch(() => null);

  if (stabilizeMs > 0) await page.waitForTimeout(stabilizeMs);

  const runtimePattern = await detectRuntimeOverlay(page);
  if (runtimePattern) {
    throw new Error(`Runtime overlay detected (${runtimePattern})`);
  }
}

async function ensureLargeViewportForClips(page, width) {
  const dims = await page.evaluate(() => {
    const docEl = document.documentElement;
    const body = document.body;
    const pageWidth = Math.max(
      docEl ? docEl.scrollWidth : 0,
      docEl ? docEl.clientWidth : 0,
      body ? body.scrollWidth : 0,
      body ? body.clientWidth : 0,
    );
    const pageHeight = Math.max(
      docEl ? docEl.scrollHeight : 0,
      docEl ? docEl.clientHeight : 0,
      body ? body.scrollHeight : 0,
      body ? body.clientHeight : 0,
    );
    return { pageWidth, pageHeight };
  });

  const targetHeight = Math.max(DEFAULT_VIEWPORT.height, Math.min(MAX_PAGE_HEIGHT_FOR_CLIPS, dims.pageHeight + 120));
  await page.setViewportSize({ width, height: targetHeight });
  await page.waitForTimeout(200);

  return {
    pageWidth: Math.max(width, dims.pageWidth),
    pageHeight: Math.max(targetHeight, dims.pageHeight),
  };
}

function geomOf(el) {
  const g = el && el.geometry;
  if (!g) return null;
  const x = Number(g.x);
  const y = Number(g.y);
  const width = Number(g.width);
  const height = Number(g.height);
  if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(width) || !Number.isFinite(height)) return null;
  if (width <= 0 || height <= 0) return null;
  return { x, y, width, height };
}

function area(rect) {
  return rect.width * rect.height;
}

function centerX(rect) {
  return rect.x + rect.width / 2;
}

function unionRects(rects) {
  if (!rects || rects.length === 0) return null;
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const rect of rects) {
    minX = Math.min(minX, rect.x);
    minY = Math.min(minY, rect.y);
    maxX = Math.max(maxX, rect.x + rect.width);
    maxY = Math.max(maxY, rect.y + rect.height);
  }
  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

function intersectY(rect, yStart, yEnd) {
  const rStart = rect.y;
  const rEnd = rect.y + rect.height;
  return rEnd > yStart && rStart < yEnd;
}

function clipToBounds(rect, bounds) {
  const x = Math.max(0, Math.min(rect.x, bounds.pageWidth - 1));
  const y = Math.max(0, Math.min(rect.y, bounds.pageHeight - 1));
  const maxW = Math.max(1, bounds.pageWidth - x);
  const maxH = Math.max(1, bounds.pageHeight - y);
  const width = Math.min(rect.width, maxW);
  const height = Math.min(rect.height, maxH);

  const round = {
    x: Math.floor(x),
    y: Math.floor(y),
    width: Math.max(1, Math.floor(width)),
    height: Math.max(1, Math.floor(height)),
  };

  if (round.width < 12 || round.height < 12) return null;
  return round;
}

function findScanJsonForPage(scanRunDir, pageName, viewportText) {
  const candidates = [
    `${pageName}-${viewportText}-scan.json`,
    `${pageName}-scan.json`,
  ];
  for (const file of candidates) {
    const filePath = path.join(scanRunDir, file);
    if (!fs.existsSync(filePath)) continue;
    const parsed = safeReadJson(filePath);
    if (parsed && Array.isArray(parsed.elements)) {
      return { filePath, fileName: file, json: parsed };
    }
  }
  return null;
}

function chooseLargestElement(elements, predicate) {
  let chosen = null;
  for (const el of elements) {
    if (!predicate(el)) continue;
    const rect = geomOf(el);
    if (!rect) continue;
    const candidate = { el, rect, area: area(rect) };
    if (!chosen || candidate.area > chosen.area) chosen = candidate;
  }
  return chosen;
}

function buildMainSplitPlan(scanJson, subcolumnLimit) {
  const elements = Array.isArray(scanJson.elements) ? scanJson.elements : [];
  const pageWidth = Number(scanJson.meta?.pageSize?.width) || 1440;
  const pageHeight = Number(scanJson.meta?.pageSize?.height) || 9000;

  const header = chooseLargestElement(elements, (el) => el.tag === 'header');
  const footer = chooseLargestElement(elements, (el) => el.tag === 'footer');
  const main = chooseLargestElement(elements, (el) => el.tag === 'main');

  const mainRect = main ? main.rect : {
    x: 0,
    y: header ? header.rect.y + header.rect.height : 0,
    width: pageWidth,
    height: Math.max(200, pageHeight - (header ? header.rect.y + header.rect.height : 0) - (footer ? footer.rect.height : 0)),
  };

  const sectionCandidates = elements
    .map((el, index) => ({
      index,
      el,
      rect: geomOf(el),
    }))
    .filter((row) => row.rect)
    .filter((row) => row.el.tag === 'section')
    .filter((row) => row.rect.width >= mainRect.width * 0.25)
    .filter((row) => row.rect.height >= 90)
    .filter((row) => intersectY(row.rect, mainRect.y, mainRect.y + mainRect.height))
    .sort((a, b) => a.rect.y - b.rect.y || b.rect.width * b.rect.height - a.rect.width * a.rect.height);

  let hero = sectionCandidates.find((row) => /hero/i.test(String(row.el.label || '')));
  if (!hero) {
    hero = sectionCandidates.find((row) => row.rect.y <= mainRect.y + Math.max(280, mainRect.height * 0.22));
  }

  const contentTop = hero ? Math.max(mainRect.y, hero.rect.y + hero.rect.height) : mainRect.y;
  const contentBottomCandidate = footer ? footer.rect.y : mainRect.y + mainRect.height;
  const contentBottom = Math.max(contentTop + 80, Math.min(contentBottomCandidate, mainRect.y + mainRect.height));
  const contentRect = {
    x: mainRect.x,
    y: contentTop,
    width: mainRect.width,
    height: Math.max(80, contentBottom - contentTop),
  };

  const contentSections = sectionCandidates
    .filter((row) => intersectY(row.rect, contentRect.y, contentRect.y + contentRect.height))
    .filter((row) => row.rect.y >= contentRect.y - 2)
    .filter((row) => row.rect.width <= mainRect.width * 0.98);

  const clusters = [];
  const clusterThreshold = Math.max(120, mainRect.width * 0.18);

  for (const row of contentSections) {
    const cx = centerX(row.rect);
    let best = null;
    let bestDist = Number.POSITIVE_INFINITY;

    for (const cluster of clusters) {
      const dist = Math.abs(cluster.centerX - cx);
      if (dist < bestDist) {
        bestDist = dist;
        best = cluster;
      }
    }

    if (!best || bestDist > clusterThreshold) {
      clusters.push({ centerX: cx, items: [row] });
      continue;
    }

    best.items.push(row);
    best.centerX = best.items.reduce((sum, item) => sum + centerX(item.rect), 0) / best.items.length;
  }

  clusters.sort((a, b) => a.centerX - b.centerX);

  const regions = [];
  if (header) {
    regions.push({
      id: 'header',
      type: 'header',
      label: String(header.el.label || 'header'),
      rect: header.rect,
      sourceIndex: elements.indexOf(header.el),
    });
  }
  if (hero) {
    regions.push({
      id: 'hero',
      type: 'hero',
      label: String(hero.el.label || 'hero'),
      rect: hero.rect,
      sourceIndex: hero.index,
    });
  }

  regions.push({
    id: 'content',
    type: 'content',
    label: 'content-region',
    rect: contentRect,
    sourceIndex: null,
  });

  if (footer) {
    regions.push({
      id: 'footer',
      type: 'footer',
      label: String(footer.el.label || 'footer'),
      rect: footer.rect,
      sourceIndex: elements.indexOf(footer.el),
    });
  }

  if (clusters.length > 0) {
    for (let i = 0; i < clusters.length; i++) {
      const cluster = clusters[i];
      const rect = unionRects(cluster.items.map((item) => item.rect));
      if (!rect) continue;

      const columnId = `content-column-${i + 1}`;
      regions.push({
        id: columnId,
        type: 'content-column',
        label: `content column ${i + 1}`,
        rect,
        sourceIndex: null,
      });

      if (subcolumnLimit > 0) {
        const sub = [...cluster.items]
          .sort((a, b) => area(b.rect) - area(a.rect))
          .slice(0, subcolumnLimit);

        for (let j = 0; j < sub.length; j++) {
          const item = sub[j];
          const sourceLabel = String(item.el.label || `${item.el.tag || 'section'}-${item.index}`);
          regions.push({
            id: `${columnId}-sub-${j + 1}-${slugify(sourceLabel).slice(0, 32)}`,
            type: 'content-subcolumn',
            label: sourceLabel,
            rect: item.rect,
            sourceIndex: item.index,
            parentId: columnId,
          });
        }
      }
    }
  }

  return {
    pageSize: { width: pageWidth, height: pageHeight },
    regions,
    clusters: clusters.map((cluster, index) => ({
      index: index + 1,
      centerX: cluster.centerX,
      itemCount: cluster.items.length,
    })),
  };
}

async function buildAppMainSplitPlanFromDom(page) {
  const evaluated = await page.evaluate(() => {
    const defs = [
      { id: 'app-shell', type: 'app-shell', label: '#app', selector: '#app' },
      { id: 'header', type: 'header', label: 'header', selector: 'header' },
      { id: 'incoming', type: 'incoming', label: '#zone-top', selector: '#zone-top' },
      { id: 'wheel-stage', type: 'wheel-stage', label: '#zone-middle', selector: '#zone-middle' },
      { id: 'wheel-ring', type: 'wheel-ring', label: '#wheel', selector: '#wheel' },
      { id: 'current-card', type: 'current-card', label: '#active-card', selector: '#active-card' },
      { id: 'wheel-knob', type: 'wheel-knob', label: '#knob', selector: '#knob' },
      { id: 'previous', type: 'previous', label: '#zone-bottom', selector: '#zone-bottom' },
      { id: 'footer', type: 'footer', label: 'footer', selector: 'footer' },
      { id: 'checklist', type: 'checklist', label: '#checklist-area', selector: '#checklist-area' },
      { id: 'timer', type: 'timer', label: '#timer', selector: '#timer' },
    ];

    function toRect(el) {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      if (!Number.isFinite(r.width) || !Number.isFinite(r.height) || r.width <= 2 || r.height <= 2) {
        return null;
      }
      return {
        x: window.scrollX + r.left,
        y: window.scrollY + r.top,
        width: r.width,
        height: r.height,
      };
    }

    const regions = [];
    defs.forEach((def, index) => {
      const el = document.querySelector(def.selector);
      const rect = toRect(el);
      if (!rect) return;
      regions.push({
        id: def.id,
        type: def.type,
        label: def.label,
        selector: def.selector,
        sourceIndex: index,
        rect,
      });
    });

    const docEl = document.documentElement;
    const body = document.body;
    const pageWidth = Math.max(
      docEl ? docEl.scrollWidth : 0,
      docEl ? docEl.clientWidth : 0,
      body ? body.scrollWidth : 0,
      body ? body.clientWidth : 0,
    );
    const pageHeight = Math.max(
      docEl ? docEl.scrollHeight : 0,
      docEl ? docEl.clientHeight : 0,
      body ? body.scrollHeight : 0,
      body ? body.clientHeight : 0,
    );

    return {
      pageSize: { width: pageWidth, height: pageHeight },
      regions,
    };
  });

  if (!evaluated || !Array.isArray(evaluated.regions) || evaluated.regions.length < 5) return null;
  return {
    pageSize: evaluated.pageSize,
    regions: evaluated.regions,
    clusters: [],
  };
}

async function captureMainSplitScreenshots({
  page,
  runDir,
  pageName,
  viewportText,
  scanRunDir,
  pageBounds,
  splitSubcolumns,
  splitCategory = 'static',
  splitKey = null,
  transitionStage = null,
  transition = null,
  stateSnapshot = null,
}) {
  const key = splitKey || `${pageName}-${viewportText}`;
  const splitDir = path.join(runDir, 'splits', splitCategory, 'main', key);
  const imagesDir = path.join(splitDir, 'images');
  ensureDir(imagesDir);

  let sourceType = null;
  let sourceScan = null;
  let plan = null;
  const appPlan = await buildAppMainSplitPlanFromDom(page);
  if (appPlan && pageName === 'home') {
    sourceType = 'app-dom';
    plan = appPlan;
  } else {
    const scan = findScanJsonForPage(scanRunDir, pageName, viewportText);
    if (!scan) {
      return {
        ok: false,
        reason: `No scan JSON found for page=${pageName} viewport=${viewportText} and no app DOM plan available`,
        splitDir: null,
        mapFile: null,
        extracted: 0,
        failed: 0,
        regions: [],
      };
    }
    sourceType = 'scan-json';
    sourceScan = scan;
    plan = buildMainSplitPlan(scan.json, splitSubcolumns);
  }

  const regionRows = [];
  let extracted = 0;
  let failed = 0;

  for (const region of plan.regions) {
    const clipped = clipToBounds(region.rect, pageBounds);
    const fileName = `${region.id}.png`;
    const outputPath = path.join(imagesDir, fileName);

    const row = {
      id: region.id,
      type: region.type,
      label: region.label,
      selector: region.selector || null,
      parentId: region.parentId || null,
      sourceIndex: region.sourceIndex,
      geometry: {
        x: region.rect.x,
        y: region.rect.y,
        width: region.rect.width,
        height: region.rect.height,
      },
      clippedGeometry: clipped,
      file: clipped ? rel(outputPath) : null,
      ok: false,
      error: null,
    };

    if (!clipped) {
      row.error = 'Region clip is out of bounds or too small';
      failed += 1;
      regionRows.push(row);
      continue;
    }

    try {
      await page.screenshot({ path: outputPath, clip: clipped });
      row.ok = true;
      extracted += 1;
    } catch (err) {
      row.error = err && err.message ? err.message : String(err);
      failed += 1;
    }

    regionRows.push(row);
  }

  const map = {
    generatedAt: new Date().toISOString(),
    source: {
      scanRunDir: rel(scanRunDir),
      sourceType,
      scanFile: sourceScan ? rel(sourceScan.filePath) : null,
      page: pageName,
      splitCategory,
      transitionStage: transitionStage || null,
      transition: transition || null,
      stateSnapshot: stateSnapshot || null,
      viewport: viewportText,
      screenshotBounds: pageBounds,
    },
    plan: {
      clusterSummary: plan.clusters,
      regionCount: plan.regions.length,
      pageSizeFromScan: plan.pageSize,
    },
    summary: {
      extracted,
      failed,
    },
    regions: regionRows,
  };

  const mapFile = path.join(splitDir, 'regions_map.json');
  fs.writeFileSync(mapFile, `${JSON.stringify(map, null, 2)}\n`, 'utf8');

  return {
    ok: true,
    reason: null,
    splitDir: rel(splitDir),
    mapFile: rel(mapFile),
    extracted,
    failed,
    regions: regionRows,
  };
}

async function captureSingleScreenshot({
  browser,
  runDir,
  scanRunDir,
  baseUrl,
  mode,
  slug,
  viewport,
  opts,
}) {
  const label = pageLabel(slug);
  const vpText = viewportKey(viewport);
  const url = routeUrl(baseUrl, slug, mode);
  const fileName = `${label}-${mode}-${vpText}.png`;
  const outFile = path.join(runDir, 'screenshots', 'static', mode, fileName);
  ensureDir(path.dirname(outFile));

  const attemptErrors = [];

  for (let attempt = 1; attempt <= opts.captureAttempts; attempt++) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();

    try {
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 });
      const status = response ? response.status() : null;

      await waitForPageStable(page, mode, opts.stabilizeMs);
      const pageBounds = await ensureLargeViewportForClips(page, viewport.width);

      if (typeof status === 'number' && status >= 400) {
        throw new Error(`HTTP ${status}`);
      }

      await page.screenshot({ path: outFile, fullPage: true });

      let split = null;
      if (mode === 'main' && opts.splitMain) {
        split = await captureMainSplitScreenshots({
          page,
          runDir,
          pageName: label,
          viewportText: vpText,
          scanRunDir,
          pageBounds,
          splitSubcolumns: opts.splitSubcolumns,
          splitCategory: 'static',
          transitionStage: 'static',
        });
      }

      console.log(`  [shot] ${mode} ${label} @ ${vpText} -> ${rel(outFile)} (attempt ${attempt}/${opts.captureAttempts})`);
      await ctx.close();

      return {
        category: 'static',
        mode,
        page: label,
        slug,
        viewport: vpText,
        url,
        status,
        ok: true,
        error: null,
        file: rel(outFile),
        attempts: attempt,
        attemptErrors,
        transitionStage: 'static',
        split,
      };
    } catch (err) {
      const message = err && err.message ? err.message : String(err);
      attemptErrors.push(message);
      await ctx.close();

      if (attempt >= opts.captureAttempts) {
        console.log(`  [shot:failed] ${mode} ${label} @ ${vpText} -> ${message}`);
        return {
          category: 'static',
          mode,
          page: label,
          slug,
          viewport: vpText,
          url,
          status: null,
          ok: false,
          error: message,
          file: null,
          attempts: attempt,
          attemptErrors,
          transitionStage: 'static',
          split: null,
        };
      }

      await sleep(800 + attempt * 600);
    }
  }

  return {
    category: 'static',
    mode,
    page: label,
    slug,
    viewport: vpText,
    url,
    status: null,
    ok: false,
    error: 'Unknown screenshot failure',
    file: null,
    attempts: opts.captureAttempts,
    attemptErrors,
    transitionStage: 'static',
    split: null,
  };
}

async function captureScreenshots({ runDir, scanRunDir, baseUrl, mode, pages, viewports, opts }) {
  function buildTransitionEdgesFromModel(model, maxTransitions) {
    const cards = Array.isArray(model && model.cards) ? model.cards : [];
    const edges = [];
    const dedup = new Set();

    for (const card of cards) {
      const fromId = card && card.id ? String(card.id) : null;
      if (!fromId) continue;
      const transitions = card && card.transitions ? card.transitions : null;
      if (!transitions || !transitions.type) continue;

      if (transitions.type === 'linear' && transitions.next_id) {
        const toId = String(transitions.next_id);
        const key = `${fromId}|${toId}|linear|0`;
        if (dedup.has(key)) continue;
        dedup.add(key);
        const slug = `${slugify(fromId)}-to-${slugify(toId)}`;
        edges.push({
          type: 'linear',
          fromId,
          toId,
          optionIndex: null,
          optionLabel: null,
          slug,
        });
        continue;
      }

      if (transitions.type === 'split' && Array.isArray(transitions.options)) {
        transitions.options.forEach((opt, idx) => {
          if (!opt || !opt.target_id) return;
          const toId = String(opt.target_id);
          const optionLabel = opt.label || `option-${idx + 1}`;
          const key = `${fromId}|${toId}|split|${idx}`;
          if (dedup.has(key)) return;
          dedup.add(key);
          const slug = `${slugify(fromId)}-to-${slugify(toId)}-opt-${idx + 1}-${slugify(optionLabel)}`;
          edges.push({
            type: 'split',
            fromId,
            toId,
            optionIndex: idx,
            optionLabel,
            slug,
          });
        });
      }
    }

    return edges.slice(0, maxTransitions);
  }

  async function captureDynamicTransitionsForPage({
    browser,
    runDir,
    scanRunDir,
    baseUrl,
    mode,
    slug,
    viewport,
    opts,
  }) {
    const shots = [];
    const splitArtifacts = [];
    const label = pageLabel(slug);
    const vpText = viewportKey(viewport);
    const url = routeUrl(baseUrl, slug, mode);

    // Dynamic state transitions are only meaningful for the single-page main flow.
    if (mode !== 'main' || label !== 'home') {
      return { shots, splitArtifacts };
    }

    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();
    try {
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 });
      const status = response ? response.status() : null;
      await waitForPageStable(page, mode, opts.stabilizeMs);

      if (typeof status === 'number' && status >= 400) {
        throw new Error(`HTTP ${status}`);
      }

      const model = await page.evaluate(() => {
        const api = window.__WARDEN_AUTOMATION;
        if (!api || typeof api.getModel !== 'function') return null;
        return api.getModel();
      });

      const edges = buildTransitionEdgesFromModel(model, opts.dynamicMaxTransitions);
      if (edges.length === 0) {
        shots.push({
          category: 'dynamic',
          mode,
          page: label,
          slug,
          viewport: vpText,
          url,
          status,
          ok: false,
          error: 'No transition edges available via window.__WARDEN_AUTOMATION.getModel()',
          file: null,
          attempts: 1,
          attemptErrors: [],
          transitionIndex: null,
          transition: null,
          beforeSnapshot: null,
          afterSnapshot: null,
          split: null,
        });
        return { shots, splitArtifacts };
      }

      for (let i = 0; i < edges.length; i++) {
        const edge = edges[i];
        const transitionIndex = i + 1;
        const transitionToken = `${String(transitionIndex).padStart(3, '0')}-${edge.slug}`;
        const attemptErrors = [];
        let capturedPair = null;

        for (let attempt = 1; attempt <= opts.captureAttempts; attempt++) {
          try {
            const setup = await page.evaluate((payload) => {
              const api = window.__WARDEN_AUTOMATION;
              if (!api) throw new Error('window.__WARDEN_AUTOMATION is missing');
              if (typeof api.gotoCard !== 'function') throw new Error('Automation API missing gotoCard');
              if (typeof api.advance !== 'function') throw new Error('Automation API missing advance');

              const goto = api.gotoCard(payload.fromId);
              if (!goto || goto.ok === false) {
                throw new Error(goto && goto.error ? goto.error : `Unable to go to card ${payload.fromId}`);
              }

              if (payload.type === 'split') {
                if (typeof api.selectDecisionOption !== 'function') {
                  throw new Error('Automation API missing selectDecisionOption');
                }
                const pick = api.selectDecisionOption(payload.optionIndex);
                if (!pick || pick.ok === false) {
                  throw new Error(pick && pick.error ? pick.error : 'Failed to select decision option');
                }
              }

              const before = typeof api.getSnapshot === 'function' ? api.getSnapshot() : null;
              return { before };
            }, edge);

            if (opts.dynamicSettleMs > 0) await page.waitForTimeout(opts.dynamicSettleMs);
            const beforeBounds = await ensureLargeViewportForClips(page, viewport.width);
            const beforeFile = path.join(
              runDir,
              'screenshots',
              'dynamic',
              mode,
              `${label}-${mode}-${vpText}-edge-${transitionToken}-before.png`,
            );
            ensureDir(path.dirname(beforeFile));
            await page.screenshot({ path: beforeFile, fullPage: true });

            let splitBefore = null;
            if (opts.splitMain) {
              splitBefore = await captureMainSplitScreenshots({
                page,
                runDir,
                pageName: label,
                viewportText: vpText,
                scanRunDir,
                pageBounds: beforeBounds,
                splitSubcolumns: opts.splitSubcolumns,
                splitCategory: 'dynamic',
                splitKey: `${label}-${vpText}-edge-${transitionToken}-before`,
                transitionStage: 'before',
                transition: edge,
                stateSnapshot: setup.before || null,
              });
            }

            const advanced = await page.evaluate(() => {
              const api = window.__WARDEN_AUTOMATION;
              if (!api) throw new Error('window.__WARDEN_AUTOMATION is missing');
              if (typeof api.advance !== 'function') throw new Error('Automation API missing advance');
              const move = api.advance();
              if (!move || move.ok === false) {
                throw new Error(move && move.error ? move.error : 'Advance action failed');
              }
              const after = typeof api.getSnapshot === 'function'
                ? api.getSnapshot()
                : (move.snapshot || null);
              return {
                before_id: move.before_id || null,
                after_id: move.after_id || null,
                after,
              };
            });

            if (advanced && advanced.after && edge.toId && advanced.after.currentId && advanced.after.currentId !== edge.toId) {
              throw new Error(`Transition mismatch: expected ${edge.toId} got ${advanced.after.currentId}`);
            }

            if (opts.dynamicSettleMs > 0) await page.waitForTimeout(opts.dynamicSettleMs);
            const afterBounds = await ensureLargeViewportForClips(page, viewport.width);
            const afterFile = path.join(
              runDir,
              'screenshots',
              'dynamic',
              mode,
              `${label}-${mode}-${vpText}-edge-${transitionToken}-after.png`,
            );
            ensureDir(path.dirname(afterFile));
            await page.screenshot({ path: afterFile, fullPage: true });

            let splitAfter = null;
            if (opts.splitMain) {
              splitAfter = await captureMainSplitScreenshots({
                page,
                runDir,
                pageName: label,
                viewportText: vpText,
                scanRunDir,
                pageBounds: afterBounds,
                splitSubcolumns: opts.splitSubcolumns,
                splitCategory: 'dynamic',
                splitKey: `${label}-${vpText}-edge-${transitionToken}-after`,
                transitionStage: 'after',
                transition: edge,
                stateSnapshot: advanced.after || null,
              });
            }

            capturedPair = {
              before: {
                category: 'dynamic',
                transitionStage: 'before',
                mode,
                page: label,
                slug,
                viewport: vpText,
                url,
                status,
                ok: true,
                error: null,
                file: rel(beforeFile),
                attempts: attempt,
                attemptErrors,
                transitionIndex,
                transition: edge,
                beforeSnapshot: setup.before || null,
                afterSnapshot: null,
                split: splitBefore,
              },
              after: {
                category: 'dynamic',
                transitionStage: 'after',
                mode,
                page: label,
                slug,
                viewport: vpText,
                url,
                status,
                ok: true,
                error: null,
                file: rel(afterFile),
                attempts: attempt,
                attemptErrors,
                transitionIndex,
                transition: edge,
                beforeSnapshot: setup.before || null,
                afterSnapshot: advanced.after || null,
                split: splitAfter,
              },
            };
            break;
          } catch (err) {
            const message = err && err.message ? err.message : String(err);
            attemptErrors.push(message);
            if (attempt < opts.captureAttempts) {
              await page.waitForTimeout(600 + attempt * 400);
            }
          }
        }

        if (!capturedPair) {
          shots.push({
            category: 'dynamic',
            transitionStage: 'after',
            mode,
            page: label,
            slug,
            viewport: vpText,
            url,
            status: null,
            ok: false,
            error: attemptErrors[attemptErrors.length - 1] || 'Unknown dynamic capture failure',
            file: null,
            attempts: opts.captureAttempts,
            attemptErrors,
            transitionIndex,
            transition: edge,
            beforeSnapshot: null,
            afterSnapshot: null,
            split: null,
          });
          continue;
        }

        shots.push(capturedPair.before);
        shots.push(capturedPair.after);

        if (capturedPair.before.split) {
          splitArtifacts.push({
            category: 'dynamic',
            transitionStage: 'before',
            mode: capturedPair.before.mode,
            page: capturedPair.before.page,
            viewport: capturedPair.before.viewport,
            transitionIndex: capturedPair.before.transitionIndex,
            transition: capturedPair.before.transition,
            ...capturedPair.before.split,
          });
        }
        if (capturedPair.after.split) {
          splitArtifacts.push({
            category: 'dynamic',
            transitionStage: 'after',
            mode: capturedPair.after.mode,
            page: capturedPair.after.page,
            viewport: capturedPair.after.viewport,
            transitionIndex: capturedPair.after.transitionIndex,
            transition: capturedPair.after.transition,
            ...capturedPair.after.split,
          });
        }
      }
    } finally {
      await ctx.close();
    }

    return { shots, splitArtifacts };
  }

  const modes = ['main'];
  const chromiumBrowser = ensurePlaywrightChromium();
  const browser = await chromiumBrowser.launch({ headless: true });
  const staticShots = [];
  const dynamicShots = [];
  const staticSplitArtifacts = [];
  const dynamicSplitArtifacts = [];

  try {
    for (const currentMode of modes) {
      ensureDir(path.join(runDir, 'screenshots', 'static', currentMode));
      ensureDir(path.join(runDir, 'screenshots', 'dynamic', currentMode));

      for (const vp of viewports) {
        for (const slug of pages) {
          const shot = await captureSingleScreenshot({
            browser,
            runDir,
            scanRunDir,
            baseUrl,
            mode: currentMode,
            slug,
            viewport: vp,
            opts,
          });
          staticShots.push(shot);
          if (shot.split) {
            staticSplitArtifacts.push({
              category: 'static',
              transitionStage: 'static',
              mode: shot.mode,
              page: shot.page,
              viewport: shot.viewport,
              ...shot.split,
            });
          }

          if (opts.dynamicMain) {
            const dynamic = await captureDynamicTransitionsForPage({
              browser,
              runDir,
              scanRunDir,
              baseUrl,
              mode: currentMode,
              slug,
              viewport: vp,
              opts,
            });
            dynamicShots.push(...dynamic.shots);
            dynamicSplitArtifacts.push(...dynamic.splitArtifacts);
          }
        }
      }
    }
  } finally {
    await browser.close();
  }

  const shots = [...staticShots, ...dynamicShots];
  const splitArtifacts = [...staticSplitArtifacts, ...dynamicSplitArtifacts];

  return {
    shots,
    splitArtifacts,
    staticShots,
    dynamicShots,
    staticSplitArtifacts,
    dynamicSplitArtifacts,
  };
}

function writeBundleSummaryMarkdown(runDir, manifest) {
  const allShots = manifest.screenshots || [];
  const staticShots = allShots.filter((s) => s.category !== 'dynamic');
  const dynamicShots = allShots.filter((s) => s.category === 'dynamic');
  const staticOk = staticShots.filter((s) => s.ok).length;
  const staticFail = staticShots.length - staticOk;
  const dynamicOk = dynamicShots.filter((s) => s.ok).length;
  const dynamicFail = dynamicShots.length - dynamicOk;
  const splitSummary = manifest.splitSummary || {
    bundles: 0,
    extracted: 0,
    failed: 0,
    byCategory: {
      static: { bundles: 0, extracted: 0, failed: 0 },
      dynamic: { bundles: 0, extracted: 0, failed: 0 },
    },
  };

  const lines = [
    '# Warden Design Bundle',
    '',
    `Generated: ${manifest.generatedAt}`,
    '',
    '## Linked Runs',
    '',
    `- Blueprint run: \`${manifest.blueprint.runDir}\``,
    `- Scan run: \`${manifest.scan.runDir}\``,
    '',
    '## Capture Controls',
    '',
    `- Base URL: \`${manifest.capture.baseUrl}\``,
    `- Mode: \`${manifest.capture.mode}\``,
    `- Pages: ${manifest.capture.pages.map((p) => p || 'home').join(', ')}`,
    `- Viewports: ${manifest.capture.viewports.join(', ')}`,
    `- Capture attempts per page: ${manifest.capture.captureAttempts}`,
    `- Stabilize wait: ${manifest.capture.stabilizeMs} ms`,
    `- Warmup rounds: ${manifest.capture.warmupRounds}`,
    `- Dev server started by script: ${manifest.capture.devServerStartedByScript}`,
    `- Dynamic main transitions: ${manifest.capture.dynamicMain ? 'enabled' : 'disabled'}`,
    `- Dynamic transition cap: ${manifest.capture.dynamicMaxTransitions}`,
    `- Dynamic settle wait: ${manifest.capture.dynamicSettleMs} ms`,
    '',
    '## Screenshot Results',
    '',
    `- Static screenshots: ${staticOk} ok, ${staticFail} failed`,
    `- Dynamic transition screenshots: ${dynamicOk} ok, ${dynamicFail} failed`,
    `- Total screenshots: ${allShots.length}`,
    '',
    '## Split Results',
    '',
    `- Static split bundles: ${splitSummary.byCategory.static.bundles}`,
    `- Static split crops: ${splitSummary.byCategory.static.extracted} extracted, ${splitSummary.byCategory.static.failed} failed`,
    `- Dynamic split bundles: ${splitSummary.byCategory.dynamic.bundles}`,
    `- Dynamic split crops: ${splitSummary.byCategory.dynamic.extracted} extracted, ${splitSummary.byCategory.dynamic.failed} failed`,
    `- Total split bundles: ${splitSummary.bundles}`,
    `- Total split crops: ${splitSummary.extracted} extracted, ${splitSummary.failed} failed`,
    '',
    '## Coverage Snapshot (from scan output)',
    '',
  ];

  const summary = manifest.scan.coverageSummary;
  if (summary) {
    lines.push(`- Scans: ${summary.scans}`);
    lines.push(`- Total scanned elements: ${summary.totalScannedElements}`);
    lines.push(`- Scanned ratio of includeable: ${summary.scannedRatioOfIncludeable}`);
    lines.push(`- Scanned ratio of unique: ${summary.scannedRatioOfUnique}`);
  } else {
    lines.push('- No coverage summary found in linked scan run.');
  }

  lines.push('');
  lines.push('## Blueprint Snapshot (from run_meta)');
  lines.push('');
  if (manifest.blueprint.runMeta) {
    lines.push(`- Source path: \`${manifest.blueprint.runMeta.source_path || 'n/a'}\``);
    lines.push(`- Files scanned: ${manifest.blueprint.runMeta.files_scanned ?? 'n/a'}`);
    lines.push(`- Entities found: ${manifest.blueprint.runMeta.entities_found ?? 'n/a'}`);
    lines.push(`- Edges found: ${manifest.blueprint.runMeta.edges_found ?? 'n/a'}`);
    lines.push(`- Domains: ${(manifest.blueprint.runMeta.domains_run || []).join(', ')}`);
  } else {
    lines.push('- No run_meta.json found in linked blueprint run.');
  }

  lines.push('');
  lines.push('## Screenshot Index');
  lines.push('');
  lines.push('| Category | Stage | Mode | Page | Viewport | Status | Attempts | Transition | File |');
  lines.push('|---|---|---|---|---|---|---|---|---|');
  for (const shot of manifest.screenshots) {
    const status = shot.ok ? 'ok' : `failed (${shot.error || 'error'})`;
    const transition = shot.transition
      ? `${shot.transition.fromId} -> ${shot.transition.toId}${shot.transition.optionLabel ? ` (${shot.transition.optionLabel})` : ''}`
      : '-';
    lines.push(`| ${shot.category || 'static'} | ${shot.transitionStage || '-'} | ${shot.mode} | ${shot.page} | ${shot.viewport} | ${status} | ${shot.attempts} | ${transition} | ${shot.file ? `\`${shot.file}\`` : '-'} |`);
  }

  lines.push('');
  lines.push('## Split Index');
  lines.push('');
  lines.push('| Category | Stage | Page | Viewport | Status | Transition | Map | Extracted | Failed |');
  lines.push('|---|---|---|---|---|---|---|---|---|');
  for (const split of manifest.splitArtifacts || []) {
    const status = split.ok ? 'ok' : `failed (${split.reason || 'error'})`;
    const transition = split.transition
      ? `${split.transition.fromId} -> ${split.transition.toId}${split.transition.optionLabel ? ` (${split.transition.optionLabel})` : ''}`
      : '-';
    lines.push(`| ${split.category || 'static'} | ${split.transitionStage || '-'} | ${split.page} | ${split.viewport} | ${status} | ${transition} | ${split.mapFile ? `\`${split.mapFile}\`` : '-'} | ${split.extracted ?? 0} | ${split.failed ?? 0} |`);
  }

  lines.push('');
  const summaryPath = path.join(runDir, 'bundle_summary.md');
  fs.writeFileSync(summaryPath, `${lines.join('\n')}\n`, 'utf8');
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const blueprintRunDir = resolveRunDir(BLUEPRINT_RUNS_DIR, opts.blueprintRun, 'Blueprint');
  const scanRunDir = resolveRunDir(SCAN_RUNS_DIR, opts.scanRun, 'Scan');
  const pages = resolvePages(opts, scanRunDir);
  const runDir = buildRunDir(opts, blueprintRunDir, scanRunDir);
  // Fail fast before launching/stopping dev server work.
  ensurePlaywrightChromium();

  ensureDir(runDir);
  ensureDir(path.join(runDir, 'linked'));

  console.log('\nWarden Design Bundle');
  console.log(`  Blueprint run: ${rel(blueprintRunDir)}`);
  console.log(`  Scan run     : ${rel(scanRunDir)}`);
  console.log(`  Output dir   : ${rel(runDir)}`);
  console.log(`  Mode         : ${opts.mode}`);
  console.log(`  Pages        : ${pages.map((p) => p || 'home').join(', ')}`);
  console.log(`  Viewports    : ${opts.viewports.map(viewportKey).join(', ')}`);
  console.log(`  Dynamic main : ${opts.dynamicMain ? 'enabled' : 'disabled'}`);
  if (opts.dynamicMain) {
    console.log(`  Dynamic cap  : ${opts.dynamicMaxTransitions} transitions/viewport`);
  }

  const blueprintLink = ensureSymlink(blueprintRunDir, path.join(runDir, 'linked', 'blueprint_run'));
  const scanLink = ensureSymlink(scanRunDir, path.join(runDir, 'linked', 'scan_run'));

  let devHandle = { started: false, child: null };
  let screenshots = [];
  let splitArtifacts = [];
  let staticScreenshots = [];
  let dynamicScreenshots = [];
  let staticSplitArtifacts = [];
  let dynamicSplitArtifacts = [];
  try {
    devHandle = await ensureDevServer(opts.baseUrl, opts.mode, opts.devTimeoutSeconds);
    await warmupRoutes(opts.baseUrl, opts.mode, pages, opts.warmupRounds);

    const capture = await captureScreenshots({
      runDir,
      scanRunDir,
      baseUrl: opts.baseUrl,
      mode: opts.mode,
      pages,
      viewports: opts.viewports,
      opts,
    });
    screenshots = capture.shots;
    splitArtifacts = capture.splitArtifacts;
    staticScreenshots = capture.staticShots;
    dynamicScreenshots = capture.dynamicShots;
    staticSplitArtifacts = capture.staticSplitArtifacts;
    dynamicSplitArtifacts = capture.dynamicSplitArtifacts;
  } finally {
    if (devHandle.started && !opts.keepDev) {
      console.log('[Step] Stop Dev Server');
      await stopDevServer(devHandle.child);
      console.log('[Info] Dev server stopped.');
    } else if (devHandle.started && opts.keepDev) {
      console.log('[Info] Keeping dev server running (--keep-dev).');
    }
  }

  const blueprint = summarizeBlueprint(blueprintRunDir);
  const scan = summarizeScan(scanRunDir);

  const splitByCategory = {
    static: {
      bundles: staticSplitArtifacts.length,
      extracted: staticSplitArtifacts.reduce((sum, s) => sum + (s.extracted || 0), 0),
      failed: staticSplitArtifacts.reduce((sum, s) => sum + (s.failed || 0), 0),
    },
    dynamic: {
      bundles: dynamicSplitArtifacts.length,
      extracted: dynamicSplitArtifacts.reduce((sum, s) => sum + (s.extracted || 0), 0),
      failed: dynamicSplitArtifacts.reduce((sum, s) => sum + (s.failed || 0), 0),
    },
  };

  const splitSummary = {
    bundles: splitByCategory.static.bundles + splitByCategory.dynamic.bundles,
    extracted: splitByCategory.static.extracted + splitByCategory.dynamic.extracted,
    failed: splitByCategory.static.failed + splitByCategory.dynamic.failed,
    byCategory: splitByCategory,
  };

  const screenshotSummary = {
    static: {
      total: staticScreenshots.length,
      ok: staticScreenshots.filter((s) => s.ok).length,
      failed: staticScreenshots.filter((s) => !s.ok).length,
    },
    dynamic: {
      total: dynamicScreenshots.length,
      ok: dynamicScreenshots.filter((s) => s.ok).length,
      failed: dynamicScreenshots.filter((s) => !s.ok).length,
    },
    total: screenshots.length,
    ok: screenshots.filter((s) => s.ok).length,
    failed: screenshots.filter((s) => !s.ok).length,
  };

  const manifest = {
    generatedAt: new Date().toISOString(),
    runDir: rel(runDir),
    linkedAt: {
      blueprintRunDir: rel(blueprintRunDir),
      scanRunDir: rel(scanRunDir),
    },
    links: {
      blueprintSymlinkCreated: blueprintLink.ok,
      blueprintFallbackFile: blueprintLink.fallbackFile ? rel(blueprintLink.fallbackFile) : null,
      scanSymlinkCreated: scanLink.ok,
      scanFallbackFile: scanLink.fallbackFile ? rel(scanLink.fallbackFile) : null,
    },
    capture: {
      baseUrl: opts.baseUrl,
      mode: opts.mode,
      pages,
      viewports: opts.viewports.map(viewportKey),
      devServerStartedByScript: devHandle.started,
      captureAttempts: opts.captureAttempts,
      stabilizeMs: opts.stabilizeMs,
      warmupRounds: opts.warmupRounds,
      splitMain: opts.splitMain,
      splitSubcolumns: opts.splitSubcolumns,
      dynamicMain: opts.dynamicMain,
      dynamicMaxTransitions: opts.dynamicMaxTransitions,
      dynamicSettleMs: opts.dynamicSettleMs,
    },
    blueprint: {
      runDir: blueprint.runDir,
      runName: blueprint.runName,
      fileCount: blueprint.fileCount,
      files: blueprint.files,
      runMeta: blueprint.runMeta,
    },
    scan: {
      runDir: scan.runDir,
      runName: scan.runName,
      fileCount: scan.fileCount,
      files: scan.files,
      runManifest: scan.runManifest,
      coverageSummary: scan.coverageReport ? scan.coverageReport.summary : null,
    },
    screenshots,
    screenshotsStatic: staticScreenshots,
    screenshotsDynamic: dynamicScreenshots,
    screenshotSummary,
    splitArtifacts,
    splitArtifactsStatic: staticSplitArtifacts,
    splitArtifactsDynamic: dynamicSplitArtifacts,
    splitSummary,
  };

  const manifestPath = path.join(runDir, 'bundle_manifest.json');
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  writeBundleSummaryMarkdown(runDir, manifest);

  ensureDir(DESIGN_ROOT);
  fs.writeFileSync(
    path.join(DESIGN_ROOT, 'current_bundle.json'),
    `${JSON.stringify({ runDir: rel(runDir), generatedAt: manifest.generatedAt }, null, 2)}\n`,
    'utf8',
  );

  console.log('\nBundle complete.');
  console.log(`  Manifest: ${rel(manifestPath)}`);
  console.log(`  Summary : ${rel(path.join(runDir, 'bundle_summary.md'))}`);
  console.log(`  Static shots : ${screenshotSummary.static.ok} ok, ${screenshotSummary.static.failed} failed`);
  console.log(`  Dynamic shots: ${screenshotSummary.dynamic.ok} ok, ${screenshotSummary.dynamic.failed} failed`);
  console.log(`  Static splits : ${splitByCategory.static.extracted} extracted, ${splitByCategory.static.failed} failed`);
  console.log(`  Dynamic splits: ${splitByCategory.dynamic.extracted} extracted, ${splitByCategory.dynamic.failed} failed`);
  console.log('');
}

main().catch((err) => {
  console.error(`\nFatal: ${err.message}`);
  process.exit(1);
});
