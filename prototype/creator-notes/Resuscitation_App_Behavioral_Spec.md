# RESUSCITATION APP: BEHAVIORAL SPECIFICATION GUIDE
## "The Federalist Papers" - Complete A-Z Reference

---

# PART 1: FOUNDATIONAL ARCHITECTURE

## 1.1 The Core Metaphor
The app is a **State-Machine-Driven Deck with Z-axis Navigation**:
- **Engine**: JSON Graph (State Machine)
- **View**: A "Wheel" that scrolls through time (Past/Present/Future)
- **Philosophy**: Like a dating app rotated 90° - swipe down instead of left/right

## 1.2 The Three Temporal Zones
| Zone | Position | Represents | Visual State |
|------|----------|------------|--------------|
| **Top Zone** | Above wheel | FUTURE | Preview stack, 3 cards max |
| **Middle Zone** | Center (in wheel) | PRESENT | Active card, full interaction |
| **Bottom Zone** | Below wheel | PAST | History stack, faded/greyscale |

## 1.3 Global Dimensions (iPhone 14 Pro Reference)
```
Frame:        390 × 844px
Header:       50-60px fixed
Footer:       90-120px fixed  
Wheel:        300-340px diameter
Active Card:  180-220px × 200-260px (INSCRIBED in wheel)
Preview Card: 120-140px × 90-100px
History Card: 110-130px × 80-100px
Safe Margin:  16px
```

---

# PART 2: THE WHEEL (Primary Navigation)

## 2.1 Wheel Physics
| Direction | Action | Result |
|-----------|--------|--------|
| **Anticlockwise** | Pull/Drag down | ADVANCE (next card) |
| **Clockwise** | Push/Drag up | REWIND (previous card) |

## 2.2 Knob Positions (Design Degrees)
```
0° = 12 o'clock (Top)
90° = 3 o'clock (Right)  
180° = 6 o'clock (Bottom)
270° = 9 o'clock (Left)
330° = 11 o'clock (Start position)
```

### Position Mapping by State
| State | Knob Position | Phase |
|-------|---------------|-------|
| Cover/Start | 330° (11:00) | `start_point` |
| First Card | 0° (12:00) | `assessment` |
| Standard Cards | ~270° (9:00) | `action` |
| CPR Loop | 180° (6:00) | `loop_holding_pattern` |
| End/Handover | 60° (2:00) | `complete` |

## 2.3 Degree-to-Pixel Conversion
```javascript
// Design degrees (0° = 12 o'clock) to Math degrees (0° = 3 o'clock)
const mathDeg = designDeg - 90;
const rad = mathDeg * (Math.PI / 180);
const x = centerX + radius * Math.cos(rad);
const y = centerY + radius * Math.sin(rad);
```

## 2.4 Threshold Gate (Anti-Accidental Activation)
- **Minimum drag**: 20-30 degrees before triggering transition
- **Rubber-band**: If < threshold and released → spring back to origin
- **Timer protection**: Timer does NOT start until threshold crossed

## 2.5 Wheel States
| State | Behavior |
|-------|----------|
| **Free-Spinning** | Normal navigation (linear transitions) |
| **Locked** | Decision card active - wheel controls carousel, not vertical |
| **Magnetic Lock** | On decision cards, snaps to neutral center position |
| **Pulse/Animate** | During CPR loop - slight movement to indicate "holding pattern" |

---

# PART 3: THE CARDS

## 3.1 Card Types
| Type | Behavior | Wheel State |
|------|----------|-------------|
| `cover` | Title only, no border, transparent bg | Free, starts timer on exit |
| `standard` | Full card with checklist/tools | Free |
| `decision` | YES/NO split, locks wheel | LOCKED - horizontal mode |
| `loop` | Part of CPR cycle, pulsing animation | Free with visual pulse |
| `terminal` | End state, wheel stops | Stopped |

## 3.2 Card Anatomy
```
┌─────────────────────────────────────┐
│ [Decision Icon]     [Fullscreen] ← │  Top corners
│                                     │
│           CARD TITLE                │  Header
│                                     │
│         Card Body/Content           │  Body (may have slides)
│                                     │
│ [Toolbox]    [● ○ ○]    [Expand] ← │  Bottom row
└─────────────────────────────────────┘
```

