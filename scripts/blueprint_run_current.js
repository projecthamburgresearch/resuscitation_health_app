#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = process.cwd();
const DEFAULT_BLUEPRINT_ROOT = path.join(ROOT, 'appendix/blueprint');
const DEFAULT_OUTPUT_ROOT = path.join(ROOT, 'appendix/blueprint_outputs');
const DEFAULT_BLUEPRINT_VENV = '.venv';
const BPIGNORE_FILE = '.bpignore';
const MANAGED_BPIGNORE_START = '# codex-blueprint-run-current:start';
const MANAGED_BPIGNORE_END = '# codex-blueprint-run-current:end';

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function parseArgs(argv) {
  const out = {
    preset: 'standard',
    projectRoot: path.join(ROOT, 'app'),
    blueprintRoot: DEFAULT_BLUEPRINT_ROOT,
    outputRoot: DEFAULT_OUTPUT_ROOT,
    skipAudit: false,
    bootstrapVenv: false,
    excludeDevMode: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--preset') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --preset');
      out.preset = next;
      i += 1;
    } else if (arg.startsWith('--preset=')) {
      out.preset = arg.split('=', 2)[1];
    } else if (arg === '--project-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --project-root');
      out.projectRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--project-root=')) {
      out.projectRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--blueprint-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --blueprint-root');
      out.blueprintRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--blueprint-root=')) {
      out.blueprintRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--output-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --output-root');
      out.outputRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--output-root=')) {
      out.outputRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--skip-audit') {
      out.skipAudit = true;
    } else if (arg === '--bootstrap-venv') {
      out.bootstrapVenv = true;
    } else if (arg === '--exclude-dev-mode') {
      out.excludeDevMode = true;
    } else if (arg === '--no-exclude-dev-mode') {
      out.excludeDevMode = false;
    } else if (arg === '--help' || arg === '-h') {
      console.log(`
Usage:
  node scripts/blueprint_run_current.js
  node scripts/blueprint_run_current.js --preset standard
  node scripts/blueprint_run_current.js --project-root . --blueprint-root appendix/blueprint
  node scripts/blueprint_run_current.js --bootstrap-venv
  node scripts/blueprint_run_current.js --skip-audit
  node scripts/blueprint_run_current.js --exclude-dev-mode

Behavior:
  1) Runs blueprint full scan on the current project
  2) Writes raw run outputs to appendix/blueprint_outputs/runs/<timestamp>/
  3) Archives previous current snapshot to appendix/blueprint_outputs/archive/current-<timestamp>/
  4) Syncs latest artifacts to appendix/blueprint_outputs/current/
  5) Runs scripts/blueprint_app_audit.js against current artifacts (unless --skip-audit)

Notes:
  - Default project root is app/ for focused static-surface analysis.
  - Use --exclude-dev-mode only if you add a dev-mode mirror later and want
    it excluded from the full Blueprint scan.
`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }
  return out;
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function rotateCurrentToArchive(currentDir, archiveRoot, stamp) {
  ensureDir(currentDir);
  ensureDir(archiveRoot);
  const entries = fs.readdirSync(currentDir, { withFileTypes: true });
  if (entries.length === 0) return null;

  const archiveDir = path.join(archiveRoot, `current-${stamp}`);
  ensureDir(archiveDir);
  for (const entry of entries) {
    fs.renameSync(path.join(currentDir, entry.name), path.join(archiveDir, entry.name));
  }
  return archiveDir;
}

function copyArtifactFiles(srcDir, dstDir) {
  ensureDir(dstDir);
  const files = fs.readdirSync(srcDir, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .filter((name) => /\.(json|ya?ml|md)$/i.test(name));

  for (const file of files) {
    const src = path.join(srcDir, file);
    const dst = path.join(dstDir, file);
    fs.copyFileSync(src, dst);
  }
  return files;
}

function runCommand(cmd, args, cwd) {
  return spawnSync(cmd, args, { cwd, stdio: 'inherit' });
}

function removeDirIfEmpty(dirPath) {
  try {
    const entries = fs.readdirSync(dirPath);
    if (entries.length === 0) fs.rmdirSync(dirPath);
  } catch {
    // best-effort cleanup only
  }
}

function resolveBlueprintPython(blueprintRoot) {
  if (process.env.BLUEPRINT_PYTHON) return process.env.BLUEPRINT_PYTHON;

  const venvDir = path.join(blueprintRoot, DEFAULT_BLUEPRINT_VENV, 'bin');
  const candidates = [
    path.join(venvDir, 'python3'),
    path.join(venvDir, 'python'),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return 'python3';
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function resolveManagedBpignorePatterns(projectRoot) {
  const target = path.join(ROOT, 'app', 'dev-mode');
  const rel = path.relative(projectRoot, target).replace(/\\/g, '/');

  // If app/dev-mode is inside the active project root, use that relative pattern.
  if (rel && !rel.startsWith('..')) {
    const normalized = rel.replace(/\/+$/, '');
    return [`${normalized}/`];
  }

  // Fallback for non-standard roots.
  return ['app/dev-mode/'];
}

function managedBpignoreBlock(patterns) {
  const lines = [
    MANAGED_BPIGNORE_START,
    '# Added by scripts/blueprint_run_current.js to keep dev-mode mirror routes out of full Blueprint scans.',
    ...patterns,
    MANAGED_BPIGNORE_END,
  ];
  return `${lines.join('\n')}\n`;
}

function upsertManagedBpignore(filePath, patterns) {
  const originalExists = fs.existsSync(filePath);
  const originalText = originalExists ? fs.readFileSync(filePath, 'utf8') : '';
  const block = managedBpignoreBlock(patterns);
  const managedBlockRegex = new RegExp(
    `${escapeRegExp(MANAGED_BPIGNORE_START)}[\\s\\S]*?${escapeRegExp(MANAGED_BPIGNORE_END)}\\n?`,
    'g',
  );

  const withoutManaged = originalText.replace(managedBlockRegex, '').trimEnd();
  const nextText = withoutManaged.length > 0
    ? `${withoutManaged}\n\n${block}`
    : block;

  fs.writeFileSync(filePath, nextText, 'utf8');
  return { filePath, originalExists, originalText };
}

function restoreBpignore(state) {
  if (!state) return;
  if (state.originalExists) {
    fs.writeFileSync(state.filePath, state.originalText, 'utf8');
    return;
  }
  if (fs.existsSync(state.filePath)) {
    fs.unlinkSync(state.filePath);
  }
}

function bootstrapVenv(blueprintRoot) {
  const venvPython = path.join(blueprintRoot, DEFAULT_BLUEPRINT_VENV, 'bin', 'python3');
  if (!fs.existsSync(venvPython)) {
    const create = runCommand('python3', ['-m', 'venv', DEFAULT_BLUEPRINT_VENV], blueprintRoot);
    if (create.status !== 0) return create.status || 1;
  }
  const install = runCommand(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt'], blueprintRoot);
  return install.status || 0;
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  const stamp = nowStamp();
  const runDir = path.join(opts.outputRoot, 'runs', stamp);
  const currentDir = path.join(opts.outputRoot, 'current');
  const archiveRoot = path.join(opts.outputRoot, 'archive');

  if (!['quick', 'standard', 'deep'].includes(opts.preset)) {
    throw new Error(`Invalid --preset '${opts.preset}'. Use one of: quick, standard, deep`);
  }
  if (!fs.existsSync(opts.blueprintRoot)) {
    throw new Error(`Blueprint root not found: ${path.relative(ROOT, opts.blueprintRoot)}`);
  }

  if (opts.bootstrapVenv) {
    console.log('\nBootstrapping Blueprint venv...');
    const bootstrapStatus = bootstrapVenv(opts.blueprintRoot);
    if (bootstrapStatus !== 0) {
      console.error('\nBlueprint venv bootstrap failed.');
      process.exit(bootstrapStatus);
    }
  }

  const blueprintPython = resolveBlueprintPython(opts.blueprintRoot);
  const pythonLabel = path.isAbsolute(blueprintPython)
    ? (path.relative(ROOT, blueprintPython) || blueprintPython)
    : blueprintPython;

  ensureDir(runDir);
  const archivedCurrentDir = rotateCurrentToArchive(currentDir, archiveRoot, stamp);

  console.log('\nBlueprint Current Run');
  console.log(`  Blueprint root : ${path.relative(ROOT, opts.blueprintRoot)}`);
  console.log(`  Project root   : ${path.relative(ROOT, opts.projectRoot) || '.'}`);
  console.log(`  Run output     : ${path.relative(ROOT, runDir)}`);
  console.log(`  Current output : ${path.relative(ROOT, currentDir)}`);
  if (archivedCurrentDir) {
    console.log(`  Archive output : ${path.relative(ROOT, archivedCurrentDir)} (previous current snapshot)`);
  }
  console.log(`  Preset         : ${opts.preset}`);
  console.log(`  Python         : ${pythonLabel}`);
  console.log(`  Exclude dev    : ${opts.excludeDevMode ? 'enabled (.bpignore-managed)' : 'disabled'}`);
  console.log('');

  let bpignoreState = null;
  if (opts.excludeDevMode) {
    const bpignorePath = path.join(opts.projectRoot, BPIGNORE_FILE);
    const bpignorePatterns = resolveManagedBpignorePatterns(opts.projectRoot);
    bpignoreState = upsertManagedBpignore(bpignorePath, bpignorePatterns);
  }

  const scanArgs = [
    '-m', 'src.cli', 'scan',
    '--root', opts.projectRoot,
    '--output', runDir,
    '--preset', opts.preset,
    '--no-git',
    '--format', 'yaml',
  ];
  let scanResult;
  try {
    scanResult = runCommand(blueprintPython, scanArgs, opts.blueprintRoot);
  } finally {
    restoreBpignore(bpignoreState);
  }
  if (scanResult.status !== 0) {
    removeDirIfEmpty(runDir);
    console.error('\nBlueprint scan failed.');
    console.error('If dependencies are missing, bootstrap a local venv with:');
    console.error('  node scripts/blueprint_run_current.js --bootstrap-venv');
    process.exit(scanResult.status || 1);
  }

  const synced = copyArtifactFiles(runDir, currentDir);
  const runManifest = {
    generatedAt: new Date().toISOString(),
    blueprintRoot: path.relative(ROOT, opts.blueprintRoot),
    projectRoot: path.relative(ROOT, opts.projectRoot) || '.',
    runDir: path.relative(ROOT, runDir),
    currentDir: path.relative(ROOT, currentDir),
    archivedCurrentDir: archivedCurrentDir ? path.relative(ROOT, archivedCurrentDir) : null,
    preset: opts.preset,
    excludeDevMode: opts.excludeDevMode,
    filesSynced: synced,
  };
  fs.writeFileSync(path.join(currentDir, 'run_manifest.json'), `${JSON.stringify(runManifest, null, 2)}\n`, 'utf8');

  if (!opts.skipAudit) {
    const auditArgs = [
      'scripts/blueprint_app_audit.js',
      '--blueprint-dir', currentDir,
      '--output-dir', currentDir,
    ];
    const auditResult = runCommand('node', auditArgs, ROOT);
    if (auditResult.status !== 0) process.exit(auditResult.status || 1);
  }

  console.log('\nBlueprint current artifacts refreshed.');
  console.log(`  Current bundle: ${path.relative(ROOT, currentDir)}`);
  console.log('');
}

try {
  main();
} catch (err) {
  console.error(`\nFatal: ${err.message}`);
  process.exit(1);
}
