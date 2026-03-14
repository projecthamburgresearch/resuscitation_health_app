# Warden Methodology: Dynamic State Research Loop

This protocol defines how to resolve design and implementation questions for this app's dynamic decision workflow.

## The 4-Phase Loop

### Phase 1: Ticket Framing
1. Start from `research_ticket_template.yaml`.
2. Lock scope to route, viewport, and theme profile.
3. Define transition/state scope (forward, backward, or both).
4. Define expected incoming/current/previous contract.

### Phase 2: Evidence Ingestion
1. Resolve latest linked run IDs:
- Blueprint run
- Scan run
- Design bundle run
2. Load artifacts in this order:
- dynamic screenshots/splits
- static screenshots/splits
- scan telemetry
- blueprint outputs
3. Create a session file in `research/sessions/` with exact artifact references.

### Phase 3: Recursive Resolution
For each unresolved question node:
1. Extract telemetry facts (positions, card IDs, transitions, timer/checklist indicators).
2. Validate against rubric criteria (binary pass/fail).
3. If needed, query local references:
- `research/rubric-guide/` for criterion quality rules
- `research/reference/` for algorithm framing support
4. Synthesize into concrete implementation directives and risks.

### Phase 4: Verification and Closure
1. Re-run analysis (`analyze:warden:local` or lane-appropriate command).
2. Re-check acceptance gates with new dynamic/static evidence.
3. Record deltas and closure decision.

## Required Session Output Structure
1. Context and run IDs.
2. Transition map examined.
3. Findings by severity with evidence links.
4. Code targets and impact surface.
5. Implementation directives.
6. Validation results and closure status.

## Mandatory Validation Targets
1. State identity correctness (`fromId`, `toId`, current card content).
2. Wheel progression behavior across transitions.
3. Incoming/current/previous zone integrity.
4. Reverse navigation integrity.
5. Timer/checklist/notes continuity when applicable.

## Out-of-Scope by Default
1. Dark mode parity.
2. Desktop-first composition optimization.
3. Multi-route architecture unless ticket explicitly expands scope.
