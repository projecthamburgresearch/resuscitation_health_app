message_id: "MSG-20260313-REQ015-WARDEN-ROOT-NORMALIZATION"
date: "2026-03-13"
status: "ARCHIVED"
selected_delegate: "Gemini CLI"
claimed_at: "2026-03-13T21:04:05.540Z"
finished_at: "2026-03-13T21:04:06.543Z"
reviewer: "Steward"
review_verdict: "accept_with_fixes"
reviewed_at: "2026-03-13T21:12:22.053Z"
selected_by: "Steward"
intended_role: "warden"
ticket_refs:
  - "REQ-015-ROOT-NORMALIZATION-AND-BASELINE"
handoff_refs:
  - "appendix/guidance/headmaster/research/handoffs/REQ-015-ROOT-NORMALIZATION-AND-BASELINE.md"
prompt_entrypoint: "Read the required files, normalize canonical vs legacy root surfaces for the first accepted baseline commit, write the required exit interview, and stop there unless explicitly assigned as Steward."
required_reads:
  - "README.md"
  - "appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md"
  - "appendix/guidance/headmaster/research/handoffs/REQ-015-ROOT-NORMALIZATION-AND-BASELINE.md"
  - "appendix/guidance/headmaster/research/tickets/HREQ-005-CANONICAL-ROOTS-AND-STAGING-PLAN.yaml"
  - "appendix/guidance/warden/README.md"
  - "appendix/guidance/warden/research/system/CONSTITUTION.md"
  - "appendix/guidance/warden/research/tickets/REQ-015-ROOT-NORMALIZATION-AND-BASELINE.yaml"
  - ".gitignore"
required_exit_interview: "appendix/guidance/switchboard/outbox/MSG-20260313-REQ015-WARDEN-ROOT-NORMALIZATION-EXIT.md"
expected_output_paths:
  - "appendix/guidance/warden/research/tickets/REQ-015-ROOT-NORMALIZATION-AND-BASELINE.yaml"
  - "appendix/guidance/switchboard/outbox/MSG-20260313-REQ015-WARDEN-ROOT-NORMALIZATION-EXIT.md"
delegate_boundary: "Stop after assigned lane artifacts and required exit interview unless this message explicitly assigns Steward responsibilities."

## Task
Normalize the repo root surfaces so canonical authority paths are clear, legacy roots are preserved but no longer compete visually, and the project moves closer to a trustworthy accepted baseline commit.

## Success Condition
A bounded Warden lane improves canonical-vs-legacy clarity without deleting project-specific history.

## Notes
- Do not redesign the runtime state machine in this lane.
- Do not perform Steward review or archive unless explicitly reassigned.
