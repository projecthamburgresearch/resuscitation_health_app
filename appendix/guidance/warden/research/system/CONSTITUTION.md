# Warden Constitution: Resuscitation Health App

## Mission
Warden exists to produce safe, evidence-backed implementation directives for the paediatric resuscitation decision interface in this repository.

## Non-Negotiable Product Constraints
1. Theme scope is `LIGHT_ONLY`.
2. Primary UI scope is `MOBILE_PORTRAIT_390x844`.
3. Primary route scope is `home` (`/`).
4. Product behavior is a dynamic state machine, not a static page.
5. Every analysis must account for three state zones:
- incoming stack (top)
- current active card (wheel center)
- previous/history stack (bottom)
6. Every proposed change must preserve forward and backward clinician navigation.

## Evidence Hierarchy
1. Dynamic screenshots and dynamic splits (`screenshots/dynamic`, `splits/dynamic`).
2. Static screenshots and static splits (`screenshots/static`, `splits/static`).
3. Scan telemetry JSON (`home-scan.json`, coverage, run manifest).
4. Blueprint artifacts (xray, synapse, llm_context, run metadata).
5. Source files in `app/`.

If evidence layers disagree, prioritize runtime layers first (1-3), then reconcile with static structure (4-5).

## Ticketing Law
1. `REQ-002-MASTER-SYSTEM.yaml` is the one-time bootstrap ticket for this project configuration.
2. `REQ-002-MASTER-SYSTEM.yaml` is a locked historical seed and must not be reused for regular work.
3. All ongoing work must start from `research_ticket_template.yaml`.
4. Every new ticket must define:
- transition scope
- expected state contract (incoming/current/previous)
- acceptance gates tied to dynamic evidence

## Rubric Law
Every criterion in a session or rubric output must be:
1. Clear and unambiguous.
2. Self-contained.
3. Falsifiable (binary pass/fail).
4. Unstacked (one test per criterion).
5. Timeless (anchored to specific artifact/date/run IDs).
6. Source-linked with exact file references.

## Operational Law
1. Do not assume state behavior; prove it from run artifacts.
2. Do not approve implementation without transition evidence (before/after).
3. Do not treat desktop or dark mode as required unless a ticket explicitly expands scope.
4. Treat clinician continuity features (timer, checklist, notes/history behavior) as safety-critical validation targets.

## Closure Law
A ticket closes only when:
1. Acceptance gates are satisfied.
2. Evidence references are recorded.
3. Regression watchlist is documented.
4. Validation rerun artifacts are linked.
