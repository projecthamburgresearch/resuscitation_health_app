# Warden Handoff: REQ-014-BEHAVIOR-TEST-REFRESH

## Problem Statement
The current behavior-contract validator times out waiting for `.decision-option-card.selected` because `REQ-008` intentionally introduced a required tap-before-confirm step. The product is behaving as designed; the validator is stale.

## Constraints To Preserve
1. Preserve live clinician-facing runtime behavior.
2. Preserve existing Warden `REQ-*` lineage.
3. Do not change runtime state-machine semantics in this lane.
4. Refresh only the validator/test behavior so it reflects the current decision-tap contract.

## Code / Evidence Targets
1. `scripts/test_behavior.js`
2. `appendix/guidance/warden/research/reports/behavior_report.json`
3. `app/src/cards/preview-zone.ts`
4. `app/src/cards/decision-cards.ts`

## Acceptance Gates
1. The validator explicitly performs the mandatory decision-option tap before asserting selection state.
2. The behavior-contract suite passes for all five sampled algorithms.
3. The lane does not modify clinician-facing runtime behavior.
4. Updated validation evidence is recorded explicitly.

## Verification
1. Run the behavior-contract validation after updating the script.
2. Record the refreshed report and any remaining blockers.
3. Confirm no runtime application files were changed unless a blocker proves they must be.

## Non-Goals
1. Do not redesign the state machine.
2. Do not rewrite algorithm sources in this lane.
3. Do not broaden into UI or architecture modernization.

## Ticket Mapping
Create or update Warden lane `REQ-014-BEHAVIOR-TEST-REFRESH`.
