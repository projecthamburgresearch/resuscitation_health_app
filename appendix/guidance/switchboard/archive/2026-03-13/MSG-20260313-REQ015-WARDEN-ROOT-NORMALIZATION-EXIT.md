# Exit Interview: MSG-20260313-REQ015-WARDEN-ROOT-NORMALIZATION

- message_id: "MSG-20260313-REQ015-WARDEN-ROOT-NORMALIZATION"
- date: "2026-03-13"
- role: "warden"
- status: "COMPLETED"

## Summary of Work
Normalized the repository root surfaces to distinguish the canonical authority stack from preserved legacy materials. Relocated superseded roots and updated `.gitignore` to support the first authority-aware baseline commit.

## Key Findings
1.  **Legacy Bloat:** Superseded roots like `appendix/blueprint` contained large ephemeral artifacts (e.g., `.venv`) that should not be tracked.
2.  **Gitignore Priority:** Discovered that `.gitignore` rule order was blocking the authority stack; corrected it by placing broad ignores above exclusions.
3.  **Preservation:** Historical provenance was preserved by moving legacy roots to `appendix/guidance/materials/legacy/` rather than deleting them.

## Action Taken
- Relocated `appendix/blueprint/`, `appendix/blueprint_outputs/`, `appendix/scans_outputs/`, and `appendix/system/` to `appendix/guidance/materials/legacy/`.
- Created `appendix/guidance/materials/legacy/README.md` to document frozen historical context.
- Optimized `.gitignore` to track the authority stack while ignoring legacy and ephemeral bulk.
- Updated root `README.md` to include the legacy surface.
- Closed Warden ticket `REQ-015`.

## Next Steps
- The repo is now ready for the first accepted baseline commit.
- Recommend a bounded Headmaster follow-on to curate the first accepted baseline commit boundary before any real commit/push decision.

## Verification Results
- `git status` confirms canonical paths are ready for staging while legacy bulk remains ignored.
- `git check-ignore` verifies that ephemeral folders (like `.venv`) are correctly excluded even in canonical paths.

## Stewardship Recommendation
Root surfaces are now normalized and the authority stack is easy to stage. Recommend accepting the lane closure.
