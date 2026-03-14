# Design Algorithms: Resuscitation Health App

This directory contains design-source algorithm files and schema references for the Resuscitation Health App decision wheel.

## Source of Truth Rule
1. `prototype/json-algorithms/` is a derived or mirrored design surface for alignment and audit.
2. `app/algorithms/` is the canonical runtime authority.
3. Any JSON algorithm mirrored here should be synchronized to the `app/algorithms/` version to maintain design-runtime parity.
4. Historical `.txt` mirrors and schema text files are preserved here as legacy reference artifacts; they are not canonical and are not consumed by the runtime.

## Contents
- `algorithm-schema-v3.json` - Upstream schema reference
- `algorithm-schema-v3.txt` - Historical text mirror of the schema reference
- `index.json` - Mirrored algorithm manifest
- `algo_*.json` - Mirrored clinical algorithm definitions
- `algo_*.txt` - Historical text mirrors retained for audit/reference
