# Nurse-Facing Flow: Resuscitation App Anchor V2 Navigation

This document outlines the expected clinical workflow principles of the resuscitation wheel application. This interaction model (Anchor V2) is constructed to eliminate ambiguity and prevent dangerous mis-navigations during critical resuscitation episodes.

## Core Navigation Principles

1. **One Gesture, One Step**: During normal progression through linear steps and cardiovascular checks, spinning the wheel aggressively will *not* catapult you multiple steps forward. One discrete forward drag translates to exactly *one* step of the algorithm. 
2. **Anchor Snapping**: After releasing the wheel, it acts as a progress barometer. The knob will predictably snap to its anchor position. A position near "11 o'clock" represents the start of the algorithm, progressing anticlockwise towards "1 o'clock" for completion.
3. **No Drift**: If a drag does not meet the necessary threshold to commit to a step transition, the knob will snap back to the current active anchor. It will not float between states.

## Decision Points (The Lock Mechanism)

Clinical algorithms frequently split (e.g., "Shockable Rhythm?" -> Yes/No). In out-of-hospital and in-hospital environments, these are high-stakes bifurcations.

- **The Hard Stop**: The wheel mechanism will completely lock forward navigation upon hitting a decision card. You cannot inadvertently bypass a decision by over-spinning. 
- **The Confirmation Act**: To traverse past a decision, the user must explicitly:
  1. *Cycle* between the available options.
  2. *Drag* the selected option card downwards into the center active zone. 
- **Auditable Trails**: Every confirmed decision leaves a telemetry trail, recording the option chosen, maintaining clinical accountability.

## Seamless Rewinding

Medical emergencies are dynamic; new information might prompt a reassessment of a previous state.

- **Frictionless Retracing**: A reverse gesture (clockwise rotation) reliably rewinds exactly one step back. 
- **Passing Through Decisions**: If you rewind *past* a previously confirmed decision point, the wheel will smoothly transition without forcing you to re-confirm the prior choice backward. When you move forward again, your previous choice is remembered and presented, unless actively altered. 
- **Non-Destructive Exploration**: If a user selects an option at a decision point, progresses, and then rewinds, that forward path remains the projected path (retained in application memory) until a new superseding decision commits.

## CPR Loops and Timers

CPR cycles are handled identically to the rest of the flow regarding wheel interactions.

- **Loop Consistency**: Stepping through a CPR loop utilizes the same "One Gesture, One Step" pattern. 
- **Global Timekeeping**: Algorithm progression automatically manages the global timers, initiating when specific critical cards are reached without requiring manual nurse intervention. 
