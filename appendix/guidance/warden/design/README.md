# Warden Design Method

This folder is the design-analysis bridge between:
1. Blueprint runs in `appendix/guidance/warden/blueprint_outputs/runs/*`
2. Scan runs in `appendix/guidance/warden/scans_outputs/runs/*`
3. Runtime screenshots/splits captured from the local app

## Primary Tool
Run:

```bash
npm run warden:design:bundle
```

Explicit run pair:

```bash
npm run warden:design:bundle -- \
  --blueprint-run <blueprint-run-id> \
  --scan-run <scan-run-id> \
  --mode main
```

Mobile portrait baseline capture:

```bash
npm run warden:design:bundle -- --mode main --viewport 390x844
```

## What It Does
1. Resolves Blueprint and Scan runs (latest by default).
2. Creates a bundle under `appendix/guidance/warden/design/runs/<timestamp>__bp-...__scan-.../`.
3. Links source runs into `linked/`.
4. Starts local app on `http://127.0.0.1:3000` if needed.
5. Captures static screenshots for baseline composition.
6. Captures dynamic transition screenshots for the main decision flow.
7. Creates static and dynamic split crops (region-level evidence).
8. Writes machine and human summaries:
- `bundle_manifest.json`
- `bundle_summary.md`

## Artifact Layout
1. Static screenshots: `screenshots/static/main/`
2. Dynamic screenshots: `screenshots/dynamic/main/`
3. Static splits: `splits/static/main/<page>-<viewport>/`
4. Dynamic splits: `splits/dynamic/main/<transition>-<viewport>/`
5. Region maps: `splits/*/main/*/regions_map.json`

## Reliability Flags

```bash
npm run warden:design:bundle -- \
  --capture-attempts 4 \
  --stabilize-ms 2600 \
  --warmup-rounds 3 \
  --dynamic-max-transitions 120
```

## Current Pointer
`current_bundle.json` always points to the latest bundle in this folder.
