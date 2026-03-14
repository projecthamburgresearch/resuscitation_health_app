# Resuscitation Health App Exit

Exit is the continuity and re-entry subsystem for Resuscitation Health App.

## Role
1. raw terminal transcripts are canonical under `appendix/guidance/exit/logs/raw/`
2. Exit compiles live repo state, queue state, and current authority pointers into a re-entry surface
3. Exit prefers the live Switchboard queue as the next-lane source when one exists
4. Exit carries the delegate-vs-Steward boundary into the next session prompt

## Trust Rule
If live `git rev-parse HEAD`, `git status --porcelain`, or the live Switchboard queue differ from the recorded continuity packet, trust the live repo state and refresh Exit as soon as practical.
