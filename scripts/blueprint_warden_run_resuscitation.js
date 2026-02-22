#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = process.cwd();
const DEFAULT_BLUEPRINT_ROOT = path.join(ROOT, 'appendix/blueprint');
const DEFAULT_OUTPUT_ROOT = path.join(ROOT, 'appendix/blueprint_outputs');
const DEFAULT_PROJECT_ROOT = path.join(ROOT, 'app');
const DEFAULT_WORKSPACE_NAME = 'blueprint_outputs';
const DEFAULT_TARGET_NAME = 'resuscitation-app';
const DEFAULT_BLUEPRINT_VENV = '.venv';
const DEFAULT_SOURCE = 'local';
const DEFAULT_LANE = 'warden';
const DEFAULT_GITHUB_REF = 'main';

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function parseArgs(argv) {
  const out = {
    blueprintRoot: DEFAULT_BLUEPRINT_ROOT,
    outputRoot: DEFAULT_OUTPUT_ROOT,
    projectRoot: DEFAULT_PROJECT_ROOT,
    workspacePath: null,
    targetName: null,
    preset: 'standard',
    skipAudit: false,
    ensureCertificate: true,
    bootstrapVenv: false,
    lane: DEFAULT_LANE,
    source: DEFAULT_SOURCE,
    repo: '',
    ref: DEFAULT_GITHUB_REF,
    tokenEnv: '',
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--blueprint-root') {
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
    } else if (arg === '--project-root') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --project-root');
      out.projectRoot = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--project-root=')) {
      out.projectRoot = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--workspace-path') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --workspace-path');
      out.workspacePath = path.resolve(ROOT, next);
      i += 1;
    } else if (arg.startsWith('--workspace-path=')) {
      out.workspacePath = path.resolve(ROOT, arg.split('=', 2)[1]);
    } else if (arg === '--target-name') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --target-name');
      out.targetName = next.trim();
      i += 1;
    } else if (arg.startsWith('--target-name=')) {
      out.targetName = arg.split('=', 2)[1].trim();
    } else if (arg === '--lane') {
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
    } else if (arg === '--preset') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --preset');
      out.preset = next;
      i += 1;
    } else if (arg.startsWith('--preset=')) {
      out.preset = arg.split('=', 2)[1];
    } else if (arg === '--skip-audit') {
      out.skipAudit = true;
    } else if (arg === '--with-certificate') {
      out.ensureCertificate = true;
    } else if (arg === '--no-certificate') {
      out.ensureCertificate = false;
    } else if (arg === '--bootstrap-venv') {
      out.bootstrapVenv = true;
    } else if (arg === '--help' || arg === '-h') {
      console.log(`
Usage:
  node scripts/blueprint_warden_run_resuscitation.js
  node scripts/blueprint_warden_run_resuscitation.js --project-root app
  node scripts/blueprint_warden_run_resuscitation.js --lane system --source local
  node scripts/blueprint_warden_run_resuscitation.js --lane warden --source github --repo owner/repo --ref main
  node scripts/blueprint_warden_run_resuscitation.js --workspace-path appendix/blueprint/blueprint_outputs
  node scripts/blueprint_warden_run_resuscitation.js --skip-audit
  node scripts/blueprint_warden_run_resuscitation.js --no-certificate
  node scripts/blueprint_warden_run_resuscitation.js --bootstrap-venv

Behavior:
  1) Initializes a dedicated Blueprint workspace for this run
  2) Writes workspace deploy.yaml for the selected project root
  3) Ensures certificate validity (unless --no-certificate)
  4) Runs blueprint workspace analysis (snapshot mode)
  5) Archives previous current snapshot to <output-root>/archive/current-<timestamp>/
  6) Syncs latest run artifacts into <output-root>/{runs,current}
  7) Runs scripts/blueprint_app_audit.js unless --skip-audit

Notes:
  - --source local: uses --project-root (default: app).
  - --source github: uses --repo owner/name, --ref, optional --token-env.
  - --lane is metadata for manifest/reporting (warden|system).
  - Certificate mode requires pytest in the selected Blueprint Python environment.
  - Use --bootstrap-venv to create/update appendix/blueprint/.venv with
    requirements-dev.txt when setting up a fresh machine.
`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }

  if (!out.workspacePath) {
    out.workspacePath = path.join(out.blueprintRoot, DEFAULT_WORKSPACE_NAME);
  }

  if (!['warden', 'system'].includes(out.lane)) {
    throw new Error(`Invalid --lane '${out.lane}'. Use warden or system.`);
  }

  if (!['local', 'github'].includes(out.source)) {
    throw new Error(`Invalid --source '${out.source}'. Use local or github.`);
  }

  if (out.source === 'github') {
    if (!out.repo || !out.repo.includes('/')) {
      throw new Error(`GitHub source requires --repo owner/name. Received: '${out.repo || ''}'`);
    }
    if (!out.targetName) {
      out.targetName = out.repo.split('/').pop();
    }
  } else if (!out.targetName) {
    out.targetName = DEFAULT_TARGET_NAME;
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

function writeFile(filePath, content) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, content, 'utf8');
}

