# Research Session: HREQ-003-ARCHITECTURE-TARGET-REFINEMENT

- date: 2026-03-13
- role: headmaster
- ticket_ref: HREQ-003-ARCHITECTURE-TARGET-REFINEMENT

## Objective
Refine the future-state architecture target around the state-machine modernization and algorithm source-of-truth boundaries.

## 1. Algorithm Source-of-Truth Analysis

### Findings
- **Runtime Authority:** `app/algorithms/` is the active surface consumed by the app via `app/src/algorithms/loader.ts`. It includes a manifest (`index.json`) and JSON algorithm files.
- **Design/Prototype:** `prototype/json-algorithms/` contains older versions (as evidenced by file sizes and diffs for `algo_paed_bls_in.json`). It also includes `.txt` mirrors and `algorithm-schema-v3.json`.
- **Drift:** `app/algorithms/` has been updated more recently (e.g., March 10, 2026) compared to the prototype (December 2025).

### Recommendation
- **Source Selection:** `app/algorithms/` must be treated as the canonical source for runtime behavior.
- **Warden Handoff:** Open a Warden-facing lane to synchronize `prototype/json-algorithms/` with `app/algorithms/` or clearly mark `prototype/` as legacy/historical to prevent accidental regression from stale design files.

## 2. State-Machine Modernization Boundary

### Current State
- The state machine is centralized in `app/src/state/` (inferred) and uses a `Card` deck model.
- Navigation and wheel positioning are tightly coupled in the algorithm JSON (e.g., `position_degrees`, `phase`).
- `loader.ts` contains significant normalization logic (e.g., `normalizeAlgorithm`, `derivePositionDegrees`) which indicates the runtime is already doing heavy lifting to fix loose data.

### Future Target
- **Decoupling:** Separate physical wheel configuration (degrees, phases) from clinical algorithm logic. Clinical algorithms should define the "What" (state, content, transitions) while the App/Renderer defines the "How" (degrees on the wheel).
- **Schema Enforcement:** Move the normalization logic from `loader.ts` into a build-time or validation-time step.
- **Safe Modernization:** Any shift to a more robust state machine (e.g., XState or a cleaner custom reducer) must be proven in the Warden `app/dev-mode/` surface before replacing the core runtime.

## 3. Authority Split

### Headmaster Domain (Future Direction)
- Defining the "V2" Algorithm Schema that separates clinical vs. visual metadata.
- Planning the transition to a more maintainable state machine implementation.
- Establishing the "Clinical Behavior Contract" that all state-machine changes must satisfy.

### Warden Domain (Current Implementation)
- Measuring the live state-machine behavior against `Warden Constitution` constraints.
- Implementing "Bridge Patches" to fix bugs in the current `loader.ts` or `renderer.ts`.
- Validating algorithm content against medical standards.

## Next Steps
1. **Update ARCHITECTURE_TARGET.md:** Reflect the clinical vs. visual metadata separation.
2. **Warden Handoff:** Normalize the algorithm source-of-truth to stop the drift between `app/` and `prototype/`.
3. **Draft Syllabus Unit 3:** Focus on "Clinical vs. Visual Metadata Separation".


## Outcome
`HREQ-003` refined the future-state architecture target and produced a bounded Warden follow-on for algorithm source normalization.
