# Question -> Answer Matrix (Dynamic State Model)

This matrix maps common project questions to the correct evidence path.

## State and Transition Questions

1. "Did this transition land on the right next card?"
- Primary: dynamic screenshots (`before/after`) and transition metadata in bundle manifest
- Secondary: model JSON (`fromId`/`toId` expectations)
- Output: transition pass/fail table

2. "Did the wheel angle/phase move as expected?"
- Primary: `beforeSnapshot.wheel` and `afterSnapshot.wheel`
- Secondary: model card metadata (phase/canonical angle)
- Output: angle/phase deviation report

3. "Did incoming/current/previous zones stay correct?"
- Primary: dynamic split crops + regions map
- Secondary: scan geometry for targeted elements
- Output: zone contract verdict and evidence list

4. "Can clinician move backward safely?"
- Primary: reverse-direction dynamic transitions
- Secondary: history stack behavior in snapshots
- Output: back-navigation integrity report

## Clinical Continuity Questions

1. "Do timer/checklist/notes surfaces stay stable across steps?"
- Primary: dynamic splits for footer/checklist/timer regions
- Secondary: scan element continuity checks
- Output: continuity status and regression notes

2. "Does light mode remain consistent and readable?"
- Primary: scan `meta.theme`, color physics, WCAG
- Secondary: static screenshots for visual context
- Output: light-mode integrity verdict

## Engineering Impact Questions

1. "Where is this implemented?"
- Primary: Blueprint (`xray`, `synapse`, `llm_context`) + repo search
- Secondary: split map `sourceIndex` mapping to scan elements
- Output: concrete file/component target list

2. "What else might break if we edit here?"
- Primary: Blueprint graph/hotspots
- Secondary: bundle coverage of affected UI regions
- Output: impact surface and regression watchlist

## Operational Reliability Questions

1. "Can this run be trusted?"
- Primary: bundle capture retries/errors + scan attempts
- Secondary: artifact completeness checks
- Output: stability score and rerun decision
