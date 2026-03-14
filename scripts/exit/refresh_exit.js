#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..", "..");
const EXIT_RAW_LOGS = path.join(ROOT, "appendix", "guidance", "exit", "logs", "raw");
const EXIT_ROOT = path.join(ROOT, "appendix", "guidance", "exit");
const EXIT_LOGS = path.join(EXIT_ROOT, "logs");
const EXIT_REGISTRY = path.join(EXIT_ROOT, "registry");
const EXIT_PROMPTS = path.join(EXIT_ROOT, "prompts");
const EXIT_SNAPSHOTS = path.join(EXIT_ROOT, "snapshots");
const STATE_PATH = path.join(EXIT_REGISTRY, "state.json");
const CALIBRATION_PATH = path.join(EXIT_REGISTRY, "calibration.json");
const LOG_CATALOG_PATH = path.join(EXIT_LOGS, "log_catalog.json");
const LATEST_LOG_POINTER_PATH = path.join(EXIT_LOGS, "latest_log_pointer.json");
const LATEST_PROMPT_PATH = path.join(EXIT_PROMPTS, "LATEST_SESSION_REENTRY.md");
const LATEST_CALIBRATION_PATH = path.join(EXIT_PROMPTS, "LATEST_SESSION_CALIBRATION.md");

function parseArgs(argv) {
  const args = { command: "refresh", log: "", reviewer: "Steward" };
  const parts = argv.slice(2);
  if (parts[0] && !parts[0].startsWith("--")) {
    args.command = parts.shift();
  }
  for (let i = 0; i < parts.length; i += 1) {
    const part = parts[i];
    if (part === "--log") {
      args.log = parts[i + 1] || "";
      i += 1;
    } else if (part === "--reviewer") {
      args.reviewer = parts[i + 1] || "Steward";
      i += 1;
    }
  }
  return args;
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) {
    return null;
  }
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function rel(filePath) {
  return path.relative(ROOT, filePath).replace(/\\/g, "/");
}

function git(cmd) {
  return execSync(cmd, { cwd: ROOT, encoding: "utf8", maxBuffer: 16 * 1024 * 1024 }).trim();
}

function computeLiveContinuityDrift(recordedState) {
  const liveHead = git("git rev-parse HEAD");
  const liveWorktreeClean = git("git status --porcelain") === "";
  const liveSwitchboard = {
    inbox: listMessageFiles(path.join(ROOT, "appendix", "guidance", "switchboard", "inbox")),
    active: listMessageFiles(path.join(ROOT, "appendix", "guidance", "switchboard", "active")),
    outbox: listMessageFiles(path.join(ROOT, "appendix", "guidance", "switchboard", "outbox")),
  };

  const driftReasons = [];
  if (recordedState.latest_commit !== liveHead) {
    driftReasons.push("git HEAD advanced beyond the recorded continuity snapshot");
  }
  if (recordedState.worktree_clean !== liveWorktreeClean) {
    driftReasons.push("worktree cleanliness changed after the last continuity refresh");
  }
  if (
    JSON.stringify(recordedState.switchboard?.inbox || []) !== JSON.stringify(liveSwitchboard.inbox) ||
    JSON.stringify(recordedState.switchboard?.active || []) !== JSON.stringify(liveSwitchboard.active) ||
    JSON.stringify(recordedState.switchboard?.outbox || []) !== JSON.stringify(liveSwitchboard.outbox)
  ) {
    driftReasons.push("Switchboard queue changed after the last continuity refresh");
  }

  return {
    stale: driftReasons.length > 0,
    live_head: liveHead,
    live_worktree_clean: liveWorktreeClean,
    live_switchboard: liveSwitchboard,
    reasons: driftReasons,
  };
}

function listLogs() {
  if (!fs.existsSync(EXIT_RAW_LOGS)) {
    return [];
  }
  return fs
    .readdirSync(EXIT_RAW_LOGS)
    .filter((name) => name.endsWith(".txt"))
    .map((name) => {
      const fullPath = path.join(EXIT_RAW_LOGS, name);
      const stat = fs.statSync(fullPath);
      return {
        name,
        path: rel(fullPath),
        size_bytes: stat.size,
        mtime: stat.mtime.toISOString(),
      };
    })
    .sort((a, b) => new Date(b.mtime) - new Date(a.mtime));
}

