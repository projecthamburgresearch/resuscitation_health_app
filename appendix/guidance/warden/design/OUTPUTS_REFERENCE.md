# Blueprint + Scan + Screenshot Output Reference

## 1) Blueprint Run Output (`appendix/guidance/warden/blueprint_outputs/runs/<run>/`)
Blueprint gives static/system-level evidence from app source.

Key files:
- `xray_result.json`
- `llm_context.json`
- `manifest.yaml`
- `sonar_report.json`
- `synapse_report.json`
- `run_meta.json`

Best use:
- identify code ownership and impact risk before edits
- map shared dependencies and hotspot areas

## 2) Scan Run Output (`appendix/guidance/warden/scans_outputs/runs/<run>/`)
Scan gives runtime telemetry from rendered app output.

Key files:
- `home-scan.json`
- `run_manifest.json`
- `scan-coverage-report.json`
- optional `*-diff.json`

Best use:
- verify actual runtime geometry/typography/contrast
- quantify before/after deltas

## 3) Warden Design Bundle (`appendix/guidance/warden/design/runs/<bundle>/`)
This combines Blueprint + Scan + screenshot truth.

Key files and folders:
- `linked/blueprint_run`
- `linked/scan_run`
- `screenshots/static/main/*.png`
- `screenshots/dynamic/main/*.png`
- `splits/static/main/<page>-<viewport>/images/*.png`
- `splits/dynamic/main/<transition>-<viewport>/images/*.png`
- `splits/*/main/*/regions_map.json`
- `bundle_manifest.json`
- `bundle_summary.md`

Best use:
- evaluate dynamic transition fidelity and static layout baseline together
- reduce ambiguity before implementation
- support validation reruns with traceable evidence

## Practical Collaboration Loop
1. Build evidence:
- `npm run analyze:warden:local`
2. Investigate:
- dynamic screenshots/splits first
- static screenshots/splits second
- scan metrics and blueprint impact mapping
3. Implement and verify:
- code changes
- rerun analysis
- compare `bundle_summary.md` + artifacts + telemetry deltas
