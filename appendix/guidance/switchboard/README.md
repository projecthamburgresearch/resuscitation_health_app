# Resuscitation Health App Switchboard

Switchboard is the async operator messaging layer for Resuscitation Health App.

## Role Boundary
1. delegates do the assigned lane plus the required exit interview
2. delegates do not review/archive unless explicitly assigned as `Steward`
3. `Steward` owns fix / accept / archive by default

## Local Naming Context
1. Headmaster tickets in this repo use `HREQ-*`
2. Warden tickets in this repo continue to use the existing `REQ-*` lineage

## Core Commands
1. `npm run switchboard:list`
2. `npm run switchboard:claim -- --message-id MSG-... --delegate "Claude Code"`
3. `npm run switchboard:close -- --message-id MSG-...`
4. `npm run switchboard:review -- --message-id MSG-... --reviewer "Steward" --verdict accept_with_fixes`
5. `npm run switchboard:archive -- --message-id MSG-... --reviewer "Steward" --verdict accept_with_fixes`