function listMessageFiles(folderPath) {
  if (!fs.existsSync(folderPath)) {
    return [];
  }
  return fs
    .readdirSync(folderPath)
    .filter((name) => {
      if (!name.endsWith(".md") || name === "README.md" || name.endsWith("-EXIT.md")) {
        return false;
      }
      if (path.basename(folderPath) === "outbox" && name.endsWith("-REVIEW.md")) {
        return false;
      }
      return true;
    })
    .sort();
}

function collectSwitchboardInboxMessages() {
  const inboxDir = path.join(ROOT, "appendix", "guidance", "switchboard", "inbox");
  if (!fs.existsSync(inboxDir)) {
    return [];
  }

  return fs
    .readdirSync(inboxDir)
    .filter((name) => name.endsWith(".md") && name.startsWith("MSG-") && name !== "README.md")
    .sort()
    .map((name) => {
      const fullPath = path.join(inboxDir, name);
      const text = fs.readFileSync(fullPath, "utf8");
      const role = (text.match(/^intended_role:\s*"([^"]+)"/m) || [])[1] || "unknown";
      const ticketRefsBlock = text.match(/^ticket_refs:\s*\n((?:\s+-\s.*\n?)*)/m);
      const ticketRefs = ticketRefsBlock
        ? ticketRefsBlock[1]
            .split("\n")
            .filter(Boolean)
            .map((line) => line.replace(/^\s+-\s*/, "").replace(/^"|"$/g, ""))
        : [];
      return {
        message_id: name.replace(/\.md$/, ""),
        path: rel(fullPath),
        intended_role: role,
        ticket_refs: ticketRefs,
      };
    });
}

function collectOpenHeadmasterTickets() {
  const ticketsDir = path.join(
    ROOT,
    "appendix",
    "guidance",
    "headmaster",
    "research",
    "tickets",
  );

  return fs
    .readdirSync(ticketsDir)
    .filter((name) => name.endsWith(".yaml") && name !== "research_ticket_template.yaml")
    .map((name) => {
      const fullPath = path.join(ticketsDir, name);
      const text = fs.readFileSync(fullPath, "utf8");
      const ticketId = (text.match(/^ticket_id:\s*"([^"]+)"/m) || [])[1] || name;
      const status = (text.match(/^status:\s*"([^"]+)"/m) || [])[1] || "UNKNOWN";
      const objective = (text.match(/^objective:\s*\|\n([\s\S]*?)(?:\n[a-z_]+:|\nacceptance_criteria:|$)/m) || [])[1]
        ?.trim()
        .split("\n")[0] || "";
      return {
        ticket_id: ticketId,
        status,
        objective,
        path: rel(fullPath),
      };
    })
    .filter((ticket) => ticket.status !== "CLOSED" && ticket.status !== "HEADMASTER_COMPLETE")
    .sort((a, b) => a.ticket_id.localeCompare(b.ticket_id));
}

function deriveDefaultRole(state) {
  if (state.next_priority?.role === "headmaster") {
    return "Headmaster";
  }
  if (state.next_priority?.role === "warden") {
    return "Warden";
  }
  if (state.next_priority?.role === "offgrid") {
    return "offgrid";
  }
  const ticketId = state.next_priority?.ticket_id || "";
  if (ticketId.startsWith("HREQ-")) {
    return "Headmaster";
  }
  if (ticketId.startsWith("WDN-")) {
    return "Warden";
  }
  return "Steward";
}

