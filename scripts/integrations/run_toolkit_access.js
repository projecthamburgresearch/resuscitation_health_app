#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = process.cwd();
const DEFAULT_TOOLKIT_ROOT = process.env.TOOLKIT_ROOT || '/Users/mordecaimachazire/Documents/local-projects/toolkit';
const DEFAULT_PACKAGE_ROOT = path.join(ROOT, 'integrations/access/bundle');
const DEFAULT_ENV_FILE = path.join(ROOT, '.env');

function parseArgs(argv) {
  const out = {
    command: 'full',
    toolkitRoot: DEFAULT_TOOLKIT_ROOT,
    packageRoot: DEFAULT_PACKAGE_ROOT,
    envFile: DEFAULT_ENV_FILE,
    profile: 'all',
    output: '',
    sources: [`resuscitation_health_app=${ROOT}`],
  };

  const args = [...argv];
  if (args[0] && !args[0].startsWith('--')) {
    out.command = args.shift();
  }

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--toolkit-root') {
      out.toolkitRoot = args[++i];
    } else if (arg.startsWith('--toolkit-root=')) {
      out.toolkitRoot = arg.split('=', 2)[1];
    } else if (arg === '--package-root') {
      out.packageRoot = args[++i];
    } else if (arg.startsWith('--package-root=')) {
      out.packageRoot = arg.split('=', 2)[1];
    } else if (arg === '--env-file') {
      out.envFile = args[++i];
    } else if (arg.startsWith('--env-file=')) {
      out.envFile = arg.split('=', 2)[1];
    } else if (arg === '--profile') {
      out.profile = args[++i];
    } else if (arg.startsWith('--profile=')) {
      out.profile = arg.split('=', 2)[1];
    } else if (arg === '--output') {
      out.output = args[++i];
    } else if (arg.startsWith('--output=')) {
      out.output = arg.split('=', 2)[1];
    } else if (arg === '--source') {
      out.sources.push(args[++i]);
    } else if (arg.startsWith('--source=')) {
      out.sources.push(arg.split('=', 2)[1]);
    } else if (arg === '--help' || arg === '-h') {
      console.log(`
Usage:
  node scripts/integrations/run_toolkit_access.js build
  node scripts/integrations/run_toolkit_access.js env-test --profile all
  node scripts/integrations/run_toolkit_access.js full

Defaults:
  toolkit root : ${DEFAULT_TOOLKIT_ROOT}
  package root : integrations/access/bundle
  env file     : .env

Examples:
  node scripts/integrations/run_toolkit_access.js build
  node scripts/integrations/run_toolkit_access.js env-test --profile sector:ai_foundation_models
  node scripts/integrations/run_toolkit_access.js full --source resuscitation_health_app=/path/to/resuscitation_health_app
`);
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return out;
}

function runCommand(label, command, args) {
  console.log(`\n[access] ${label}`);
  const result = spawnSync(command, args, {
    cwd: ROOT,
    stdio: 'inherit',
  });

  if (result.status !== 0) {
    throw new Error(`${label} failed with exit code ${result.status || 1}`);
  }
}

function ensureToolkitScript(toolkitRoot, relativeScriptPath) {
  const scriptPath = path.join(toolkitRoot, relativeScriptPath);
  if (!fs.existsSync(scriptPath)) {
    throw new Error(`Toolkit script not found: ${scriptPath}`);
  }
  return scriptPath;
}

function buildBundle(opts) {
  fs.mkdirSync(opts.packageRoot, { recursive: true });
  const scriptPath = ensureToolkitScript(opts.toolkitRoot, 'packages/access/scripts/build_access_bundle.py');
  const args = [scriptPath, '--package-root', opts.packageRoot];
  for (const source of opts.sources) args.push('--source', source);
  runCommand('Building local access bundle from toolkit', 'python3', args);
}

function generateEnvTest(opts) {
  const scriptPath = ensureToolkitScript(opts.toolkitRoot, 'packages/access/scripts/generate_env_test_spec.py');
  const catalogPath = path.join(opts.packageRoot, 'data/access-all-in-one.json');
  if (!fs.existsSync(catalogPath)) {
    throw new Error(`Missing access catalog: ${catalogPath}. Run "build" first or use "full".`);
  }

  const outputPath = opts.output || path.join(opts.packageRoot, 'output', 'resuscitation-health-app-access-env-test.yaml');
  runCommand('Generating env test spec from local access catalog', 'python3', [
    scriptPath,
    '--catalog',
    catalogPath,
    '--env-file',
    opts.envFile,
    '--profile',
    opts.profile,
    '--output',
    outputPath,
  ]);
}

function main() {
  const opts = parseArgs(process.argv.slice(2));

  if (!fs.existsSync(opts.toolkitRoot)) {
    throw new Error(`Toolkit root not found: ${opts.toolkitRoot}`);
  }

  if (opts.command === 'build') {
    buildBundle(opts);
    return;
  }

  if (opts.command === 'env-test') {
    generateEnvTest(opts);
    return;
  }

  if (opts.command === 'full') {
    buildBundle(opts);
    generateEnvTest(opts);
    return;
  }

  throw new Error(`Unknown command: ${opts.command}`);
}

try {
  main();
} catch (err) {
  console.error(`Fatal: ${err.message}`);
  process.exit(1);
}
