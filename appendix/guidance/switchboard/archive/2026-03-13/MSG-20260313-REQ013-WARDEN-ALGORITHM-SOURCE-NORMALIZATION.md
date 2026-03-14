message_id: "MSG-20260313-REQ013-WARDEN-ALGORITHM-SOURCE-NORMALIZATION"
date: "2026-03-13"
status: "ARCHIVED"
selected_delegate: "Gemini CLI"
claimed_at: "2026-03-13T19:47:03.499Z"
finished_at: "2026-03-13T19:47:04.223Z"
reviewer: "Steward"
review_verdict: "accept_with_fixes"
reviewed_at: "2026-03-13T19:51:52.591Z"
selected_by: "Operator"
intended_role: "warden"
ticket_refs:
  - "REQ-013-ALGORITHM-SOURCE-NORMALIZATION"
handoff_refs:
  - "appendix/guidance/headmaster/research/handoffs/REQ-013-ALGORITHM-SOURCE-NORMALIZATION.md"
prompt_entrypoint: "Read the required files, create or update the Warden ticket, normalize the algorithm source boundary between runtime and prototype surfaces, write the required exit interview, and stop there unless explicitly assigned as Steward."
required_reads:
  - "README.md"
  - "appendix/guidance/headmaster/research/handoffs/REQ-013-ALGORITHM-SOURCE-NORMALIZATION.md"
  - "appendix/guidance/headmaster/research/tickets/HREQ-003-ARCHITECTURE-TARGET-REFINEMENT.yaml"
  - "appendix/guidance/warden/README.md"
  - "appendix/guidance/warden/research/system/CONSTITUTION.md"
  - "appendix/guidance/warden/research/tickets/REQ-013-ALGORITHM-SOURCE-NORMALIZATION.yaml"
  - "app/algorithms/"
  - "prototype/json-algorithms/"
expected_output_paths:
  - "appendix/guidance/warden/research/tickets/REQ-013-ALGORITHM-SOURCE-NORMALIZATION.yaml"
  - "appendix/guidance/switchboard/outbox/MSG-20260313-REQ013-WARDEN-ALGORITHM-SOURCE-NORMALIZATION-EXIT.md"
required_exit_interview: "appendix/guidance/switchboard/outbox/MSG-20260313-REQ013-WARDEN-ALGORITHM-SOURCE-NORMALIZATION-EXIT.md"
delegate_boundary: "Stop after assigned lane artifacts and required exit interview unless this message explicitly assigns Steward responsibilities."

## Task
Normalize the algorithm source boundary between `app/algorithms/` and `prototype/json-algorithms/` while preserving the live clinician-facing state-machine behavior. Use the Headmaster handoff as the bounded implementation brief.

## Success Condition
A Warden lane exists for algorithm-source normalization, the source-of-truth rule is clearer, and any touched files are validated without speculative architecture churn.

## Notes
- Preserve the existing Warden `REQ-*` lineage.
- Do not introduce state-machine rewrites in this lane.
