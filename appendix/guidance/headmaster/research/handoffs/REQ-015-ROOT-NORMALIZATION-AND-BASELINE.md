# Warden Handoff: REQ-015-ROOT-NORMALIZATION-AND-BASELINE

## Problem Statement
The upgraded authority stack is now present and the canonical roots are classified, but the repo still mixes canonical authority surfaces with superseded legacy roots and broad dirty bootstrap state. The next bounded implementation lane should normalize the root layout enough to support the first accepted baseline commit without erasing project-specific history.

## Constraints To Preserve
1. Preserve the existing Warden `REQ-*` lineage.
2. Do not delete historical materials or erase provenance.
3. Keep the project-specific Warden/mobile/light-only ethos intact.
4. Prefer relocation or explicit legacy freezing over destructive cleanup.

## Code / Evidence Targets
1. `.gitignore`
2. `appendix/blueprint/`
3. `appendix/blueprint_outputs/`
4. `appendix/scans_outputs/`
5. `appendix/system/`
6. `appendix/guidance/`
7. `appendix/materials/`
8. `README.md`

## Acceptance Gates
1. Canonical authority surfaces and reference surfaces are easy to distinguish from legacy roots.
2. Legacy roots are either relocated or frozen behind explicit legacy documentation.
3. The repo is in a better position for a first accepted baseline commit without flattening project-specific history.
4. Documentation reflects the normalized canonical vs legacy split.

## Verification
1. Run `npm run switchboard:list`.
2. Run `npm run exit:refresh -- --reviewer "Steward"`.
3. Record the resulting canonical vs legacy layout explicitly.

## Non-Goals
1. Do not redesign the runtime state machine.
2. Do not rewrite algorithms in this lane.
3. Do not collapse the project into MapleCare’s exact folder model.

## Ticket Mapping
Create or update Warden lane `REQ-015-ROOT-NORMALIZATION-AND-BASELINE`.
