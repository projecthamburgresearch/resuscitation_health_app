## 2024-05-14 - Replace header SVG icons with accessible buttons
**Learning:** Found header and card icons as naked `svg` or `div` elements lacking keyboard navigation, proper focus states, and semantic ARIA labeling in `app/index.html` and `app/src/cards/renderer.ts`.
**Action:** Wrap naked icon SVGs in `<button>` with clear `aria-label`s, applying existing `.header-icon` and `.card-icon` classes. Adding reset styles to buttons will maintain UI parity while making it screen reader and keyboard accessible.
