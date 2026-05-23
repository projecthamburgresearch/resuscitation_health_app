## 2024-05-18 - Non-semantic Interactive Icons
**Learning:** Interactive icons (like header icons, card icons, and overflow buttons) in this app are frequently implemented using non-semantic elements (`<svg>` or `<div>`) without focus styles or ARIA labels, breaking keyboard navigation and screen reader support.
**Action:** Always use semantic `<button>` elements with `aria-label` for icon-only controls, applying a transparent CSS reset to preserve layout while enabling accessibility.
