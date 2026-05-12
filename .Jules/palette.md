## 2024-05-12 - [Header Icons Accessibility]
**Learning:** Icon-only SVG elements used for actions lack semantic meaning and keyboard navigability without ARIA attributes and a button wrapper. This is a common pattern in this app.
**Action:** Wrap icon-only SVGs in `<button>` elements with clear `aria-label`s and apply a transparent CSS reset to preserve existing visual layout while improving accessibility. Ensure event listeners correctly target the new button wrappers.
