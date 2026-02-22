#!/usr/bin/env node
'use strict';

const http = require('http');
const https = require('https');
const path = require('path');
const { URL } = require('url');
const { spawn, spawnSync } = require('child_process');

const ROOT = process.cwd();
const DEFAULT_BASE_URL = process.env.ANALYZE_BASE_URL || 'http://127.0.0.1:3000';
const DEFAULT_PROJECT_ROOT = path.join(ROOT, 'app');
const DEFAULT_GITHUB_REF = 'main';
const DEFAULT_VIEWPORT_SPEC = process.env.ANALYZE_VIEWPORT || '390x844';

const LANE_DEFAULTS = {
  warden: {
    blueprintOutputRoot: path.join(ROOT, 'appendix/guidance/warden/blueprint_outputs'),
    scanOutputRoot: path.join(ROOT, 'appendix/guidance/warden/scans_outputs'),
    designRoot: path.join(ROOT, 'appendix/guidance/warden/design'),
    workspacePath: path.join(ROOT, 'appendix/blueprint/blueprint_outputs_warden'),
  },
  system: {
    blueprintOutputRoot: path.join(ROOT, 'appendix/system/blueprint_outputs'),
    scanOutputRoot: path.join(ROOT, 'appendix/system/scans_outputs'),
    designRoot: path.join(ROOT, 'appendix/system/design'),
    workspacePath: path.join(ROOT, 'appendix/blueprint/blueprint_outputs_system'),
  },
};

function rel(filePath) {
  return path.relative(ROOT, filePath) || '.';
}

function latestDirectory(dirPath) {
  const fs = require('fs');
  if (!fs.existsSync(dirPath)) return null;
  const dirs = fs.readdirSync(dirPath, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(dirPath, entry.name));
  if (dirs.length === 0) return null;
  dirs.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return dirs[0];
}

