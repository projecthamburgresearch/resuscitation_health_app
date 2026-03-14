# Exit Recovery Rubric

This rubric follows the toolkit rubric-guide discipline: binary, self-contained, source-cited criteria.

## Criteria
1. `EX-001 latest raw log named`
- sources:
  - `appendix/guidance/exit/logs/raw/`
  - `appendix/guidance/exit/logs/latest_log_pointer.json`
- pass rule:
  - PASS only if the latest raw terminal log path is explicitly recorded in Exit outputs

2. `EX-002 current continuity state recorded`
- sources:
  - `appendix/guidance/exit/registry/state.json`
- pass rule:
  - PASS only if `created_at`, `last_updated_at`, and `last_reviewed_at` are all present

3. `EX-003 queue captured`
- sources:
  - `appendix/guidance/switchboard/`
  - `appendix/guidance/exit/registry/state.json`
- pass rule:
  - PASS only if the current Switchboard inbox, active, and outbox state are reflected in the continuity state

4. `EX-004 current authority pointers captured`
- sources:
  - `appendix/guidance/headmaster/research/cycles/`
  - `appendix/guidance/warden/`
- pass rule:
  - PASS only if the continuity outputs name the current cycle log and at least one Warden report or evidence pointer

5. `EX-005 re-entry prompt concrete`
- sources:
  - `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`
- pass rule:
  - PASS only if the re-entry prompt contains a concrete read order, a next-step description, and an explicit live-state verification step

6. `EX-006 no chat-only dependency`
- sources:
  - `appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md`
  - `README.md`
- pass rule:
  - PASS only if the prompt explicitly instructs the next session to trust on-disk artifacts rather than chat memory

## Calibration Extension
See `CALIBRATION_RUBRIC.md` for the bounded doctrine layer that ships with Exit.
