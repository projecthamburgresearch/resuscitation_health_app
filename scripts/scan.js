#!/usr/bin/env node
'use strict';

/**
 * Design Telemetry Scanner (Dev-Mode adaptation)
 * -----------------------------------------------------------------------------
 * - Discovers scan targets from HTML files under app/dev-mode/
 * - Captures runtime telemetry via in-page dev-mode export when available
 * - Writes run/current/archive artifacts + optional diffs + coverage report
 */

const fs = require('fs');
const path = require('path');
let chromium = null;

// -----------------------------------------------------------------------------
// Config
// -----------------------------------------------------------------------------

const REPO_ROOT = path.resolve(__dirname, '..');
const APP_DIR = path.resolve(__dirname, '../app');
const DEV_MODE_DIR = path.resolve(__dirname, '../app/dev-mode');
const SCAN_OUTPUT_DIR = process.env.SCAN_OUTPUT_DIR || '../appendix/scans_outputs';
const SCAN_ROOT_DIR = path.resolve(__dirname, SCAN_OUTPUT_DIR);
const SCAN_RUNS_DIR = path.join(SCAN_ROOT_DIR, 'runs');
const SCAN_CURRENT_DIR = path.join(SCAN_ROOT_DIR, 'current');
const SCAN_ARCHIVE_DIR = path.join(SCAN_ROOT_DIR, 'archive');
const LEGACY_APPENDIX_DIR = path.resolve(__dirname, '../appendix');
const LEGACY_SCAN_ROOT_DIR = path.resolve(__dirname, '../appendix/scans');
const BASE_URL = (process.env.SCAN_BASE_URL || 'http://localhost:3000').replace(/\/$/, '');

const DEV_MODE_HTML_FILE_RE = /\.html?$/i;
const ERROR_PATTERNS = [
  'runtime chunkloaderror',
  'failed to load chunk',
  'chunkloaderror',
  'application error:',
  'a client-side exception has occurred',
];
const DEFAULT_VIEWPORT = { width: 390, height: 844 };
const MULTI_VIEWPORT_PRESETS = [
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 390, height: 844 },
];
const VIEWPORT_ALIASES = {
  desktop: '1440x900',
  tablet: '1024x768',
  mobile: '390x844',
};
const SCAN_MAX_ATTEMPTS = Number(process.env.SCAN_MAX_ATTEMPTS || 3);
const SCAN_NAV_TIMEOUT_MS = Number(process.env.SCAN_NAV_TIMEOUT_MS || 60_000);
const SCAN_STABILIZE_MS = Number(process.env.SCAN_STABILIZE_MS || 1_200);
const SCAN_RETRY_DELAY_MS = Number(process.env.SCAN_RETRY_DELAY_MS || 1_000);
const MAX_SCAN_ELEMENTS = Number(process.env.MAX_SCAN_ELEMENTS || 450);

const WATCHED_FIELDS = [
  ['colorPhysics.dark.contrast.ratio', (e) => e.colorPhysics?.dark?.contrast?.ratio],
  ['colorPhysics.dark.contrast.wcag', (e) => e.colorPhysics?.dark?.contrast?.wcag],
  ['colorPhysics.dark.background.hex', (e) => e.colorPhysics?.dark?.background?.hex],
  ['colorPhysics.dark.text.hex', (e) => e.colorPhysics?.dark?.text?.hex],
  ['paragraphPhysics.measure.status', (e) => e.paragraphPhysics?.measure?.status],
  ['paragraphPhysics.measure.characters', (e) => e.paragraphPhysics?.measure?.characters],
  ['typography.fontSizePx', (e) => e.typography?.fontSizePx],
  ['typography.fontWeight', (e) => e.typography?.fontWeight],
  ['geometry.x', (e) => e.geometry?.x],
  ['geometry.y', (e) => e.geometry?.y],
  ['geometry.width', (e) => e.geometry?.width],
  ['geometry.height', (e) => e.geometry?.height],
  ['layoutContext.display', (e) => e.layoutContext?.display],
  ['layoutContext.gridColumnStart', (e) => e.layoutContext?.gridColumnStart],
  ['layoutContext.gridColumnSpan', (e) => e.layoutContext?.gridColumnSpan],
  ['layoutContext.alignment', (e) => e.layoutContext?.alignment],
  ['composition.type', (e) => e.composition?.type],
];

const RUN_STAMP = nowStamp();

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

// -----------------------------------------------------------------------------
// CLI
// -----------------------------------------------------------------------------

function parseArgs(argv) {
  const out = {
    scanAll: false,
    diff: false,
    coverageReport: false,
    help: false,
    listPages: false,
    multiViewport: false,
    viewportSpecs: [],
    positionals: [],
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];

    if (arg === '--all') out.scanAll = true;
    else if (arg === '--diff') out.diff = true;
    else if (arg === '--coverage-report') out.coverageReport = true;
    else if (arg === '--help' || arg === '-h') out.help = true;
    else if (arg === '--list-pages') out.listPages = true;
    else if (arg === '--multi-viewport') out.multiViewport = true;
    else if (arg === '--viewport') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) {
        throw new Error('Missing value after --viewport. Expected WIDTHxHEIGHT (example: 1440x900).');
      }
      out.viewportSpecs.push(next);
      i += 1;
    } else if (arg.startsWith('--viewport=')) {
      const value = arg.split('=', 2)[1];
      if (!value) throw new Error('Missing value in --viewport=WIDTHxHEIGHT');
      out.viewportSpecs.push(value);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    } else {
      out.positionals.push(arg);
    }
  }

  if (out.positionals.length > 1) {
    throw new Error(`Only one page argument is supported. Received: ${out.positionals.join(', ')}`);
  }
  return out;
}

function printHelp() {
  console.log(`
Usage:
  node scripts/scan.js
  node scripts/scan.js home
  node scripts/scan.js --all
  node scripts/scan.js --all --diff
  node scripts/scan.js --all --diff --coverage-report
  node scripts/scan.js --viewport 1280x800
  node scripts/scan.js --viewport 390x844 --viewport 844x390 --all
  node scripts/scan.js --multi-viewport --all
  node scripts/scan.js --list-pages

Flags:
  --all             Scan all discovered app/dev-mode/*.html routes
  --diff            Write diff files against latest prior matching scan
  --coverage-report Write run-level coverage report JSON (runs + current)
  --viewport        Viewport spec WIDTHxHEIGHT (repeatable, default: 390x844)
  --multi-viewport  Presets: desktop(1440x900), tablet(1024x768), mobile(390x844)
  --list-pages      Print discovered /dev-mode pages and exit
  --help, -h        Show this help

Env:
  SCAN_BASE_URL=https://preview-host node scripts/scan.js --all
  SCAN_OUTPUT_DIR=../appendix/scans_outputs node scripts/scan.js --all
  SCAN_MAX_ATTEMPTS=4 SCAN_NAV_TIMEOUT_MS=90000 node scripts/scan.js --all
`);
}

