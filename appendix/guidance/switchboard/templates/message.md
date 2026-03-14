# Message Template

```md
message_id: "MSG-YYYYMMDD-HHMMSS"
date: "YYYY-MM-DD"
status: "NEW" # NEW | CLAIMED | DONE | REVIEWED | ARCHIVED
selected_delegate: ""
selected_by: "Operator" # Operator | self-assigned
intended_role: "headmaster" # headmaster | warden | offgrid
ticket_refs: []
handoff_refs: []
prompt_entrypoint: ""
required_reads: []
expected_output_paths: []
required_exit_interview: ""
delegate_boundary: "Stop after assigned lane artifacts and required exit interview unless this message explicitly assigns Steward responsibilities."

## Task
Write the exact bounded assignment here.

## Success Condition
Write the concrete done condition here.

## Notes
- local inspection links if relevant
- verification expectations if relevant
```
