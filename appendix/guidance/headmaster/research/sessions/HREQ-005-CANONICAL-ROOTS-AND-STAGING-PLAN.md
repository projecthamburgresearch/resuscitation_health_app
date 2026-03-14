# Research Session: HREQ-005-CANONICAL-ROOTS-AND-STAGING-PLAN

- date: 2026-03-13
- role: headmaster
- ticket_ref: HREQ-005-CANONICAL-ROOTS-AND-STAGING-PLAN

## Objective
Classify the current repository roots into canonical, legacy, project-material, and bootstrap buckets, and define the first accepted staging boundary.

## 1. Root Classification

### A. Canonical Authority Surface (STAGED)
These are the primary sources of truth for product behavior and authority direction. They must be tracked in git.
- `appendix/guidance/headmaster/` — Future direction and source mapping.
- `appendix/guidance/warden/` — Current-state evidence and implementation contract.
- `appendix/guidance/switchboard/` — Async messaging and delegate history.
- `appendix/guidance/exit/` — Continuity state and raw terminal logs.
- `app/` — Runtime source code and algorithms.
- `scripts/` — Project-specific tooling and automation.
- `docs/` — High-level architecture and implementation plans.
- `prototype/` — Original design schema and interaction references.
- Root config: `README.md`, `package.json`, `package-lock.json`, `.gitignore`.

### B. Project Material / Reference (STAGED)
Supporting data that is not part of the active authority stack but provides necessary context.
- `appendix/css-web-ui-demos/` — Interaction design reference.
- `appendix/guidance/materials/` — Legacy local notes.

### C. Legacy / Stale Surface (DEFERRED/IGNORED)
Old versions of toolkit artifacts or temporary outputs that have been superseded by the `appendix/guidance/` hierarchy.
- `appendix/blueprint/` — Legacy toolkit copy.
- `appendix/blueprint_outputs/` — Legacy root-level output (superseded by `appendix/guidance/warden/blueprint_outputs/`).
- `appendix/scans_outputs/` — Legacy root-level output (superseded by `appendix/guidance/warden/scans_outputs/`).
- `appendix/system/` — Early-stage authority layout (superseded by `appendix/guidance/`).

### D. Ephemeral / Runtime (IGNORED)
Generated files and environment-specific artifacts.
- `node_modules/`
- `.claude/`
- `app/dist/`

## 2. Staging Plan: Accepted Baseline Commit

The goal is to move the repo from its current "bootstrap" state to an "accepted baseline" where the authority stack is officially recognized.

### Step 1: Normalize .gitignore
Ensure `.gitignore` explicitly tracks the **Canonical** and **Reference** surfaces while ignoring the **Legacy** and **Ephemeral** surfaces.

### Step 2: Stage Canonical Roots
Stage all files in the **Canonical Authority Surface** and **Project Material** buckets.

### Step 3: Deferred Normalization (Warden Follow-On)
Rather than deleting legacy roots immediately, they should be moved to an `archive/` or `appendix/materials/legacy/` folder in a future Warden lane once the baseline commit is secured.

## 3. Findings
- **Path Duplication:** Found duplicate output roots at `appendix/blueprint_outputs/` and `appendix/guidance/warden/blueprint_outputs/`. The latter is the new canonical path.
- **Gitignore Gap:** The current `.gitignore` is broad (`appendix/*`) and relies on specific exceptions. This should be tightened to be more intentional about what is canonical.

## Next Steps
1. **Update .gitignore:** Narrow the scope to track only canonical/reference paths.
2. **Close HREQ-005:** Submit the classification and staging plan.
3. **Open Warden Lane:** Execute `REQ-015-ROOT-NORMALIZATION-AND-BASELINE` to normalize the root surfaces after the staging plan.
