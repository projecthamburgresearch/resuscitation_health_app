# X-Ray Analysis Report

**Root:** `/Users/mordecaimachazire/Documents/local-projects/resuscitation_health_app/app`  

**Domain:** xray v2.0.0  

**Timestamp:** 2026-03-13 14:29:58.583220  


## Statistics

- **files_scanned:** 55
- **files_parsed:** 50
- **files_skipped:** 0
- **entity_count:** 1578
- **edge_count:** 3171
- **entity_types:**
  - file: 55
  - table: 10
  - variable: 1143
  - import: 111
  - chunk: 76
  - constant: 14
  - function: 128
  - type_alias: 5
  - export: 2
  - network_request: 3
  - endpoint: 3
  - interface: 28
- **elapsed_seconds:** 0.599
- **error_count:** 0

## Entities by Type

### Chunk (76)

| Name | File | Line | Complexity |
|------|------|------|------------|
| /src/main.ts | index.html | 80 | - |
| manifest.webmanifest | index.html | 7 | - |
| /aix-ppc64-0.25.12.tgz | package-lock.json | 17 | - |
| /android-arm-0.25.12.tgz | package-lock.json | 34 | - |
| /android-arm64-0.25.12.tgz | package-lock.json | 51 | - |
| /android-x64-0.25.12.tgz | package-lock.json | 68 | - |
| /darwin-arm64-0.25.12.tgz | package-lock.json | 85 | - |
| /darwin-x64-0.25.12.tgz | package-lock.json | 102 | - |
| /freebsd-arm64-0.25.12.tgz | package-lock.json | 119 | - |
| /freebsd-x64-0.25.12.tgz | package-lock.json | 136 | - |
| /linux-arm-0.25.12.tgz | package-lock.json | 153 | - |
| /linux-arm64-0.25.12.tgz | package-lock.json | 170 | - |
| /linux-ia32-0.25.12.tgz | package-lock.json | 187 | - |
| /linux-loong64-0.25.12.tgz | package-lock.json | 204 | - |
| /linux-mips64el-0.25.12.tgz | package-lock.json | 221 | - |
| /linux-ppc64-0.25.12.tgz | package-lock.json | 238 | - |
| /linux-riscv64-0.25.12.tgz | package-lock.json | 255 | - |
| /linux-s390x-0.25.12.tgz | package-lock.json | 272 | - |
| /linux-x64-0.25.12.tgz | package-lock.json | 289 | - |
| /netbsd-arm64-0.25.12.tgz | package-lock.json | 306 | - |
| /netbsd-x64-0.25.12.tgz | package-lock.json | 323 | - |
| /openbsd-arm64-0.25.12.tgz | package-lock.json | 340 | - |
| /openbsd-x64-0.25.12.tgz | package-lock.json | 357 | - |
| /openharmony-arm64-0.25.12.tgz | package-lock.json | 374 | - |
| /sunos-x64-0.25.12.tgz | package-lock.json | 391 | - |
| /win32-arm64-0.25.12.tgz | package-lock.json | 408 | - |
| /win32-ia32-0.25.12.tgz | package-lock.json | 425 | - |
| /win32-x64-0.25.12.tgz | package-lock.json | 442 | - |
| /rollup-android-arm-eabi-4.59.0.tgz | package-lock.json | 459 | - |
| /rollup-android-arm64-4.59.0.tgz | package-lock.json | 473 | - |
| /rollup-darwin-arm64-4.59.0.tgz | package-lock.json | 487 | - |
| /rollup-darwin-x64-4.59.0.tgz | package-lock.json | 501 | - |
| /rollup-freebsd-arm64-4.59.0.tgz | package-lock.json | 515 | - |
| /rollup-freebsd-x64-4.59.0.tgz | package-lock.json | 529 | - |
| /rollup-linux-arm-gnueabihf-4.59.0.tgz | package-lock.json | 543 | - |
| /rollup-linux-arm-musleabihf-4.59.0.tgz | package-lock.json | 557 | - |
| /rollup-linux-arm64-gnu-4.59.0.tgz | package-lock.json | 571 | - |
| /rollup-linux-arm64-musl-4.59.0.tgz | package-lock.json | 585 | - |
| /rollup-linux-loong64-gnu-4.59.0.tgz | package-lock.json | 599 | - |
| /rollup-linux-loong64-musl-4.59.0.tgz | package-lock.json | 613 | - |
| /rollup-linux-ppc64-gnu-4.59.0.tgz | package-lock.json | 627 | - |
| /rollup-linux-ppc64-musl-4.59.0.tgz | package-lock.json | 641 | - |
| /rollup-linux-riscv64-gnu-4.59.0.tgz | package-lock.json | 655 | - |
| /rollup-linux-riscv64-musl-4.59.0.tgz | package-lock.json | 669 | - |
| /rollup-linux-s390x-gnu-4.59.0.tgz | package-lock.json | 683 | - |
| /rollup-linux-x64-gnu-4.59.0.tgz | package-lock.json | 697 | - |
| /rollup-linux-x64-musl-4.59.0.tgz | package-lock.json | 711 | - |
| /rollup-openbsd-x64-4.59.0.tgz | package-lock.json | 725 | - |
| /rollup-openharmony-arm64-4.59.0.tgz | package-lock.json | 739 | - |
| /rollup-win32-arm64-msvc-4.59.0.tgz | package-lock.json | 753 | - |

