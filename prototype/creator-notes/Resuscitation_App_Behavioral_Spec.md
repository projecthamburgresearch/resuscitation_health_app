# RESUSCITATION APP: BEHAVIORAL SPECIFICATION GUIDE
## Version 2.0 — Post-REQ-009 Modular PWA Architecture

---

# PART 1: FOUNDATIONAL ARCHITECTURE

## 1.1 The Core Metaphor
The app is a **State-Machine-Driven Deck with Z-axis Navigation**:
- **Engine**: JSON Graph (State Machine)
- **View**: A "Wheel" that scrolls through time (Past/Present/Future)
- **Philosophy**: Like a dating app rotated 90° — swipe down instead of left/right

## 1.2 Technology Stack (REQ-009)
| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | TypeScript | Type safety for complex state machine |
| Bundler | Vite | Hot reload, ES modules, code splitting |
| Styling | Modular CSS | Design tokens, responsive, themeable |
| PWA | Service Worker + manifest | Offline-first, installable |
| Framework | None (vanilla) | Direct DOM for wheel physics, no jitter |

## 1.3 Module Architecture
```
app/src/
├── main.ts              Entry point, DOM refs, init
├── types.ts             All type definitions
├── automation.ts        Warden automation API
├── state/
│   ├── store.ts         Global state, DECK map, algorithm runtime
│   └── decisions.ts     Decision state helpers
├── algorithms/
│   └── loader.ts        Fetch, normalize, DECK builder
├── wheel/
│   ├── physics.ts       Angle math, knob positioning
│   ├── knob.ts          Drag handlers, finger-following
│   ├── gestures.ts      Forward/reverse gesture detection
│   └── fsm.ts           Wheel mode computation
├── navigation/
│   ├── advance.ts       advance(), rewind(), canTapAdvance()
│   ├── anchors.ts       Anchor-point engine, forward path
│   └── zone-drag.ts     Card swipe between zones
├── cards/
│   ├── renderer.ts      Main render loop, active card
│   ├── preview-zone.ts  Top zone: preview stack + decision options
│   ├── history-zone.ts  Bottom zone: history mirror
│   ├── decision-cards.ts Drag-to-confirm decisions
│   ├── checklist-card.ts Checklist as navigable card
│   └── checklist.ts     Footer checklist rendering
├── ticker/
│   ├── engine.ts        Message evaluation + fade transitions
│   └── rules.ts         Priority-based coaching rules
├── ui/
│   ├── menu.ts          3-dot menu, protocol list, settings
│   ├── modal.ts         Toolbox modal
│   ├── timer.ts         Global timer
│   ├── haptic.ts        Vibration feedback
│   └── protocol-landing.ts  Protocol selection page
├── pwa/
│   └── register.ts      Service worker registration
└── styles/
    ├── tokens.css       Design tokens (colors, sizes, fonts)
    ├── layout.css       App shell, zones, header, footer
    ├── wheel.css        Circle, knob, dragging transitions
    ├── cards.css        Card faces, cover, loop, decisions
    ├── stack.css        3D perspective depth for zones
    ├── ticker.css       Footer ticker styling
    ├── menu.css         Menu panel, settings, themes
    └── responsive.css   Breakpoints, compact mode
```

## 1.4 The Three Temporal Zones
| Zone | Position | Represents | Visual State |
|------|----------|------------|--------------|
| **Top Zone** | Above wheel | FUTURE | Preview stack with 3D depth perspective |
| **Middle Zone** | Center (in wheel) | PRESENT | Active card with entrance animation |
| **Bottom Zone** | Below wheel | PAST | History mirror, greyscale with depth |

## 1.5 Enhanced Card Zones (REQ-009 Phase 2)

**Preview Zone — 3D Depth Stack:**
Cards use CSS `perspective: 800px` and `--depth` CSS variable for:
- `translateZ()` — depth into screen
- `scale()` — smaller with depth
- `opacity` — fades with depth
- Smooth transitions: `0.4s cubic-bezier(0.25, 0.8, 0.25, 1)`

**History Zone — Mirror Chirality:**
Mirrors the preview zone with downward offset instead of upward, plus grayscale filter.

**Active Card — 3D Entrance Animation:**
When navigating to a new card, `card-arrive` keyframes: `rotateY(-8deg) translateZ(-20px) scale(0.95)` → `transform: none`.

