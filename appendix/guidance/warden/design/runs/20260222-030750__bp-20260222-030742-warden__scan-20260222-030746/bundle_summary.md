# Warden Design Bundle

Generated: 2026-02-22T08:08:24.103Z

## Linked Runs

- Blueprint run: `appendix/guidance/warden/blueprint_outputs/runs/20260222-030742-warden`
- Scan run: `appendix/guidance/warden/scans_outputs/runs/20260222-030746`

## Capture Controls

- Base URL: `http://127.0.0.1:3000`
- Mode: `main`
- Pages: home
- Viewports: 390x844
- Capture attempts per page: 3
- Stabilize wait: 1800 ms
- Warmup rounds: 2
- Dev server started by script: false
- Dynamic main transitions: enabled
- Dynamic transition cap: 80
- Dynamic settle wait: 220 ms

## Screenshot Results

- Static screenshots: 1 ok, 0 failed
- Dynamic transition screenshots: 26 ok, 0 failed
- Total screenshots: 27

## Split Results

- Static split bundles: 1
- Static split crops: 11 extracted, 0 failed
- Dynamic split bundles: 26
- Dynamic split crops: 286 extracted, 0 failed
- Total split bundles: 27
- Total split crops: 297 extracted, 0 failed

## Coverage Snapshot (from scan output)

- Scans: 1
- Total scanned elements: 27
- Scanned ratio of includeable: 1
- Scanned ratio of unique: 0.75

## Blueprint Snapshot (from run_meta)

- Source path: `/Users/mordecaimachazire/Documents/local-projects/resuscitation_health_app/app`
- Files scanned: 10
- Entities found: 171
- Edges found: 269
- Domains: xray, manifest, cortex, registry, sonar, synapse

## Screenshot Index

