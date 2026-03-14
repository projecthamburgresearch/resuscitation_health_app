# Research Session: HREQ-004-BEHAVIOR-CONTRACT-FAILURE-TRIAGE

- date: 2026-03-13
- role: headmaster
- ticket_ref: HREQ-004-BEHAVIOR-CONTRACT-FAILURE-TRIAGE

## Objective
Triage the current behavior-contract validation failures reported in `appendix/guidance/warden/research/reports/behavior_report.json`.

## 1. Failure Analysis

### Symptom
All 5 algorithms fail with the same error:
`Execution error: locator.boundingBox: Timeout 30000ms exceeded. waiting for locator('.decision-option-card.selected')`

### Root Cause
- **Drift Type:** Stale Validator Assumption (Tooling Drift).
- **Product Change:** `REQ-008-DECISION-CONFIRM-AND-NAV-CONSUMED-FIX.yaml` introduced the `state.decisionTapped` flag. This change requires a clinician to explicitly **tap** a decision option card before it becomes "selected" and ready for "drag-to-confirm".
- **Evidence:**
    - `app/src/cards/preview-zone.ts` gates the `.selected` CSS class on `state.decisionTapped`.
    - `app/src/cards/decision-cards.ts` gates the `advance()` trigger on `state.decisionTapped`.
    - `scripts/test_behavior.js` does NOT simulate a tap/click on decision options. It attempts to locate a `.selected` card immediately after reaching the decision state.

### Conclusion
This is not a product regression. The product is behaving exactly as designed in `REQ-008`. The behavior-contract test script is stale and must be updated to reflect the mandatory "tap-before-confirm" workflow.

## 2. Classification
- **Type:** Stale Validator Assumption / Tooling Drift.
- **Severity:** High (blocks clinical validation pipeline).
- **Risk:** Low (no runtime change needed, only test update).

## 3. Recommended Next Lane
- **Role:** Warden
- **Ticket:** `REQ-014-BEHAVIOR-TEST-REFRESH` (New)
- **Scope:** Update `scripts/test_behavior.js` to include the mandatory tap step when a decision state is reached. Use `__WARDEN_AUTOMATION.selectDecisionOption(0)` or a direct `page.click('.decision-option-card')` simulation.
- **Verification:** `npm run test:behavior` (or equivalent) should pass for all algorithms after the fix.

## 4. Continuity Note
The failure was discovered during the Headmaster bootstrap and atlas refresh. Triaging it now prevents it from being misidentified as an architecture regression during future state-machine modernization.