// -----------------------------------------------------------------------------
// Discovery
// -----------------------------------------------------------------------------

function discoverDevModePages() {
  const pages = [];
  const warnings = [];
  const bySlug = new Map();

  if (!fs.existsSync(DEV_MODE_DIR)) {
    warnings.push(`Missing directory: ${relativeFromRepo(DEV_MODE_DIR)}`);
    return { pages, warnings };
  }

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
      if (!DEV_MODE_HTML_FILE_RE.test(entry.name)) continue;

      const relFile = path.relative(DEV_MODE_DIR, abs).replace(/\\/g, '/');
      const source = relativeFromRepo(abs);
      const route = devModeFileToRoute(relFile);
      const slug = route.slug;

      const page = {
        slug,
        name: pageNameFromSlug(slug),
        urlPath: route.urlPath,
        source,
      };

      if (bySlug.has(slug)) {
        const existing = bySlug.get(slug);
        const preferCurrent = /(^|\/)index\.html$/i.test(relFile) && !/(^|\/)index\.html$/i.test(existing.sourceRelFile || '');
        if (preferCurrent) {
          bySlug.set(slug, { ...page, sourceRelFile: relFile });
        } else {
          warnings.push(`Duplicate route ${page.urlPath} in ${source}; keeping first from ${existing.source}`);
        }
        continue;
      }

      bySlug.set(slug, { ...page, sourceRelFile: relFile });
      pages.push(page);
    }
  }

  walk(DEV_MODE_DIR);

  // Prefer canonical home source (index.html) when duplicate home files exist.
  const home = pages.filter((p) => p.slug === '');
  if (home.length > 1) {
    const preferred = home.find((p) => /\/index\.html$/i.test(p.source)) || home[0];
    for (const p of home) {
      if (p !== preferred) {
        warnings.push(`Duplicate /dev-mode home source detected: ${p.source}; preferred ${preferred.source}`);
      }
    }
  }

  const dedup = Array.from(bySlug.values()).map((p) => ({
    slug: p.slug,
    name: p.name,
    urlPath: p.urlPath,
    source: p.source,
  }));

  dedup.sort((a, b) => {
    if (a.slug === '' && b.slug !== '') return -1;
    if (b.slug === '' && a.slug !== '') return 1;
    return a.slug.localeCompare(b.slug);
  });

  return { pages: dedup, warnings };
}

function devModeFileToRoute(relFile) {
  const normalized = String(relFile || '').replace(/\\/g, '/');
  const noExt = normalized.replace(/\.html?$/i, '');

  // Canonical /dev-mode home aliases.
  if (normalized.toLowerCase() === 'index.html') {
    return { slug: '', urlPath: '/dev-mode' };
  }
  if (normalized.toLowerCase() === 'resuscitation_app_complete.html') {
    return { slug: '', urlPath: '/dev-mode' };
  }

  if (/\/index$/i.test(noExt)) {
    const slug = noExt.replace(/\/index$/i, '').replace(/^\/+/, '').replace(/\/+$/, '');
    return {
      slug,
      urlPath: slug ? `/dev-mode/${slug}` : '/dev-mode',
    };
  }

  const slug = noExt.replace(/^\/+/, '').replace(/\/+$/, '');
  return {
    slug,
    urlPath: slug ? `/dev-mode/${slug}` : '/dev-mode',
  };
}

// -----------------------------------------------------------------------------
// Viewports
// -----------------------------------------------------------------------------

