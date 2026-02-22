(function () {
  'use strict';

  const OVERLAY_SELECTOR = [
    'header', 'main', 'footer', 'section', 'article', 'nav', 'aside',
    'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
    'a', 'button', 'input', 'label', 'textarea', 'select',
    'img', 'svg', 'figure', 'figcaption', 'table', 'blockquote', 'pre', 'code'
  ].join(',');

  const PALETTE = ['#39ff14', '#00f5ff', '#ff4dff', '#ffd800', '#ff5a5f', '#7df9ff'];
  const PHI = 1.618;
  const BASE_GRID = 8;
  const MAX_SCAN_ELEMENTS = 450;
  const MAX_OVERLAY_BOXES = 280;

  const preview = document.getElementById('devmode-preview');
  const overlayLayer = document.getElementById('devmode-overlay-layer');
  const countEl = document.getElementById('devmode-count');
  const targetEl = document.getElementById('devmode-target');
  const statusEl = document.getElementById('devmode-status');
  const scanBtn = document.getElementById('devmode-scan-btn');

  let raf = null;
  let detachPreview = null;

  function normalizeTargetPath(value) {
    let text = String(value || '/').trim();
    if (!text) return '/';
    if (!text.startsWith('/')) text = `/${text}`;
    if (text === '/dev-mode' || text.startsWith('/dev-mode/')) return '/';
    return text;
  }

  function sanitizeAlgorithmFile(value) {
    const text = String(value || '').trim();
    if (!text) return null;
    if (!/^[a-zA-Z0-9._-]+\.json$/.test(text)) return null;
    return text;
  }

  function appendAlgoParam(pathname, algoFile) {
    if (!algoFile) return pathname;
    const base = `https://devmode.local${pathname.startsWith('/') ? pathname : `/${pathname}`}`;
    const url = new URL(base);
    if (!url.searchParams.get('algo')) {
      url.searchParams.set('algo', algoFile);
    }
    return `${url.pathname}${url.search}${url.hash}`;
  }

  function resolveTargetSpec() {
    const params = new URLSearchParams(window.location.search);
    const targetPath = normalizeTargetPath(params.get('target') || '/');
    const algoFile = sanitizeAlgorithmFile(params.get('algo'));
    return {
      targetPath: appendAlgoParam(targetPath, algoFile),
      algoFile,
    };
  }

  const targetSpec = resolveTargetSpec();
  preview.src = targetSpec.targetPath;
  targetEl.textContent = targetSpec.algoFile
    ? `target=${targetSpec.targetPath} algo=${targetSpec.algoFile}`
    : `target=${targetSpec.targetPath}`;

  function getPreviewContext() {
    const win = preview.contentWindow;
    const doc = preview.contentDocument || (win && win.document);
    if (!win || !doc || !doc.documentElement || !doc.body) return null;
    return { win, doc };
  }

  function clamp01(v) {
    if (!Number.isFinite(v)) return 0;
    return Math.max(0, Math.min(1, v));
  }

  function safeNumber(v, fallback) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  }

  function normalizedText(input) {
    return String(input || '').replace(/\s+/g, ' ').trim().slice(0, 280);
  }

  function parseColor(input) {
    if (!input) return null;
    const text = String(input).trim().toLowerCase();
    if (!text || text === 'transparent') return { r: 0, g: 0, b: 0, a: 0 };
    const m = text.match(/^rgba?\(([^)]+)\)$/);
    if (!m) return null;

    const parts = m[1].split(',').map((p) => p.trim());
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
    return 0.2126 * toLinear(c.r) + 0.7152 * toLinear(c.g) + 0.0722 * toLinear(c.b);
  }

  function contrastRatio(fg, bg) {
    const l1 = luminance(fg);
    const l2 = luminance(bg);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return Math.round(((lighter + 0.05) / (darker + 0.05)) * 1000) / 1000;
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

  function resolveBackground(win, doc, el) {
    let composed = { r: 255, g: 255, b: 255, a: 1 };
    let node = el;
    let hops = 0;

    while (node && hops < 40) {
      const style = win.getComputedStyle(node);
      const color = parseColor(style.backgroundColor);
      if (color && color.a > 0) {
        composed = blend(color, composed);
        if (composed.a >= 0.999) break;
      }
      if (node === doc.documentElement) break;
      node = node.parentElement;
      hops += 1;
    }

    return composed;
  }

  function collectTrackedElements(win, doc, maxElements, includeCoverage) {
    const nodes = Array.from(doc.querySelectorAll(OVERLAY_SELECTOR));
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

    const docEl = doc.documentElement;
    const body = doc.body;
    const pageWidth = Math.max(
      docEl ? docEl.scrollWidth : 0,
      docEl ? docEl.clientWidth : 0,
      body ? body.scrollWidth : 0,
      body ? body.clientWidth : 0,
      win.innerWidth || 0,
    );
    const pageHeight = Math.max(
      docEl ? docEl.scrollHeight : 0,
      docEl ? docEl.clientHeight : 0,
      body ? body.scrollHeight : 0,
      body ? body.clientHeight : 0,
      win.innerHeight || 0,
    );

    for (const el of uniqueNodes) {
      const style = win.getComputedStyle(el);
      const rect = el.getBoundingClientRect();

      const width = safeNumber(rect.width, 0);
      const height = safeNumber(rect.height, 0);

      if (width < 6 || height < 6) {
        dropped['too-small'] += 1;
        continue;
      }

      if (style.display === 'none' || style.visibility === 'hidden' || safeNumber(style.opacity, 1) === 0) {
        dropped.hidden += 1;
        continue;
      }

      const absX = safeNumber(rect.left, 0) + safeNumber(win.scrollX, 0);
      const absY = safeNumber(rect.top, 0) + safeNumber(win.scrollY, 0);

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
      const fontSizePx = safeNumber(String(style.fontSize).replace('px', ''), 16);
      const lineHeightPx = safeNumber(String(style.lineHeight).replace('px', ''), fontSizePx * 1.25);
      const fontWeight = safeNumber(style.fontWeight, 400);
      const letterSpacingPx = safeNumber(String(style.letterSpacing).replace('px', ''), 0);
      const color = parseColor(style.color) || { r: 0, g: 0, b: 0, a: 1 };
      const background = resolveBackground(win, doc, el);
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

    if (!includeCoverage) return { elements, coverage: null, pageWidth, pageHeight, uniqueNodes };

    const scannedCount = elements.length;
    const uniqueCandidateCount = uniqueNodes.length;
    const selectorCandidateCount = nodes.length;
    const capped = scannedCount >= maxElements && includeableCount > maxElements;

    return {
      elements,
      pageWidth,
      pageHeight,
      uniqueNodes,
      coverage: {
        mode: 'devmode-overlay',
        selectorCandidateCount,
        uniqueCandidateCount,
        includeableCount,
        scannedCount,
        scanCap: maxElements,
        capped,
        dropped,
        scannedRatioOfUnique: uniqueCandidateCount > 0 ? Math.round((scannedCount / uniqueCandidateCount) * 1000) / 1000 : 0,
        scannedRatioOfIncludeable: includeableCount > 0 ? Math.round((scannedCount / includeableCount) * 1000) / 1000 : 0,
      },
    };
  }

  function computeOverlayBoxes() {
    const ctx = getPreviewContext();
    if (!ctx) return [];
    const { win, doc } = ctx;
    const snap = collectTrackedElements(win, doc, MAX_OVERLAY_BOXES, false);
    const frameRect = preview.getBoundingClientRect();

    return snap.elements.map((el, idx) => {
      const depth = String(el.planarPhysics && el.planarPhysics.parentFrameId ? el.planarPhysics.parentFrameId : 'root').split('>').length - 1;
      return {
        id: `${idx}-${el.geometry.x}-${el.geometry.y}`,
        index: idx + 1,
        depth,
        label: el.label,
        top: frameRect.top + (el.geometry.y - win.scrollY),
        left: frameRect.left + (el.geometry.x - win.scrollX),
        width: el.geometry.width,
        height: el.geometry.height,
      };
    });
  }

  function renderOverlay(boxes) {
    overlayLayer.innerHTML = '';
    const frag = document.createDocumentFragment();

    for (const box of boxes) {
      const color = PALETTE[box.depth % PALETTE.length];
      const el = document.createElement('div');
      el.className = 'devmode-overlay-box';
      el.style.top = `${box.top}px`;
      el.style.left = `${box.left}px`;
      el.style.width = `${box.width}px`;
      el.style.height = `${box.height}px`;
      el.style.borderColor = color;
      el.style.boxShadow = `0 0 0 1px ${color}66, 0 0 10px ${color}44`;

      const label = document.createElement('span');
      label.className = 'devmode-overlay-label';
      label.style.background = color;
      label.textContent = `${box.index} d${box.depth} ${box.label}`;
      el.appendChild(label);

      frag.appendChild(el);
    }

    overlayLayer.appendChild(frag);
    countEl.textContent = `${boxes.length} live boxes`;
  }

  function scheduleRefresh() {
    if (raf !== null) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      raf = null;
      renderOverlay(computeOverlayBoxes());
    });
  }

  function detachPreviewListenersIfAny() {
    if (typeof detachPreview === 'function') {
      detachPreview();
      detachPreview = null;
    }
  }

  function attachPreviewListeners() {
    const ctx = getPreviewContext();
    if (!ctx) return;
    const { win, doc } = ctx;

    const onScroll = () => scheduleRefresh();
    const onResize = () => scheduleRefresh();

    win.addEventListener('scroll', onScroll, true);
    win.addEventListener('resize', onResize, true);

    const obs = new MutationObserver(() => scheduleRefresh());
    obs.observe(doc.body, { subtree: true, childList: true, attributes: true });

    detachPreview = function () {
      win.removeEventListener('scroll', onScroll, true);
      win.removeEventListener('resize', onResize, true);
      obs.disconnect();
    };
  }

  function themeLabel(doc) {
    const explicit = doc.documentElement.getAttribute('data-theme');
    if (explicit) return explicit;
    const cls = String(doc.documentElement.className || '');
    if (/\bdark\b/i.test(cls)) return 'dark';
    if (/\blight\b/i.test(cls)) return 'light';
    return 'default';
  }

  function buildInventory(maxElements) {
    const ctx = getPreviewContext();
    if (!ctx) throw new Error('Preview is not ready');
    const { win, doc } = ctx;

    const collected = collectTrackedElements(win, doc, maxElements, true);
    const elements = collected.elements;

    for (const element of elements) {
      const g = element.geometry;
      if (!g || !Number.isFinite(g.width) || !Number.isFinite(g.height) || g.height === 0) continue;
      const ratio = Number(g.width) / Number(g.height);
      element.goldenRatio = {
        compliance: Math.abs(ratio - PHI) < 0.15 ? 'near' : 'off',
        phiDeviation: Math.round(Math.abs(ratio - PHI) * 1000) / 1000,
        verticalRhythm: {
          score: Math.round((1 - ((Number(g.y) % BASE_GRID) / BASE_GRID)) * 1000) / 1000,
        },
      };
    }

    return {
      meta: {
        url: win.location.href,
        timestamp: new Date().toISOString(),
        theme: themeLabel(doc),
        viewport: {
          width: win.innerWidth,
          height: win.innerHeight,
        },
        pageSize: {
          width: collected.pageWidth,
          height: collected.pageHeight,
        },
        count: elements.length,
        coverage: collected.coverage,
        project: {
          framework: 'static-html-devmode',
          styling: 'css',
          themeStrategy: 'runtime-snapshot',
        },
        goldenConstants: {
          phi: PHI,
          baseUnit: 8,
          baseGrid: BASE_GRID,
        },
      },
      elements,
    };
  }

  function exportScan(maxElements) {
    const inventory = buildInventory(Number(maxElements) || MAX_SCAN_ELEMENTS);
    const json = JSON.stringify(inventory, null, 2);

    window.__DEV_MODE_LAST_SCAN_JSON = json;
    window.__DEV_MODE_LAST_SCAN_META = inventory.meta;

    navigator.clipboard.writeText(json).catch(function () {
      // Clipboard can fail in non-secure contexts; the global export still works.
    });

    return json;
  }

  window.__DEV_MODE_EXPORT_SCAN = exportScan;

  scanBtn.addEventListener('click', function () {
    scanBtn.textContent = 'SCANNING...';
    statusEl.textContent = 'collecting telemetry';

    requestAnimationFrame(function () {
      try {
        exportScan(MAX_SCAN_ELEMENTS);
        scanBtn.textContent = 'COPIED!';
        statusEl.textContent = `captured ${new Date().toLocaleTimeString()}`;
        setTimeout(function () {
          scanBtn.textContent = 'SCAN & COPY';
        }, 1800);
      } catch (err) {
        scanBtn.textContent = 'SCAN & COPY';
        statusEl.textContent = `scan failed: ${err && err.message ? err.message : String(err)}`;
      }
    });
  });

  preview.addEventListener('load', function () {
    detachPreviewListenersIfAny();
    attachPreviewListeners();
    statusEl.textContent = 'preview loaded';
    scheduleRefresh();
  });

  window.addEventListener('resize', scheduleRefresh, true);

  // Initial render attempt (in case iframe loads quickly from cache).
  setTimeout(scheduleRefresh, 50);
})();
