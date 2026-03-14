# Exit Pathways

## Standard Closeout
1. finish the lane
2. verify
3. stop local servers
4. push
5. wait for GitHub CI/Deploy when applicable
6. run `npm run exit:refresh -- --reviewer "Steward"`

## New Session Bootstrap
1. read `prompts/LATEST_SESSION_REENTRY.md`
2. verify live `HEAD`, worktree state, and Switchboard queue
3. trust live queue over stale continuity metadata if they differ
4. continue from the queued lane named by Exit or Switchboard