function parseViewportSpec(spec) {
  if (!spec) throw new Error('Viewport spec is empty');
  const normalized = String(spec).trim().toLowerCase();
  const source = VIEWPORT_ALIASES[normalized] || normalized;
  const match = source.match(/^(\d{2,5})x(\d{2,5})$/);
  if (!match) {
    throw new Error(`Invalid viewport "${spec}". Use WIDTHxHEIGHT (example: 1440x900).`);
  }

  const width = Number(match[1]);
  const height = Number(match[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width < 200 || height < 200) {
    throw new Error(`Invalid viewport "${spec}". Width/height must be at least 200.`);
  }
  return { width, height };
}

function resolveViewports(viewportSpecs, multiViewport) {
  const raw = [];

  for (const spec of viewportSpecs) {
    raw.push(parseViewportSpec(spec));
  }

  if (multiViewport) {
    for (const vp of MULTI_VIEWPORT_PRESETS) raw.push(vp);
  }

  if (raw.length === 0) raw.push(DEFAULT_VIEWPORT);

  const dedup = new Map();
  for (const vp of raw) dedup.set(viewportKey(vp), vp);
  return Array.from(dedup.values());
}

function viewportKey(vp) {
  return `${vp.width}x${vp.height}`;
}

// -----------------------------------------------------------------------------
// Target Resolution
// -----------------------------------------------------------------------------

function resolveTargets(rawPageArg, scanAll, discoveredPages) {
  if (scanAll) {
    return discoveredPages.map((p) => ({
      name: p.name,
      slug: p.slug,
      url: `${BASE_URL}${p.urlPath}`,
      source: p.source,
      discovered: true,
    }));
  }

  const home = discoveredPages.find((p) => p.slug === '') || discoveredPages[0];

  if (!rawPageArg) {
    if (!home) throw new Error('No pages discovered. Add at least one app/dev-mode/*.html file.');
    return [{
      name: home.name,
      slug: home.slug,
      url: `${BASE_URL}${home.urlPath}`,
      source: home.source,
      discovered: true,
    }];
  }

  if (rawPageArg.startsWith('http://') || rawPageArg.startsWith('https://')) {
    const parsed = new URL(rawPageArg);
    const normalized = normalizePageArg(parsed.pathname);
    return [{
      name: pageNameFromSlug(normalized),
      slug: normalized,
      url: rawPageArg,
      source: 'manual-url',
      discovered: false,
    }];
  }

  const normalized = normalizePageArg(rawPageArg);
  const bySlug = discoveredPages.find((p) => p.slug === normalized);
  if (bySlug) {
    return [{
      name: bySlug.name,
      slug: bySlug.slug,
      url: `${BASE_URL}${bySlug.urlPath}`,
      source: bySlug.source,
      discovered: true,
    }];
  }

  const directName = discoveredPages.find((p) => p.name === rawPageArg);
  if (directName) {
    return [{
      name: directName.name,
      slug: directName.slug,
      url: `${BASE_URL}${directName.urlPath}`,
      source: directName.source,
      discovered: true,
    }];
  }

  const fallbackSlug = normalized;
  const fallbackPath = fallbackSlug ? `/dev-mode/${fallbackSlug}` : '/dev-mode';
  return [{
    name: pageNameFromSlug(fallbackSlug),
    slug: fallbackSlug,
    url: `${BASE_URL}${fallbackPath}`,
    source: 'manual-arg',
    discovered: false,
  }];
}

function normalizePageArg(input) {
  let v = String(input || '').trim();
  if (!v) return '';
  v = v.replace(/^\/+/, '');
  v = v.replace(/^dev-mode\/?/, '');
  v = v.replace(/^app\//, '');
  v = v.replace(/\.html?$/i, '');
  v = v.replace(/\/+$/, '');
  if (v === '' || v.toLowerCase() === 'home') return '';
  if (v.toLowerCase() === 'index') return '';
  if (v.toLowerCase() === 'resuscitation_app_complete') return '';
  return v;
}

function pageNameFromSlug(slug) {
  if (!slug) return 'home';
  return slug
    .split('/')
    .map((part) => part.toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''))
    .filter(Boolean)
    .join('-') || 'page';
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// -----------------------------------------------------------------------------
// Scan + Diff
// -----------------------------------------------------------------------------

async function detectRuntimeOverlay(page) {
  const text = await page.evaluate(() => {
    const bodyText = document.body ? document.body.innerText || '' : '';
    return String(bodyText).toLowerCase();
  });

  for (const pattern of ERROR_PATTERNS) {
    if (text.includes(pattern)) return pattern;
  }
  return null;
}

async function waitForPageStable(page) {
  await page.waitForLoadState('domcontentloaded', { timeout: SCAN_NAV_TIMEOUT_MS });
  await page.waitForLoadState('networkidle', { timeout: SCAN_NAV_TIMEOUT_MS }).catch(() => null);
  await page.waitForFunction(() => document.readyState === 'complete', null, { timeout: 20_000 }).catch(() => null);
  await page.evaluate(() => (document.fonts && document.fonts.ready ? document.fonts.ready.then(() => true) : true)).catch(() => null);
  if (SCAN_STABILIZE_MS > 0) await page.waitForTimeout(SCAN_STABILIZE_MS);

  const runtimePattern = await detectRuntimeOverlay(page);
  if (runtimePattern) {
    throw new Error(`Runtime overlay detected (${runtimePattern})`);
  }
}

async function scanPage(browser, target, viewport) {
  const vpKey = viewportKey(viewport);
  const maxAttempts = Number.isFinite(SCAN_MAX_ATTEMPTS) && SCAN_MAX_ATTEMPTS > 0 ? Math.floor(SCAN_MAX_ATTEMPTS) : 1;
  const attemptErrors = [];

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();

    try {
      process.stdout.write(`  Loading ${target.url} @ ${vpKey} (attempt ${attempt}/${maxAttempts}) ... `);
      const response = await page.goto(target.url, { waitUntil: 'domcontentloaded', timeout: SCAN_NAV_TIMEOUT_MS });
      const status = response ? response.status() : 0;
      if (status >= 400) throw new Error(`HTTP ${status}`);

      await waitForPageStable(page);

      process.stdout.write('collecting telemetry ... ');

      const parsed = await page.evaluate((maxElements) => {
        // Preferred path: dev-mode page provides a scanner export hook.
        if (typeof window.__DEV_MODE_EXPORT_SCAN === 'function') {
          const exported = window.__DEV_MODE_EXPORT_SCAN(maxElements);
          if (typeof exported === 'string') return JSON.parse(exported);
          if (exported && typeof exported === 'object') return exported;
        }

        const PROJECT_INFO = {
          framework: 'static-html',
          styling: 'css',
          themeStrategy: 'css-custom-properties-or-static',
        };

        function clamp01(v) {
          if (!Number.isFinite(v)) return 0;
          return Math.max(0, Math.min(1, v));
        }

        function parseColor(input) {
          if (!input) return null;
          const text = String(input).trim().toLowerCase();
          if (!text || text === 'transparent') return { r: 0, g: 0, b: 0, a: 0 };

          const rgbaMatch = text.match(/^rgba?\(([^)]+)\)$/);
          if (!rgbaMatch) return null;
          const parts = rgbaMatch[1].split(',').map((p) => p.trim());
          if (parts.length < 3) return null;

          const r = Number(parts[0]);
          const g = Number(parts[1]);
          const b = Number(parts[2]);
          const a = parts.length >= 4 ? Number(parts[3]) : 1;

          if (![r, g, b, a].every((n) => Number.isFinite(n))) return null;
          return {
            r: Math.max(0, Math.min(255, Math.round(r))),
            g: Math.max(0, Math.min(255, Math.round(g))),
            b: Math.max(0, Math.min(255, Math.round(b))),
            a: clamp01(a),
          };
        }

        function rgbaToHex(c) {
          if (!c) return null;
          const hex = (n) => n.toString(16).padStart(2, '0');
          return `#${hex(c.r)}${hex(c.g)}${hex(c.b)}`;
        }

        function rgbaToCss(c) {
          if (!c) return null;
          const a = Math.round(c.a * 1000) / 1000;
          return `rgba(${c.r}, ${c.g}, ${c.b}, ${a})`;
        }

        function blend(top, bottom) {
          if (!top) return bottom;
          if (!bottom) return top;
          const a = clamp01(top.a + bottom.a * (1 - top.a));
          if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };

          const r = Math.round((top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a);
          const g = Math.round((top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a);
          const b = Math.round((top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a);
          return { r, g, b, a };
        }

        function toLinear(v) {
          const s = v / 255;
          return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
        }

        function luminance(c) {
          if (!c) return 0;
          const r = toLinear(c.r);
          const g = toLinear(c.g);
          const b = toLinear(c.b);
          return 0.2126 * r + 0.7152 * g + 0.0722 * b;
        }

        function contrastRatio(fg, bg) {
          const l1 = luminance(fg);
          const l2 = luminance(bg);
          const lighter = Math.max(l1, l2);
          const darker = Math.min(l1, l2);
          const ratio = (lighter + 0.05) / (darker + 0.05);
          return Math.round(ratio * 1000) / 1000;
        }

        function wcagLevel(ratio, fontSizePx, fontWeight) {
          const size = Number(fontSizePx) || 16;
          const weight = Number(fontWeight) || 400;
          const isLarge = size >= 24 || (size >= 18.66 && weight >= 700);

          if (isLarge) {
            if (ratio >= 4.5) return 'AAA';
            if (ratio >= 3) return 'AA';
            return 'FAIL';
          }
          if (ratio >= 7) return 'AAA';
          if (ratio >= 4.5) return 'AA';
          return 'FAIL';
        }

        function resolveBackground(el) {
          let composed = { r: 255, g: 255, b: 255, a: 1 };
          let node = el;
          let hops = 0;

          while (node && hops < 40) {
            const style = window.getComputedStyle(node);
            const color = parseColor(style.backgroundColor);
            if (color && color.a > 0) {
              composed = blend(color, composed);
              if (composed.a >= 0.999) break;
            }
            if (node === document.documentElement) break;
            node = node.parentElement;
            hops += 1;
          }

          return composed;
        }

        function safeNumber(v, fallback = 0) {
          const n = Number(v);
          return Number.isFinite(n) ? n : fallback;
        }

        function normalizedText(input) {
          return String(input || '')
            .replace(/\s+/g, ' ')
            .trim()
            .slice(0, 280);
        }

        function measureStatus(characters) {
          if (!Number.isFinite(characters) || characters <= 0) return 'na';
          if (characters >= 45 && characters <= 85) return 'optimal';
          if (characters < 45) return 'short';
          return 'long';
        }

        function semanticRole(el) {
          const explicit = el.getAttribute('role');
          if (explicit) return explicit;
          const tag = el.tagName.toLowerCase();
          if (tag === 'a') return 'link';
          if (tag === 'button') return 'button';
          if (/^h[1-6]$/.test(tag)) return 'heading';
          if (tag === 'nav') return 'navigation';
          if (tag === 'main') return 'main';
          if (tag === 'header') return 'banner';
          if (tag === 'footer') return 'contentinfo';
          if (tag === 'section') return 'region';
          if (tag === 'input' || tag === 'textarea' || tag === 'select') return 'form-control';
          return 'generic';
        }

        function elementLabel(el) {
          const tag = el.tagName.toLowerCase();
          const id = el.id ? `#${el.id}` : '';
          const classes = Array.from(el.classList || [])
            .filter(Boolean)
            .slice(0, 3)
            .map((c) => `.${c}`)
            .join('');
          return `${tag}${id}${classes}`;
        }

        function parentFrameId(el) {
          const parent = el.parentElement;
          if (!parent) return 'root';
          const tag = parent.tagName.toLowerCase();
          if (parent.id) return `${tag}#${parent.id}`;
          return tag;
        }

        function compositionType(display) {
          const text = String(display || '').toLowerCase();
          if (text.includes('grid')) return 'grid';
          if (text.includes('flex')) return 'flex';
          if (text.includes('table')) return 'table';
          return 'flow';
        }

        function simpleHash(input) {
          let h = 2166136261;
          const s = String(input || '');
          for (let i = 0; i < s.length; i++) {
            h ^= s.charCodeAt(i);
            h = (h * 16777619) >>> 0;
          }
          return h.toString(16);
        }

        const selector = [
          'header', 'main', 'footer', 'section', 'article', 'nav', 'aside',
          'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
          'a', 'button', 'input', 'label', 'textarea', 'select',
          'img', 'svg', 'figure', 'figcaption', 'table', 'blockquote', 'pre', 'code'
        ].join(',');

        const nodes = Array.from(document.querySelectorAll(selector));
        const uniqueNodes = Array.from(new Set(nodes));

        const dropped = {
          'too-small': 0,
          hidden: 0,
          offscreen: 0,
          'no-signal': 0,
          'cap-reached': 0,
        };

        const elements = [];
        let includeableCount = 0;

        const docEl = document.documentElement;
        const body = document.body;
        const pageWidth = Math.max(
          docEl ? docEl.scrollWidth : 0,
          docEl ? docEl.clientWidth : 0,
          body ? body.scrollWidth : 0,
          body ? body.clientWidth : 0,
          window.innerWidth || 0,
        );
        const pageHeight = Math.max(
          docEl ? docEl.scrollHeight : 0,
          docEl ? docEl.clientHeight : 0,
          body ? body.scrollHeight : 0,
          body ? body.clientHeight : 0,
          window.innerHeight || 0,
        );

        for (const el of uniqueNodes) {
          const style = window.getComputedStyle(el);
          const rect = el.getBoundingClientRect();

          const width = safeNumber(rect.width);
          const height = safeNumber(rect.height);

          if (width < 6 || height < 6) {
            dropped['too-small'] += 1;
            continue;
          }

          if (style.display === 'none' || style.visibility === 'hidden' || safeNumber(style.opacity, 1) === 0) {
            dropped.hidden += 1;
            continue;
          }

          const absX = safeNumber(rect.left) + safeNumber(window.scrollX);
          const absY = safeNumber(rect.top) + safeNumber(window.scrollY);

          if (absY + height < -10 || absY > pageHeight + 10 || absX + width < -10 || absX > pageWidth + 10) {
            dropped.offscreen += 1;
            continue;
          }

          includeableCount += 1;

          if (elements.length >= maxElements) {
            dropped['cap-reached'] += 1;
            continue;
          }

          const tag = el.tagName.toLowerCase();
          const label = elementLabel(el);
          const text = normalizedText(el.innerText || el.textContent || '');
          const fontSizePx = safeNumber(style.fontSize.replace('px', ''));
          const lineHeightPx = safeNumber(style.lineHeight.replace('px', ''), fontSizePx * 1.25);
          const fontWeight = safeNumber(style.fontWeight, 400);
          const letterSpacingPx = safeNumber(style.letterSpacing.replace('px', ''), 0);
          const color = parseColor(style.color) || { r: 0, g: 0, b: 0, a: 1 };
          const background = resolveBackground(el);
          const contrast = contrastRatio(color, background);
          const wcag = wcagLevel(contrast, fontSizePx, fontWeight);

          const charCount = text.length;
          const childList = el.parentElement ? Array.from(el.parentElement.children) : [];
          const localLayerIndex = childList.indexOf(el);

          elements.push({
            index: elements.length,
            sourceIndex: elements.length,
            id: el.id || null,
            tag,
            label,
            semanticRole: semanticRole(el),
            content: { text },
            typography: {
              fontFamily: style.fontFamily,
              fontSizePx,
              fontWeight,
              lineHeightPx,
              letterSpacingPx,
            },
            geometry: {
              x: Math.round(absX * 100) / 100,
              y: Math.round(absY * 100) / 100,
              width: Math.round(width * 100) / 100,
              height: Math.round(height * 100) / 100,
            },
            box: {
              x: Math.round(absX * 100) / 100,
              y: Math.round(absY * 100) / 100,
              width: Math.round(width * 100) / 100,
              height: Math.round(height * 100) / 100,
              left: Math.round(absX * 100) / 100,
              top: Math.round(absY * 100) / 100,
              right: Math.round((absX + width) * 100) / 100,
              bottom: Math.round((absY + height) * 100) / 100,
            },
            layoutContext: {
              display: style.display,
              position: style.position,
              alignment: style.textAlign || null,
              gridColumnStart: style.gridColumnStart || null,
              gridColumnSpan: style.gridColumnEnd || null,
            },
            composition: {
              type: compositionType(style.display),
            },
            planarPhysics: {
              parentFrameId: parentFrameId(el),
              localLayerIndex,
            },
            componentIdentity: {
              hash: simpleHash(`${tag}|${el.id || ''}|${Array.from(el.classList || []).join('.')}`),
            },
            colorPhysics: {
              dark: {
                text: { hex: rgbaToHex(color), rgba: rgbaToCss(color) },
                background: { hex: rgbaToHex(background), rgba: rgbaToCss(background) },
                contrast: { ratio: contrast, wcag },
              },
              light: {
                text: { hex: rgbaToHex(color), rgba: rgbaToCss(color) },
                background: { hex: rgbaToHex(background), rgba: rgbaToCss(background) },
                contrast: { ratio: contrast, wcag },
              },
            },
            paragraphPhysics: {
              measure: {
                characters: charCount,
                status: measureStatus(charCount),
              },
            },
            goldenRatio: {
              compliance: null,
              phiDeviation: null,
              verticalRhythm: { score: null },
            },
          });
        }

        const scannedCount = elements.length;
        const uniqueCandidateCount = uniqueNodes.length;
        const selectorCandidateCount = nodes.length;
        const scanCap = maxElements;
        const capped = scannedCount >= scanCap && includeableCount > scanCap;

        const coverage = {
          mode: 'static-dom',
          selectorCandidateCount,
          uniqueCandidateCount,
          includeableCount,
          scannedCount,
          scanCap,
          capped,
          dropped,
          scannedRatioOfUnique: uniqueCandidateCount > 0 ? Math.round((scannedCount / uniqueCandidateCount) * 1000) / 1000 : 0,
          scannedRatioOfIncludeable: includeableCount > 0 ? Math.round((scannedCount / includeableCount) * 1000) / 1000 : 0,
        };

        return {
          meta: {
            url: window.location.href,
            timestamp: new Date().toISOString(),
            theme: document.documentElement.getAttribute('data-theme') || 'default',
            viewport: {
              width: window.innerWidth,
              height: window.innerHeight,
            },
            pageSize: {
              width: pageWidth,
              height: pageHeight,
            },
            count: scannedCount,
            coverage,
            project: PROJECT_INFO,
            goldenConstants: {
              phi: 1.618,
              baseUnit: 8,
              baseGrid: 8,
            },
          },
          elements,
        };
      }, MAX_SCAN_ELEMENTS);

      await ctx.close();

      if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.elements)) {
        throw new Error('Telemetry collection failed: invalid payload');
      }

      process.stdout.write(`ok (${parsed.meta?.count ?? '?'} elements)\n`);
      return {
        pageName: target.name,
        viewportKey: vpKey,
        json: JSON.stringify(parsed, null, 2),
        parsed,
        attempts: attempt,
        attemptErrors,
      };
    } catch (err) {
      const message = err && err.message ? err.message : String(err);
      attemptErrors.push(message);
      await ctx.close();

      if (attempt >= maxAttempts) {
        throw new Error(`Scan failed after ${maxAttempts} attempts: ${message}`);
      }

      process.stdout.write(`retrying after error: ${message}\n`);
      if (SCAN_RETRY_DELAY_MS > 0) await sleep(SCAN_RETRY_DELAY_MS + attempt * 300);
    }
  }

  throw new Error('Unexpected scan retry exhaustion');
}

