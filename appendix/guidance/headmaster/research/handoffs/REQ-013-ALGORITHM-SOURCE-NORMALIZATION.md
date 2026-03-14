# Warden Handoff: REQ-013-ALGORITHM-SOURCE-NORMALIZATION

## Problem Statement
Resuscitation Health App currently has two algorithm surfaces:
1. `app/algorithms/` — the active runtime authority consumed by the app
2. `prototype/json-algorithms/` — older design-source files that have drifted from runtime truth

This drift makes it too easy for operators to trust stale prototype files and weakens future state-machine modernization work.

## Constraints To Preserve
1. Preserve the live clinician-facing state-machine behavior.
2. Preserve the existing Warden `REQ-*` lineage.
3. Do not rewrite the state machine or app architecture in this lane.
4. Treat `app/algorithms/` as canonical runtime authority unless current evidence proves otherwise.
5. Respect the existing `incoming / current / previous` state contract when checking algorithm impact.

## Code / Evidence Targets
1. `app/algorithms/`
2. `prototype/json-algorithms/`
3. `app/src/algorithms/loader.ts`
4. Warden behavior-contract outputs under `appendix/guidance/warden/research/reports/`

## Acceptance Gates
1. A clear canonical-vs-derived rule exists for `app/algorithms/` and `prototype/json-algorithms/`.
2. Prototype files are either synchronized to runtime truth or explicitly marked legacy/derived where appropriate.
3. The lane does not silently change clinician runtime behavior.
4. Any touched algorithm evidence preserves the current state-machine behavior contract.

## Verification
1. `npm run check:devmode:parity`
2. `npm run analyze:warden:local`
3. Re-run the relevant behavior-contract validation for touched algorithms or explicitly record blockers.

## Non-Goals
1. Do not redesign the app architecture.
2. Do not introduce a new runtime state-machine library in this lane.
3. Do not flatten the repo into another project’s topology.

## Ticket Mapping
This handoff should map onto a new Warden `REQ-*` lane:
- `REQ-013-ALGORITHM-SOURCE-NORMALIZATION`
