# Warden Research Pack

This folder defines the research operating system for this repository's dynamic paediatric resuscitation interface.

## Evidence Layers
1. Blueprint: `appendix/guidance/warden/blueprint_outputs/runs/*`
2. Scan: `appendix/guidance/warden/scans_outputs/runs/*`
3. Design Bundle: `appendix/guidance/warden/design/runs/*`

## Product Reality This Pack Enforces
1. Light mode only.
2. Mobile portrait baseline (`390x844`).
3. Primary route: `home`.
4. Dynamic decision-tree state flow with incoming/current/previous zones.

## Core Link Model
Every investigation should link these keys:
1. `page` (`home`)
2. `viewport` (`390x844` by default)
3. `transition.slug` and `transitionIndex` (dynamic captures)
4. `state card id` (`fromId`, `toId`, `currentId`)
5. `region id` + `sourceIndex` from split maps
6. `component/file path` from Blueprint + code search

## Daily Workflow
1. Refresh Warden lane evidence:
- `npm run analyze:warden:local`
2. Optional system lane evidence:
- `npm run analyze:system:local`
3. Review bundle artifacts:
- static screenshots: `screenshots/static/main/`
- dynamic screenshots: `screenshots/dynamic/main/`
- static splits: `splits/static/main/*`
- dynamic splits: `splits/dynamic/main/*`
4. Run ticket-guided investigation and log session.
5. Implement changes.
6. Re-run analysis and close with evidence.

## Ticket System
1. One-time bootstrap seed: `tickets/REQ-002-MASTER-SYSTEM.yaml`
2. Legacy imported seed (archival): `tickets/REQ-001-MASTER-SYSTEM.yaml`
3. Reusable ticket contract: `tickets/research_ticket_template.yaml`
4. Clinician behavior matrix templates:
- `tickets/behavior_contract_matrix_template.yaml`
- `tickets/behavior_contract_matrix_template.json`

Rule: use the template for ongoing work; do not reuse the bootstrap seed ticket.

## Rubric and Prompt Guidance
Use these local sources when authoring criteria or research prompts:
1. `research/system/AGENTIC_RUBRIC_FRAMEWORK.md`
2. `research/rubric-guide/*`
3. `research/reference/*`

## Related Docs
1. `GRAPHIC_DESIGNER_WORKFLOW.md`
2. `QUESTION_ANSWER_MATRIX.md`
3. `qa_matrix.json`
4. `RESEARCH_SESSION_TEMPLATE.md`
5. `system/CONSTITUTION.md`
6. `system/METHODOLOGY.md`
7. `system/AGENTIC_RUBRIC_FRAMEWORK.md`