function diffScans(beforeJson, afterJson) {
  const before = JSON.parse(beforeJson);
  const after = JSON.parse(afterJson);
  const changes = [];

  if (before.meta?.count !== after.meta?.count) {
    changes.push({
      type: 'meta',
      field: 'count',
      before: before.meta?.count ?? null,
      after: after.meta?.count ?? null,
    });
  }

  const matched = matchElements(before.elements || [], after.elements || []);

  for (const m of matched.matches) {
    const be = before.elements[m.beforeIdx];
    const ae = after.elements[m.afterIdx];
    const elChanges = [];
    for (const [field, getter] of WATCHED_FIELDS) {
      const bVal = getter(be);
      const aVal = getter(ae);
      if (bVal !== aVal) elChanges.push({ field, before: bVal, after: aVal });
    }
    if (elChanges.length > 0) {
      changes.push({
        type: 'element-changed',
        beforeIndex: be.index,
        afterIndex: ae.index,
        label: ae.label,
        tag: ae.tag,
        matchReason: m.reason,
        changes: elChanges,
      });
    }
  }

  for (const afterIdx of matched.unmatchedAfter) {
    const e = after.elements[afterIdx];
    changes.push({
      type: 'element-added',
      index: e.index,
      label: e.label,
      tag: e.tag,
    });
  }

  for (const beforeIdx of matched.unmatchedBefore) {
    const e = before.elements[beforeIdx];
    changes.push({
      type: 'element-removed',
      index: e.index,
      label: e.label,
      tag: e.tag,
    });
  }

  return {
    summary: {
      page: after.meta?.url || null,
      before: {
        timestamp: before.meta?.timestamp || null,
        count: before.meta?.count ?? null,
      },
      after: {
        timestamp: after.meta?.timestamp || null,
        count: after.meta?.count ?? null,
      },
      matching: {
        strategy: 'hybrid:id/component/layout/geometry',
        matched: matched.matches.length,
        unmatchedBefore: matched.unmatchedBefore.length,
        unmatchedAfter: matched.unmatchedAfter.length,
        reasonCounts: matched.reasonCounts,
      },
      totalChanges: changes.length,
      added: changes.filter((c) => c.type === 'element-added').length,
      removed: changes.filter((c) => c.type === 'element-removed').length,
      changed: changes.filter((c) => c.type === 'element-changed').length,
    },
    changes,
  };
}

