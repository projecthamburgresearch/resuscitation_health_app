## 2026-06-07 - Wrap SVGs in Semantic Buttons
**Learning:** When replacing structural div elements containing SVGs with semantic `<button>` wrappers to improve accessibility, the child SVG can unexpectedly intercept click events, preventing event delegation on the button from firing.
**Action:** Always apply `pointer-events: none;` to the child `<svg>` element to ensure click events correctly bubble up and target the parent `<button>`.
