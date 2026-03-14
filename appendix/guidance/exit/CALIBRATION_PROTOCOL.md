# Exit Calibration Protocol

Exit calibration exists so a resumed session inherits more than file paths and queue state. It inherits the project's default operating doctrine unless the operator overrides it.

## Purpose
1. surface the non-discoverable questions that materially affect session behavior
2. record the current default answers that the project operates under
3. mark those answers as `default-until-overridden`, not eternal truth
4. give the next session a bounded calibration packet instead of a free-form reorientation

## Rule
Calibration questions must be questions that are not safely recoverable from repo state alone.

They are allowed to have project-default answers only when:
1. the defaults are already embodied in accepted operating history
2. the defaults are clearly marked as overridable by the operator
3. the packet cites the on-disk basis used to infer those defaults

## Recommended Core Set
Use a bounded set that covers:
1. role
2. priority order
3. lane strictness
4. success criteria
5. autonomy level
6. off-limits surfaces
7. user intent vs docs
8. off-repo context assumptions
9. authoritative vs inspirational sources
10. key current risks
11. ticket authority
12. proof level
13. default behavior if operator contact is lost
14. what counts as a true resume

## Pipeline Rule
`npm run exit:refresh` should regenerate the calibration packet alongside:
1. `registry/state.json`
2. `snapshots/*.md`
3. `prompts/LATEST_SESSION_REENTRY.md`

The re-entry prompt should point the next session at the calibration packet.

## Operator Rule
Calibration defaults are a starting doctrine, not a substitute for explicit operator direction.

If the operator gives a direct override:
1. the override wins for the current session
2. accepted doctrine and docs should be updated later if the override becomes the new standard