*... and 26 more*


### Constant (14)

| Name | File | Line | Complexity |
|------|------|------|------------|
| CACHE_NAME | public/sw.js | 2 | - |
| PRECACHE_URLS | public/sw.js | 3 | - |
| DEFAULT_ALGORITHM | src/algorithms/loader.ts | 5 | - |
| PHASE_ANCHOR_RATIO | src/algorithms/loader.ts | 155 | - |
| DEFAULT_WHEEL_ARC | src/algorithms/loader.ts | 167 | - |
| DEFAULT_ALGORITHM_FILES | src/algorithms/loader.ts | 174 | - |
| DRAG_OWNER | src/cards/decision-cards.ts | 9 | - |
| DRAG_OWNER | src/navigation/zone-drag.ts | 10 | - |
| ADVANCE_THRESHOLD_RATIO | src/navigation/zone-drag.ts | 11 | - |
| REWIND_THRESHOLD_RATIO | src/navigation/zone-drag.ts | 12 | - |
| DECK | src/state/store.ts | 48 | - |
| DEFAULT_MESSAGES | src/ticker/rules.ts | 114 | - |
| FONT_SCALE | src/ui/menu.ts | 198 | - |
| NAV_THRESHOLD_DEG | src/wheel/physics.ts | 9 | - |

### Endpoint (3)

| Name | File | Line | Complexity |
|------|------|------|------------|
| GET /api/src/algorithms/loader.ts | src/algorithms/loader.ts | 389 | - |
| GET /api/src/main.ts | src/main.ts | 45 | - |
| GET /api/src/wheel/physics.ts | src/wheel/physics.ts | 61 | - |

### Export (2)

| Name | File | Line | Complexity |
|------|------|------|------------|
| angleOnArc | src/algorithms/loader.ts | 393 | - |
| resetTimerState | src/navigation/advance.ts | 103 | - |

### File (55)