function buildCalibrationItems(state) {
  const defaultRole = deriveDefaultRole(state);
  const nextPriorityAnswer =
    state.next_priority.ticket_id === "none"
      ? "There is no currently recorded bounded next priority. The next session should refresh the queue and cycle log before choosing a lane."
      : `Current default priority is \`${state.next_priority.ticket_id}\`, because Exit records it as the next bounded lane from the live cycle state. After that, choose the next bounded lane from the refreshed backlog rather than stale chat memory.`;

  return [
    {
      id: "CAL-001",
      question: "What role am I in for this session?",
      default_answer: `Default next-session role is \`${defaultRole}\` because the current queued lane is \`${state.next_priority.ticket_id}\`.`,
      basis: [state.cycle_log_path, state.latest_prompt_path],
      override_rule: "If the operator explicitly assigns a different role, the operator wins.",
    },
    {
      id: "CAL-002",
      question: "What is the real priority order right now?",
      default_answer: nextPriorityAnswer,
      basis: [state.cycle_log_path, state.next_priority.path || state.cycle_log_path],
      override_rule: "If the operator reprioritizes explicitly, that override wins.",
    },
    {
      id: "CAL-003",
      question: "Should I stay strictly in-lane or fix nearby drift?",
      default_answer:
        "Stay bounded to the named lane, but fix nearby drift when it is necessary for truth, continuity, verification, or safe closure. Do not silently expand into adjacent product work.",
      basis: [
        "appendix/guidance/headmaster/research/system/TICKET_PROCESS.md",
        "appendix/guidance/switchboard/PATHWAYS.md",
      ],
      override_rule: "If the operator asks for strict narrow execution, do only the named lane.",
    },
    {
      id: "CAL-004",
      question: "What outcome would make this session successful?",
      default_answer:
        "A successful session leaves the repo in a truer and more recoverable state: the lane advances correctly, artifacts are updated on disk, review fixes are applied if needed, and the next step is clearer than before.",
      basis: ["README.md", "appendix/guidance/exit/PROTOCOL.md"],
      override_rule: "If the operator defines a narrower success condition for the session, that narrower condition wins.",
    },
    {
      id: "CAL-005",
      question: "How much autonomy should I use before pausing?",
      default_answer:
        "Use high autonomy inside a bounded lane. Pause only for destructive actions, ambiguous user-intent conflicts, or major cross-cutting structural changes outside the lane.",
      basis: [
        "appendix/guidance/headmaster/research/system/METHODOLOGY.md",
        "appendix/guidance/warden/research/system/METHODOLOGY.md",
      ],
      override_rule: "If the operator asks for tighter checkpoints, adopt them immediately.",
    },
    {
      id: "CAL-006",
      question: "Are any areas off-limits unless explicitly approved?",
      default_answer:
        "Yes. Destructive deletes or moves of canonical materials, secret-handling changes, broad redesigns outside the lane, and sweeping unrelated work into a cycle are off-limits unless explicitly approved.",
      basis: [
        "appendix/guidance/headmaster/research/system/METHODOLOGY.md",
        "appendix/guidance/warden/research/system/CONSTITUTION.md",
      ],
      override_rule: "Explicit operator approval can open a bounded exception.",
    },
    {
      id: "CAL-007",
      question: "If operator intent conflicts with docs, which wins?",
      default_answer:
        "Latest explicit operator intent wins, but the accepted repo and docs must be updated so the on-disk source of truth catches up before closure.",
      basis: ["README.md", "appendix/guidance/exit/PROTOCOL.md"],
      override_rule: "If there is no explicit operator direction, fall back to current on-disk doctrine.",
    },
    {
      id: "CAL-008",
      question: "Are there off-repo notes, hidden decisions, or extra contexts that matter?",
      default_answer:
        "Assume none unless explicitly given. The sanctioned extra-memory source is the raw terminal log named by Exit.",
      basis: ["appendix/guidance/exit/README.md", "appendix/guidance/exit/logs/latest_log_pointer.json"],
      override_rule: "If the operator names another external context, record and use it explicitly.",
    },
    {
      id: "CAL-009",
      question: "Which external projects or corpora are authoritative, and which are only inspiration?",
      default_answer:
        "Authoritative sources are live Resuscitation Health App repo state, the current Headmaster cycle log, the current Switchboard queue, the current Warden evidence, and Toolkit Librarian resources when intentionally cited. Prototype assets and css-web-ui-demos are inspiration unless promoted into a lane with evidence.",
      basis: [
        "README.md",
        "appendix/guidance/headmaster/research/system/RESOURCE_ATLAS.md",
      ],
      override_rule: "If the operator elevates a source for the current lane, record that elevation explicitly.",
    },
    {
      id: "CAL-010",
      question: "Which current risks should I watch most aggressively?",
      default_answer:
        "Watch continuity drift, lane and role drift, bridge patches becoming permanent by accident, evidence overclaiming, design debt in the large HTML tool islands, and stale docs after structural changes.",
      basis: [
        "appendix/guidance/headmaster/research/system/BRIDGE_PATCH_BACKLOG.md",
        state.warden_work_report_path,
      ],
      override_rule: "If the operator highlights a more urgent risk, treat that as the session's primary watchpoint.",
    },
    {
      id: "CAL-011",
      question: "May I open or update bounded tickets when I discover new needs?",
      default_answer:
        "Yes. Open or update bounded tickets when needed, but do not create sprawling new workstreams without clearly justifying them.",
      basis: [
        "appendix/guidance/headmaster/research/system/TICKET_PROCESS.md",
        "appendix/guidance/switchboard/PROTOCOL.md",
      ],
      override_rule: "If the operator asks for recommendation-only behavior, recommend instead of opening or editing tickets.",
    },
    {
      id: "CAL-012",
      question: "What proof level counts as complete?",
      default_answer:
        "For research-only lanes, docs correct on disk are the minimum. For implementation lanes, completion requires local verification, review and fixes, push, green GitHub CI and Deploy, and Exit refresh for cycle closure.",
      basis: [
        "appendix/guidance/headmaster/research/system/DEPLOYMENT_PROTOCOL.md",
        "appendix/guidance/warden/research/system/METHODOLOGY.md",
      ],
      override_rule: "If the operator explicitly lowers or raises the proof bar for a lane, record that as a lane-specific exception.",
    },
    {
      id: "CAL-013",
      question: "If operator contact is lost mid-lane, what default decision rule should I follow?",
      default_answer:
        "Optimize for recoverability over cleverness. Keep work bounded and prefer a durable partial state plus a clear next step over speculative expansion.",
      basis: ["appendix/guidance/exit/PROTOCOL.md", "appendix/guidance/exit/PATHWAYS.md"],
      override_rule: "If the operator leaves a different explicit mid-lane instruction, that instruction wins.",
    },
    {
      id: "CAL-014",
      question: "What would make it true that I really resumed from where the last session left off?",
      default_answer:
        "A true resume reads Exit, verifies live repo state, identifies the real current lane, catches drift instead of repeating it, and continues without needing a broad reorientation pass.",
      basis: [state.latest_prompt_path, "appendix/guidance/exit/PROTOCOL.md"],
      override_rule: "If the operator defines a sharper resume standard, adopt that as the new calibration target.",
    },
  ].map((item) => ({
    ...item,
    answer_status: "default-until-overridden",
  }));
}

