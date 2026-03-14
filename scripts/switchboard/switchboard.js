#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const SWITCHBOARD_ROOT = path.join(ROOT, 'appendix/guidance/switchboard');
const INBOX_DIR = path.join(SWITCHBOARD_ROOT, 'inbox');
const ACTIVE_DIR = path.join(SWITCHBOARD_ROOT, 'active');
const OUTBOX_DIR = path.join(SWITCHBOARD_ROOT, 'outbox');
const ARCHIVE_DIR = path.join(SWITCHBOARD_ROOT, 'archive');
const REGISTRY_FILE = path.join(SWITCHBOARD_ROOT, 'registry/dispatches.jsonl');

function parseArgs(argv) {
  const out = {
    command: 'list',
    messageId: '',
    delegate: '',
    reviewer: '',
    verdict: '',
    notes: '',
    delegateOutcome: '',
    fixesApplied: '',
    recurringMistakes: '',
    followOnAction: '',
  };

  const args = [...argv];
  if (args[0] && !args[0].startsWith('--')) {
    out.command = args.shift();
  }

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--message-id') out.messageId = args[++i];
    else if (arg.startsWith('--message-id=')) out.messageId = arg.split('=', 2)[1];
    else if (arg === '--delegate') out.delegate = args[++i];
    else if (arg.startsWith('--delegate=')) out.delegate = arg.split('=', 2)[1];
    else if (arg === '--reviewer') out.reviewer = args[++i];
    else if (arg.startsWith('--reviewer=')) out.reviewer = arg.split('=', 2)[1];
    else if (arg === '--verdict') out.verdict = args[++i];
    else if (arg.startsWith('--verdict=')) out.verdict = arg.split('=', 2)[1];
    else if (arg === '--notes') out.notes = args[++i];
    else if (arg.startsWith('--notes=')) out.notes = arg.split('=', 2)[1];
    else if (arg === '--delegate-outcome') out.delegateOutcome = args[++i];
    else if (arg.startsWith('--delegate-outcome=')) out.delegateOutcome = arg.split('=', 2)[1];
    else if (arg === '--fixes-applied') out.fixesApplied = args[++i];
    else if (arg.startsWith('--fixes-applied=')) out.fixesApplied = arg.split('=', 2)[1];
    else if (arg === '--recurring-mistakes') out.recurringMistakes = args[++i];
    else if (arg.startsWith('--recurring-mistakes=')) out.recurringMistakes = arg.split('=', 2)[1];
    else if (arg === '--follow-on-action') out.followOnAction = args[++i];
    else if (arg.startsWith('--follow-on-action=')) out.followOnAction = arg.split('=', 2)[1];
    else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return out;
}

function printHelp() {
  console.log(`
Usage:
  node scripts/switchboard/switchboard.js list
  node scripts/switchboard/switchboard.js claim --message-id MSG-... --delegate "Claude CLI"
  node scripts/switchboard/switchboard.js close --message-id MSG-...
  node scripts/switchboard/switchboard.js review --message-id MSG-... --reviewer "Steward" --verdict accept_with_fixes
  node scripts/switchboard/switchboard.js archive --message-id MSG-... --reviewer "Steward" --verdict accept_with_fixes

Folders:
  appendix/guidance/switchboard/{inbox,active,outbox,archive,registry}
`);
}

function ensureDirs() {
  [
    SWITCHBOARD_ROOT,
    INBOX_DIR,
    ACTIVE_DIR,
    OUTBOX_DIR,
    ARCHIVE_DIR,
    path.dirname(REGISTRY_FILE),
  ].forEach((dir) => fs.mkdirSync(dir, { recursive: true }));
}

function isoNow() {
  return new Date().toISOString();
}

function dateFolder() {
  return isoNow().slice(0, 10);
}

function readFileText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function writeFileText(filePath, text) {
  fs.writeFileSync(filePath, text, 'utf8');
}

function resolveRepoPath(filePath) {
  if (!filePath) return '';
  return path.isAbsolute(filePath) ? filePath : path.join(ROOT, filePath);
}

function findMessagePath(messageId) {
  const roots = [INBOX_DIR, ACTIVE_DIR, OUTBOX_DIR, ARCHIVE_DIR];
  const targetName = `${messageId}.md`;

  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    const stack = [root];
    while (stack.length > 0) {
      const current = stack.pop();
      const entries = fs.readdirSync(current, { withFileTypes: true });
      for (const entry of entries) {
        const nextPath = path.join(current, entry.name);
        if (entry.isDirectory()) stack.push(nextPath);
        else if (entry.isFile() && entry.name === targetName) return nextPath;
      }
    }
  }

  throw new Error(`Message not found: ${messageId}`);
}