| Name | File | Line | Complexity |
|------|------|------|------------|
| .DS_Store | - | - | - |
| .bpignore | - | - | - |
| .nojekyll | - | - | - |
| Resuscitation_App_Complete.html | Resuscitation_App_Complete.html | 1 | - |
| algo_anaphylaxis.json | algorithms/algo_anaphylaxis.json | 1 | - |
| algo_newborn_ls.json | algorithms/algo_newborn_ls.json | 1 | - |
| algo_paed_bls_in.json | algorithms/algo_paed_bls_in.json | 1 | - |
| algo_paed_bls_out.json | algorithms/algo_paed_bls_out.json | 1 | - |
| algo_paed_fbao.json | algorithms/algo_paed_fbao.json | 1 | - |
| index.json | algorithms/index.json | 1 | - |
| index.html | index.html | 1 | - |
| package-lock.json | package-lock.json | 1 | - |
| package.json | package.json | 1 | - |
| .DS_Store | - | - | - |
| sw.js | public/sw.js | 1 | - |
| .DS_Store | - | - | - |
| loader.ts | src/algorithms/loader.ts | 1 | - |
| automation.ts | src/automation.ts | 1 | - |
| checklist-card.ts | src/cards/checklist-card.ts | 1 | - |
| checklist.ts | src/cards/checklist.ts | 1 | - |
| decision-cards.ts | src/cards/decision-cards.ts | 1 | - |
| history-zone.ts | src/cards/history-zone.ts | 1 | - |
| preview-zone.ts | src/cards/preview-zone.ts | 1 | - |
| renderer.ts | src/cards/renderer.ts | 1 | - |
| main.ts | src/main.ts | 1 | - |
| advance.ts | src/navigation/advance.ts | 1 | - |
| anchors.ts | src/navigation/anchors.ts | 1 | - |
| zone-drag.ts | src/navigation/zone-drag.ts | 1 | - |
| register.ts | src/pwa/register.ts | 1 | - |
| decisions.ts | src/state/decisions.ts | 1 | - |
| store.ts | src/state/store.ts | 1 | - |
| cards.css | src/styles/cards.css | 1 | - |
| layout.css | src/styles/layout.css | 1 | - |
| menu.css | src/styles/menu.css | 1 | - |
| responsive.css | src/styles/responsive.css | 1 | - |
| stack.css | src/styles/stack.css | 1 | - |
| ticker.css | src/styles/ticker.css | 1 | - |
| tokens.css | src/styles/tokens.css | 1 | - |
| wheel.css | src/styles/wheel.css | 1 | - |
| engine.ts | src/ticker/engine.ts | 1 | - |
| rules.ts | src/ticker/rules.ts | 1 | - |
| types.ts | src/types.ts | 1 | - |
| drag-lock.ts | src/ui/drag-lock.ts | 1 | - |
| drag-overlay.ts | src/ui/drag-overlay.ts | 1 | - |
| haptic.ts | src/ui/haptic.ts | 1 | - |
| menu.ts | src/ui/menu.ts | 1 | - |
| modal.ts | src/ui/modal.ts | 1 | - |
| protocol-landing.ts | src/ui/protocol-landing.ts | 1 | - |
| timer.ts | src/ui/timer.ts | 1 | - |
| fsm.ts | src/wheel/fsm.ts | 1 | - |

*... and 5 more*


### Function (128)

| Name | File | Line | Complexity |
|------|------|------|------------|
| deepClone | src/algorithms/loader.ts | 182 | 1 |
| normalizeDegrees | src/algorithms/loader.ts | 186 | 3 |
| normalizeWheelArc | src/algorithms/loader.ts | 193 | 8 |
| angleOnArc | src/algorithms/loader.ts | 217 | 2 |
| inferPhase | src/algorithms/loader.ts | 227 | 12 |
| normalizeTransitions | src/algorithms/loader.ts | 244 | 22 |
| derivePositionDegrees | src/algorithms/loader.ts | 287 | 10 |
| normalizeAlgorithm | src/algorithms/loader.ts | 327 | 13 |
| sanitizeAlgorithmFile | src/algorithms/loader.ts | 358 | 4 |
| discoverAvailableAlgorithmFiles | src/algorithms/loader.ts | 365 | 7 |
| loadAlgorithmByFileName | src/algorithms/loader.ts | 381 | 3 |
| getDefaultAlgorithm | src/algorithms/loader.ts | 389 | 1 |
| summarizeTransition | src/automation.ts | 13 | 12 |
| snapshotForAutomation | src/automation.ts | 34 | 8 |
| setCurrentCardForAutomation | src/automation.ts | 65 | 3 |
| setupWardenAutomation | src/automation.ts | 99 | 13 |
| hasChecklistItems | src/cards/checklist-card.ts | 7 | 2 |
| renderChecklistCardContent | src/cards/checklist-card.ts | 11 | 6 |
| evaluateVisibility | src/cards/checklist-card.ts | 40 | 2 |
| renderChecklist | src/cards/checklist.ts | 6 | 7 |
| evaluateVisibility | src/cards/checklist.ts | 38 | 2 |
| handleCheckChange | src/cards/checklist.ts | 51 | 2 |
| setupDecisionDrag | src/cards/decision-cards.ts | 16 | 1 |
| removeDecisionDragListeners | src/cards/decision-cards.ts | 25 | 1 |
| cleanupDecisionDragVisuals | src/cards/decision-cards.ts | 34 | 2 |
| resetDecisionDragState | src/cards/decision-cards.ts | 42 | 1 |
| cancelDecisionDrag | src/cards/decision-cards.ts | 49 | 2 |
| startDecisionDrag | src/cards/decision-cards.ts | 57 | 7 |
| onDecisionDrag | src/cards/decision-cards.ts | 92 | 5 |
| endDecisionDrag | src/cards/decision-cards.ts | 110 | 5 |
| renderHistoryZone | src/cards/history-zone.ts | 5 | 2 |
| _setRenderFn | src/cards/preview-zone.ts | 10 | 1 |
| renderPreviewZone | src/cards/preview-zone.ts | 14 | 13 |
| selectDecisionOption | src/cards/preview-zone.ts | 98 | 3 |
| getUpcomingCardsFrom | src/cards/preview-zone.ts | 106 | 8 |
| getUpcomingCards | src/cards/preview-zone.ts | 129 | 6 |
| render | src/cards/renderer.ts | 14 | 2 |
| renderActiveCard | src/cards/renderer.ts | 38 | 14 |
| getCardBodyContent | src/cards/renderer.ts | 97 | 11 |
| renderCarouselDots | src/cards/renderer.ts | 110 | 3 |
| getDom | src/main.ts | 45 | 2 |
| syncHeaderFromAlgorithm | src/main.ts | 63 | 5 |
| applyAlgorithm | src/main.ts | 72 | 8 |
| initAlgorithmFromUrl | src/main.ts | 118 | 7 |
| init | src/main.ts | 149 | 12 |
| advance | src/navigation/advance.ts | 9 | 29 |
| rewind | src/navigation/advance.ts | 77 | 3 |
| canTapAdvance | src/navigation/advance.ts | 97 | 4 |
| getCurrentWheelArc | src/navigation/anchors.ts | 6 | 3 |
| angleOnArc | src/navigation/anchors.ts | 13 | 4 |