## 1.6 Global Dimensions (iPhone 14 Pro Reference)
```
Frame:        390 × 844px
Header:       50px fixed
Footer:       100px fixed (checklist + ticker + timer)
Wheel:        300px diameter (240px on short screens)
Active Card:  180 × 210px (INSCRIBED in wheel)
Preview Card: 130 × 95px
History Card: 120 × 85px
```

---

# PART 2: THE WHEEL (Primary Navigation)

## 2.1 Anchor-Point System (REQ-004)
The wheel uses discrete **anchor points** — one per card in the current path. Cards are distributed evenly across the wheel arc.

| Property | Value |
|----------|-------|
| Arc start | 330° (11 o'clock) |
| Arc end | 30° (1 o'clock) |
| Direction | Anticlockwise |
| Distribution | Even spacing across arc |

**Knob follows circular path**: `transform: rotate(angle) translateY(-radius) rotate(-angle)` — knob animates along the arc, never cuts across the chord.

**Visual angle tracking**: `state.wheel.visualAngle` uses shortest-path logic to prevent 350° jumps.

## 2.2 Wheel FSM (Finite State Machine)
| Mode | Trigger | Behavior |
|------|---------|----------|
| COVER | `card.type === 'cover'` | Forward gesture only |
| LINEAR | Standard cards | Forward/reverse navigation |
| DECISION | `card.type === 'decision'` | Locked — tap to select, drag to confirm |
| LOOP | CPR loop phase | Same as LINEAR, pulse animation |
| TERMINAL | `card.type === 'terminal'` | Reverse gesture only |

## 2.3 Drag Mechanics
| Phase | Behavior |
|-------|----------|
| `touchstart` | Record drag origin, add `.dragging` class (disables CSS transition) |
| `touchmove` | Track finger, compute delta from origin |
| Below threshold (10°) | Knob follows finger for responsive feel |
| Cross threshold | Remove `.dragging`, enable transition, trigger advance/rewind |
| `touchend` | Smooth snap back to current anchor |

**One navigation per drag**: `state.wheel.navConsumed` prevents multiple transitions.

## 2.4 Gesture Detection
```typescript
NAV_THRESHOLD_DEG = 10  // degrees to trigger navigation
// Anticlockwise arc: delta > threshold = forward, delta < -threshold = reverse
```

---

# PART 3: THE CARDS

## 3.1 Card Types
| Type | Behavior | Wheel Mode |
|------|----------|------------|
| `cover` | Title only, transparent, no border | COVER |
| `standard` | Full card with checklist/tools | LINEAR |
| `carousel_action` | Multiple slides, click to cycle | LINEAR |
| `decision` | YES/NO split, locks wheel | DECISION |
| `loop_start` | CPR cycle, pulse animation | LOOP |
| `action` | Standard in-loop action | LOOP |
| `terminal` | End state, wheel stops | TERMINAL |

## 3.2 Decision Tap-to-Confirm (REQ-008)
1. **Tap** an option card → `state.decisionTapped = true`, option becomes selected
2. **Drag** selected option down (or drag knob forward) → confirms decision
3. Without tap, forward gesture is blocked — prevents accidental selection

## 3.3 Card Swipe Navigation (REQ-009 Phase 3)
| Gesture | Direction | Result |
|---------|-----------|--------|
| Drag **preview card** down | Top → Middle | ADVANCE |
| Drag **history card** up | Bottom → Middle | REWIND |
| Cross 35% of zone height | — | Commit navigation |
| Release before threshold | — | Rubber-band snap back |

Knob syncs automatically via `render()` → `syncAnchors()`.

## 3.4 Card Stacking (3D Perspective)
**Preview Stack:**
```css
.preview-card {
    --depth: 0|1|2;  /* set by JS */
    transform: translateY(calc(var(--depth) * -12px))
               translateZ(calc(var(--depth) * -60px))
               scale(calc(1 - var(--depth) * 0.06));
    opacity: calc(1 - var(--depth) * 0.15);
}
```

**History Stack (Mirror):**
```css
.history-card {
    --depth: 0|1|2;
    transform: translateY(calc(var(--depth) * 12px))
               translateZ(calc(var(--depth) * -60px))
               scale(calc(1 - var(--depth) * 0.06));
    opacity: calc(0.7 - var(--depth) * 0.15);
    filter: grayscale(calc(var(--depth) * 30%));
}
```

---

# PART 4: ANCHOR-POINT NAVIGATION ENGINE

## 4.1 Forward Path Computation
`computeForwardPath()` walks the algorithm from start, following:
- Committed decisions (from `state.decisionRecords`)
- Longest-branch estimation for unrecorded decisions (progress never jumps backward)

## 4.2 Anchor Distribution
Cards are evenly spaced across the wheel arc: `angleOnArc(arc, i / (path.length - 1))`.

## 4.3 State Sync
`syncAnchors()` runs on every `render()`:
1. Recomputes full path and anchor angles
2. Finds current card in anchor array
3. Sets `state.anchorIndex`
4. `setKnobPosition()` animates knob to new anchor angle

---

# PART 5: FOOTER — TICKER COACH (REQ-009 Phase 4)

## 5.1 Rule-Based Coaching
The ticker evaluates rules on every render and displays the highest-priority message:

| Priority | Rule | Example |
|----------|------|---------|
| 1 | Unchecked required items | "Reminder: confirm airway is clear" |
| 2 | Decision point ahead | "Decision ahead: breathing assessment" |
| 3 | Loop count | "CPR cycle 4 — continue compressions" |
| 4 | Steps remaining | "3 steps to next decision point" |
| 5 | Timer milestone | "2 minutes elapsed — reassess" |
| 6 | Idle/default | "Follow the protocol — you're doing great" |

## 5.2 Footer Layout
```
┌──────────────────────────────────────────────┐
│ ☐ Item 1  ☐ Item 2       │  ⋮              │
├──────────────────────────────────────────────┤
│ Reminder: confirm airway  │  00:02:15       │
│ (ticker text)              │  (timer)        │
└──────────────────────────────────────────────┘
```

## 5.3 Ticker Animation
- Fade out (200ms opacity → 0)
- Update text
- Fade in (300ms opacity → 1, translateY(4px → 0))

---

# PART 6: CHECKLIST

## 6.1 Checklist Location
- **Footer area** — dynamic per card
- Items filtered by `visible_if` conditions
- State persists in `state.checklistState`

## 6.2 Checklist Types
| Type | Behavior |
|------|----------|
| `checkbox` | Simple "I did this" confirmation |
| `boolean_toggle` | Logic switch, reveals/hides other items |

## 6.3 Conditional Visibility
```json
{ "visible_if": "toggle_2nd_rescuer == true" }
{ "visible_if": "toggle_single_rescuer == true AND chk_speakerphone == false" }
```

---

# PART 7: PWA & MENU (REQ-009 Phase 5)

## 7.1 Progressive Web App
- `manifest.webmanifest` — name, icons, standalone display
- Service worker caches HTML, CSS, JS, all algorithm JSON
- Offline-first: works without internet after first load
- Installable on iOS Safari and Chrome Android

## 7.2 3-Dot Menu
Opens slide-down panel from header:
- **Select Protocol** — loads protocol list from `algorithms/index.json`
- **Search** — filter protocols
- **Settings** — font size, theme
- **About** — version, attribution

## 7.3 Settings (persisted to localStorage)
| Setting | Options | CSS Effect |
|---------|---------|------------|
| Font Size | Small / Medium / Large | `--font-scale` variable |
| Theme | Light / Dark / High Contrast | `data-theme` attribute |

---

# PART 8: TIMER

## 8.1 Global Timer
- Located: Footer, bottom-right
- Format: `HH:MM:SS`
- **Starts**: On first card advancement (not on cover)
- **Never resets**: Represents "time since event started"

## 8.2 Timer Integration with Ticker
Timer milestones (every 2 minutes) generate ticker messages for reassessment reminders.

---

# PART 9: JSON SCHEMA

## 9.1 Algorithm Structure
```json
{
    "algorithm_meta": {
        "id": "algo_paed_bls_001",
        "title": "Paediatric Out-of-Hospital BLS",
        "source": "Resuscitation Council UK (2021)",
        "wheel_arc": {
            "start_degrees": 330,
            "end_degrees": 30,
            "direction": "anticlockwise",
            "phase_spread_degrees": 4
        },
        "global_timer": { "enabled": true, "type": "count_up" }
    },
    "deck": [...]
}
```

## 9.2 Card Schema
```json
{
    "id": "CARD_XX",
    "type": "standard | decision | loop_start | terminal | cover",
    "content": {
        "title": "Card Title",
        "body": "Description text",
        "slides": [{ "header": "Slide 1", "text": "Content" }]
    },
    "wheel_config": {
        "position_degrees": 270,
        "phase": "action",
        "animation": "pulse"
    },
    "checklist": [
        { "id": "chk_safe", "label": "Area is safe", "type": "checkbox" }
    ],
    "toolbox": [
        { "id": "calc_age", "icon": "calculator", "label": "Age Calculator" }
    ],
    "transitions": {
        "type": "linear | split | self_loop",
        "next_id": "CARD_YY",
        "options": [
            { "label": "YES", "target_id": "CARD_YES" },
            { "label": "NO", "target_id": "CARD_NO" }
        ]
    }
}
```

## 9.3 Algorithm Files
| File | Algorithm | Context |
|------|-----------|---------|
| `algo_paed_bls_out.json` | Paediatric BLS | Out-of-hospital |
| `algo_paed_bls_in.json` | Paediatric BLS | In-hospital |
| `algo_newborn_ls.json` | Newborn Life Support | Delivery suite |
| `algo_anaphylaxis.json` | Anaphylaxis | Universal |
| `algo_paed_fbao.json` | Foreign Body Airway | Universal |

---

# PART 10: STATE MANAGEMENT

## 10.1 Core State Object
```typescript
interface AppState {
    currentId: string;
    history: string[];
    decisionIndex: number;
    decisionRecords: Record<string, number>;
    decisionTrail: DecisionTrailEntry[];
    decisionTapped: boolean;
    carouselIndex: number;
    timerSeconds: number;
    timerRunning: boolean;
    timerInterval: number | null;
    checklistState: Record<string, boolean>;
    anchors: Anchor[];
    anchorIndex: number;
    wheel: {
        mode: WheelMode;
        angle: number;
        visualAngle: number;
        dragOrigin: number | null;
        navConsumed: boolean;
    };
}
```

## 10.2 State Flow
1. User interaction (drag/tap) → `advance()` or `rewind()`
2. State mutation (currentId, history, decisions)
3. `render()` called
4. `syncAnchors()` → recompute path → set knob angle
5. `renderActiveCard()` → `renderPreviewZone()` → `renderHistoryZone()` → `renderChecklist()`
6. `updateTicker()` → evaluate rules → display coaching message

---

# PART 11: WARDEN AUTOMATION API

```typescript
window.__WARDEN_AUTOMATION = {
    version: '1.0',
    listCards(): string[]
    listAvailableAlgorithms(): Promise<string[]>
    loadAlgorithm(fileName: string): Promise<{ok, error, snapshot}>
    getModel(): {start_id, algorithm_meta, cards[]}
    getSnapshot(): AutomationSnapshot
    reset(): {ok, snapshot}
    gotoCard(cardId: string): {ok, snapshot}
    selectDecisionOption(index: number): {ok, snapshot}
    advance(): {ok, moved, before_id, after_id, snapshot}
    back(): {ok, before_id, after_id, snapshot}
}
```

---

# PART 12: RESPONSIVE DESIGN

## 12.1 Breakpoints
| Condition | Changes |
|-----------|---------|
| `max-width: 450px` | Full-width, no border |
| `max-height: 750px` | Compact mode — smaller wheel (240px), reduced padding |

## 12.2 Dynamic Dimensions
`updateDimensions()` reads CSS variables on window resize:
- `--wheel-radius` → `WHEEL_RADIUS`
- `--knob-size` → `KNOB_OFFSET`
- Force redraw of knob position

---

# PART 13: HAPTIC FEEDBACK

```typescript
function triggerHaptic(ms: number): void {
    if (navigator.vibrate) navigator.vibrate(ms);
}
```
- 15ms vibrate on navigation commit (advance/rewind)
- Applied to: knob drag, zone drag, decision confirm

---

**END OF SPECIFICATION**

*Version: 2.0*
*Last Updated: REQ-009 Modular PWA Refactoring*
*Source: Resuscitation Council UK (2021) Guidelines*
*Architecture: Vite + TypeScript, vanilla DOM, offline-first PWA*
