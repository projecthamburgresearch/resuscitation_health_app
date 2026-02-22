#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const http = require('http');
const { URL } = require('url');

const ROOT = process.cwd();
const DEFAULT_ROOT_DIR = path.join(ROOT, 'app');

function parseArgs(argv) {
  const out = {
    port: Number(process.env.PORT || 3000),
    host: process.env.HOST || '127.0.0.1',
    rootDir: process.env.APP_ROOT || DEFAULT_ROOT_DIR,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--port') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --port');
      out.port = Number(next);
      i += 1;
    } else if (arg.startsWith('--port=')) {
      out.port = Number(arg.split('=', 2)[1]);
    } else if (arg === '--host') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --host');
      out.host = next;
      i += 1;
    } else if (arg.startsWith('--host=')) {
      out.host = arg.split('=', 2)[1];
    } else if (arg === '--root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --root');
      out.rootDir = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--root=')) {
      out.rootDir = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--help' || arg === '-h') {
      console.log(`\nUsage:\n  node scripts/dev_server.js\n  node scripts/dev_server.js --port 3000 --host 127.0.0.1 --root app\n`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }

  if (!Number.isFinite(out.port) || out.port <= 0) {
    throw new Error('Invalid --port. Must be a positive integer.');
  }

  return out;
}

function sanitizePathname(pathname) {
  const normalized = path.posix.normalize(`/${pathname || ''}`).replace(/^\/+/g, '/');
  return normalized;
}

function fileExists(filePath) {
  try {
    const stat = fs.statSync(filePath);
    return stat.isFile();
  } catch {
    return false;
  }
}

function resolveFile(rootDir, pathname) {
  const cleaned = sanitizePathname(pathname);
  const decoded = decodeURIComponent(cleaned);

  const candidates = [];
  if (decoded === '/' || decoded === '') {
    candidates.push('/index.html');
  } else {
    candidates.push(decoded);
    if (!decoded.endsWith('/')) candidates.push(`${decoded}.html`);
    candidates.push(`${decoded.replace(/\/+$/, '')}/index.html`);
  }

  for (const candidate of candidates) {
    const absPath = path.resolve(rootDir, `.${candidate}`);
    if (!absPath.startsWith(path.resolve(rootDir))) continue;
    if (fileExists(absPath)) return absPath;
  }

  return null;
}

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.html' || ext === '.htm') return 'text/html; charset=utf-8';
  if (ext === '.css') return 'text/css; charset=utf-8';
  if (ext === '.js') return 'application/javascript; charset=utf-8';
  if (ext === '.json') return 'application/json; charset=utf-8';
  if (ext === '.svg') return 'image/svg+xml';
  if (ext === '.png') return 'image/png';
  if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg';
  if (ext === '.gif') return 'image/gif';
  if (ext === '.webp') return 'image/webp';
  if (ext === '.ico') return 'image/x-icon';
  if (ext === '.txt') return 'text/plain; charset=utf-8';
  return 'application/octet-stream';
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  const rootDir = path.resolve(opts.rootDir);

  if (!fs.existsSync(rootDir)) {
    throw new Error(`Root directory not found: ${rootDir}`);
  }

  const server = http.createServer((req, res) => {
    try {
      const reqUrl = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
      const filePath = resolveFile(rootDir, reqUrl.pathname);

      if (!filePath) {
        res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
        res.end('Not Found\n');
        return;
      }

      const stat = fs.statSync(filePath);
      const headers = {
        'content-type': contentType(filePath),
        'content-length': String(stat.size),
        'cache-control': 'no-cache',
      };

      if (req.method === 'HEAD') {
        res.writeHead(200, headers);
        res.end();
        return;
      }

      res.writeHead(200, headers);
      const stream = fs.createReadStream(filePath);
      stream.on('error', (err) => {
        res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' });
        res.end(`Read error: ${err.message}\n`);
      });
      stream.pipe(res);
    } catch (err) {
      res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' });
      res.end(`Server error: ${err.message}\n`);
    }
  });

  server.listen(opts.port, opts.host, () => {
    console.log(`Static server running at http://${opts.host}:${opts.port}`);
    console.log(`Serving: ${path.relative(ROOT, rootDir) || rootDir}`);
  });

  const shutdown = () => {
    server.close(() => process.exit(0));
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

try {
  main();
} catch (err) {
  console.error(`Fatal: ${err.message}`);
  process.exit(1);
}