function matchElements(beforeElements, afterElements) {
  const matches = [];
  const reasonCounts = {};
  const unmatchedBefore = new Set(beforeElements.map((_, i) => i));
  const unmatchedAfter = new Set(afterElements.map((_, i) => i));

  function trackReason(reason) {
    const key = reason.includes(':') ? reason.split(':', 1)[0] : reason;
    reasonCounts[key] = (reasonCounts[key] || 0) + 1;
  }

  function addMatch(beforeIdx, afterIdx, reason) {
    if (!unmatchedBefore.has(beforeIdx) || !unmatchedAfter.has(afterIdx)) return;
    unmatchedBefore.delete(beforeIdx);
    unmatchedAfter.delete(afterIdx);
    matches.push({ beforeIdx, afterIdx, reason });
    trackReason(reason);
  }

  function consumeUniqueMatches(reason, keyFn) {
    const beforeMap = new Map();
    const afterMap = new Map();

    for (const bi of unmatchedBefore) {
      const key = keyFn(beforeElements[bi]);
      if (!key) continue;
      if (!beforeMap.has(key)) beforeMap.set(key, []);
      beforeMap.get(key).push(bi);
    }

    for (const ai of unmatchedAfter) {
      const key = keyFn(afterElements[ai]);
      if (!key) continue;
      if (!afterMap.has(key)) afterMap.set(key, []);
      afterMap.get(key).push(ai);
    }

    for (const [key, bIdxs] of beforeMap.entries()) {
      const aIdxs = afterMap.get(key);
      if (!aIdxs || bIdxs.length !== 1 || aIdxs.length !== 1) continue;
      addMatch(bIdxs[0], aIdxs[0], reason);
    }
  }

  consumeUniqueMatches('id', (e) => (e.id ? `${e.tag || ''}|${e.id}` : null));
  consumeUniqueMatches('component-parent-layer', (e) => {
    const hash = e.componentIdentity?.hash || null;
    const parent = e.planarPhysics?.parentFrameId || 'root';
    const layer = e.planarPhysics?.localLayerIndex;
    if (!hash || layer === undefined || layer === null) return null;
    return `${hash}|${parent}|${layer}`;
  });
  consumeUniqueMatches('role-label-tag', (e) => {
    if (!e.label) return null;
    return `${e.tag || ''}|${e.semanticRole || ''}|${e.label}`;
  });

  const candidatePairs = [];
  for (const ai of unmatchedAfter) {
    for (const bi of unmatchedBefore) {
      const scored = scoreMatchCandidate(beforeElements[bi], afterElements[ai]);
      if (scored.score >= 5) {
        candidatePairs.push({ beforeIdx: bi, afterIdx: ai, score: scored.score, reason: scored.reason });
      }
    }
  }

  candidatePairs.sort((a, b) => b.score - a.score || a.afterIdx - b.afterIdx || a.beforeIdx - b.beforeIdx);
  for (const pair of candidatePairs) {
    if (!unmatchedBefore.has(pair.beforeIdx) || !unmatchedAfter.has(pair.afterIdx)) continue;
    addMatch(pair.beforeIdx, pair.afterIdx, `similarity:${pair.reason}`);
  }

  matches.sort((a, b) => a.afterIdx - b.afterIdx);
  return {
    matches,
    unmatchedBefore: Array.from(unmatchedBefore).sort((a, b) => a - b),
    unmatchedAfter: Array.from(unmatchedAfter).sort((a, b) => a - b),
    reasonCounts,
  };
}

