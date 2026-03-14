# Resuscitation Health App Session Calibration Packet

- generated_at: 2026-03-13T23:09:24.148Z
- reviewer: Steward
- latest_commit: b64b9b2669a175f4464271b95b660441d83779d9
- next_priority: none
- question_count: 14

Use this packet after reading `LATEST_SESSION_REENTRY.md`.

For each calibration item:
1. treat the answer as the current project default
2. allow direct operator overrides to win
3. keep live repo state and live queue ahead of stale continuity metadata

## CAL-001

### Question
What role am I in for this session?

### Default Answer
Default next-session role is `Steward` because the current queued lane is `none`.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/cycles/CYCLE-001-HEADMASTER-BOOTSTRAP.md`
  - `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`

### Override Rule
If the operator explicitly assigns a different role, the operator wins.

## CAL-002

### Question
What is the real priority order right now?

### Default Answer
There is no currently recorded bounded next priority. The next session should refresh the queue and cycle log before choosing a lane.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/cycles/CYCLE-001-HEADMASTER-BOOTSTRAP.md`
  - `appendix/guidance/headmaster/research/cycles/CYCLE-001-HEADMASTER-BOOTSTRAP.md`

### Override Rule
If the operator reprioritizes explicitly, that override wins.

## CAL-003

### Question
Should I stay strictly in-lane or fix nearby drift?

### Default Answer
Stay bounded to the named lane, but fix nearby drift when it is necessary for truth, continuity, verification, or safe closure. Do not silently expand into adjacent product work.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/system/TICKET_PROCESS.md`
  - `appendix/guidance/switchboard/PATHWAYS.md`

### Override Rule
If the operator asks for strict narrow execution, do only the named lane.

## CAL-004

### Question
What outcome would make this session successful?

### Default Answer
A successful session leaves the repo in a truer and more recoverable state: the lane advances correctly, artifacts are updated on disk, review fixes are applied if needed, and the next step is clearer than before.

### Status
`default-until-overridden`

### Basis
  - `README.md`
  - `appendix/guidance/exit/PROTOCOL.md`

### Override Rule
If the operator defines a narrower success condition for the session, that narrower condition wins.

## CAL-005

### Question
How much autonomy should I use before pausing?

### Default Answer
Use high autonomy inside a bounded lane. Pause only for destructive actions, ambiguous user-intent conflicts, or major cross-cutting structural changes outside the lane.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/system/METHODOLOGY.md`
  - `appendix/guidance/warden/research/system/METHODOLOGY.md`

### Override Rule
If the operator asks for tighter checkpoints, adopt them immediately.

## CAL-006

### Question
Are any areas off-limits unless explicitly approved?

### Default Answer
Yes. Destructive deletes or moves of canonical materials, secret-handling changes, broad redesigns outside the lane, and sweeping unrelated work into a cycle are off-limits unless explicitly approved.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/system/METHODOLOGY.md`
  - `appendix/guidance/warden/research/system/CONSTITUTION.md`

### Override Rule
Explicit operator approval can open a bounded exception.

## CAL-007

### Question
If operator intent conflicts with docs, which wins?

### Default Answer
Latest explicit operator intent wins, but the accepted repo and docs must be updated so the on-disk source of truth catches up before closure.

### Status
`default-until-overridden`

### Basis
  - `README.md`
  - `appendix/guidance/exit/PROTOCOL.md`

### Override Rule
If there is no explicit operator direction, fall back to current on-disk doctrine.

## CAL-008

### Question
Are there off-repo notes, hidden decisions, or extra contexts that matter?

### Default Answer
Assume none unless explicitly given. The sanctioned extra-memory source is the raw terminal log named by Exit.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/exit/README.md`
  - `appendix/guidance/exit/logs/latest_log_pointer.json`

### Override Rule
If the operator names another external context, record and use it explicitly.

## CAL-009

### Question
Which external projects or corpora are authoritative, and which are only inspiration?

### Default Answer
Authoritative sources are live Resuscitation Health App repo state, the current Headmaster cycle log, the current Switchboard queue, the current Warden evidence, and Toolkit Librarian resources when intentionally cited. Prototype assets and css-web-ui-demos are inspiration unless promoted into a lane with evidence.

### Status
`default-until-overridden`

### Basis
  - `README.md`
  - `appendix/guidance/headmaster/research/system/RESOURCE_ATLAS.md`

### Override Rule
If the operator elevates a source for the current lane, record that elevation explicitly.

## CAL-010

### Question
Which current risks should I watch most aggressively?

### Default Answer
Watch continuity drift, lane and role drift, bridge patches becoming permanent by accident, evidence overclaiming, design debt in the large HTML tool islands, and stale docs after structural changes.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/system/BRIDGE_PATCH_BACKLOG.md`
  - `appendix/guidance/warden/report/latest_analysis.md`

### Override Rule
If the operator highlights a more urgent risk, treat that as the session's primary watchpoint.

## CAL-011

### Question
May I open or update bounded tickets when I discover new needs?

### Default Answer
Yes. Open or update bounded tickets when needed, but do not create sprawling new workstreams without clearly justifying them.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/system/TICKET_PROCESS.md`
  - `appendix/guidance/switchboard/PROTOCOL.md`

### Override Rule
If the operator asks for recommendation-only behavior, recommend instead of opening or editing tickets.

## CAL-012

### Question
What proof level counts as complete?

### Default Answer
For research-only lanes, docs correct on disk are the minimum. For implementation lanes, completion requires local verification, review and fixes, push, green GitHub CI and Deploy, and Exit refresh for cycle closure.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/headmaster/research/system/DEPLOYMENT_PROTOCOL.md`
  - `appendix/guidance/warden/research/system/METHODOLOGY.md`

### Override Rule
If the operator explicitly lowers or raises the proof bar for a lane, record that as a lane-specific exception.

## CAL-013

### Question
If operator contact is lost mid-lane, what default decision rule should I follow?

### Default Answer
Optimize for recoverability over cleverness. Keep work bounded and prefer a durable partial state plus a clear next step over speculative expansion.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/exit/PROTOCOL.md`
  - `appendix/guidance/exit/PATHWAYS.md`

### Override Rule
If the operator leaves a different explicit mid-lane instruction, that instruction wins.

## CAL-014

### Question
What would make it true that I really resumed from where the last session left off?

### Default Answer
A true resume reads Exit, verifies live repo state, identifies the real current lane, catches drift instead of repeating it, and continues without needing a broad reorientation pass.

### Status
`default-until-overridden`

### Basis
  - `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`
  - `appendix/guidance/exit/PROTOCOL.md`

### Override Rule
If the operator defines a sharper resume standard, adopt that as the new calibration target.
