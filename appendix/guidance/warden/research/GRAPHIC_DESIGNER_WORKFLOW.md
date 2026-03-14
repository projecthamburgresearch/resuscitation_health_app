# Graphic Designer Workflow (Dynamic + Static)

This workflow is optimized for a single mobile portrait app with dynamic state transitions.

## Step 1: Read the Dynamic Flow First
Start with dynamic captures, not static:
1. `.../screenshots/dynamic/main/*.png`
2. `.../splits/dynamic/main/*/images/*.png`
3. `.../splits/dynamic/main/*/regions_map.json`

Goal: verify state-to-state behavior, not just one frozen frame.

## Step 2: Validate Zone Contract
For each sampled transition, verify:
1. Top incoming stack reflects upcoming context.
2. Center card is the active decision state.
3. Bottom stack reflects valid history.

Use region crops (`incoming`, `wheel-stage`, `history`, `checklist`, `timer`) for direct checks.

## Step 3: Pull Measured Facts
When something looks wrong:
1. Use region `sourceIndex` from `regions_map.json`.
2. Locate matching element in `home-scan.json`.
3. Extract measurable values (geometry, typography, contrast).

Avoid subjective-only decisions.

## Step 4: Map to Code and Risk
1. Use Blueprint outputs to find file ownership and dependency risk.
2. Use repository search (`rg`) for exact implementation points.
3. Record regression watchlist before editing.

## Step 5: Verify with Re-run
1. `npm run analyze:warden:local`
2. Compare new dynamic/static screenshots and split maps.
3. Confirm acceptance gates in active ticket.

## Important Principle
Dynamic artifacts are primary truth for this app. Static artifacts support layout context, but transition correctness decides pass/fail.