function headerBoundary(text) {
  const match = text.match(/\n\s*\n/);
  return match ? match.index : text.length;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function extractField(text, key) {
  const match = text.match(new RegExp(`^${escapeRegExp(key)}:\\s*(.*)$`, 'm'));
  return match ? match[1].trim() : '';
}

function parseScalar(value) {
  if (!value) return '';
  if (value === '[]') return '[]';
  if (value.startsWith('"') && value.endsWith('"')) return value.slice(1, -1);
  return value;
}

function extractList(text, key) {
  const lines = text.split('\n');
  const start = lines.findIndex((line) => line.startsWith(`${key}:`));
  if (start === -1) return [];
  const inline = lines[start].slice(`${key}:`.length).trim();
  if (inline === '[]') return [];

  const out = [];
  for (let i = start + 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (/^  - /.test(line)) {
      out.push(parseScalar(line.replace(/^  - /, '').trim()));
      continue;
    }
    if (/^\S/.test(line)) break;
    if (!line.trim()) break;
  }
  return out;
}

function upsertScalar(text, key, value, afterKey) {
  const safeValue = `"${String(value).replace(/"/g, '\\"')}"`;
  const linePattern = new RegExp(`^${escapeRegExp(key)}:\\s*.*$`, 'm');
  if (linePattern.test(text)) {
    return text.replace(linePattern, `${key}: ${safeValue}`);
  }

  if (afterKey) {
    const afterPattern = new RegExp(`^${escapeRegExp(afterKey)}:\\s*.*$`, 'm');
    const match = text.match(afterPattern);
    if (match && typeof match.index === 'number') {
      const insertAt = match.index + match[0].length;
      return `${text.slice(0, insertAt)}\n${key}: ${safeValue}${text.slice(insertAt)}`;
    }
  }

  const boundary = headerBoundary(text);
  return `${text.slice(0, boundary)}\n${key}: ${safeValue}${text.slice(boundary)}`;
}

function moveMessage(currentPath, destinationDir) {
  fs.mkdirSync(destinationDir, { recursive: true });
  const nextPath = path.join(destinationDir, path.basename(currentPath));
  fs.renameSync(currentPath, nextPath);
  return nextPath;
}

function moveIfExists(filePath, destinationDir) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  fs.mkdirSync(destinationDir, { recursive: true });
  const nextPath = path.join(destinationDir, path.basename(filePath));
  fs.renameSync(filePath, nextPath);
  return nextPath;
}

function appendRegistry(entry) {
  ensureDirs();
  fs.appendFileSync(REGISTRY_FILE, `${JSON.stringify(entry)}\n`, 'utf8');
}

function loadLatestRegistrySnapshots() {
  ensureDirs();
  if (!fs.existsSync(REGISTRY_FILE)) return new Map();
  const map = new Map();
  const lines = fs.readFileSync(REGISTRY_FILE, 'utf8').split('\n').filter(Boolean);
  for (const line of lines) {
    try {
      const entry = JSON.parse(line);
      if (entry.message_id) map.set(entry.message_id, entry);
    } catch (_) {
      // Ignore malformed historical lines; keep the tool resilient.
    }
  }
  return map;
}

function messageSummary(filePath) {
  const text = readFileText(filePath);
  return {
    messageId: parseScalar(extractField(text, 'message_id')),
    status: parseScalar(extractField(text, 'status')),
    delegate: parseScalar(extractField(text, 'selected_delegate')),
    role: parseScalar(extractField(text, 'intended_role')),
  };
}

function listMessages() {
  ensureDirs();
  const buckets = [
    ['inbox', INBOX_DIR],
    ['active', ACTIVE_DIR],
    ['outbox', OUTBOX_DIR],
  ];

  console.log('Resuscitation Health App Switchboard');
  for (const [label, dir] of buckets) {
    const files = fs.existsSync(dir)
      ? fs.readdirSync(dir)
        .filter((name) => {
          if (!name.endsWith('.md') || !name.startsWith('MSG-')) return false;
          if (name.endsWith('-EXIT.md')) return false;
          if (label === 'outbox' && name.endsWith('-REVIEW.md')) return false;
          return true;
        })
        .sort()
      : [];
    console.log(`\n${label}: ${files.length}`);
    for (const file of files) {
      const summary = messageSummary(path.join(dir, file));
      console.log(`- ${summary.messageId} [${summary.status}] ${summary.role} -> ${summary.delegate || 'unassigned'}`);
    }
  }
}

