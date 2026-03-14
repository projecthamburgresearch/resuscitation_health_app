# Warden Handoff: REQ-016-BASELINE-COMMIT-EXECUTION

- upstream_headmaster_ticket: `HREQ-006-FIRST-ACCEPTED-BASELINE-COMMIT-CURATION`
- date: 2026-03-13
- authority: `headmaster`
- status: `READY_FOR_WARDEN`

## Why This Lane Exists
The authority/bootstrap upgrade is now coherent enough to define the first accepted baseline commit boundary, but the repo should not be committed by blind sweep. Warden must turn the Headmaster curation into an exact staging recommendation and commit-ready candidate set.

## Bounded Objective
Produce the first accepted baseline-commit candidate for the upgraded authority stack by:
1. validating the curated buckets from `HREQ-006`
2. removing or deferring obvious noise like `.DS_Store`
3. staging only the canonical/reference surfaces meant for the first accepted baseline
4. reporting the exact staged set and recommended commit message

This lane is about **staging discipline**, not product redesign.

## In Scope
- canonical authority stack under `appendix/guidance/`
- root project/operator files like `README.md`, `.gitignore`, `package.json`
- project tooling/scripts added for the upgraded authority model
- accepted algorithm/prototype normalization files
- preserved legacy/reference surfaces that Headmaster marked as part of the baseline
- staging report and commit-message recommendation

## Out Of Scope
- pushing the repo
- changing product behavior
- redesigning guidance doctrine
- deleting preserved historical materials
- opportunistic cleanup outside the curated baseline boundary

## Required Reads
1. `README.md`
2. `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`
3. `appendix/guidance/headmaster/research/tickets/HREQ-006-FIRST-ACCEPTED-BASELINE-COMMIT-CURATION.yaml`
4. `appendix/guidance/headmaster/research/sessions/HREQ-006-FIRST-ACCEPTED-BASELINE-COMMIT-CURATION.md`
5. `appendix/guidance/headmaster/research/cycles/CYCLE-001-HEADMASTER-BOOTSTRAP.md`
6. `.gitignore`
7. `appendix/guidance/warden/README.md`

## Acceptance Gates
1. The candidate baseline staging set matches the Headmaster curation and excludes deferred noise.
2. No `.DS_Store` files are included in the staged candidate.
3. The lane records the exact staged set and a recommended commit message.
4. The lane does not push the repo or overreach into unrelated cleanup.

## Required Output
- Warden ticket update
- staging summary / evidence note
- required Switchboard exit interview

## Notes
- If the curation from `HREQ-006` proves incomplete or contradictory, stop and bounce it back rather than stretching the lane.
- Do not commit/push unless a later explicit operator instruction says to do so.
