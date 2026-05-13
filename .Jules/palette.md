## 2025-02-26 - Playwright Strict Mode Exact Matching
**Learning:** Playwright's `get_by_role` with a `name` argument uses substring matching by default. This causes strict mode violations when multiple interactive elements share text fragments (e.g., a "Search" header button and a "Search" menu item).
**Action:** When validating interactive components in the test environment, consistently use `exact=True` (e.g., `page.get_by_role("button", name="Search", exact=True)`) to guarantee precise element targeting and avoid false negative test failures.