*... and 78 more*


### Import (111)

| Name | File | Line | Complexity |
|------|------|------|------------|
| /src/main.ts | index.html | 80 | - |
| manifest.webmanifest | index.html | 7 | - |
| ../types | src/algorithms/loader.ts | 2 | - |
| ./main | src/automation.ts | 11 | - |
| ./algorithms/loader | src/automation.ts | 10 | - |
| ./cards/renderer | src/automation.ts | 9 | - |
| ./navigation/advance | src/automation.ts | 8 | - |
| ./navigation/anchors | src/automation.ts | 7 | - |
| ./wheel/physics | src/automation.ts | 6 | - |
| ./wheel/fsm | src/automation.ts | 5 | - |
| ./state/decisions | src/automation.ts | 4 | - |
| ./state/store | src/automation.ts | 3 | - |
| ./types | src/automation.ts | 2 | - |
| ../state/store | src/cards/checklist-card.ts | 5 | - |
| ../types | src/cards/checklist-card.ts | 4 | - |
| ../main | src/cards/checklist.ts | 4 | - |
| ../state/store | src/cards/checklist.ts | 3 | - |
| ../types | src/cards/checklist.ts | 2 | - |
| ../ui/drag-lock | src/cards/decision-cards.ts | 7 | - |
| ../ui/drag-overlay | src/cards/decision-cards.ts | 6 | - |
| ../navigation/advance | src/cards/decision-cards.ts | 4 | - |
| ../main | src/cards/decision-cards.ts | 3 | - |
| ../state/store | src/cards/decision-cards.ts | 2 | - |
| ../main | src/cards/history-zone.ts | 3 | - |
| ../state/store | src/cards/history-zone.ts | 2 | - |
| ../state/decisions | src/cards/preview-zone.ts | 6 | - |
| ./decision-cards | src/cards/preview-zone.ts | 5 | - |
| ../main | src/cards/preview-zone.ts | 4 | - |
| ../state/store | src/cards/preview-zone.ts | 3 | - |
| ../types | src/cards/preview-zone.ts | 2 | - |
| ../ticker/engine | src/cards/renderer.ts | 12 | - |
| ../ui/modal | src/cards/renderer.ts | 11 | - |
| ./checklist | src/cards/renderer.ts | 10 | - |
| ./history-zone | src/cards/renderer.ts | 9 | - |
| ./preview-zone | src/cards/renderer.ts | 8 | - |
| ../main | src/cards/renderer.ts | 7 | - |
| ../navigation/anchors | src/cards/renderer.ts | 6 | - |
| ../wheel/physics | src/cards/renderer.ts | 5 | - |
| ../wheel/fsm | src/cards/renderer.ts | 4 | - |
| ../state/store | src/cards/renderer.ts | 3 | - |
| ../types | src/cards/renderer.ts | 2 | - |
| ./pwa/register | src/main.ts | 28 | - |
| ./ui/menu | src/main.ts | 27 | - |
| ./ticker/engine | src/main.ts | 26 | - |
| ./automation | src/main.ts | 25 | - |
| ./cards/preview-zone | src/main.ts | 24 | - |
| ./cards/renderer | src/main.ts | 23 | - |
| ./ui/modal | src/main.ts | 22 | - |
| ./ui/timer | src/main.ts | 21 | - |
| ./navigation/advance | src/main.ts | 20 | - |

