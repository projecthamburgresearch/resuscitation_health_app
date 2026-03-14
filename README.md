# Resuscitation Health App

Resuscitation Health App is a clinician-facing paediatric resuscitation decision interface built around a dynamic card-wheel state machine.

## Runtime Shape
1. `app/`
- Vite-based runtime, dev-mode mirror, styles, and state-machine sources

2. `prototype/`
- upstream schema and design references for the decision workflow

3. `appendix/guidance/warden/`
- current-state implementation and evidence authority for the live clinical interface

4. `appendix/guidance/headmaster/`
- future-state research, architecture direction, and Warden handoff authority

5. `appendix/guidance/switchboard/`
- async delegate routing for bounded Headmaster, Warden, and offgrid assignments

6. `appendix/guidance/exit/`
- continuity and re-entry layer built from raw terminal provenance and live project state

7. `integrations/access/`
- project-local integration access surface generated from the external Toolkit packages/access module

8. `appendix/guidance/materials/legacy/`
- preserved legacy roots and bootstrap-era materials kept for provenance only

## Core Product Constraints
1. `LIGHT_ONLY`
2. `MOBILE_PORTRAIT_390x844`
3. primary route is `home` (`/`)
4. product behavior is a dynamic state machine, not a static page
5. every change must preserve `incoming / current / previous` state-zone integrity and clinician-safe forward/back navigation

## Command Surface
1. `npm run dev`
- run the Vite app

2. `npm run dev:legacy`
- run the legacy local static server

3. `npm run check:devmode:parity`
- verify `app/` and `app/dev-mode/` remain mirrored

4. `npm run analyze:warden:local`
- refresh Blueprint, scan/domscan, and design bundle evidence through the current Warden pipeline

5. `npm run switchboard:list`
- inspect pending/active/completed delegate assignments

6. `npm run exit:refresh -- --reviewer "Steward"`
- compile the continuity pack from raw logs, live queue state, and current repo state

7. `npm run exit:status`
- inspect the current continuity packet and drift status

## Repeatable Operating Cycle
1. a bounded research or implementation need enters Headmaster, Warden, or an offgrid discovery lane
2. Headmaster researches future-state direction and writes bounded handoffs when needed
3. Warden measures or implements against the live state-machine evidence
4. Switchboard routes delegate work but does not replace Headmaster or Warden authority
5. Steward reviews/fixes/archives delegate work unless explicitly delegated otherwise
6. accepted work is verified locally, pushed, and checked against GitHub CI/Deploy when those surfaces exist
7. Exit is refreshed so the next session can resume from durable state instead of vanished chat memory

## Where To Start
1. `appendix/guidance/headmaster/README.md`
2. `appendix/guidance/warden/research/system/CONSTITUTION.md`
3. `appendix/guidance/switchboard/README.md`
4. `appendix/guidance/exit/README.md`

## Rule
Do not treat chat memory as the source of truth. Trust the documented authority lanes, the Warden evidence, the live Switchboard queue, and the Exit continuity surface.
