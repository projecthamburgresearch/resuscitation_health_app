## 2025-03-16 - Replaced div/svg icons with semantic buttons
**Learning:** Converting div and svg icons directly into buttons with aria-labels improves accessibility (keyboard + screen reader focus) and allows the removal of inline onclick handlers in favor of data-attributes and semantic HTML. Applying CSS resets to the button maintains existing aesthetic polish seamlessly.
**Action:** Always wrap interactive icon-only elements in a semantic button with an aria-label and reset its CSS to preserve the current visual design pattern.