function ensureBlueprintCertificateLayout(blueprintRoot) {
  // Blueprint certificate flow writes history under workspace/status/certificate.
  // Fresh local clones may not include this directory yet.
  ensureDir(path.join(blueprintRoot, 'workspace', 'status', 'certificate'));
}

function runCommand(cmd, args, cwd, label) {
  const result = spawnSync(cmd, args, { cwd, stdio: 'inherit' });
  if (result.status !== 0) {
    throw new Error(`${label} failed with exit code ${result.status || 1}`);
  }
}

function resolveBlueprintPython(blueprintRoot) {
  if (process.env.BLUEPRINT_PYTHON) return process.env.BLUEPRINT_PYTHON;
  const venvPython = path.join(blueprintRoot, DEFAULT_BLUEPRINT_VENV, 'bin', 'python3');
  if (fs.existsSync(venvPython)) return venvPython;
  return 'python3';
}

function bootstrapVenv(blueprintRoot) {
  const venvPython = path.join(blueprintRoot, DEFAULT_BLUEPRINT_VENV, 'bin', 'python3');
  if (!fs.existsSync(venvPython)) {
    const create = spawnSync('python3', ['-m', 'venv', DEFAULT_BLUEPRINT_VENV], {
      cwd: blueprintRoot,
      stdio: 'inherit',
    });
    if (create.status !== 0) {
      throw new Error(`Venv creation failed with exit code ${create.status || 1}`);
    }
  }

  const install = spawnSync(
    venvPython,
    ['-m', 'pip', 'install', '-r', 'requirements-dev.txt'],
    { cwd: blueprintRoot, stdio: 'inherit' },
  );
  if (install.status !== 0) {
    throw new Error(`Venv dependency install failed with exit code ${install.status || 1}`);
  }
}

function pythonHasModule(pythonExe, moduleName, cwd) {
  const result = spawnSync(
    pythonExe,
    ['-c', `import ${moduleName}`],
    { cwd, stdio: 'ignore' },
  );
  return result.status === 0;
}

function rel(p) {
  return path.relative(ROOT, p) || '.';
}

function resolveWorkspaceGithubCloneDir(opts) {
  const repoName = (opts.repo || '').split('/').pop() || 'repo';
  const folder = opts.targetName || repoName;
  return path.join(opts.workspacePath, 'intake', 'local', folder);
}

function buildGithubCloneUrl(opts) {
  if (opts.tokenEnv) {
    const token = process.env[opts.tokenEnv] || '';
    if (!token) {
      throw new Error(`Missing GitHub token env '${opts.tokenEnv}' for private repo access.`);
    }
    return `https://${token}@github.com/${opts.repo}.git`;
  }
  return `https://github.com/${opts.repo}.git`;
}

function ensureWorkspaceGithubClone(opts) {
  const cloneDir = resolveWorkspaceGithubCloneDir(opts);
  const gitDir = path.join(cloneDir, '.git');
  const ref = opts.ref || DEFAULT_GITHUB_REF;
  const cloneUrl = buildGithubCloneUrl(opts);

  if (fs.existsSync(cloneDir) && !fs.existsSync(gitDir)) {
    throw new Error(`Workspace clone dir exists but is not a git repo: ${rel(cloneDir)}`);
  }

  if (fs.existsSync(gitDir)) {
    runCommand('git', ['-C', cloneDir, 'fetch', '--all'], ROOT, 'Git fetch');
    runCommand('git', ['-C', cloneDir, 'checkout', ref], ROOT, 'Git checkout');
    runCommand('git', ['-C', cloneDir, 'pull', '--ff-only'], ROOT, 'Git pull');
    return cloneDir;
  }

  ensureDir(path.dirname(cloneDir));
  runCommand('git', ['clone', '--branch', ref, '--depth', '1', cloneUrl, cloneDir], ROOT, 'Git clone');
  return cloneDir;
}

function buildTargetYamlBlock(opts) {
  if (opts.source === 'github') {
    // Workspace runner currently resolves target paths before invoking
    // GitHub clone logic. To keep GitHub source reliable, sync first into
    // intake/local and analyze as a local target.
    const clonedPath = resolveWorkspaceGithubCloneDir(opts).replace(/\\/g, '/');
    return [
      '  - type: local',
      `    name: "${opts.targetName}"`,
      `    path: "${clonedPath}"`,
      '    bpignore: true',
    ].join('\n');
  }

  return [
    '  - type: local',
    `    name: "${opts.targetName}"`,
    `    path: "${opts.projectRoot.replace(/\\/g, '/')}"`,
    '    bpignore: true',
  ].join('\n');
}

