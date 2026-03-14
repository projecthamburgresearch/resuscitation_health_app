# Headmaster Handoff Protocol: Resuscitation Health App

## Purpose
Headmaster handoffs convert strategic or discovery work into bounded Warden implementation lanes.

## Required Elements
1. exact problem statement
2. live product constraints preserved by the handoff
3. code targets or evidence targets
4. acceptance gates
5. verification steps
6. explicit non-goals
7. note on whether the handoff should map onto an existing or new Warden `REQ-*` ticket

## Project-Specific Rule
Do not write handoffs that ignore the app's state-machine nature. Every implementation handoff must say how it preserves or modifies the `incoming / current / previous` state contract when relevant.
