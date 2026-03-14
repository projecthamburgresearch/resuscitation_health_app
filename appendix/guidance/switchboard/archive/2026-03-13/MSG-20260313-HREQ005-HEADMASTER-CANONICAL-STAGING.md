message_id: "MSG-20260313-HREQ005-HEADMASTER-CANONICAL-STAGING"
date: "2026-03-13"
status: "ARCHIVED"
selected_delegate: "Gemini CLI"
claimed_at: "2026-03-13T20:51:44.783Z"
finished_at: "2026-03-13T20:51:45.277Z"
reviewer: "Steward"
review_verdict: "accept_with_fixes"
reviewed_at: "2026-03-13T20:57:18.890Z"
selected_by: "Steward"
intended_role: "headmaster"
ticket_refs:
  - "HREQ-005-CANONICAL-ROOTS-AND-STAGING-PLAN"
handoff_refs: []
prompt_entrypoint: "Read the required files, classify the current repo roots into canonical/legacy/project-material/bootstrap buckets, define the first accepted staging boundary, write the required exit interview, and stop there unless explicitly assigned as Steward."
required_reads:
  - "README.md"
  - "appendix/guidance/exit/prompts/LATEST_SESSION_REENTRY.md"
  - "appendix/guidance/headmaster/README.md"
  - "appendix/guidance/headmaster/research/tickets/HREQ-005-CANONICAL-ROOTS-AND-STAGING-PLAN.yaml"
  - "appendix/guidance/headmaster/research/system/RESOURCE_ATLAS.md"
  - "appendix/guidance/headmaster/research/system/ARTIFACT_READING_GUIDE.md"
  - "appendix/guidance/headmaster/research/cycles/CYCLE-001-HEADMASTER-BOOTSTRAP.md"
  - "appendix/guidance/headmaster/report/latest_analysis.md"
  - ".gitignore"
required_exit_interview: "appendix/guidance/switchboard/outbox/MSG-20260313-HREQ005-HEADMASTER-CANONICAL-STAGING-EXIT.md"
expected_output_paths:
  - "appendix/guidance/headmaster/research/tickets/HREQ-005-CANONICAL-ROOTS-AND-STAGING-PLAN.yaml"
  - "appendix/guidance/headmaster/research/sessions/HREQ-005-CANONICAL-ROOTS-AND-STAGING-PLAN.md"
  - "appendix/guidance/switchboard/outbox/MSG-20260313-HREQ005-HEADMASTER-CANONICAL-STAGING-EXIT.md"
delegate_boundary: "Stop after assigned lane artifacts and required exit interview unless this message explicitly assigns Steward responsibilities."

## Task
Produce the first deliberate canonical-root and staging plan for the upgraded authority stack so the repo can move toward a trustworthy accepted baseline commit.

## Success Condition
A bounded Headmaster lane classifies the current repo surfaces, defines what should be staged first versus deferred, and leaves a recoverable next step.

## Notes
- Do not move files or delete roots in this lane.
- Do not perform Steward review or archive unless explicitly reassigned.