*... and 61 more*


### Interface (28)

| Name | File | Line | Complexity |
|------|------|------|------------|
| DomRefs | src/main.ts | 31 | 1 |
| DragState | src/navigation/zone-drag.ts | 14 | 1 |
| TickerMessage | src/ticker/rules.ts | 5 | 1 |
| ChecklistItem | src/types.ts | 3 | 1 |
| Slide | src/types.ts | 10 | 1 |
| CardContent | src/types.ts | 17 | 1 |
| ToolboxItem | src/types.ts | 25 | 1 |
| TransitionOption | src/types.ts | 32 | 1 |
| LinearTransition | src/types.ts | 39 | 1 |
| SplitTransition | src/types.ts | 44 | 1 |
| SelfLoopTransition | src/types.ts | 49 | 1 |
| WheelConfig | src/types.ts | 56 | 1 |
| Card | src/types.ts | 62 | 1 |
| WheelArc | src/types.ts | 79 | 1 |
| AlgorithmMeta | src/types.ts | 86 | 1 |
| Algorithm | src/types.ts | 101 | 1 |
| Anchor | src/types.ts | 108 | 1 |
| HistoryEntry | src/types.ts | 114 | 1 |
| WheelState | src/types.ts | 119 | 1 |
| AppState | src/types.ts | 127 | 1 |
| DecisionTrailEntry | src/types.ts | 146 | 1 |
| AdvanceOptions | src/types.ts | 156 | 1 |
| CardSnapshot | src/types.ts | 162 | 1 |
| TransitionSummary | src/types.ts | 172 | 1 |
| TransitionOptionSummary | src/types.ts | 178 | 1 |
| AutomationSnapshot | src/types.ts | 186 | 1 |
| DragOverlayOptions | src/ui/drag-overlay.ts | 4 | 1 |
| DragOverlaySession | src/ui/drag-overlay.ts | 10 | 1 |

### Network_Request (3)

| Name | File | Line | Complexity |
|------|------|------|------------|
| GET algorithms/index.json | src/algorithms/loader.ts | 367 | - |
| GET algorithms/${safe} | src/algorithms/loader.ts | 384 | - |
| GET algorithms/index.json | src/ui/menu.ts | 96 | - |

### Table (10)

| Name | File | Line | Complexity |
|------|------|------|------------|
| Blueprint | .bpignore | 1 | - |
| your | Resuscitation_App_Complete.html | 516 | - |
| a | Resuscitation_App_Complete.html | 939 | - |
| visibility | Resuscitation_App_Complete.html | 1118 | - |
| anterolateral | algorithms/algo_anaphylaxis.json | 283 | - |
| parents | algorithms/algo_newborn_ls.json | 800 | - |
| signs | algorithms/algo_paed_fbao.json | 318 | - |
| closing | src/main.ts | 212 | - |
| active | src/ui/menu.ts | 174 | - |
| of | src/ui/protocol-landing.ts | 3 | - |

### Type_Alias (5)

| Name | File | Line | Complexity |
|------|------|------|------------|
| AlgorithmMetaLike | src/algorithms/loader.ts | 215 | - |
| Transition | src/types.ts | 54 | - |
| WheelMode | src/types.ts | 106 | - |
| DeckMap | src/types.ts | 207 | - |
| DragCancelFn | src/ui/drag-lock.ts | 4 | - |

### Variable (1143)

