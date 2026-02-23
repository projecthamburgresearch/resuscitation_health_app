'use strict';

const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const {
  normalizeSlugFromHtmlRel,
  discoverPages,
  calculateParity
} = require('./check_dev_mode_parity.js');

test('normalizeSlugFromHtmlRel', async (t) => {
  await t.test('should handle empty or null input', () => {
    assert.strictEqual(normalizeSlugFromHtmlRel(''), '');
    assert.strictEqual(normalizeSlugFromHtmlRel(null), '');
  });

  await t.test('should handle index.html', () => {
    assert.strictEqual(normalizeSlugFromHtmlRel('index.html'), '');
    assert.strictEqual(normalizeSlugFromHtmlRel('INDEX.HTML'), '');
  });

  await t.test('should handle resuscitation_app_complete.html', () => {
    assert.strictEqual(normalizeSlugFromHtmlRel('resuscitation_app_complete.html'), '');
  });

  await t.test('should handle nested index.html', () => {
    assert.strictEqual(normalizeSlugFromHtmlRel('nested/index.html'), 'nested');
  });

  await t.test('should handle simple page', () => {
    assert.strictEqual(normalizeSlugFromHtmlRel('about.html'), 'about');
  });

  await t.test('should handle nested page', () => {
    assert.strictEqual(normalizeSlugFromHtmlRel('path/to/page.html'), 'path/to/page');
  });

  await t.test('should handle windows paths', () => {
    assert.strictEqual(normalizeSlugFromHtmlRel('path\\to\\page.html'), 'path/to/page');
  });
});

test('discoverPages', async (t) => {
  const mockFs = {
    existsSync: (p) => {
      return p === '/app' || p === '/app/subdir' || p === '/app/dev-mode';
    },
    readdirSync: (p, opts) => {
      if (p === '/app') {
        return [
          { name: 'index.html', isFile: () => true, isDirectory: () => false },
          { name: 'about.html', isFile: () => true, isDirectory: () => false },
          { name: 'subdir', isFile: () => false, isDirectory: () => true },
          { name: 'dev-mode', isFile: () => false, isDirectory: () => true },
        ];
      }
      if (p === '/app/subdir') {
        return [
          { name: 'nested.html', isFile: () => true, isDirectory: () => false },
        ];
      }
      return [];
    }
  };

  await t.test('should discover pages and apply skips', () => {
    const pages = discoverPages('/app', '/app', mockFs, ['dev-mode']);
    assert.deepStrictEqual(pages.sort(), ['', 'about', 'subdir/nested'].sort());
  });

  await t.test('should return empty array if directory does not exist', () => {
    const emptyFs = { existsSync: () => false };
    const pages = discoverPages('/none', '/none', emptyFs);
    assert.deepStrictEqual(pages, []);
  });
});

test('calculateParity', async (t) => {
  const mainPages = ['', 'about', 'contact'];

  await t.test('should pass when pages match exactly', () => {
    const devPages = ['', 'about', 'contact'];
    const result = calculateParity(mainPages, devPages);
    assert.strictEqual(result.success, true);
    assert.strictEqual(result.missingInDev.length, 0);
    assert.strictEqual(result.extraInDev.length, 0);
  });

  await t.test('should fail when pages are missing in dev', () => {
    const devPages = ['', 'about'];
    const result = calculateParity(mainPages, devPages);
    assert.strictEqual(result.success, false);
    assert.deepStrictEqual(result.missingInDev, ['contact']);
  });

  await t.test('should fail when extra pages are in dev (strict mode)', () => {
    const devPages = ['', 'about', 'contact', 'extra'];
    const result = calculateParity(mainPages, devPages, { allowExtraDev: false });
    assert.strictEqual(result.success, false);
    assert.deepStrictEqual(result.extraInDev, ['extra']);
  });

  await t.test('should pass when extra pages are in dev (non-strict mode)', () => {
    const devPages = ['', 'about', 'contact', 'extra'];
    const result = calculateParity(mainPages, devPages, { allowExtraDev: true });
    assert.strictEqual(result.success, true);
    assert.deepStrictEqual(result.extraInDev, ['extra']);
  });
});