| Category | Stage | Mode | Page | Viewport | Status | Attempts | Transition | File |
|---|---|---|---|---|---|---|---|---|
| static | static | main | home | 390x844 | ok | 1 | - | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/static/main/home-main-390x844.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_00_START -> CARD_01_UNRESPONSIVE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-001-card-00-start-to-card-01-unresponsive-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_00_START -> CARD_01_UNRESPONSIVE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-001-card-00-start-to-card-01-unresponsive-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_01_UNRESPONSIVE -> CARD_02_SHOUT | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-002-card-01-unresponsive-to-card-02-shout-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_01_UNRESPONSIVE -> CARD_02_SHOUT | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-002-card-01-unresponsive-to-card-02-shout-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_02_SHOUT -> CARD_03_AIRWAY | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-003-card-02-shout-to-card-03-airway-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_02_SHOUT -> CARD_03_AIRWAY | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-003-card-02-shout-to-card-03-airway-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_03_AIRWAY -> CARD_04_BREATHING | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-004-card-03-airway-to-card-04-breathing-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_03_AIRWAY -> CARD_04_BREATHING | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-004-card-03-airway-to-card-04-breathing-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_04_BREATHING -> CARD_END_OBSERVE (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-005-card-04-breathing-to-card-end-observe-opt-1-yes-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_04_BREATHING -> CARD_END_OBSERVE (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-005-card-04-breathing-to-card-end-observe-opt-1-yes-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_04_BREATHING -> CARD_05_BREATHS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-006-card-04-breathing-to-card-05-breaths-opt-2-no-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_04_BREATHING -> CARD_05_BREATHS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-006-card-04-breathing-to-card-05-breaths-opt-2-no-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_05_BREATHS -> CARD_06_SIGNS_OF_LIFE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-007-card-05-breaths-to-card-06-signs-of-life-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_05_BREATHS -> CARD_06_SIGNS_OF_LIFE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-007-card-05-breaths-to-card-06-signs-of-life-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_06_SIGNS_OF_LIFE -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-008-card-06-signs-of-life-to-card-end-recovery-opt-1-yes-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_06_SIGNS_OF_LIFE -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-008-card-06-signs-of-life-to-card-end-recovery-opt-1-yes-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_06_SIGNS_OF_LIFE -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-009-card-06-signs-of-life-to-card-07-compressions-opt-2-no-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_06_SIGNS_OF_LIFE -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-009-card-06-signs-of-life-to-card-07-compressions-opt-2-no-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_07_COMPRESSIONS -> CARD_08_LOOP_BREATHS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-010-card-07-compressions-to-card-08-loop-breaths-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_07_COMPRESSIONS -> CARD_08_LOOP_BREATHS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-010-card-07-compressions-to-card-08-loop-breaths-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_08_LOOP_BREATHS -> CARD_09_REASSESS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-011-card-08-loop-breaths-to-card-09-reassess-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_08_LOOP_BREATHS -> CARD_09_REASSESS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-011-card-08-loop-breaths-to-card-09-reassess-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_09_REASSESS -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-012-card-09-reassess-to-card-07-compressions-opt-1-no-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_09_REASSESS -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-012-card-09-reassess-to-card-07-compressions-opt-1-no-after.png` |
| dynamic | before | main | home | 390x844 | ok | 1 | CARD_09_REASSESS -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-013-card-09-reassess-to-card-end-recovery-opt-2-yes-before.png` |
| dynamic | after | main | home | 390x844 | ok | 1 | CARD_09_REASSESS -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/screenshots/dynamic/main/home-main-390x844-edge-013-card-09-reassess-to-card-end-recovery-opt-2-yes-after.png` |

## Split Index

| Category | Stage | Page | Viewport | Status | Transition | Map | Extracted | Failed |
|---|---|---|---|---|---|---|---|---|
| static | static | home | 390x844 | ok | - | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/static/main/home-390x844/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_00_START -> CARD_01_UNRESPONSIVE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-001-card-00-start-to-card-01-unresponsive-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_00_START -> CARD_01_UNRESPONSIVE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-001-card-00-start-to-card-01-unresponsive-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_01_UNRESPONSIVE -> CARD_02_SHOUT | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-002-card-01-unresponsive-to-card-02-shout-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_01_UNRESPONSIVE -> CARD_02_SHOUT | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-002-card-01-unresponsive-to-card-02-shout-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_02_SHOUT -> CARD_03_AIRWAY | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-003-card-02-shout-to-card-03-airway-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_02_SHOUT -> CARD_03_AIRWAY | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-003-card-02-shout-to-card-03-airway-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_03_AIRWAY -> CARD_04_BREATHING | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-004-card-03-airway-to-card-04-breathing-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_03_AIRWAY -> CARD_04_BREATHING | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-004-card-03-airway-to-card-04-breathing-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_04_BREATHING -> CARD_END_OBSERVE (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-005-card-04-breathing-to-card-end-observe-opt-1-yes-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_04_BREATHING -> CARD_END_OBSERVE (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-005-card-04-breathing-to-card-end-observe-opt-1-yes-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_04_BREATHING -> CARD_05_BREATHS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-006-card-04-breathing-to-card-05-breaths-opt-2-no-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_04_BREATHING -> CARD_05_BREATHS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-006-card-04-breathing-to-card-05-breaths-opt-2-no-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_05_BREATHS -> CARD_06_SIGNS_OF_LIFE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-007-card-05-breaths-to-card-06-signs-of-life-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_05_BREATHS -> CARD_06_SIGNS_OF_LIFE | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-007-card-05-breaths-to-card-06-signs-of-life-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_06_SIGNS_OF_LIFE -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-008-card-06-signs-of-life-to-card-end-recovery-opt-1-yes-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_06_SIGNS_OF_LIFE -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-008-card-06-signs-of-life-to-card-end-recovery-opt-1-yes-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_06_SIGNS_OF_LIFE -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-009-card-06-signs-of-life-to-card-07-compressions-opt-2-no-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_06_SIGNS_OF_LIFE -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-009-card-06-signs-of-life-to-card-07-compressions-opt-2-no-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_07_COMPRESSIONS -> CARD_08_LOOP_BREATHS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-010-card-07-compressions-to-card-08-loop-breaths-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_07_COMPRESSIONS -> CARD_08_LOOP_BREATHS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-010-card-07-compressions-to-card-08-loop-breaths-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_08_LOOP_BREATHS -> CARD_09_REASSESS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-011-card-08-loop-breaths-to-card-09-reassess-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_08_LOOP_BREATHS -> CARD_09_REASSESS | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-011-card-08-loop-breaths-to-card-09-reassess-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_09_REASSESS -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-012-card-09-reassess-to-card-07-compressions-opt-1-no-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_09_REASSESS -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-012-card-09-reassess-to-card-07-compressions-opt-1-no-after/regions_map.json` | 11 | 0 |
| dynamic | before | home | 390x844 | ok | CARD_09_REASSESS -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-013-card-09-reassess-to-card-end-recovery-opt-2-yes-before/regions_map.json` | 11 | 0 |
| dynamic | after | home | 390x844 | ok | CARD_09_REASSESS -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260222-030750__bp-20260222-030742-warden__scan-20260222-030746/splits/dynamic/main/home-390x844-edge-013-card-09-reassess-to-card-end-recovery-opt-2-yes-after/regions_map.json` | 11 | 0 |