| Name | File | Line | Complexity |
|------|------|------|------------|
| #app | Resuscitation_App_Complete.html | 450 | - |
| #stage | Resuscitation_App_Complete.html | 465 | - |
| #zone-top | Resuscitation_App_Complete.html | 466 | - |
| #zone-middle | Resuscitation_App_Complete.html | 467 | - |
| #wheel | Resuscitation_App_Complete.html | 468 | - |
| #active-card | Resuscitation_App_Complete.html | 469 | - |
| #knob | Resuscitation_App_Complete.html | 470 | - |
| #zone-bottom | Resuscitation_App_Complete.html | 472 | - |
| #checklist-area | Resuscitation_App_Complete.html | 479 | - |
| #timer | Resuscitation_App_Complete.html | 481 | - |
| #modal-overlay | Resuscitation_App_Complete.html | 486 | - |
| #icon-fullscreen | Resuscitation_App_Complete.html | 499 | - |
| #icon-toolbox | Resuscitation_App_Complete.html | 502 | - |
| #icon-decision | Resuscitation_App_Complete.html | 507 | - |
| algorithm_meta | algorithms/algo_anaphylaxis.json | 1 | - |
| id | algorithms/algo_anaphylaxis.json | 1 | - |
| title | algorithms/algo_anaphylaxis.json | 1 | - |
| subtitle | algorithms/algo_anaphylaxis.json | 1 | - |
| source | algorithms/algo_anaphylaxis.json | 1 | - |
| context | algorithms/algo_anaphylaxis.json | 1 | - |
| version | algorithms/algo_anaphylaxis.json | 1 | - |
| page_ref | algorithms/algo_anaphylaxis.json | 1 | - |
| color_theme | algorithms/algo_anaphylaxis.json | 1 | - |
| primary | algorithms/algo_anaphylaxis.json | 1 | - |
| decision | algorithms/algo_anaphylaxis.json | 1 | - |
| action | algorithms/algo_anaphylaxis.json | 1 | - |
| terminal | algorithms/algo_anaphylaxis.json | 1 | - |
| warning | algorithms/algo_anaphylaxis.json | 1 | - |
| global_timer | algorithms/algo_anaphylaxis.json | 1 | - |
| enabled | algorithms/algo_anaphylaxis.json | 1 | - |
| label | algorithms/algo_anaphylaxis.json | 1 | - |
| type | algorithms/algo_anaphylaxis.json | 1 | - |
| auto_start_on_card | algorithms/algo_anaphylaxis.json | 1 | - |
| header_reference | algorithms/algo_anaphylaxis.json | 1 | - |
| type | algorithms/algo_anaphylaxis.json | 1 | - |
| items | algorithms/algo_anaphylaxis.json | 1 | - |
| reference_panels | algorithms/algo_anaphylaxis.json | 1 | - |
| panels | algorithms/algo_anaphylaxis.json | 1 | - |
| linked_algorithms | algorithms/algo_anaphylaxis.json | 1 | - |
| deck | algorithms/algo_anaphylaxis.json | 1 | - |
| algorithm_meta | algorithms/algo_newborn_ls.json | 1 | - |
| id | algorithms/algo_newborn_ls.json | 1 | - |
| title | algorithms/algo_newborn_ls.json | 1 | - |
| subtitle | algorithms/algo_newborn_ls.json | 1 | - |
| source | algorithms/algo_newborn_ls.json | 1 | - |
| context | algorithms/algo_newborn_ls.json | 1 | - |
| version | algorithms/algo_newborn_ls.json | 1 | - |
| page_ref | algorithms/algo_newborn_ls.json | 1 | - |
| color_theme | algorithms/algo_newborn_ls.json | 1 | - |
| primary | algorithms/algo_newborn_ls.json | 1 | - |

*... and 1093 more*


## Complexity Hotspots

| Entity | File | CC | LOC |
|--------|------|----|-----|
| advance | src/navigation/advance.ts | 29 | 60 |
| normalizeTransitions | src/algorithms/loader.ts | 22 | 36 |
| showSettings | src/ui/menu.ts | 16 | 43 |
| renderActiveCard | src/cards/renderer.ts | 14 | 44 |
| normalizeAlgorithm | src/algorithms/loader.ts | 13 | 27 |
| setupWardenAutomation | src/automation.ts | 13 | 94 |
| renderPreviewZone | src/cards/preview-zone.ts | 13 | 67 |
| inferPhase | src/algorithms/loader.ts | 12 | 15 |
| summarizeTransition | src/automation.ts | 12 | 18 |
| init | src/main.ts | 12 | 47 |
| checkStepsRemaining | src/ticker/rules.ts | 12 | 23 |
| onKnobDrag | src/wheel/knob.ts | 12 | 56 |
| getCardBodyContent | src/cards/renderer.ts | 11 | 12 |
| computeForwardPath | src/navigation/anchors.ts | 11 | 29 |
| derivePositionDegrees | src/algorithms/loader.ts | 10 | 35 |
| countPathLength | src/navigation/anchors.ts | 10 | 22 |
| longestBranchTarget | src/navigation/anchors.ts | 10 | 15 |
| handleDecisionWheelDrag | src/wheel/knob.ts | 9 | 23 |
| normalizeWheelArc | src/algorithms/loader.ts | 8 | 20 |
| snapshotForAutomation | src/automation.ts | 8 | 30 |
