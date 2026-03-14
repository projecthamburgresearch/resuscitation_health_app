# Resuscitation Health App Session Reentry Prompt

Use this prompt when a new terminal session, CLI, IDE, or reassigned delegate must rebuild Resuscitation Health App context without relying on vanished chat history.

## Role
You are resuming Resuscitation Health App with a continuity-first mindset. Read the current on-disk artifacts first, then act within the assigned lane.

## Read Order
1. `README.md`
2. `appendix/guidance/exit/README.md`
3. `appendix/guidance/exit/PROTOCOL.md`
4. `appendix/guidance/exit/RECOVERY_RUBRIC.md`
5. `appendix/guidance/exit/CALIBRATION_PROTOCOL.md`
6. `appendix/guidance/exit/CALIBRATION_RUBRIC.md`
7. `appendix/guidance/exit/CHECKLIST.md`
8. `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`
9. `appendix/guidance/exit/prompts/LATEST_SESSION_CALIBRATION.md`
10. `appendix/guidance/exit/snapshots/20260314T052627-continuity.md`
11. `appendix/guidance/exit/logs/raw/202602221025-terminal-saved-output-health-app-logs.txt`
12. `appendix/guidance/headmaster/README.md`
13. `appendix/guidance/warden/README.md`
14. `appendix/guidance/switchboard/README.md`
15. `appendix/guidance/switchboard/PATHWAYS.md`
16. `appendix/guidance/headmaster/research/cycles/CYCLE-001-HEADMASTER-BOOTSTRAP.md`
17. `appendix/guidance/warden/report/latest_analysis.md`

## Current State Summary
- latest commit: `2c2add703e9878d72166c54709c13c4949e0e871`
- worktree clean: `false`
- latest raw log: `appendix/guidance/exit/logs/raw/202602221025-terminal-saved-output-health-app-logs.txt`
- last continuity refresh: `2026-03-14T05:26:27.231Z`
- reviewer: `Steward`
- default session role: `Steward`
- calibration packet: `appendix/guidance/exit/prompts/LATEST_SESSION_CALIBRATION.md`

## Live-State Guard
Before trusting the summary above, compare the recorded continuity packet with live repo state:
1. run `git rev-parse HEAD`
2. run `git status --porcelain`
3. check the current Switchboard queue on disk

If live state differs from the recorded continuity packet, trust:
1. live `HEAD`
2. the current cycle log
3. the live Switchboard queue
4. the current Warden work report

Then run `npm run exit:refresh -- --reviewer "Steward"` as soon as practical to refresh continuity metadata.

## Current Queue
- none

## Open Headmaster Tickets
- none

## Calibration Rule
Read `appendix/guidance/exit/prompts/LATEST_SESSION_CALIBRATION.md` before acting. It carries the current 14-question default doctrine for the next session. Treat those answers as `default-until-overridden`, not as stronger than live repo state or explicit operator direction.

## Role Boundary Guard
If you are resuming as a delegate for a Headmaster, Warden, or offgrid message:
1. do the work for the role named in the message
2. write the required exit interview
3. stop there unless you were also explicitly assigned as `Steward`

Default rule:
- delegates do not perform `switchboard:review` or `switchboard:archive`
- Steward handles review, fixes, archive, and final acceptance normalization

## Recommended Next Lane
`none` — no open Headmaster ticket currently recorded

## Rule
Do not treat chat memory as the source of truth. The source of truth is the documented cycle, the Warden evidence, the Switchboard queue, and the latest raw log named above.
