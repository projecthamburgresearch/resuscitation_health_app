# Warden Design Bundle

Generated: 2026-02-22T00:44:22.318Z

## Linked Runs

- Blueprint run: `appendix/blueprint_outputs/runs/20260221-190758-warden`
- Scan run: `appendix/scans_outputs/runs/20260221-190802`

## Capture Controls

- Base URL: `http://127.0.0.1:3000`
- Mode: `main`
- Pages: home
- Viewports: 1440x900
- Capture attempts per page: 1
- Stabilize wait: 1800 ms
- Warmup rounds: 2
- Dev server started by script: false
- Dynamic main transitions: enabled
- Dynamic transition cap: 40
- Dynamic settle wait: 220 ms

## Screenshot Results

- Static screenshots: 1 ok, 0 failed
- Dynamic transition screenshots: 13 ok, 0 failed
- Total screenshots: 14

## Split Results

- Static split bundles: 1
- Static split crops: 3 extracted, 0 failed
- Dynamic split bundles: 13
- Dynamic split crops: 39 extracted, 0 failed
- Total split bundles: 14
- Total split crops: 42 extracted, 0 failed

## Coverage Snapshot (from scan output)

- Scans: 1
- Total scanned elements: 28
- Scanned ratio of includeable: 1
- Scanned ratio of unique: 0.778

## Blueprint Snapshot (from run_meta)

- Source path: `/Users/mordecaimachazire/Documents/local-projects/resuscitation_health_app/app`
- Files scanned: 4
- Entities found: 39
- Edges found: 35
- Domains: xray, manifest, cortex, registry, sonar, synapse

## Screenshot Index

| Category | Mode | Page | Viewport | Status | Attempts | Transition | File |
|---|---|---|---|---|---|---|---|
| static | main | home | 1440x900 | ok | 1 | - | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/static/main/home-main-1440x900.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_00_START -> CARD_01_UNRESPONSIVE | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-001-card-00-start-to-card-01-unresponsive.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_01_UNRESPONSIVE -> CARD_02_SHOUT | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-002-card-01-unresponsive-to-card-02-shout.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_02_SHOUT -> CARD_03_AIRWAY | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-003-card-02-shout-to-card-03-airway.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_03_AIRWAY -> CARD_04_BREATHING_DECISION | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-004-card-03-airway-to-card-04-breathing-decision.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_04_BREATHING_DECISION -> CARD_END_OBSERVE (YES) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-005-card-04-breathing-decision-to-card-end-observe-opt-1-yes.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_04_BREATHING_DECISION -> CARD_05_BREATHS (NO) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-006-card-04-breathing-decision-to-card-05-breaths-opt-2-no.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_05_BREATHS -> CARD_06_CHECK_LIFE_PRE_CPR | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-007-card-05-breaths-to-card-06-check-life-pre-cpr.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_06_CHECK_LIFE_PRE_CPR -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-008-card-06-check-life-pre-cpr-to-card-end-recovery-opt-1-yes.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_06_CHECK_LIFE_PRE_CPR -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-009-card-06-check-life-pre-cpr-to-card-07-compressions-opt-2-no.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_07_COMPRESSIONS -> CARD_08_LOOP_BREATHS | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-010-card-07-compressions-to-card-08-loop-breaths.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_08_LOOP_BREATHS -> CARD_09_LOOP_CHECK | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-011-card-08-loop-breaths-to-card-09-loop-check.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_09_LOOP_CHECK -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-012-card-09-loop-check-to-card-07-compressions-opt-1-no.png` |
| dynamic | main | home | 1440x900 | ok | 1 | CARD_09_LOOP_CHECK -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/screenshots/dynamic/main/home-main-1440x900-edge-013-card-09-loop-check-to-card-end-recovery-opt-2-yes.png` |

## Split Index

| Category | Page | Viewport | Status | Transition | Map | Extracted | Failed |
|---|---|---|---|---|---|---|---|
| static | home | 1440x900 | ok | - | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/static/main/home-1440x900/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_00_START -> CARD_01_UNRESPONSIVE | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-001-card-00-start-to-card-01-unresponsive/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_01_UNRESPONSIVE -> CARD_02_SHOUT | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-002-card-01-unresponsive-to-card-02-shout/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_02_SHOUT -> CARD_03_AIRWAY | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-003-card-02-shout-to-card-03-airway/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_03_AIRWAY -> CARD_04_BREATHING_DECISION | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-004-card-03-airway-to-card-04-breathing-decision/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_04_BREATHING_DECISION -> CARD_END_OBSERVE (YES) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-005-card-04-breathing-decision-to-card-end-observe-opt-1-yes/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_04_BREATHING_DECISION -> CARD_05_BREATHS (NO) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-006-card-04-breathing-decision-to-card-05-breaths-opt-2-no/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_05_BREATHS -> CARD_06_CHECK_LIFE_PRE_CPR | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-007-card-05-breaths-to-card-06-check-life-pre-cpr/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_06_CHECK_LIFE_PRE_CPR -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-008-card-06-check-life-pre-cpr-to-card-end-recovery-opt-1-yes/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_06_CHECK_LIFE_PRE_CPR -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-009-card-06-check-life-pre-cpr-to-card-07-compressions-opt-2-no/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_07_COMPRESSIONS -> CARD_08_LOOP_BREATHS | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-010-card-07-compressions-to-card-08-loop-breaths/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_08_LOOP_BREATHS -> CARD_09_LOOP_CHECK | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-011-card-08-loop-breaths-to-card-09-loop-check/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_09_LOOP_CHECK -> CARD_07_COMPRESSIONS (NO) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-012-card-09-loop-check-to-card-07-compressions-opt-1-no/regions_map.json` | 3 | 0 |
| dynamic | home | 1440x900 | ok | CARD_09_LOOP_CHECK -> CARD_END_RECOVERY (YES) | `appendix/guidance/warden/design/runs/20260221-194404__bp-20260221-190758-warden__scan-20260221-190802/splits/dynamic/main/home-1440x900-edge-013-card-09-loop-check-to-card-end-recovery-opt-2-yes/regions_map.json` | 3 | 0 |

