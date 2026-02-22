# Dual Run Modes

This project now supports a dual execution model:

- `warden` lane: assistant-operated workflow space
- `system` lane: traditional project workflow space

Each lane supports two Blueprint input sources:

- `local` (analyze local `app` files)
- `github` (analyze a GitHub repo via Blueprint workspace target)

## Matrix Commands

Use these `npm` commands:

- `npm run analyze:warden:local`
- `npm run analyze:warden:github -- --repo owner/repo`
- `npm run analyze:system:local`
- `npm run analyze:system:github -- --repo owner/repo`

Optional GitHub flags:

- `--ref main`
- `--token-env GITHUB_TOKEN` (for private repos)

## Output Spaces

Warden lane outputs:

- Blueprint: `appendix/guidance/warden/blueprint_outputs`
- Scan: `appendix/guidance/warden/scans_outputs`
- Design bundle: `appendix/guidance/warden/design`

System lane outputs:

- Blueprint: `appendix/system/blueprint_outputs`
- Scan: `appendix/system/scans_outputs`
- Design bundle: `appendix/system/design`

## Notes

- For `--source github`, the pipeline defaults to Blueprint-only.
- Add `--include-ui-stages` if you also want scan/design against a running UI base URL.
- Certificate defaults:
  - `warden` lane: enabled
  - `system` lane: skipped