function claimMessage(opts) {
  if (!opts.messageId.trim()) throw new Error('Missing required --message-id.');
  if (!opts.delegate.trim()) throw new Error('Missing required --delegate.');

  const currentPath = findMessagePath(opts.messageId);
  if (!currentPath.startsWith(INBOX_DIR)) {
    throw new Error(`Message ${opts.messageId} must be in inbox/ before claiming.`);
  }

  const claimedAt = isoNow();
  let text = readFileText(currentPath);
  text = upsertScalar(text, 'status', 'CLAIMED', 'date');
  text = upsertScalar(text, 'selected_delegate', opts.delegate, 'status');
  text = upsertScalar(text, 'claimed_at', claimedAt, 'selected_delegate');
  writeFileText(currentPath, text);

  const nextPath = moveMessage(currentPath, ACTIVE_DIR);
  const registrySnapshots = loadLatestRegistrySnapshots();
  const previous = registrySnapshots.get(opts.messageId) || {};
  appendRegistry({
    message_id: opts.messageId,
    created_at: previous.created_at || claimedAt,
    claimed_at: claimedAt,
    closed_at: previous.closed_at || null,
    selected_delegate: opts.delegate,
    intended_role: parseScalar(extractField(text, 'intended_role')),
    ticket_refs: extractList(text, 'ticket_refs'),
    verdict: previous.verdict || 'claimed',
    reviewer: previous.reviewer || 'pending',
    event: 'claim',
    state: 'CLAIMED',
    location: path.relative(ROOT, nextPath),
  });

  console.log(`Claimed ${opts.messageId}`);
  console.log(path.relative(ROOT, nextPath));
}

function closeMessage(opts) {
  if (!opts.messageId.trim()) throw new Error('Missing required --message-id.');

  const currentPath = findMessagePath(opts.messageId);
  if (!currentPath.startsWith(ACTIVE_DIR)) {
    throw new Error(`Message ${opts.messageId} must be in active/ before closing.`);
  }

  const finishedAt = isoNow();
  let text = readFileText(currentPath);
  const exitInterview = parseScalar(extractField(text, 'required_exit_interview'));
  if (exitInterview) {
    const exitPath = resolveRepoPath(exitInterview);
    if (!fs.existsSync(exitPath)) {
      throw new Error(`Required exit interview not found: ${exitInterview}`);
    }
  }

  text = upsertScalar(text, 'status', 'DONE', 'date');
  text = upsertScalar(text, 'finished_at', finishedAt, 'claimed_at');
  writeFileText(currentPath, text);

  const nextPath = moveMessage(currentPath, OUTBOX_DIR);
  const registrySnapshots = loadLatestRegistrySnapshots();
  const previous = registrySnapshots.get(opts.messageId) || {};
  appendRegistry({
    message_id: opts.messageId,
    created_at: previous.created_at || finishedAt,
    claimed_at: previous.claimed_at || parseScalar(extractField(text, 'claimed_at')) || null,
    closed_at: finishedAt,
    selected_delegate: parseScalar(extractField(text, 'selected_delegate')),
    intended_role: parseScalar(extractField(text, 'intended_role')),
    ticket_refs: extractList(text, 'ticket_refs'),
    verdict: 'pending_review',
    reviewer: previous.reviewer || 'pending',
    event: 'close',
    state: 'DONE',
    location: path.relative(ROOT, nextPath),
  });

  console.log(`Closed ${opts.messageId} to outbox`);
  console.log(path.relative(ROOT, nextPath));
}

function reviewArtifactPath(messageId) {
  return path.join(OUTBOX_DIR, `${messageId}-REVIEW.md`);
}

function numberedLine(value) {
  return value && value.trim() ? `1. ${value.trim()}` : '1.';
}

function buildReviewArtifact(opts, reviewedAt) {
  return `message_id: "${opts.messageId}"
reviewer: "${opts.reviewer}"
verdict: "${opts.verdict}"
reviewed_at: "${reviewedAt}"

## Delegate Outcome
${numberedLine(opts.delegateOutcome)}

## Fixes Applied By Steward
${numberedLine(opts.fixesApplied)}

## Recurring Mistakes To Capture
${numberedLine(opts.recurringMistakes)}

## Follow-On Action
${numberedLine(opts.followOnAction)}
`;
}

