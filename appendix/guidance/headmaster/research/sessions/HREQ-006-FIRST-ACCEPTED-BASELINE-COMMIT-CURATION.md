# Research Session: HREQ-006-FIRST-ACCEPTED-BASELINE-COMMIT-CURATION

- date: 2026-03-13
- role: headmaster
- ticket_ref: HREQ-006-FIRST-ACCEPTED-BASELINE-COMMIT-CURATION

## Objective
Define the first accepted baseline commit boundary for the upgraded authority stack.

## 1. Commit Classification

### A. Core Authority Stack (STAGED)
These files represent the permanent upgraded project governance and continuity layer.
- `appendix/guidance/headmaster/`
- `appendix/guidance/warden/`
- `appendix/guidance/switchboard/`
- `appendix/guidance/exit/`
- `appendix/guidance/README.md`
- `appendix/guidance/PROTOCOL.md` (if exists)
- `README.md` (root)
- `.gitignore` (root)
- `package.json` (root)

### B. Project Tooling & Scripts (STAGED)
Automation and support scripts for the upgraded stack.
- `scripts/exit/`
- `scripts/integrations/`
- `scripts/switchboard/`
- All modified scripts: `scripts/run_unified_analysis.js`, `scripts/scan.js`, `scripts/test_behavior.js`, `scripts/warden_design_bundle.js`.

### C. Clinical Content & Algorithm Normalization (STAGED)
Accepted clinical data changes and the new algorithm source rules.
- `app/algorithms/README.md`
- `prototype/json-algorithms/README.md`
- `prototype/json-algorithms/algo_paed_bls_in.json`
- `prototype/json-algorithms/algo_paed_bls_out.json`
- `prototype/json-algorithms/index.json`

### D. Preserved Legacy & Reference (STAGED)
Relocated roots kept for provenance.
- `appendix/guidance/materials/legacy/`
- `appendix/css-web-ui-demos/`

### E. Integration Surface (STAGED)
- `integrations/access/`

### F. Defer / Ignore (NOT STAGED)
- `.DS_Store` files.
- `.specstory/history/` modifications (unless specifically requested).
- Any ephemeral logs in `appendix/guidance/exit/logs/` that are not the canonical re-entry log.

## 2. Implementation Plan: REQ-016-BASELINE-COMMIT-EXECUTION

The execution of this commit should be handled by a Warden lane to ensure staging integrity.

### Step 1: Clean Up .DS_Store
Remove all `.DS_Store` files from the repo to prevent them from entering the baseline.

### Step 2: Curation Staging
Use `git add` on the classified buckets.

### Step 3: Baseline Commit
Execute the commit with a message reflecting the authority upgrade:
`feat: upgrade authority stack to Headmaster/Warden/Switchboard/Exit`

## 3. Findings
- **Baseline Readiness:** The repo is structurally sound. The "tap-before-confirm" behavior is validated and clinical algorithms are synchronized.
- **Gitignore Success:** The tighter `.gitignore` correctly prevents large ephemeral bulk from entering the staging area.

## Next Steps
1. **Close HREQ-006:** Submit the curation plan.
2. **Open Warden Lane REQ-016:** Execute the curated staging and baseline commit.
