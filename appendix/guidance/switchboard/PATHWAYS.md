# Switchboard Pathways

## Normal Delegate Flow
1. a bounded message is created in `inbox/`
2. a delegate claims it and moves it into `active/`
3. the delegate completes the lane artifacts and writes the required exit interview
4. the message moves to `outbox/`
5. Steward reviews, fixes, archives, and records lessons if needed

## Offgrid Flow
1. an offgrid message is created when a bounded discovery is needed outside the main product queue
2. the delegate still stops at the exit interview boundary
3. Steward decides whether the result becomes a Headmaster lane, a Warden lane, or only a durable note