function buildDeployYaml(opts) {
  return `version: "1.0"
purpose: "Resuscitation app structural and quality analysis via Blueprint workspace snapshot mode"

targets:
${buildTargetYamlBlock(opts)}

domains:
  - xray
  - manifest
  - cortex
  - registry
  - sonar
  - synapse

preset: "${opts.preset}"

output:
  formats:
    - json
    - markdown
  manifest_format: "yaml"
  git_analysis: false

warden:
  auto_recover: true
  checkpoint_before_changes: true
  sync_after_run: true
  max_retries: 3
`;
}

function findLatestRunDir(workspacePath, targetName) {
  const targetRoot = path.join(workspacePath, 'results', targetName);
  if (!fs.existsSync(targetRoot)) return null;
  const dirs = fs.readdirSync(targetRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(targetRoot, entry.name))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return dirs[0] || null;
}

function copyArtifactFiles(srcDir, dstDir) {
  ensureDir(dstDir);
  const files = fs.readdirSync(srcDir, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .filter((name) => /\.(json|ya?ml|md)$/i.test(name));

  for (const file of files) {
    fs.copyFileSync(path.join(srcDir, file), path.join(dstDir, file));
  }
  return files;
}

function ensureAppBpignore(projectRoot) {
  const devModeDir = path.join(projectRoot, 'dev-mode');
  if (!fs.existsSync(devModeDir)) return;

  const bpignorePath = path.join(projectRoot, '.bpignore');
  const requiredPattern = 'dev-mode/';
  if (!fs.existsSync(bpignorePath)) {
    writeFile(bpignorePath, '# Exclude dev-mode mirror routes from Blueprint app-root runs\ndev-mode/\n');
    return;
  }
  const text = fs.readFileSync(bpignorePath, 'utf8');
  const hasPattern = text.split(/\r?\n/).some((line) => line.trim() === requiredPattern);
  if (hasPattern) return;
  const next = `${text.trimEnd()}\n${requiredPattern}\n`;
  writeFile(bpignorePath, next);
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (!['quick', 'standard', 'deep'].includes(opts.preset)) {
    throw new Error(`Invalid --preset '${opts.preset}'. Use quick, standard, or deep.`);
  }
  if (!fs.existsSync(opts.blueprintRoot)) throw new Error(`Blueprint root not found: ${rel(opts.blueprintRoot)}`);
  if (opts.source === 'local' && !fs.existsSync(opts.projectRoot)) {
    throw new Error(`Project root not found: ${rel(opts.projectRoot)}`);
  }

  if (opts.bootstrapVenv) {
    console.log('\nBootstrapping Blueprint venv...');
    bootstrapVenv(opts.blueprintRoot);
  }

  const stamp = nowStamp();
  const runDir = path.join(opts.outputRoot, 'runs', `${stamp}-${opts.lane}`);
  const currentDir = path.join(opts.outputRoot, 'current');
  const archiveRoot = path.join(opts.outputRoot, 'archive');
  const deployPath = path.join(opts.workspacePath, 'intake', 'deploy.yaml');
  const blueprintPython = resolveBlueprintPython(opts.blueprintRoot);
  const pythonLabel = path.isAbsolute(blueprintPython) ? rel(blueprintPython) : blueprintPython;

  console.log('\nBlueprint Workspace Run (Resuscitation)');
  console.log(`  Lane           : ${opts.lane}`);
  console.log(`  Source         : ${opts.source}`);
  console.log(`  Blueprint root : ${rel(opts.blueprintRoot)}`);
  console.log(`  Workspace      : ${rel(opts.workspacePath)}`);
  if (opts.source === 'github') {
    console.log(`  GitHub repo    : ${opts.repo}`);
    console.log(`  GitHub ref     : ${opts.ref}`);
    if (opts.tokenEnv) console.log(`  GitHub token   : ${opts.tokenEnv}`);
  } else {
    console.log(`  Project root   : ${rel(opts.projectRoot)}`);
  }
  console.log(`  Output run     : ${rel(runDir)}`);
  console.log(`  Output current : ${rel(currentDir)}`);
  const archivedCurrentDir = rotateCurrentToArchive(currentDir, archiveRoot, stamp);
  if (archivedCurrentDir) {
    console.log(`  Output archive : ${rel(archivedCurrentDir)} (previous current snapshot)`);
  }
  console.log(`  Preset         : ${opts.preset}`);
  console.log(`  Certificate    : ${opts.ensureCertificate ? 'enabled' : 'skipped'}`);
  console.log(`  Python         : ${pythonLabel}`);
  console.log('');

  ensureDir(runDir);

  // Only enforce app/.bpignore dev-mode exclusion for local app-root runs.
  if (opts.source === 'local') {
    ensureAppBpignore(opts.projectRoot);
  }

  runCommand(
    blueprintPython,
    ['-m', 'src.cli', 'workspace', 'init', '--path', opts.workspacePath],
    opts.blueprintRoot,
    'Workspace init',
  );

  let githubCloneDir = null;
  if (opts.source === 'github') {
    console.log('[Step] Sync GitHub source into workspace intake/local');
    githubCloneDir = ensureWorkspaceGithubClone(opts);
    console.log(`  Clone path     : ${rel(githubCloneDir)}`);
  }

  writeFile(deployPath, buildDeployYaml(opts));

  if (opts.ensureCertificate) {
    if (!pythonHasModule(blueprintPython, 'pytest', opts.blueprintRoot)) {
      throw new Error(
        `Certificate mode requires pytest in ${pythonLabel}. ` +
        'Run with --bootstrap-venv or install requirements-dev.txt for Blueprint.',
      );
    }
    ensureBlueprintCertificateLayout(opts.blueprintRoot);
    const certScript = [
      'from pathlib import Path',
      'from src.core.certificate import ensure_certificate',
      `ok, msg, _ = ensure_certificate(Path(${JSON.stringify(opts.blueprintRoot)}).resolve(), auto_issue=True)`,
      'print(msg)',
      'raise SystemExit(0 if ok else 1)',
    ].join('; ');
    runCommand(
      blueprintPython,
      ['-c', certScript],
      opts.blueprintRoot,
      'Certificate check/issue',
    );
  }

  runCommand(
    blueprintPython,
    ['-m', 'src.cli', 'workspace', 'run', '--path', opts.workspacePath],
    opts.blueprintRoot,
    'Workspace run',
  );

  const latestResultsDir = findLatestRunDir(opts.workspacePath, opts.targetName);
  if (!latestResultsDir) throw new Error(`No workspace result dir found for target '${opts.targetName}'`);

  const synced = copyArtifactFiles(latestResultsDir, runDir);
  copyArtifactFiles(latestResultsDir, currentDir);

  const runMetaPath = path.join(latestResultsDir, 'run_meta.json');
  const runMeta = fs.existsSync(runMetaPath) ? JSON.parse(fs.readFileSync(runMetaPath, 'utf8')) : null;
  const manifest = {
    generatedAt: new Date().toISOString(),
    mode: opts.lane === 'warden' ? 'workspace-warden' : 'workspace-system',
    lane: opts.lane,
    sourceType: opts.source,
    sourceRef: opts.source === 'github' ? `${opts.repo}@${opts.ref || DEFAULT_GITHUB_REF}` : rel(opts.projectRoot),
    blueprintRoot: rel(opts.blueprintRoot),
    workspacePath: rel(opts.workspacePath),
    deployPath: rel(deployPath),
    projectRoot: opts.source === 'local' ? rel(opts.projectRoot) : null,
    repo: opts.source === 'github' ? opts.repo : null,
    ref: opts.source === 'github' ? (opts.ref || DEFAULT_GITHUB_REF) : null,
    tokenEnv: opts.source === 'github' && opts.tokenEnv ? opts.tokenEnv : null,
    githubCloneDir: opts.source === 'github' && githubCloneDir ? rel(githubCloneDir) : null,
    targetName: opts.targetName,
    preset: opts.preset,
    certificateEnsured: opts.ensureCertificate,
    workspaceResultDir: rel(latestResultsDir),
    workspaceRunId: runMeta && runMeta.run_id ? runMeta.run_id : null,
    runDir: rel(runDir),
    currentDir: rel(currentDir),
    archivedCurrentDir: archivedCurrentDir ? rel(archivedCurrentDir) : null,
    filesSynced: synced,
  };
  writeFile(path.join(currentDir, 'run_manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);

  if (!opts.skipAudit) {
    runCommand(
      'node',
      [
        'scripts/blueprint_app_audit.js',
        '--blueprint-dir', currentDir,
        '--output-dir', currentDir,
      ],
      ROOT,
      'App audit',
    );
  }

  console.log('\nBlueprint workspace run complete.');
  console.log(`  Workspace results: ${rel(latestResultsDir)}`);
  console.log(`  Synced run folder: ${rel(runDir)}`);
  console.log(`  Current bundle   : ${rel(currentDir)}`);
  console.log('');
}

try {
  main();
} catch (err) {
  console.error(`\nFatal: ${err.message}`);
  process.exit(1);
}
