# Headmaster Ticket Process: Resuscitation Health App

## Ticket Prefix
Headmaster tickets use `HREQ-*` in this project.

## Why
Warden already has a long-running `REQ-*` lineage. Headmaster must not create cross-authority ambiguity by reusing the same namespace.

## Minimum Ticket Schema
Every Headmaster ticket must define:
1. `ticket_id`
2. `date`
3. `status`
4. `authority`
5. `title`
6. `objective`
7. `scope`
8. `source_pack`
9. `acceptance_criteria`
10. `acceptance_results`
11. `checklist_outcome`
12. `rubric_outcome`
13. `research_session`
14. `artifacts_updated`

## Status Set
1. `OPEN`
2. `IN_PROGRESS`
3. `READY_FOR_WARDEN`
4. `RESEARCH_MORE`
5. `REJECT_FOR_NOW`
6. `HEADMASTER_COMPLETE`
7. `CLOSED`

## Handoff Rule
If a Headmaster lane produces implementation work, it should create a bounded handoff that targets the existing Warden lane system instead of inventing a second implementation namespace.