function buildCalibrationPacket(state) {
  const items = state.calibration.items
    .map((item) => {
      const basis = item.basis.map((entry) => `  - \`${entry}\``).join("\n");
      return `## ${item.id}

### Question
${item.question}

### Default Answer
${item.default_answer}

### Status
\`${item.answer_status}\`

### Basis
${basis}

### Override Rule
${item.override_rule}`;
    })
    .join("\n\n");

  return `# Resuscitation Health App Session Calibration Packet

- generated_at: ${state.last_updated_at}
- reviewer: ${state.last_reviewed_by}
- latest_commit: ${state.latest_commit}
- next_priority: ${state.next_priority.ticket_id}
- question_count: ${state.calibration.question_count}

Use this packet after reading \`LATEST_SESSION_REENTRY.md\`.

For each calibration item:
1. treat the answer as the current project default
2. allow direct operator overrides to win
3. keep live repo state and live queue ahead of stale continuity metadata

${items}
`;
}

function buildPrompt(state) {
  const queue = state.switchboard.inbox.length
    ? state.switchboard.inbox.map((item) => `- \`${item}\``).join("\n")
    : "- none";

  const openTickets = state.open_headmaster_tickets.length
    ? state.open_headmaster_tickets
        .map((ticket) => `- \`${ticket.ticket_id}\` (${ticket.status}) — ${ticket.path}`)
        .join("\n")
    : "- none";

  return `# Resuscitation Health App Session Reentry Prompt

Use this prompt when a new terminal session, CLI, IDE, or reassigned delegate must rebuild Resuscitation Health App context without relying on vanished chat history.

## Role
You are resuming Resuscitation Health App with a continuity-first mindset. Read the current on-disk artifacts first, then act within the assigned lane.

## Read Order
1. \`README.md\`
2. \`appendix/guidance/exit/README.md\`
3. \`appendix/guidance/exit/PROTOCOL.md\`
4. \`appendix/guidance/exit/RECOVERY_RUBRIC.md\`
5. \`appendix/guidance/exit/CALIBRATION_PROTOCOL.md\`
6. \`appendix/guidance/exit/CALIBRATION_RUBRIC.md\`
7. \`appendix/guidance/exit/CHECKLIST.md\`
8. \`${state.latest_prompt_path}\`
9. \`${state.calibration.packet_path}\`
10. \`${state.snapshot_path}\`
11. \`${state.latest_log.path}\`
12. \`appendix/guidance/headmaster/README.md\`
13. \`appendix/guidance/warden/README.md\`
14. \`appendix/guidance/switchboard/README.md\`
15. \`appendix/guidance/switchboard/PATHWAYS.md\`
16. \`${state.cycle_log_path}\`
17. \`${state.warden_work_report_path}\`

## Current State Summary
- latest commit: \`${state.latest_commit}\`
- worktree clean: \`${state.worktree_clean}\`
- latest raw log: \`${state.latest_log.path}\`
- last continuity refresh: \`${state.last_updated_at}\`
- reviewer: \`${state.last_reviewed_by}\`
- default session role: \`${state.calibration.default_role}\`
- calibration packet: \`${state.calibration.packet_path}\`

## Live-State Guard
Before trusting the summary above, compare the recorded continuity packet with live repo state:
1. run \`git rev-parse HEAD\`
2. run \`git status --porcelain\`
3. check the current Switchboard queue on disk

If live state differs from the recorded continuity packet, trust:
1. live \`HEAD\`
2. the current cycle log
3. the live Switchboard queue
4. the current Warden work report

Then run \`npm run exit:refresh -- --reviewer "Steward"\` as soon as practical to refresh continuity metadata.

## Current Queue
${queue}

## Open Headmaster Tickets
${openTickets}

## Calibration Rule
Read \`${state.calibration.packet_path}\` before acting. It carries the current 14-question default doctrine for the next session. Treat those answers as \`default-until-overridden\`, not as stronger than live repo state or explicit operator direction.

## Role Boundary Guard
If you are resuming as a delegate for a Headmaster, Warden, or offgrid message:
1. do the work for the role named in the message
2. write the required exit interview
3. stop there unless you were also explicitly assigned as \`Steward\`

Default rule:
- delegates do not perform \`switchboard:review\` or \`switchboard:archive\`
- Steward handles review, fixes, archive, and final acceptance normalization

## Recommended Next Lane
\`${state.next_priority.ticket_id}\` — ${state.next_priority.reason}

## Rule
Do not treat chat memory as the source of truth. The source of truth is the documented cycle, the Warden evidence, the Switchboard queue, and the latest raw log named above.
`;
}

