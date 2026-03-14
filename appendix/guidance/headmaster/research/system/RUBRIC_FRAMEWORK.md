# Headmaster Rubric Framework (Resuscitation Health App)

Headmaster tickets should be judged with explicit criteria, not vague approval language.

## Criterion Shape
Every criterion should include:
1. `criterion_id`
2. `description`
3. `sources`
4. `criterion_type`
5. `pass_fail_rule`
6. `rationale`
7. `dependencies`
8. `result`

## Allowed Outcomes
1. `READY_FOR_WARDEN`
2. `RESEARCH_MORE`
3. `REJECT_FOR_NOW`
4. `HEADMASTER_COMPLETE`

## Intent
- `READY_FOR_WARDEN` means a bounded `WDN-*` handoff must exist.
- `HEADMASTER_COMPLETE` means the work closed entirely in Headmaster without creating implementation scope.

Generated: 2026-03-13
