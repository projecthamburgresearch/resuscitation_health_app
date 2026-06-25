
## 2023-11-20 - Establishing Accessible Icon Button Pattern
**Learning:** Found several SVG icons functioning as interactive buttons but lacking semantic `<button>` wrappers and `aria-label`s. Wrapping them in `<button>` elements creates an accessible keyboard and screen-reader experience.
**Action:** When converting non-semantic SVGs to buttons, ensure we wrap the SVG in a `<button>` with an `aria-label`, apply `pointer-events: none` and `width: 100%; height: 100%;` to the inner SVG to maintain click targets, and add CSS resets (`background: transparent; border: none; padding: 0; display: inline-flex; align-items: center; justify-content: center; color: inherit;`) to the button wrapper to perfectly preserve the existing layout.