function buildSnapshot(state) {
  const queue = state.switchboard.inbox.length
    ? state.switchboard.inbox.map((item) => `- \`${item}\``).join("\n")
    : "- none";

  const tickets = state.open_headmaster_tickets.length
    ? state.open_headmaster_tickets
        .map((ticket) => `- \`${ticket.ticket_id}\` (${ticket.status}) — ${ticket.path}`)
        .join("\n")
    : "- none";

  return `# Exit Continuity Snapshot

- created_at: ${state.created_at}
- last_updated_at: ${state.last_updated_at}
- last_reviewed_at: ${state.last_reviewed_at}
- last_reviewed_by: ${state.last_reviewed_by}

## Latest Raw Log
- \`${state.latest_log.path}\`

## Current Repo State
- latest_commit: \`${state.latest_commit}\`
- worktree_clean: \`${state.worktree_clean}\`
- default_session_role: \`${state.calibration.default_role}\`
- calibration_packet: \`${state.calibration.packet_path}\`

## Live-State Guard
This snapshot is only as current as its refresh timestamp.
If \`git rev-parse HEAD\`, \`git status --porcelain\`, or the live Switchboard queue differ from this snapshot, treat this file as stale context support and trust the live repo plus the current cycle log over this snapshot metadata.

## Authority Pointers
1. cycle log:
   - \`${state.cycle_log_path}\`
2. mutable Warden report:
   - \`${state.warden_work_report_path}\`
3. accepted Warden report:
   - \`${state.warden_cycle_report_path}\`

## Queue
${queue}

## Open Headmaster Tickets
${tickets}

## Recommended Next Lane
- \`${state.next_priority.ticket_id}\` — ${state.next_priority.reason}
`;
}

