# Blueprint + Scan + Warden Clone Plan (Resuscitation App)

## Goal

Clone the nonprofit toolchain pattern into this project while adapting it to a static `app/` surface and local-only appendix workflow.

## Target Folder Shape

- `app/`
- `scripts/`
- `appendix/blueprint/`
- `appendix/blueprint_outputs/{runs,current,archive}`
- `appendix/scans_outputs/{runs,current,archive}`
- `appendix/guidance/warden/{design,research,report}`
- `appendix/guidance/materials/`

## Implementation Steps

1. Copy and adapt scan tooling for static HTML routes.
2. Copy and adapt blueprint runners to target `app/` by default.
3. Copy and adapt warden design bundling for main-route capture.
4. Add local static dev server (`scripts/dev_server.js`) and package scripts.
5. Install nonprofit-style guidance docs, tickets, and session templates in `appendix/guidance`.
6. Validate script entrypoints (`--help`, syntax checks, server smoke test).

## Adaptation Notes

- This project does not require a `dev-mode` mirror. Scripts are adapted to main-route operation.
- `appendix/` remains gitignored to preserve local operator workflow.
- Blueprint and Scan outputs still keep `runs/current/archive` semantics for parity with the nonprofit process.