function reviewMessage(opts) {
  if (!opts.messageId.trim()) throw new Error('Missing required --message-id.');
  if (!opts.reviewer.trim()) throw new Error('Missing required --reviewer.');
  if (!opts.verdict.trim()) throw new Error('Missing required --verdict.');

  const currentPath = findMessagePath(opts.messageId);
  if (!currentPath.startsWith(OUTBOX_DIR)) {
    throw new Error(`Message ${opts.messageId} must be in outbox/ before review.`);
  }

  const reviewedAt = isoNow();
  const reviewPath = reviewArtifactPath(opts.messageId);
  writeFileText(reviewPath, buildReviewArtifact(opts, reviewedAt));

  let text = readFileText(currentPath);
  text = upsertScalar(text, 'status', 'REVIEWED', 'date');
  text = upsertScalar(text, 'reviewer', opts.reviewer, 'finished_at');
  text = upsertScalar(text, 'review_verdict', opts.verdict, 'reviewer');
  text = upsertScalar(text, 'reviewed_at', reviewedAt, 'review_verdict');
  writeFileText(currentPath, text);

  const registrySnapshots = loadLatestRegistrySnapshots();
  const previous = registrySnapshots.get(opts.messageId) || {};
  appendRegistry({
    message_id: opts.messageId,
    created_at: previous.created_at || parseScalar(extractField(text, 'date')) || reviewedAt,
    claimed_at: previous.claimed_at || parseScalar(extractField(text, 'claimed_at')) || null,
    closed_at: previous.closed_at || parseScalar(extractField(text, 'finished_at')) || null,
    selected_delegate: parseScalar(extractField(text, 'selected_delegate')),
    intended_role: parseScalar(extractField(text, 'intended_role')),
    ticket_refs: extractList(text, 'ticket_refs'),
    verdict: opts.verdict,
    reviewer: opts.reviewer,
    event: 'review',
    state: 'REVIEWED',
    location: path.relative(ROOT, reviewPath),
    notes: opts.notes || '',
  });

  console.log(`Reviewed ${opts.messageId}`);
  console.log(path.relative(ROOT, reviewPath));
}

function archiveMessage(opts) {
  if (!opts.messageId.trim()) throw new Error('Missing required --message-id.');
  if (!opts.reviewer.trim()) throw new Error('Missing required --reviewer.');
  if (!opts.verdict.trim()) throw new Error('Missing required --verdict.');

  const currentPath = findMessagePath(opts.messageId);
  if (!currentPath.startsWith(OUTBOX_DIR)) {
    throw new Error(`Message ${opts.messageId} must be in outbox/ before archiving.`);
  }

  const reviewedAt = isoNow();
  let text = readFileText(currentPath);
  text = upsertScalar(text, 'status', 'ARCHIVED', 'date');
  text = upsertScalar(text, 'reviewer', opts.reviewer, 'finished_at');
  text = upsertScalar(text, 'review_verdict', opts.verdict, 'reviewer');
  text = upsertScalar(text, 'reviewed_at', reviewedAt, 'review_verdict');
  writeFileText(currentPath, text);

  const archiveDir = path.join(ARCHIVE_DIR, dateFolder());
  const exitInterview = parseScalar(extractField(text, 'required_exit_interview'));
  const exitInterviewPath = resolveRepoPath(exitInterview);
  const reviewPath = reviewArtifactPath(opts.messageId);
  const archivePath = moveMessage(currentPath, archiveDir);
  moveIfExists(exitInterviewPath, archiveDir);
  moveIfExists(reviewPath, archiveDir);
  const registrySnapshots = loadLatestRegistrySnapshots();
  const previous = registrySnapshots.get(opts.messageId) || {};
  appendRegistry({
    message_id: opts.messageId,
    created_at: previous.created_at || reviewedAt,
    claimed_at: previous.claimed_at || parseScalar(extractField(text, 'claimed_at')) || null,
    closed_at: previous.closed_at || parseScalar(extractField(text, 'finished_at')) || null,
    selected_delegate: parseScalar(extractField(text, 'selected_delegate')),
    intended_role: parseScalar(extractField(text, 'intended_role')),
    ticket_refs: extractList(text, 'ticket_refs'),
    verdict: opts.verdict,
    reviewer: opts.reviewer,
    event: 'archive',
    state: 'ARCHIVED',
    location: path.relative(ROOT, archivePath),
    notes: opts.notes || '',
  });

  console.log(`Archived ${opts.messageId}`);
  console.log(path.relative(ROOT, archivePath));
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  ensureDirs();

  if (opts.command === 'list') {
    listMessages();
    return;
  }
  if (opts.command === 'claim') {
    claimMessage(opts);
    return;
  }
  if (opts.command === 'close') {
    closeMessage(opts);
    return;
  }
  if (opts.command === 'review') {
    reviewMessage(opts);
    return;
  }
  if (opts.command === 'archive') {
    archiveMessage(opts);
    return;
  }

  throw new Error(`Unknown command: ${opts.command}`);
}

try {
  main();
} catch (error) {
  console.error(`Switchboard error: ${error.message}`);
  process.exit(1);
}
