## 2024-05-15 - Replacing div/svg interactive elements with semantic buttons

**Learning:** When converting non-semantic interactive elements (like divs or svgs) to semantic `<button>` wrappers, you must manage `pointer-events: none` on child `<svg>` elements so that event delegation (e.g., `event.target.closest("[data-action]")` logic) on the parent button continues to function correctly without being intercepted by child SVG nodes.

**Action:** Always apply `pointer-events: none` to the child `<svg>` when wrapping an interactive SVG in a semantic `<button>` and relying on parent-level event delegation.
