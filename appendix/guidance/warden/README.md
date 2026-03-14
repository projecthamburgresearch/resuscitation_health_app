# Warden Workspace (Resuscitation Health App)

Warden is the current-state implementation and evidence authority for the clinician-facing resuscitation interface in this repository.

## Project-Specific Character
1. `LIGHT_ONLY`
2. `MOBILE_PORTRAIT_390x844`
3. route focus is `home`
4. behavior is a dynamic state machine
5. evidence must validate `incoming / current / previous` zones and forward/back clinician continuity

## Canonical Current Shape
This project still uses its established Warden output roots directly:
1. `blueprint_outputs/`
2. `scans_outputs/`
3. `design/`
4. `report/`

These are canonical for this repo right now and should not be force-migrated just because another project later adopted a different evidence topology.

## Ticketing Note
Warden tickets in this project already use `REQ-*` numbering and that remains canonical here.

## Read Order
1. `research/system/CONSTITUTION.md`
2. `research/system/METHODOLOGY.md`
3. `research/tickets/research_ticket_template.yaml`
4. latest relevant ticket in `research/tickets/`
5. latest summary in `report/latest_analysis.md`

## Neighbor Authorities
1. `headmaster/` defines future-state direction and writes bounded Warden handoffs
2. `switchboard/` routes delegate work into Warden lanes without replacing Warden authority
3. `exit/` preserves continuity so a later session can recover the current lane safely
