# HREQ-001 Session: Headmaster Bootstrap and Ethos Map

## Context
This session bootstrapped the missing Headmaster, Switchboard, and Exit authorities around an already-existing Warden-centric project.

## Key Findings
1. The project already had a strong Warden with a clear clinician/mobile/light-only state-machine ethos.
2. The missing problem was not product philosophy but missing authority surfaces and continuity.
3. The repo still assumed embedded Toolkit and `library`-era project-local copies.
4. Raw terminal logs lived outside a continuity system and were ignored by git.

## Decisions
1. Preserve the existing Warden `REQ-*` lineage.
2. Give Headmaster its own `HREQ-*` namespace.
3. Add Switchboard and Exit without flattening Warden.
4. Move raw logs into `appendix/guidance/exit/logs/raw/`.
5. Replace embedded Toolkit assumptions with local wrappers plus external Toolkit references.

## Outcome
`HREQ-001` is complete as a Headmaster-only bootstrap lane.
