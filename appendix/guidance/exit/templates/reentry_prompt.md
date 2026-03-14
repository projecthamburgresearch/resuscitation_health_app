# Session Reentry Template

Use this template to generate the current `LATEST_SESSION_REENTRY.md`.

Required sections:
1. role statement
2. read order
3. calibration packet pointer
4. current state summary
5. live-state guard that tells the next session to compare live `HEAD`, worktree state, and queue state against the recorded continuity summary
6. latest raw log pointer
7. pending queue
8. next bounded priority from the live Switchboard queue first when one exists
9. role-boundary guard that tells delegates to stop after lane artifacts plus exit interview unless explicitly assigned as `Steward`
10. rule that on-disk artifacts outrank chat memory
