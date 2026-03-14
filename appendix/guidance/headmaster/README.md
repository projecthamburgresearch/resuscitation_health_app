# Headmaster Workspace (Resuscitation Health App)

Headmaster is the future-state research and direction authority for Resuscitation Health App.

## Stack Position
Headmaster operates as one authority inside this project's four-workspace stack:
1. `warden`
2. `headmaster`
3. `switchboard`
4. `exit`

## Project-Specific Naming Rule
Because Warden already owns `REQ-*` ticket numbering in this repository, Headmaster uses `HREQ-*` tickets.

Headmaster handoffs may still target the existing Warden `REQ-*` lane system when implementation work belongs there.

## Role Split
1. `headmaster/` defines architecture targets, syllabus, source maps, ticket law, and future-state handoffs.
2. `warden/` measures and implements the live state-machine interface.
3. `switchboard/` routes delegates without replacing Headmaster or Warden authority.
4. `exit/` preserves continuity so later sessions can resume without relying on lost chat history.

## Read Order
1. `research/system/CONSTITUTION.md`
2. `research/system/METHODOLOGY.md`
3. `research/system/SOURCES.md`
4. `research/system/RUBRIC_FRAMEWORK.md`
5. `research/system/CHECKLIST.md`
6. `research/system/TICKET_PROCESS.md`
7. `research/system/HANDOFF_PROTOCOL.md`
8. `research/system/RESOURCE_ATLAS.md`
9. `research/system/ARTIFACT_READING_GUIDE.md`
10. `research/system/ARCHITECTURE_TARGET.md`
11. `research/system/SYLLABUS.md`
12. `research/system/DEPLOYMENT_PROTOCOL.md`
13. latest cycle record in `research/cycles/`

## Current Bootstrapped State
1. `HREQ-001` records the Headmaster bootstrap and ethos map.
2. `HREQ-002` is complete as the current atlas-maintenance refresh.
3. `HREQ-003` is complete as the current architecture-refinement lane.
4. `HREQ-004` is closed after the accepted Warden follow-on `REQ-014` fixed the behavior-contract tooling drift.
5. `HREQ-005` is the next queued Headmaster lane for canonical-root and staging planning.
6. Warden remains the strongest existing authority and is the primary source of live product truth.
