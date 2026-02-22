#!/usr/bin/env node
'use strict';

/**
 * Blueprint audit adapter for this project.
 *
 * Produces:
 *  - app_only_audit.json
 *  - app_only_audit.md
 *
 * The name is kept for compatibility with existing blueprint runner scripts.
 */

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const DEFAULT_BLUEPRINT_CANDIDATES = [
  path.join(ROOT, 'appendix/blueprint_outputs/current'),
  path.join(ROOT, 'appendix/blueprint_outputs'),
];

function parseArgs(argv) {
  const out = {
    blueprintDir: process.env.BLUEPRINT_DIR || null,
    outputDir: process.env.BLUEPRINT_AUDIT_OUTPUT_DIR || null,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--blueprint-dir') {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) throw new Error('Missing value after --blueprint-dir');
      out.blueprintDir = next;
      i += 1;
    } else if (arg.startsWith('--blueprint-dir=')) {
      out.blueprintDir = arg.split('=', 2)[1];
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
  node scripts/blueprint_app_audit.js
  node scripts/blueprint_app_audit.js --blueprint-dir appendix/blueprint_outputs/current
  node scripts/blueprint_app_audit.js --output-dir appendix/blueprint_outputs/current

Env:
  BLUEPRINT_DIR=<path>                 Override blueprint input directory
  BLUEPRINT_AUDIT_OUTPUT_DIR=<path>    Override audit output directory
`);
      process.exit(0);
    } else if (arg.startsWith('--')) {
      throw new Error(`Unknown flag: ${arg}`);
    }
  }
  return out;
}

function resolveBlueprintDir(overrideDir) {
  const candidates = [];
  if (overrideDir) candidates.push(path.resolve(ROOT, overrideDir));
  for (const base of DEFAULT_BLUEPRINT_CANDIDATES) candidates.push(base);

  for (const candidate of candidates) {
    if (fileExists(path.join(candidate, 'xray_result.json'))) return candidate;
  }
  return candidates[0];
}

function fileExists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function readJsonIfExists(filePath) {
  if (!fileExists(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function toSortedCountObject(entries) {
  return Object.fromEntries(
    Object.entries(entries).sort((a, b) => b[1] - a[1]),
  );
}

function shortList(counts, limit = 12) {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([key, value]) => ({ key, value }));
}

function relPath(p) {
  return path.relative(ROOT, p) || '.';
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const blueprintDir = resolveBlueprintDir(args.blueprintDir);
  const outputDir = args.outputDir ? path.resolve(ROOT, args.outputDir) : blueprintDir;

  const xray = readJsonIfExists(path.join(blueprintDir, 'xray_result.json'));
  const llm = readJsonIfExists(path.join(blueprintDir, 'llm_context.json'));
  const chronicle = readJsonIfExists(path.join(blueprintDir, 'chronicle.json'));
  const masterIndex = readJsonIfExists(path.join(blueprintDir, 'master_index.json'));
  const sonar = readJsonIfExists(path.join(blueprintDir, 'sonar_report.json'));
  const synapse = readJsonIfExists(path.join(blueprintDir, 'synapse_report.json'));
  const runMeta = readJsonIfExists(path.join(blueprintDir, 'run_meta.json'));

  if (!xray) {
    console.error(`Missing xray_result.json in ${relPath(blueprintDir)}`);
    process.exit(1);
  }

  const entities = Array.isArray(xray.entities) ? xray.entities : [];
  const entityTypes = {};
  const fileEntityCount = {};
  const functionHotspots = [];

  for (const entity of entities) {
    const type = entity.type || 'unknown';
    entityTypes[type] = (entityTypes[type] || 0) + 1;

    const file = entity.location && entity.location.file ? String(entity.location.file) : null;
    if (file) fileEntityCount[file] = (fileEntityCount[file] || 0) + 1;

    if (type === 'function') {
      functionHotspots.push({
        name: entity.name || 'anonymous',
        file: file || 'unknown',
        line: entity.location && entity.location.start_line ? entity.location.start_line : null,
        cyclomatic: entity.metrics && entity.metrics.cyclomatic_complexity ? entity.metrics.cyclomatic_complexity : 0,
        cognitive: entity.metrics && entity.metrics.cognitive_complexity ? entity.metrics.cognitive_complexity : 0,
        locCode: entity.metrics && entity.metrics.loc_code ? entity.metrics.loc_code : 0,
        fanOut: entity.metrics && entity.metrics.fan_out ? entity.metrics.fan_out : 0,
      });
    }
  }

  functionHotspots.sort((a, b) => {
    if (b.cyclomatic !== a.cyclomatic) return b.cyclomatic - a.cyclomatic;
    if (b.cognitive !== a.cognitive) return b.cognitive - a.cognitive;
    if (b.locCode !== a.locCode) return b.locCode - a.locCode;
    return b.fanOut - a.fanOut;
  });

  const llmNodeTypes = {};
  const llmEdgeTypes = {};
  const llmNodes = Array.isArray(llm && llm.nodes) ? llm.nodes : [];
  const llmEdges = Array.isArray(llm && llm.edges) ? llm.edges : [];

  for (const node of llmNodes) {
    const type = node.type || 'unknown';
    llmNodeTypes[type] = (llmNodeTypes[type] || 0) + 1;
  }
  for (const edge of llmEdges) {
    const rel = edge.rel || 'unknown';
    llmEdgeTypes[rel] = (llmEdgeTypes[rel] || 0) + 1;
  }

  const latestRun = Array.isArray(chronicle && chronicle.runs) && chronicle.runs.length > 0
    ? chronicle.runs[chronicle.runs.length - 1]
    : null;

  const sonarFindings = Array.isArray(sonar && sonar.findings)
    ? sonar.findings
    : Array.isArray(latestRun && latestRun.stats && latestRun.stats.sonar && latestRun.stats.sonar.findings)
      ? latestRun.stats.sonar.findings
      : [];

  const sonarByCategory = {};
  const sonarByLevel = {};
  for (const finding of sonarFindings) {
    const category = finding.category || 'unknown';
    const level = finding.level || 'unknown';
    sonarByCategory[category] = (sonarByCategory[category] || 0) + 1;
    sonarByLevel[level] = (sonarByLevel[level] || 0) + 1;
  }

  const synapseHotspots = Array.isArray(synapse && synapse.hotspots)
    ? synapse.hotspots
    : Array.isArray(latestRun && latestRun.stats && latestRun.stats.synapse && latestRun.stats.synapse.hotspots)
      ? latestRun.stats.synapse.hotspots
      : [];

  const zoneCount = masterIndex && masterIndex.zones ? Object.keys(masterIndex.zones).length : 0;
  const masterEntries = masterIndex && masterIndex.entries ? Object.keys(masterIndex.entries).length : 0;

  const summary = {
    generatedAt: new Date().toISOString(),
    blueprintDir: relPath(blueprintDir),
    outputDir: relPath(outputDir),
    runMeta,
    totals: {
      entities: entities.length,
      uniqueEntityFiles: Object.keys(fileEntityCount).length,
      llmNodes: llmNodes.length,
      llmEdges: llmEdges.length,
      sonarFindings: sonarFindings.length,
      synapseHotspots: synapseHotspots.length,
      masterIndexZones: zoneCount,
      masterIndexEntries: masterEntries,
    },
    entityTypes: toSortedCountObject(entityTypes),
    topEntityFiles: shortList(fileEntityCount, 25),
    topFunctionHotspots: functionHotspots.slice(0, 20),
    llmNodeTypes: toSortedCountObject(llmNodeTypes),
    llmEdgeTypes: toSortedCountObject(llmEdgeTypes),
    sonar: {
      byCategory: toSortedCountObject(sonarByCategory),
      byLevel: toSortedCountObject(sonarByLevel),
      topFindings: sonarFindings.slice(0, 20),
    },
    synapse: {
      topHotspots: synapseHotspots.slice(0, 20),
    },
  };

  fs.mkdirSync(outputDir, { recursive: true });

  const jsonPath = path.join(outputDir, 'app_only_audit.json');
  fs.writeFileSync(jsonPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');

  const md = [
    '# Blueprint Audit Summary',
    '',
    `Generated: ${summary.generatedAt}`,
    `Blueprint dir: \`${summary.blueprintDir}\``,
    '',
    '## Totals',
    '',
    `- Entities: ${summary.totals.entities}`,
    `- Unique files with entities: ${summary.totals.uniqueEntityFiles}`,
    `- LLM nodes/edges: ${summary.totals.llmNodes}/${summary.totals.llmEdges}`,
    `- Sonar findings: ${summary.totals.sonarFindings}`,
    `- Synapse hotspots: ${summary.totals.synapseHotspots}`,
    '',
    '## Top Function Hotspots',
    '',
    '| Name | File | Cyclomatic | Cognitive | LOC | Fan-out |',
    '|---|---|---:|---:|---:|---:|',
  ];

  for (const row of summary.topFunctionHotspots.slice(0, 12)) {
    md.push(`| ${row.name} | ${row.file}${row.line ? `:${row.line}` : ''} | ${row.cyclomatic} | ${row.cognitive} | ${row.locCode} | ${row.fanOut} |`);
  }

  md.push('');
  md.push('## Sonar Findings by Category');
  md.push('');
  for (const [k, v] of Object.entries(summary.sonar.byCategory)) {
    md.push(`- ${k}: ${v}`);
  }

  md.push('');
  md.push('## Sonar Findings by Level');
  md.push('');
  for (const [k, v] of Object.entries(summary.sonar.byLevel)) {
    md.push(`- ${k}: ${v}`);
  }

  md.push('');
  const mdPath = path.join(outputDir, 'app_only_audit.md');
  fs.writeFileSync(mdPath, `${md.join('\n')}\n`, 'utf8');

  console.log('Blueprint audit generated.');
  console.log(`  JSON: ${relPath(jsonPath)}`);
  console.log(`  MD  : ${relPath(mdPath)}`);
}

try {
  main();
} catch (err) {
  console.error(`Fatal: ${err.message}`);
  process.exit(1);
}