function scoreMatchCandidate(beforeEl, afterEl) {
  let score = 0;
  const reasons = [];

  if (beforeEl.id && afterEl.id && beforeEl.id === afterEl.id) {
    score += 12;
    reasons.push('id');
  }

  if (beforeEl.componentIdentity?.hash && beforeEl.componentIdentity.hash === afterEl.componentIdentity?.hash) {
    score += 4;
    reasons.push('hash');
  }

  if ((beforeEl.tag || '') === (afterEl.tag || '')) {
    score += 2;
    reasons.push('tag');
  } else {
    score -= 2;
  }

  if ((beforeEl.semanticRole || '') === (afterEl.semanticRole || '')) {
    score += 2;
    reasons.push('role');
  }

  if ((beforeEl.label || '') === (afterEl.label || '')) {
    score += 2;
    reasons.push('label');
  }

  if ((beforeEl.planarPhysics?.parentFrameId || '') === (afterEl.planarPhysics?.parentFrameId || '')) {
    score += 1;
    reasons.push('parent');
  }

  if ((beforeEl.planarPhysics?.localLayerIndex ?? null) === (afterEl.planarPhysics?.localLayerIndex ?? null)) {
    score += 1;
    reasons.push('layer');
  }

  if ((beforeEl.composition?.type || '') === (afterEl.composition?.type || '')) {
    score += 1;
  }

  const beforeText = normalizedText(beforeEl.content?.text);
  const afterText = normalizedText(afterEl.content?.text);
  if (beforeText && afterText && beforeText === afterText) {
    score += 1;
    reasons.push('text');
  }

  const dist = geometryDistance(beforeEl.geometry, afterEl.geometry);
  if (Number.isFinite(dist)) {
    if (dist < 24) {
      score += 2;
      reasons.push('geometry-tight');
    } else if (dist < 80) {
      score += 1;
      reasons.push('geometry-near');
    } else if (dist > 600) {
      score -= 2;
    }
    score -= Math.min(dist / 200, 4);
  }

  return { score, reason: reasons.join('+') || 'weak' };
}

function normalizedText(input) {
  return String(input || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80);
}

function geometryDistance(a, b) {
  if (!a || !b) return Number.POSITIVE_INFINITY;
  const acx = safeNumber(a.x) + safeNumber(a.width) / 2;
  const acy = safeNumber(a.y) + safeNumber(a.height) / 2;
  const bcx = safeNumber(b.x) + safeNumber(b.width) / 2;
  const bcy = safeNumber(b.y) + safeNumber(b.height) / 2;

  const centerDist = Math.abs(acx - bcx) + Math.abs(acy - bcy);
  const sizeDist = Math.abs(safeNumber(a.width) - safeNumber(b.width)) + Math.abs(safeNumber(a.height) - safeNumber(b.height));
  return centerDist + sizeDist * 0.5;
}

