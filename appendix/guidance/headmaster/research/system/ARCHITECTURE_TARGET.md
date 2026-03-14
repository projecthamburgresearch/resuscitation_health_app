# Architecture Target: Resuscitation Health App

## Near-Term Target
1. Preserve the existing dynamic clinician state-machine behavior.
2. Add the missing authority stack (`headmaster`, `switchboard`, `exit`) around the existing Warden without destabilizing the live interface.
3. Replace embedded Toolkit assumptions with project-local wrappers that call the external Toolkit cleanly.

## Mid-Term Target
1. Keep Warden as the current-state evidence authority.
2. Use Headmaster to define future structural changes only after Warden evidence proves the current state.
3. Decouple clinical algorithm metadata (states, content, transitions) from visual layout metadata (wheel degrees, phases).
4. Move normalization logic from runtime `loader.ts` to a validation/build-time step.
5. Pilot state-machine modernization (e.g., XState) in `app/dev-mode/` before core runtime replacement.
6. Gradually normalize older flat operator surfaces where that improves clarity and does not erase lineage.

## Non-Goals For This Bootstrap
1. Do not rewrite the live app architecture.
2. Do not rename the existing Warden `REQ-*` lineage.
3. Do not force another project's evidence directory topology onto this repo.