function parseArgs(argv) {
  const out = {
    lane: 'warden',
    source: 'local',
    baseUrl: DEFAULT_BASE_URL,
    viewportSpecs: [],
    keepDev: false,
    skipParity: false,
    skipBlueprint: false,
    skipScan: false,
    skipDesignBundle: false,
    includeUiStages: false,
    devTimeoutSeconds: 180,
    withCertificate: null,

    projectRoot: DEFAULT_PROJECT_ROOT,
    repo: '',
    ref: DEFAULT_GITHUB_REF,
    tokenEnv: '',
    targetName: '',
    preset: 'standard',

    blueprintOutputRoot: '',
    scanOutputRoot: '',
    designRoot: '',
    workspacePath: '',
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--lane') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --lane');
      out.lane = next.trim().toLowerCase();
      i += 1;
    } else if (arg.startsWith('--lane=')) {
      out.lane = arg.split('=', 2)[1].trim().toLowerCase();
    } else if (arg === '--source') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --source');
      out.source = next.trim().toLowerCase();
      i += 1;
    } else if (arg.startsWith('--source=')) {
      out.source = arg.split('=', 2)[1].trim().toLowerCase();
    } else if (arg === '--project-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --project-root');
      out.projectRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--project-root=')) {
      out.projectRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--repo') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --repo');
      out.repo = next.trim();
      i += 1;
    } else if (arg.startsWith('--repo=')) {
      out.repo = arg.split('=', 2)[1].trim();
    } else if (arg === '--ref') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --ref');
      out.ref = next.trim();
      i += 1;
    } else if (arg.startsWith('--ref=')) {
      out.ref = arg.split('=', 2)[1].trim();
    } else if (arg === '--token-env') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --token-env');
      out.tokenEnv = next.trim();
      i += 1;
    } else if (arg.startsWith('--token-env=')) {
      out.tokenEnv = arg.split('=', 2)[1].trim();
    } else if (arg === '--target-name') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --target-name');
      out.targetName = next.trim();
      i += 1;
    } else if (arg.startsWith('--target-name=')) {
      out.targetName = arg.split('=', 2)[1].trim();
    } else if (arg === '--preset') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --preset');
      out.preset = next.trim();
      i += 1;
    } else if (arg.startsWith('--preset=')) {
      out.preset = arg.split('=', 2)[1].trim();
    } else if (arg === '--base-url') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --base-url');
      out.baseUrl = next;
      i += 1;
    } else if (arg.startsWith('--base-url=')) {
      out.baseUrl = arg.split('=', 2)[1];
    } else if (arg === '--viewport') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --viewport');
      out.viewportSpecs.push(next);
      i += 1;
    } else if (arg.startsWith('--viewport=')) {
      out.viewportSpecs.push(arg.split('=', 2)[1]);
    } else if (arg === '--blueprint-output-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --blueprint-output-root');
      out.blueprintOutputRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--blueprint-output-root=')) {
      out.blueprintOutputRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--scan-output-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --scan-output-root');
      out.scanOutputRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--scan-output-root=')) {
      out.scanOutputRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--design-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --design-root');
      out.designRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--design-root=')) {
      out.designRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--workspace-path') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --workspace-path');
      out.workspacePath = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--workspace-path=')) {
      out.workspacePath = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--keep-dev') {
      out.keepDev = true;
    } else if (arg === '--skip-parity') {
      out.skipParity = true;
    } else if (arg === '--skip-blueprint') {
      out.skipBlueprint = true;
    } else if (arg === '--skip-scan') {
      out.skipScan = true;
    } else if (arg === '--skip-design-bundle') {
      out.skipDesignBundle = true;
    } else if (arg === '--include-ui-stages') {
      out.includeUiStages = true;
    } else if (arg === '--with-certificate') {
      out.withCertificate = true;
    } else if (arg === '--no-certificate') {
      out.withCertificate = false;
    } else if (arg === '--dev-timeout') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --dev-timeout');
      out.devTimeoutSeconds = Number(next);
      i += 1;
    } else if (arg.startsWith('--dev-timeout=')) {
      out.devTimeoutSeconds = Number(arg.split('=', 2)[1]);
    } else if (arg === '--help' || arg === '-h') {
      console.log(`
Usage:
  node scripts/run_unified_analysis.js
  node scripts/run_unified_analysis.js --lane warden --source local
  node scripts/run_unified_analysis.js --lane system --source local
  node scripts/run_unified_analysis.js --lane warden --source github --repo owner/repo --ref main
  node scripts/run_unified_analysis.js --lane system --source github --repo owner/repo --ref main

Default pipeline:
  1) Optional parity check (local source only)
  2) Blueprint workspace run (lane-aware outputs)
  3) Optional UI stages: ensure local dev server, then scan + design bundle
  4) Stop dev server if this script started it (unless --keep-dev)

Dual-mode examples:
  node scripts/run_unified_analysis.js --lane warden --source local
  node scripts/run_unified_analysis.js --lane system --source local
  node scripts/run_unified_analysis.js --lane warden --source github --repo projecthamburgresearch/resuscitation_health_app
  node scripts/run_unified_analysis.js --lane system --source github --repo projecthamburgresearch/resuscitation_health_app --include-ui-stages

Flags:
  --lane warden|system        Output/operation lane (default: warden)
  --source local|github       Blueprint input source (default: local)
  --project-root PATH         Local project root for Blueprint (default: app)
  --repo owner/name           GitHub repo when --source github
  --ref REF                   GitHub branch/tag/commit (default: main)
  --token-env ENV             Env var holding GitHub token for private repos
  --target-name NAME          Explicit Blueprint target name
  --preset quick|standard|deep
  --with-certificate          Enable Blueprint certificate check
  --no-certificate            Disable Blueprint certificate check
  --include-ui-stages         Allow scan + design for github source
  --base-url URL              UI base URL for scan/design (default: ${DEFAULT_BASE_URL})
  --viewport WxH              Repeatable viewport(s) for scan + design (default: ${DEFAULT_VIEWPORT_SPEC})
  --keep-dev                  Keep dev server running if started by this script
  --skip-parity               Skip parity stage
  --skip-blueprint            Skip blueprint stage
  --skip-scan                 Skip scan stage
  --skip-design-bundle        Skip design bundle stage
  --dev-timeout SEC           Dev server readiness timeout (default: 180)

Output root overrides:
  --blueprint-output-root PATH
  --scan-output-root PATH
  --design-root PATH
  --workspace-path PATH
`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }

  if (!['warden', 'system'].includes(out.lane)) {
    throw new Error(`Invalid --lane '${out.lane}'. Use warden or system.`);
  }
  if (!['local', 'github'].includes(out.source)) {
    throw new Error(`Invalid --source '${out.source}'. Use local or github.`);
  }
  if (out.source === 'github' && (!out.repo || !out.repo.includes('/'))) {
    throw new Error(`GitHub source requires --repo owner/name. Received: '${out.repo || ''}'`);
  }
  if (!['quick', 'standard', 'deep'].includes(out.preset)) {
    throw new Error(`Invalid --preset '${out.preset}'. Use quick, standard, or deep.`);
  }

  if (!Number.isFinite(out.devTimeoutSeconds) || out.devTimeoutSeconds <= 0) {
    throw new Error('Invalid --dev-timeout value. Must be a positive number.');
  }

  const dedupViewports = new Set(
    (out.viewportSpecs.length > 0 ? out.viewportSpecs : [DEFAULT_VIEWPORT_SPEC]).map(normalizeViewportSpec),
  );
  out.viewportSpecs = Array.from(dedupViewports);

  const laneDefaults = LANE_DEFAULTS[out.lane];
  out.blueprintOutputRoot = out.blueprintOutputRoot || laneDefaults.blueprintOutputRoot;
  out.scanOutputRoot = out.scanOutputRoot || laneDefaults.scanOutputRoot;
  out.designRoot = out.designRoot || laneDefaults.designRoot;
  out.workspacePath = out.workspacePath || laneDefaults.workspacePath;
  if (out.withCertificate === null) {
    out.withCertificate = out.lane === 'warden';
  }
  if (!out.targetName) {
    out.targetName = out.source === 'github'
      ? out.repo.split('/').pop()
      : `resuscitation-app-${out.lane}`;
  }

  return out;
}