function refresh(args) {
  const now = new Date().toISOString();
  const existingState = readJsonIfExists(STATE_PATH);
  const logs = listLogs();
  if (logs.length === 0) {
    throw new Error("No raw logs found in appendix/guidance/exit/logs/raw/");
  }

  const requestedLog = args.log
    ? rel(path.isAbsolute(args.log) ? args.log : path.join(ROOT, args.log))
    : "";
  const latestLog = requestedLog
    ? logs.find((entry) => entry.path === requestedLog) || logs[0]
    : logs[0];

  const switchboard = {
    inbox: listMessageFiles(path.join(ROOT, "appendix", "guidance", "switchboard", "inbox")),
    active: listMessageFiles(path.join(ROOT, "appendix", "guidance", "switchboard", "active")),
    outbox: listMessageFiles(path.join(ROOT, "appendix", "guidance", "switchboard", "outbox")),
  };

  const openHeadmasterTickets = collectOpenHeadmasterTickets();
  const queuedMessages = collectSwitchboardInboxMessages();
  const nextPriority =
    queuedMessages[0]
      ? {
          ticket_id: queuedMessages[0].ticket_refs[0] || queuedMessages[0].message_id,
          message_id: queuedMessages[0].message_id,
          path: queuedMessages[0].path,
          role: queuedMessages[0].intended_role,
          reason: `Switchboard queue prioritizes \`${queuedMessages[0].message_id}\` as the next unclaimed ${queuedMessages[0].intended_role} lane.`,
        }
      : openHeadmasterTickets[0] || {
          ticket_id: "none",
          path: "",
          role: "Steward",
          reason: "no open Headmaster ticket currently recorded",
        };

  const state = {
    created_at: existingState?.created_at || now,
    last_updated_at: now,
    last_reviewed_at: now,
    last_reviewed_by: args.reviewer || "Steward",
    latest_commit: git("git rev-parse HEAD"),
    worktree_clean: git("git status --porcelain") === "",
    latest_log: latestLog,
    log_count: logs.length,
    cycle_log_path:
      "appendix/guidance/headmaster/research/cycles/CYCLE-001-HEADMASTER-BOOTSTRAP.md",
    warden_work_report_path:
      "appendix/guidance/warden/report/latest_analysis.md",
    warden_cycle_report_path:
      "appendix/guidance/warden/report/latest_analysis.md",
    switchboard,
    open_headmaster_tickets: openHeadmasterTickets,
    next_priority: {
      ticket_id: nextPriority.ticket_id,
      message_id: nextPriority.message_id || "",
      path: nextPriority.path || "",
      role: nextPriority.role || "",
      reason:
        nextPriority.reason || nextPriority.objective || "next unfinished Headmaster ticket",
    },
    latest_prompt_path: rel(LATEST_PROMPT_PATH),
    calibration: {
      packet_path: rel(LATEST_CALIBRATION_PATH),
      registry_path: rel(CALIBRATION_PATH),
      question_count: 0,
      default_role: "Steward",
      items: [],
    },
    snapshot_path: "",
  };

  state.live_state_guard = {
    rule: "If live HEAD, worktree state, or Switchboard queue differs from this continuity packet, trust the live repo state and refresh Exit as soon as practical.",
    checked_at_refresh: true,
  };
  state.calibration.items = buildCalibrationItems(state);
  state.calibration.question_count = state.calibration.items.length;
  state.calibration.default_role = deriveDefaultRole(state);

  fs.mkdirSync(EXIT_LOGS, { recursive: true });
  fs.mkdirSync(EXIT_REGISTRY, { recursive: true });
  fs.mkdirSync(EXIT_PROMPTS, { recursive: true });
  fs.mkdirSync(EXIT_SNAPSHOTS, { recursive: true });

  fs.writeFileSync(LOG_CATALOG_PATH, JSON.stringify(logs, null, 2) + "\n");
  fs.writeFileSync(
    LATEST_LOG_POINTER_PATH,
    JSON.stringify(
      {
        path: latestLog.path,
        name: latestLog.name,
        captured_at: now,
        note: "Raw transcript remains canonical under appendix/guidance/exit/logs/raw/",
      },
      null,
      2,
    ) + "\n",
  );

  const stamp = now.replace(/[-:]/g, "").slice(0, 15);
  const snapshotName = `${stamp}-continuity.md`;
  const snapshotPath = path.join(EXIT_SNAPSHOTS, snapshotName);
  state.snapshot_path = rel(snapshotPath);

  fs.writeFileSync(snapshotPath, buildSnapshot(state));
  fs.writeFileSync(LATEST_PROMPT_PATH, buildPrompt(state));
  fs.writeFileSync(LATEST_CALIBRATION_PATH, buildCalibrationPacket(state));
  fs.writeFileSync(CALIBRATION_PATH, JSON.stringify(state.calibration, null, 2) + "\n");
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + "\n");

  console.log("Exit refresh complete.");
  console.log(`Latest raw log : ${latestLog.path}`);
  console.log(`State file     : ${rel(STATE_PATH)}`);
  console.log(`Calibration    : ${rel(LATEST_CALIBRATION_PATH)}`);
  console.log(`Snapshot       : ${rel(snapshotPath)}`);
  console.log(`Reentry prompt : ${rel(LATEST_PROMPT_PATH)}`);
}

