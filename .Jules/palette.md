## 2026-05-26 - Semantic interactive elements and ARIA labels
**Learning:** Found that non-semantic elements like `div` and `svg` were used for interactive controls (e.g. header icons, card icons) without accessible roles or keyboard focusability, causing accessibility issues for screen readers and keyboard users.
**Action:** Implemented semantic `<button>` wrappers with `aria-label` attributes and CSS resets (`background: transparent; border: none; padding: 0; ...`) for these elements. Always use native buttons with `aria-label` for icon-only interactive controls.