function normalizeViewportSpec(spec) {
  const text = String(spec || '').trim().toLowerCase();
  const match = text.match(/^(\d{2,5})x(\d{2,5})$/);
  if (!match) {
    throw new Error(`Invalid viewport "${spec}". Use WIDTHxHEIGHT (example: 390x844).`);
  }
  const width = Number(match[1]);
  const height = Number(match[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width < 200 || height < 200) {
    throw new Error(`Invalid viewport "${spec}". Width/height must be >= 200.`);
  }
  return `${width}x${height}`;
}

function runStep(label, cmd, args, options = {}) {
  console.log(`\n[Step] ${label}`);
  console.log(`  $ ${[cmd, ...args].join(' ')}`);
  const result = spawnSync(cmd, args, {
    cwd: ROOT,
    stdio: 'inherit',
    env: { ...process.env, ...(options.env || {}) },
  });
  if (result.status !== 0) {
    throw new Error(`${label} failed with exit code ${result.status || 1}`);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function requestUrl(urlStr, timeoutMs = 3000) {
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

async function isDevReady(baseUrl) {
  const checks = [
    `${baseUrl.replace(/\/+$/, '')}/`,
    `${baseUrl.replace(/\/+$/, '')}/dev-mode`,
  ];
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

async function ensureDevServer(baseUrl, timeoutSeconds) {
  const readyAlready = await isDevReady(baseUrl);
  if (readyAlready) {
    console.log('\n[Info] Dev server already available; reusing existing process.');
    return { started: false, child: null };
  }

  const port = parsePort(baseUrl);
  console.log('\n[Step] Start Dev Server');
  console.log(`  Starting static dev server on port ${port}...`);
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
    const ready = await isDevReady(baseUrl);
    if (ready) {
      console.log('[Info] Dev server is ready.');
      return { started: true, child };
    }
    await sleep(1000);
  }

  await stopDevServer(child);
  throw new Error(`Dev server not ready within ${timeoutSeconds}s`);
}

function latestRunFromOutputRoot(outputRoot, label) {
  const runsDir = path.join(outputRoot, 'runs');
  const latest = latestDirectory(runsDir);
  if (!latest) {
    throw new Error(`No ${label} runs found under ${rel(runsDir)}`);
  }
  return latest;
}

function buildBlueprintArgs(opts) {
  const args = [
    'scripts/blueprint_warden_run_resuscitation.js',
    '--lane', opts.lane,
    '--source', opts.source,
    '--output-root', opts.blueprintOutputRoot,
    '--workspace-path', opts.workspacePath,
    '--target-name', opts.targetName,
    '--preset', opts.preset,
  ];

  if (opts.source === 'github') {
    args.push('--repo', opts.repo);
    args.push('--ref', opts.ref || DEFAULT_GITHUB_REF);
    if (opts.tokenEnv) args.push('--token-env', opts.tokenEnv);
  } else {
    args.push('--project-root', opts.projectRoot);
  }

  if (!opts.withCertificate) args.push('--no-certificate');

  return args;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const allowUiStages = opts.source === 'local' || opts.includeUiStages;
  const shouldRunParity = !opts.skipParity && opts.source === 'local';
  const shouldRunScan = !opts.skipScan && allowUiStages;
  const shouldRunDesign = !opts.skipDesignBundle && allowUiStages;
  const shouldRunBehavior = opts.lane === 'warden' && allowUiStages;

  if (!allowUiStages && (!opts.skipScan || !opts.skipDesignBundle || !opts.skipParity)) {
    console.log('\n[Info] GitHub source defaults to Blueprint-only operation.');
    console.log('       Add --include-ui-stages to run parity/scan/design against a UI base URL.');
  }

  console.log('\nUnified Analysis Pipeline');
  console.log(`  Lane          : ${opts.lane}`);
  console.log(`  Source        : ${opts.source}`);
  if (opts.source === 'github') {
    console.log(`  Repo          : ${opts.repo}`);
    console.log(`  Ref           : ${opts.ref}`);
    if (opts.tokenEnv) console.log(`  Token env     : ${opts.tokenEnv}`);
  } else {
    console.log(`  Project root  : ${rel(opts.projectRoot)}`);
  }
  console.log(`  Base URL      : ${opts.baseUrl}`);
  console.log(`  Viewport(s)   : ${opts.viewportSpecs.join(', ')}`);
  console.log(`  Keep Dev      : ${opts.keepDev}`);
  console.log(`  Run Parity    : ${shouldRunParity}`);
  console.log(`  Run Blueprint : ${!opts.skipBlueprint}`);
  console.log(`  Run Scan      : ${shouldRunScan}`);
  console.log(`  Run Design    : ${shouldRunDesign}`);
  console.log(`  Certificate   : ${opts.withCertificate ? 'enabled' : 'skipped'}`);
  console.log(`  Blueprint out : ${rel(opts.blueprintOutputRoot)}`);
  console.log(`  Scan out      : ${rel(opts.scanOutputRoot)}`);
  console.log(`  Design out    : ${rel(opts.designRoot)}`);
  console.log(`  Workspace     : ${rel(opts.workspacePath)}`);

  let devHandle = { started: false, child: null };
  try {
    if (shouldRunParity) {
      runStep('Check Dev-Mode Parity', 'node', ['scripts/check_dev_mode_parity.js']);
    }

    if (!opts.skipBlueprint) {
      runStep('Blueprint Workspace Run', 'node', buildBlueprintArgs(opts));
    }

    const needsDevServer = shouldRunScan || shouldRunDesign || shouldRunBehavior;
    if (needsDevServer) {
      devHandle = await ensureDevServer(opts.baseUrl, opts.devTimeoutSeconds);
    }

    if (shouldRunScan) {
      const scanArgs = ['scripts/scan.js', '--all', '--diff', '--coverage-report'];
      for (const vp of opts.viewportSpecs) {
        scanArgs.push('--viewport', vp);
      }
      runStep('Scan Coverage', 'node', scanArgs, {
        env: {
          SCAN_BASE_URL: opts.baseUrl,
          SCAN_OUTPUT_DIR: opts.scanOutputRoot,
        },
      });
    }

    if (shouldRunDesign) {
      const blueprintRun = latestRunFromOutputRoot(opts.blueprintOutputRoot, 'Blueprint');
      const scanRun = latestRunFromOutputRoot(opts.scanOutputRoot, 'Scan');
      const designArgs = [
        'scripts/warden_design_bundle.js',
        '--mode',
        'main',
        '--base-url',
        opts.baseUrl,
        '--blueprint-run',
        blueprintRun,
        '--scan-run',
        scanRun,
      ];
      for (const vp of opts.viewportSpecs) {
        designArgs.push('--viewport', vp);
      }
      runStep('Design Bundle', 'node', designArgs, {
        env: {
          WARDEN_DESIGN_ROOT: opts.designRoot,
          WARDEN_BLUEPRINT_RUNS_DIR: path.join(opts.blueprintOutputRoot, 'runs'),
          WARDEN_SCAN_RUNS_DIR: path.join(opts.scanOutputRoot, 'runs'),
        },
      });
    }

    if (shouldRunBehavior) {
      runStep('Behavior Contract Validation', 'node', ['scripts/test_behavior.js'], {
        env: {
          BASE_URL: opts.baseUrl,
        },
      });
    }
  } finally {
    if (devHandle.started && !opts.keepDev) {
      console.log('\n[Step] Stop Dev Server');
      await stopDevServer(devHandle.child);
      console.log('[Info] Dev server stopped.');
    } else if (devHandle.started && opts.keepDev) {
      console.log('\n[Info] Keeping dev server running (--keep-dev).');
    }
  }

  console.log('\nPipeline complete.');
  console.log('Outputs:');
  console.log(`  - Blueprint current: ${rel(path.join(opts.blueprintOutputRoot, 'current'))}/`);
  console.log(`  - Blueprint runs   : ${rel(path.join(opts.blueprintOutputRoot, 'runs'))}/`);
  console.log(`  - Scan current     : ${rel(path.join(opts.scanOutputRoot, 'current'))}/`);
  console.log(`  - Scan runs        : ${rel(path.join(opts.scanOutputRoot, 'runs'))}/`);
  console.log(`  - Design current   : ${rel(path.join(opts.designRoot, 'current_bundle.json'))}`);
  console.log(`  - Design runs      : ${rel(path.join(opts.designRoot, 'runs'))}/`);
  console.log('');
}

main().catch((err) => {
  console.error(`\nFatal: ${err.message}`);
  process.exit(1);
});