function safeNumber(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

// -----------------------------------------------------------------------------
// Output
// -----------------------------------------------------------------------------

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function removeDirIfEmpty(dirPath) {
  try {
    const entries = fs.readdirSync(dirPath);
    if (entries.length === 0) fs.rmdirSync(dirPath);
  } catch {
    // best-effort cleanup only
  }
}

function artifactFileName(pageName, suffix, viewportPart) {
  const vp = viewportPart ? `-${viewportPart}` : '';
  return `${pageName}${vp}-${suffix}.json`;
}

function runArtifactPath(runDir, pageName, suffix, viewportPart) {
  return path.join(runDir, artifactFileName(pageName, suffix, viewportPart));
}

function currentArtifactPath(pageName, suffix, viewportPart) {
  return path.join(SCAN_CURRENT_DIR, artifactFileName(pageName, suffix, viewportPart));
}

function parseLegacyScanFilename(file) {
  const match = file.match(/^(\d{8}-\d{4})-(.+)-scan\.json$/);
  if (!match) return null;

  let pageName = match[2];
  let vp = null;
  const vpMatch = pageName.match(/^(.*)-(\d{2,5}x\d{2,5})$/);
  if (vpMatch) {
    pageName = vpMatch[1];
    vp = vpMatch[2];
  }

  return {
    file,
    timestamp: match[1],
    pageName,
    viewportKey: vp,
  };
}

function findPreviousScan(pageName, viewportPart) {
  const currentPath = currentArtifactPath(pageName, 'scan', viewportPart);
  if (fs.existsSync(currentPath)) return currentPath;

  const scanRoots = [SCAN_ROOT_DIR];
  if (LEGACY_SCAN_ROOT_DIR !== SCAN_ROOT_DIR) scanRoots.push(LEGACY_SCAN_ROOT_DIR);
  if (LEGACY_APPENDIX_DIR !== SCAN_ROOT_DIR) scanRoots.push(LEGACY_APPENDIX_DIR);

  const rows = [];
  for (const root of scanRoots) {
    if (!fs.existsSync(root)) continue;
    for (const file of fs.readdirSync(root, { withFileTypes: true })) {
      if (!file.isFile()) continue;
      const parsed = parseLegacyScanFilename(file.name);
      if (!parsed) continue;
      if (parsed.pageName !== pageName) continue;
      rows.push({ ...parsed, fullPath: path.join(root, file.name) });
    }
  }

  rows.sort((a, b) => b.timestamp.localeCompare(a.timestamp) || b.file.localeCompare(a.file));

  if (rows.length === 0) return null;

  if (viewportPart) {
    const sameViewport = rows.find((r) => r.viewportKey === viewportPart);
    return sameViewport ? sameViewport.fullPath : null;
  }

  const noViewport = rows.find((r) => !r.viewportKey);
  return noViewport ? noViewport.fullPath : null;
}

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function relativeFromRepo(abs) {
  return path.relative(REPO_ROOT, abs) || '.';
}

function rotateCurrentSnapshotsToArchive() {
  ensureDir(SCAN_CURRENT_DIR);
  ensureDir(SCAN_ARCHIVE_DIR);

  const entries = fs.readdirSync(SCAN_CURRENT_DIR, { withFileTypes: true });
  if (entries.length === 0) return null;

  const archiveDir = path.join(SCAN_ARCHIVE_DIR, `current-${RUN_STAMP}`);
  ensureDir(archiveDir);

  for (const entry of entries) {
    const src = path.join(SCAN_CURRENT_DIR, entry.name);
    const dst = path.join(archiveDir, entry.name);
    fs.renameSync(src, dst);
  }
  return archiveDir;
}

function normalizeCoverageMeta(rawCoverage) {
  if (!rawCoverage || typeof rawCoverage !== 'object') return null;

  const value = {
    mode: String(rawCoverage.mode || 'unknown'),
    selectorCandidateCount: Number(rawCoverage.selectorCandidateCount || 0),
    uniqueCandidateCount: Number(rawCoverage.uniqueCandidateCount || 0),
    includeableCount: Number(rawCoverage.includeableCount || 0),
    scannedCount: Number(rawCoverage.scannedCount || 0),
    scanCap: Number(rawCoverage.scanCap || 0),
    capped: Boolean(rawCoverage.capped),
    dropped: rawCoverage.dropped || {},
    scannedRatioOfUnique: Number(rawCoverage.scannedRatioOfUnique || 0),
    scannedRatioOfIncludeable: Number(rawCoverage.scannedRatioOfIncludeable || 0),
  };
  return value;
}

function formatCoverageLine(coverage) {
  if (!coverage) return null;
  return `${coverage.scannedCount}/${coverage.includeableCount} includeable scanned, ${coverage.scannedCount}/${coverage.uniqueCandidateCount} unique candidates, capped=${coverage.capped}`;
}

function writeCoverageReport(rows, runDir) {
  const covered = rows.filter((row) => row.coverage);
  if (covered.length === 0) return null;

  const summary = {
    runStamp: RUN_STAMP,
    scans: covered.length,
    cappedScans: covered.filter((row) => row.coverage.capped).length,
    totalScannedElements: covered.reduce((sum, row) => sum + row.coverage.scannedCount, 0),
    totalIncludeableElements: covered.reduce((sum, row) => sum + row.coverage.includeableCount, 0),
    totalUniqueCandidates: covered.reduce((sum, row) => sum + row.coverage.uniqueCandidateCount, 0),
  };

  summary.scannedRatioOfIncludeable = summary.totalIncludeableElements > 0
    ? Math.round((summary.totalScannedElements / summary.totalIncludeableElements) * 1000) / 1000
    : 0;
  summary.scannedRatioOfUnique = summary.totalUniqueCandidates > 0
    ? Math.round((summary.totalScannedElements / summary.totalUniqueCandidates) * 1000) / 1000
    : 0;

  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    runStamp: RUN_STAMP,
    runDir: relativeFromRepo(runDir),
    currentDir: relativeFromRepo(SCAN_CURRENT_DIR),
    summary,
    notes: [
      'Coverage is measured against selector-filtered candidates, not the entire DOM.',
      'If capped=true, increase MAX_SCAN_ELEMENTS or narrow selector scope.',
    ],
    scans: covered.map((row) => ({
      page: row.page,
      viewport: row.viewport,
      scanFile: row.scanFile,
      coverage: row.coverage,
      attempts: row.attempts || 1,
      attemptErrors: row.attemptErrors || [],
    })),
  };

  const runFilePath = path.join(runDir, 'scan-coverage-report.json');
  const currentFilePath = path.join(SCAN_CURRENT_DIR, 'scan-coverage-report.json');
  fs.writeFileSync(runFilePath, JSON.stringify(report, null, 2), 'utf8');
  fs.copyFileSync(runFilePath, currentFilePath);
  return { runFilePath, currentFilePath };
}

function writeRunManifest(runDir, rows, options) {
  const manifest = {
    generatedAt: new Date().toISOString(),
    runStamp: RUN_STAMP,
    baseUrl: BASE_URL,
    rootDir: relativeFromRepo(SCAN_ROOT_DIR),
    runDir: relativeFromRepo(runDir),
    currentDir: relativeFromRepo(SCAN_CURRENT_DIR),
    options,
    scans: rows.map((row) => ({
      page: row.page,
      viewport: row.viewport,
      elements: row.elements,
      scanFile: row.scanFile,
      diffFile: row.diffFile || null,
      coverage: row.coverage || null,
      attempts: row.attempts || 1,
      attemptErrors: row.attemptErrors || [],
    })),
  };

  const runManifestPath = path.join(runDir, 'run_manifest.json');
  const currentManifestPath = path.join(SCAN_CURRENT_DIR, 'run_manifest.json');
  fs.writeFileSync(runManifestPath, JSON.stringify(manifest, null, 2), 'utf8');
  fs.copyFileSync(runManifestPath, currentManifestPath);
  return { runManifestPath, currentManifestPath };
}

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------