## 3.3 Card Icons (Established Filenames)
| Icon | Filename | Position | Purpose |
|------|----------|----------|---------|
| Decision Preview | `decision-tree-svgrepo-com-upper-section.svg` | Top-right of PREVIEW card | Indicates upcoming decision |
| Toolbox | `first-aid-kit-2-svgrepo-com.svg` | Bottom-left | Opens calculator/tools modal |
| Fullscreen | `fullscreen-svgrepo-com.svg` | Top-right | Expands card view |
| Search | `search-tool-symbol-svgrepo-com.svg` | Header | Search algorithms |

## 3.4 Card Stacking Rules
**Preview Stack (Top Zone):**
- Show up to 3 upcoming cards
- Reverse order: furthest card rendered first (back of stack)
- Each card offset: `translateY(depth * -10px) scale(1 - depth * 0.05)`
- Z-index decreases with depth

**History Stack (Bottom Zone):**
- Show up to 3 past cards
- Opacity: 0.5-0.7
- Filter: grayscale(100%)
- Each card offset: `translateY(depth * 10px) scale(1 - depth * 0.06)`

## 3.5 Cover State vs Card State
| Property | Cover | Card |
|----------|-------|------|
| Background | Transparent | Grey (#d0d0d0) |
| Border | None | 2px solid #1a1a1a |
| Content | Title text only | Full card structure |
| Icons | None | Fullscreen, Toolbox visible |

---

# PART 4: THE MIRACLE (Decision Logic)

## 4.1 The Miracle Mechanic
When a `decision` type card enters the Middle Zone:

1. **Wheel LOCKS** for vertical navigation
2. **Wheel REMAPS** to horizontal carousel control
3. **Top Zone** switches from vertical stack to **HORIZONTAL SPREAD**
4. User rotates wheel to toggle between options (YES/NO)
5. User **SWIPES DOWN** on selected option to confirm
6. Only then does vertical navigation resume

## 4.2 Decision Carousel Rendering
```javascript
// Horizontal spread of decision options
options.forEach((opt, idx) => {
    const isSelected = idx === state.decisionIndex;
    const xOffset = (idx - state.decisionIndex) * 160; // Spread
    const scale = isSelected ? 1.0 : 0.8;
    const opacity = isSelected ? 1.0 : 0.5;
    // Render at xOffset position
});
```

## 4.3 Decision Confirmation
- **Wheel rotation**: Toggles `decisionIndex` (which option is highlighted)
- **Swipe down** on highlighted option: Confirms selection
- **Threshold**: 50px vertical swipe to confirm
- After confirmation: `decisionIndex` resets to 0

## 4.4 Decision Protection Rules
- Preview stack touch interactions DISABLED during decision (`pointer-events: none`)
- Only the YES/NO buttons are interactive
- Wheel cannot advance past decision without selection

---

# PART 5: THE CHECKLIST

## 5.1 Checklist Location
- Fixed position in **FOOTER** area
- Updates dynamically based on current card
- Persists across navigation (card-specific items)

## 5.2 Checklist Types
| Type | Behavior | Visual |
|------|----------|--------|
| `checkbox` | Simple "I did this" | Standard checkbox |
| `boolean_toggle` | Logic switch, reveals/hides other items | Toggle switch |
| `radio_select` | Single choice from options | Radio buttons |

## 5.3 Conditional Visibility
```json
{
    "id": "chk_call_999",
    "label": "Call 999",
    "type": "checkbox",
    "visible_if": "chk_2nd_rescuer == true"
}
```
- Items can be hidden/shown based on toggle states
- `visible_if` parsed at runtime

## 5.4 Checklist → Carousel Binding
```json
{
    "id": "chk_age_select",
    "type": "radio_select",
    "options": ["Infant (<1yr)", "Child (>1yr)"],
    "affects_carousel_slide": true
}
```
- Selection can auto-switch carousel slides on the active card

---

# PART 6: THE TOOLBOX

## 6.1 Toolbox Structure
```json
"toolbox": [
    {
        "tool_id": "age_calc",
        "icon": "calculator",
        "label": "Age Calculator",
        "function": "input_dob_output_category"
    }
]
```

## 6.2 Available Tools
| Tool ID | Purpose |
|---------|---------|
| `age_converter` | DOB → Infant/Child category |
| `weight_estimator` | Age → Estimated weight |
| `drug_dosing` | Weight → Drug doses |

## 6.3 Toolbox Behavior
- Opens as **MODAL** overlay
- **Auto-Dismissal**: Any navigation event triggers `modal.close()`
- Results can bind back to card (e.g., auto-select carousel slide)

---

# PART 7: THE TIMER

## 7.1 Global Timer
```json
"global_timer": {
    "enabled": true,
    "label": "Total Time",
    "type": "count_up"
}
```
- Located: Footer, bottom-right
- Format: `HH:MM:SS`
- **Starts**: On first card advancement (not on cover)
- **Never resets**: Represents "time since event started"
- **Persists**: Across theme changes, navigation, everything

## 7.2 Card Timer (Local)
```json
"timer_config": {
    "type": "countdown",
    "duration_seconds": 18,
    "auto_start": true,
    "audio_metronome": true,
    "bpm": 110
}
```
- Used for CPR compressions (tempo guidance)
- Can be countdown or stopwatch
- Optional metronome beeps

## 7.3 Timer Controls
| Action | Result |
|--------|--------|
| Single tap | No effect |
| Double tap | Pause/Resume |
| Press and hold | Reset to start (full app reset) |

---

# PART 8: JSON SCHEMA

## 8.1 Complete Card Schema
```json
{
    "id": "CARD_XX",
    "type": "standard | decision | loop | terminal | cover",
    "content": {
        "title": "Card Title",
        "body": "Description text",
        "slides": [
            { "header": "Slide 1", "body": "Content", "context": "infant" }
        ]
    },
    "ui_config": {
        "full_screen_enabled": true,
        "carousel_dots": true
    },
    "wheel_config": {
        "position_degrees": 270,
        "phase": "action",
        "animation": "pulse"
    },
    "timer_config": {
        "type": "countdown",
        "duration_seconds": 18
    },
    "checklist": [...],
    "toolbox": [...],
    "transitions": {
        "type": "linear | split",
        "next_id": "CARD_YY",
        "options": [
            { "label": "YES", "target_id": "CARD_YES" },
            { "label": "NO", "target_id": "CARD_NO" }
        ]
    }
}
```

## 8.2 Algorithm Metadata
```json
{
    "algorithm_meta": {
        "id": "algo_paed_bls_001",
        "title": "Paediatric Out-of-Hospital BLS",
        "source": "Resuscitation Council UK (2021)",
        "root_card_id": "CARD_START",
        "global_timer": { "enabled": true, "type": "count_up" }
    },
    "global_tools": {
        "calculator_library": ["age_converter", "weight_estimator"]
    },
    "deck": [...]
}
```

## 8.3 Loop Resolution
```json
// Card 09: "Signs of life?"
"transitions": {
    "type": "split",
    "options": [
        { "label": "YES", "target_id": "CARD_END" },
        { "label": "NO", "target_id": "CARD_07" }  // Points BACK to compressions
    ]
}
```
- NO path points to earlier card ID → creates loop
- User stays in loop until YES selected

---

# PART 9: PARAMETRIC ENGINE (CSS Variables)

## 9.1 Core Variables
```css
:root {
    /* Geometry */
    --stroke-width: 2px;
    --card-radius: 12px;
    --wheel-diameter: 300px;
    --card-width: 180px;
    --card-height: 200px;
    
    /* Colors */
    --primary: #1a1a1a;
    --bg: #f5f5f5;
    --card-bg: #d0d0d0;
    
    /* Opacity Engine */
    --layer-opacity-mid: 1.0;
    --layer-opacity-preview: 0.6;
    --layer-opacity-history: 0.4;
    
    /* Global Filters (Dev only) */
    --global-contrast: 100%;
    --global-sepia: 0%;
    --global-brightness: 100%;
}
```

## 9.2 Filter Application
```css
body {
    filter: 
        contrast(var(--global-contrast)) 
        sepia(var(--global-sepia)) 
        brightness(var(--global-brightness));
}
```

## 9.3 Dev-Only Access
- No UI for users
- Adjust via code: `document.documentElement.style.setProperty('--var', 'value')`
- Or console: `setParam('--global-contrast', '120%')`

---

# PART 10: INTERACTION RULES

## 10.1 Single-Touch Singularity
- Only ONE active touch point for navigation at a time
- First touch wins:
  - If user grabs Card first → Wheel is locked
  - If user grabs Wheel first → Cards become non-interactive

## 10.2 Gesture Dominance (Keyboard)
- If keyboard is open and user touches navigation → `keyboard.dismiss()`
- Navigation always takes priority over text input

## 10.3 Auto-Dismissal
- Any navigation event broadcasts `NAVIGATION_START`
- All modals/tooltips listen and trigger `this.close()`
- Transition acts as "clean slate" wiper

## 10.4 Swipe vs Spin Protection
- If conflicting gestures detected → first gesture wins
- No simultaneous card-swipe and wheel-spin

---

# PART 11: EDGE CASES (10 Strawman Solutions)

| # | Problem | Solution |
|---|---------|----------|
| 1 | Sepia Blindness (critical icons lost) | Semantic Color Lock - bypass filters |
| 2 | Decision Skip (drag preview down) | Z-Index Lock - disable preview touch |
| 3 | Ghost Icon (icon follows card) | Transition Cleanup - icons on SLOT not card |
| 4 | Layer Collapse (opacity too low) | Opacity Clamping - min 0.9 for active |
| 5 | History Rewrite (changing past decision) | Recursive Branch Pruning - delete downstream |
| 6 | Double Decision (3+ options) | Dynamic Layout Flex - adapt to array length |
| 7 | Timer Reset (theme change) | Context Isolation - timer in separate state |
| 8 | Wheel Drift (decision card) | Magnetic Lock - snap to neutral |
| 9 | Search Overlay (old history visible) | Context Flush - clear on algorithm switch |
| 10 | SVG Pixelation (fullscreen blur) | Vector First - SVG only, @3x fallback |

---

# PART 12: WHEEL POSITION JOURNEY (Images 1-10)

| Image | State | Knob Position | Cards Visible |
|-------|-------|---------------|---------------|
| 1 | Cover | 11:00 (330°) | Title only, no card border |
| 2 | Card 1 | 3:00 | Preview: 3 cards, History: empty |
| 3 | Card 2 | 3-4:00 | Preview: 3, History: 1 |
| 4 | Card 3 | 4-5:00 | Preview shows decision icon |
| 5 | Card 4 (Decision) | 6:00 | LOCKED - carousel mode |
| 6 | Decision Carousel | 6:00 | Horizontal 5-card spread |
| 7-9 | Post-decision | 9:00 (270°) | Normal stack |
| 10 | Terminal | 2:00 (60°) | Process complete |

---

# PART 13: FOOTER STRUCTURE

```
┌─────────────────────────────────────────────────┐
│ Check List                                       │
├─────────────────────────────────────────────────┤
│ ☐ Item 1  ☐ Item 2  │  ⋮  │  00:00:00          │
│                      │     │                     │
└─────────────────────────────────────────────────┘
     Checkbox area      Menu    Timer (monospace)
```

## 13.1 Footer Components
| Element | Position | Behavior |
|---------|----------|----------|
| "Check List" label | Top-left | Static label |
| Checkbox area | Left, flex-grow | Dynamic per card |
| Overflow menu (⋮) | Center-right | Additional options |
| Timer | Right | Monospace, bordered |

---

# PART 14: STATE MANAGEMENT

## 14.1 Core State Object
```javascript
let state = {
    currentId: "CARD_START",      // Active card ID
    history: [],                   // Stack of visited card IDs
    wheelAngle: 330,               // Current knob position (degrees)
    decisionIndex: 0,              // Selected option in decision carousel
    timerSeconds: 0,               // Global timer count
    timerRunning: false            // Timer started flag
};
```

## 14.2 State Transitions
```javascript
function triggerTransition() {
    const curr = DECK[state.currentId];
    if (curr.next || curr.options) {
        state.history.push(state.currentId);
        state.currentId = getNextId(curr);
        if (!state.timerRunning) startTimer();
        render();
    }
}

function triggerRewind() {
    if (state.history.length > 0) {
        state.currentId = state.history.pop();
        render();
    }
}
```

## 14.3 Decision State Change
```javascript
// During decision card - wheel controls horizontal index
if (card.type === 'decision') {
    if (delta > 30) state.decisionIndex = 0;
    else if (delta < -30) state.decisionIndex = 1;
    // Clamp to valid range
    render(); // Re-render carousel
}
```

---

# PART 15: ANIMATION & TRANSITIONS

## 15.1 Card Transitions
```css
.card {
    transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}
```

## 15.2 Wheel Transition
```css
.wheel-container {
    transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

## 15.3 Loop Pulse Animation
```css
@keyframes pulse-red {
    0% { box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
    50% { box-shadow: 0 20px 50px rgba(255, 0, 0, 0.3); border-color: red; }
    100% { box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
}
.pulsing { animation: pulse-red 1s infinite; }
```

---

# PART 16: ACCESSIBILITY & HAPTICS

## 16.1 Haptic Feedback
```javascript
// On decision toggle
if (navigator.vibrate) navigator.vibrate(10);

// On card transition
if (navigator.vibrate) navigator.vibrate(5);
```

## 16.2 Accessibility Requirements
- `aria-live` regions for dynamic content
- Touch targets minimum 44×44px
- High contrast mode support (via parametric engine)
- Screen reader announcements for state changes

---

# PART 17: DATA LOGGING

## 17.1 Session Log
At terminal card, generate summary:
```json
{
    "session_id": "uuid",
    "algorithm": "paed_bls_001",
    "start_time": "ISO timestamp",
    "end_time": "ISO timestamp",
    "total_duration_seconds": 840,
    "decisions_made": [
        { "card": "CARD_04", "choice": "NO", "timestamp": "..." }
    ],
    "cpr_cycles": 14,
    "checklist_completed": ["chk_safe", "chk_airway", ...]
}
```

---

# APPENDIX A: ICON LIBRARY

| Icon | SVG ID | Usage |
|------|--------|-------|
| Decision Tree Upper | `#sym-decision` | Preview card showing upcoming decision |
| Toolbox/First Aid | `#sym-toolbox` | Bottom-left of active card |
| Fullscreen | `#sym-fullscreen` | Top-right of active card |
| Search | (header) | Algorithm search |

---

# APPENDIX B: Z-INDEX STACK

| Layer | Z-Index | Element |
|-------|---------|---------|
| 500 | Header, Footer | Fixed chrome |
| 200 | Knob | Above wheel, below modals |
| 110 | Active Card | Primary interaction |
| 100 | Zone-Middle | Wheel container |
| 90 | Wheel circle | Behind card |
| 50 | Zone-Top | Preview stack |
| 40 | Zone-Bottom | History stack |

---

# APPENDIX C: WHEEL MATH REFERENCE

```javascript
// Convert design degrees to screen position
function degToPosition(designDeg, radius, centerX, centerY) {
    const mathDeg = designDeg - 90;  // 0° top → 0° right
    const rad = mathDeg * (Math.PI / 180);
    return {
        x: centerX + radius * Math.cos(rad),
        y: centerY + radius * Math.sin(rad)
    };
}

// Calculate angle from touch position
function positionToDeg(touchX, touchY, centerX, centerY) {
    let deg = Math.atan2(touchY - centerY, touchX - centerX) * 180 / Math.PI + 90;
    if (deg < 0) deg += 360;
    return deg;
}

// Calculate delta with wrap-around handling
function calculateDelta(oldDeg, newDeg) {
    let delta = oldDeg - newDeg;
    if (delta < -180) delta += 360;
    if (delta > 180) delta -= 360;
    return delta;
}
```

---

**END OF SPECIFICATION**

*Version: 1.0*
*Last Updated: Based on conversation logs through Image 5*
*Source: Resuscitation Council UK (2021) - Paediatric BLS Algorithm*
