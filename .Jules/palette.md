## Palette's Journal

## 2025-04-09 - Accessible Header Icons
**Learning:** Found header icons implemented as basic `<svg>` elements inside generic `<div>` containers. While visually functional, these icons represent important actions (Search, Menu) but lacked semantic meaning (no `<button>`), keyboard accessibility (not focusable), and screen reader context (no `aria-label`).
**Action:** Replaced the div-based icons with semantic `<button>` elements, applied `aria-label="Search"` and `aria-label="Menu"`, and added a CSS reset to the buttons (`background: transparent; border: none; color: inherit; padding: 0; display: inline-flex; align-items: center; justify-content: center;`) to perfectly maintain the existing design. Updated JS event listeners to target the new attribute selectors.