async function main() {
  const cli = parseArgs(process.argv.slice(2));
  if (cli.help) {
    printHelp();
    return;
  }

  const discovery = discoverDevModePages();
  const viewports = resolveViewports(cli.viewportSpecs, cli.multiViewport);
  const includeViewportInFilename = cli.viewportSpecs.length > 0 || cli.multiViewport || viewports.length > 1;
  const rawPage = cli.positionals[0];

  if (cli.listPages) {
    console.log('Discovered /dev-mode pages:');
    for (const p of discovery.pages) {
      console.log(`  - ${p.urlPath} (${p.name}) ← ${p.source}`);
    }
    if (discovery.pages.length === 0) console.log('  (none discovered)');
    if (discovery.warnings.length > 0) {
      console.log('\nDiscovery warnings:');
      for (const w of discovery.warnings) console.log(`  - ${w}`);
    }
    return;
  }

  if (discovery.pages.length === 0) {
    throw new Error('No /dev-mode pages discovered. Add app/dev-mode/*.html files or use --list-pages for diagnostics.');
  }

  // Fail fast before creating run/current directories if Playwright is unavailable.
  const chromiumBrowser = ensurePlaywrightChromium();

  const targets = resolveTargets(rawPage, cli.scanAll, discovery.pages);
  ensureDir(SCAN_ROOT_DIR);
  ensureDir(SCAN_RUNS_DIR);
  ensureDir(SCAN_CURRENT_DIR);
  ensureDir(SCAN_ARCHIVE_DIR);

  const archivedCurrentDir = rotateCurrentSnapshotsToArchive();
  const runDir = path.join(SCAN_RUNS_DIR, RUN_STAMP);
  ensureDir(runDir);

  console.log('\nDesign Telemetry Scanner');
  console.log(`  Base URL   : ${BASE_URL}`);
  console.log(`  Root dir   : ${relativeFromRepo(SCAN_ROOT_DIR)}`);
  console.log(`  Run dir    : ${relativeFromRepo(runDir)}`);
  console.log(`  Current dir: ${relativeFromRepo(SCAN_CURRENT_DIR)}`);
  if (archivedCurrentDir) {
    console.log(`  Archive dir: ${relativeFromRepo(archivedCurrentDir)} (previous current snapshot)`);
  }
  console.log(`  Pages      : ${targets.map((t) => t.name).join(', ')}`);
  console.log(`  Viewports  : ${viewports.map(viewportKey).join(', ')}`);
  console.log(`  Diff mode  : ${cli.diff ? 'on' : 'off'}`);
  console.log(`  Coverage   : ${cli.coverageReport ? 'report-on' : 'capture-only'}`);
  console.log(`  AutoDisc   : ${discovery.pages.length} route(s) found`);
  if (discovery.warnings.length > 0) {
    console.log(`  Warnings   : ${discovery.warnings.length} (use --list-pages to inspect)`);
  }
  console.log('');

  let browser;
  const results = [];

  try {
    browser = await chromiumBrowser.launch({ headless: true });
    for (const target of targets) {
      for (const vp of viewports) {
        const vpKey = viewportKey(vp);
        try {
          const result = await scanPage(browser, target, vp);
          const viewportPart = includeViewportInFilename ? vpKey : null;
          const previousScan = cli.diff ? findPreviousScan(result.pageName, viewportPart) : null;
          const scanFile = runArtifactPath(runDir, result.pageName, 'scan', viewportPart);
          const currentScanFile = currentArtifactPath(result.pageName, 'scan', viewportPart);
          fs.writeFileSync(scanFile, result.json, 'utf8');
          fs.copyFileSync(scanFile, currentScanFile);
          console.log(`  Saved      : ${path.basename(scanFile)} (run + current)`);
          if ((result.attempts || 1) > 1) {
            console.log(`  Retries    : succeeded on attempt ${result.attempts}/${SCAN_MAX_ATTEMPTS}`);
          }

          const coverage = normalizeCoverageMeta(result.parsed?.meta?.coverage);
          const coverageLine = formatCoverageLine(coverage);
          if (coverageLine) {
            console.log(`  Coverage   : ${coverageLine}`);
          } else {
            console.log('  Coverage   : unavailable (scan JSON has no meta.coverage)');
          }

          if (cli.diff) {
            if (previousScan) {
              const prevJson = fs.readFileSync(previousScan, 'utf8');
              const diff = diffScans(prevJson, result.json);
              const diffFile = runArtifactPath(runDir, result.pageName, 'diff', viewportPart);
              const currentDiffFile = currentArtifactPath(result.pageName, 'diff', viewportPart);
              fs.writeFileSync(diffFile, JSON.stringify(diff, null, 2), 'utf8');
              fs.copyFileSync(diffFile, currentDiffFile);
              const s = diff.summary;
              console.log(`  Diff       : ${s.changed} changed, ${s.added} added, ${s.removed} removed -> ${path.basename(diffFile)}`);
              results.push({
                page: result.pageName,
                viewport: vpKey,
                elements: result.parsed.meta?.count ?? 0,
                scanFile: path.basename(scanFile),
                diffFile: path.basename(diffFile),
                coverage,
                attempts: result.attempts || 1,
                attemptErrors: result.attemptErrors || [],
              });
            } else {
              console.log(`  Diff       : no prior scan found for '${result.pageName}'${viewportPart ? ` @ ${viewportPart}` : ''}`);
              results.push({
                page: result.pageName,
                viewport: vpKey,
                elements: result.parsed.meta?.count ?? 0,
                scanFile: path.basename(scanFile),
                diffFile: null,
                coverage,
                attempts: result.attempts || 1,
                attemptErrors: result.attemptErrors || [],
              });
            }
          } else {
            results.push({
              page: result.pageName,
              viewport: vpKey,
              elements: result.parsed.meta?.count ?? 0,
              scanFile: path.basename(scanFile),
              diffFile: null,
              coverage,
              attempts: result.attempts || 1,
              attemptErrors: result.attemptErrors || [],
            });
          }
        } catch (err) {
          console.error(`  Failed     : ${target.name} @ ${vpKey} — ${err.message}`);
        }
        console.log('');
      }
    }
  } catch (err) {
    removeDirIfEmpty(runDir);
    throw err;
  } finally {
    if (browser) await browser.close();
  }

  console.log('-'.repeat(84));
  console.log('  Page                 | Viewport  | Elements | Output file');
  console.log('-'.repeat(84));
  for (const r of results) {
    console.log(`  ${r.page.padEnd(20)} | ${r.viewport.padEnd(9)} | ${String(r.elements).padStart(8)} | ${r.scanFile}`);
  }
  console.log('-'.repeat(84));

  const manifest = writeRunManifest(runDir, results, {
    diff: cli.diff,
    coverageReport: cli.coverageReport,
    multiViewport: cli.multiViewport,
    viewportSpecs: cli.viewportSpecs,
    scanAll: cli.scanAll,
    pageArg: rawPage || null,
    archivedCurrentDir: archivedCurrentDir ? relativeFromRepo(archivedCurrentDir) : null,
  });
  console.log(`  Run manifest: ${path.basename(manifest.runManifestPath)} (run + current)`);

  if (cli.coverageReport) {
    const coveragePaths = writeCoverageReport(results, runDir);
    if (coveragePaths) {
      console.log(`  Coverage report: ${path.basename(coveragePaths.runFilePath)} (run + current)`);
    } else {
      console.log('  Coverage report: skipped (no coverage meta found in scan JSON)');
    }
  }

  console.log('\nDone\n');
}

main().catch((err) => {
  console.error(`\nFatal: ${err.message}`);
  process.exit(1);
});
