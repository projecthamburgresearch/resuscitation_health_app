# Exit Calibration Rubric

This rubric follows the Toolkit Librarian rubric-guide discipline: binary, self-contained, source-cited criteria.

## Criteria
1. `EX-CAL-001 calibration packet exists`
- sources:
  - `appendix/guidance/exit/prompts/LATEST_SESSION_CALIBRATION.md`
- pass rule:
  - PASS only if a latest calibration packet exists and is readable as part of the Exit package

2. `EX-CAL-002 question set bounded`
- sources:
  - `appendix/guidance/exit/CALIBRATION_QUESTION_SET.md`
  - `appendix/guidance/exit/CALIBRATION_PROTOCOL.md`
- pass rule:
  - PASS only if the calibration set is explicitly described as a bounded set of non-discoverable or not-safely-assumable questions

3. `EX-CAL-003 answers marked as defaults`
- sources:
  - `appendix/guidance/exit/prompts/LATEST_SESSION_CALIBRATION.md`
- pass rule:
  - PASS only if each calibration answer is clearly marked as a project default or assumption that can be overridden by the operator

4. `EX-CAL-004 answers cite basis`
- sources:
  - `appendix/guidance/exit/prompts/LATEST_SESSION_CALIBRATION.md`
- pass rule:
  - PASS only if each answer cites at least one on-disk basis path or explicitly says the answer is an operator-only question with no reliable repo authority

5. `EX-CAL-005 re-entry prompt links calibration`
- sources:
  - `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`
- pass rule:
  - PASS only if the re-entry prompt tells the next session to read the calibration packet as part of recovery

6. `EX-CAL-006 live state still outranks defaults`
- sources:
  - `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`
  - `appendix/guidance/exit/CALIBRATION_PROTOCOL.md`
- pass rule:
  - PASS only if the calibration packet does not override the existing live-state guard and operator-intent override rule
