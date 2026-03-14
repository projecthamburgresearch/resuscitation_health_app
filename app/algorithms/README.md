# Runtime Algorithms: Resuscitation Health App

This directory contains the canonical runtime algorithms consumed by the Resuscitation Health App state machine.

## Source of Truth Rule
1. `app/algorithms/` is the canonical runtime authority.
2. `index.json` is the manifest for the active algorithm deck.
3. Any change here MUST be validated against the clinician-facing state-machine behavior contract.
4. Changes to these files should be mirrored into `prototype/json-algorithms/` to maintain design alignment.

## Contents
- `index.json` - Active algorithm manifest
- `algo_*.json` - Clinical algorithm definitions