function status() {
  const state = readJsonIfExists(STATE_PATH);
  if (!state) {
    console.log("Exit state not initialized yet. Run `npm run exit:refresh`.");
    return;
  }

  const drift = computeLiveContinuityDrift(state);

  console.log("Resuscitation Health App Exit");
  console.log("");
  console.log(`created_at      : ${state.created_at}`);
  console.log(`last_updated_at : ${state.last_updated_at}`);
  console.log(`last_reviewed_at: ${state.last_reviewed_at}`);
  console.log(`reviewer        : ${state.last_reviewed_by}`);
  console.log(`latest_log      : ${state.latest_log.path}`);
  console.log(`next_priority   : ${state.next_priority.ticket_id}`);
  console.log(`default_role    : ${state.calibration?.default_role || "unknown"}`);
  console.log(`snapshot        : ${state.snapshot_path}`);
  console.log(`prompt          : ${state.latest_prompt_path}`);
  console.log(`calibration     : ${state.calibration?.packet_path || "missing"}`);
  console.log(`live_head       : ${drift.live_head}`);
  console.log(`live_worktree   : ${drift.live_worktree_clean}`);
  console.log(`stale           : ${drift.stale}`);
  if (drift.stale) {
    console.log("stale_reasons   :");
    drift.reasons.forEach((reason) => console.log(`- ${reason}`));
    console.log('guidance        : run `npm run exit:refresh -- --reviewer "Steward"` after reviewing live repo state');
  }
}

const args = parseArgs(process.argv);
if (args.command === "status") {
  status();
} else {
  refresh(args);
}
