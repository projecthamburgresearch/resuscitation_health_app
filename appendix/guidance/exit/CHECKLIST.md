# Exit Checklist

Use this before accepting a continuity refresh.

1. verify the latest raw log pointer is correct
2. verify the latest continuity snapshot was written
3. verify the re-entry prompt names the real next priority or says there is none
4. verify the prompt points to current Headmaster, Warden, and Switchboard surfaces
5. verify the state file records created, updated, and reviewed timestamps
6. verify no claim in the continuity pack depends on chat-only memory
7. verify the continuity pack does not relocate or delete canonical raw logs accidentally
8. verify the prompt tells the next session to compare live `HEAD`, worktree state, and queue state before trusting recorded continuity metadata
9. verify `prompts/LATEST_SESSION_CALIBRATION.md` exists
10. verify the calibration packet uses the bounded question set chosen by the project
11. verify the calibration answers are marked as project defaults or assumptions, not unquestionable truth
