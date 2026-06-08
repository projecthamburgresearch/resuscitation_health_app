## 2024-03-24 - Semantic Wrapping of SVG Icons

**Learning:** When converting standalone `div` or `svg` icons into semantic `<button>` elements (e.g., `.header-icon`), you must reset the button styles (e.g., `background: transparent; border: none; padding: 0; display: inline-flex;`) and also apply `pointer-events: none; width: 100%; height: 100%;` to the child `<svg>`. This prevents the child elements from hijacking click events intended for the button's event listeners, while keeping the layout visually identical.

**Action:** Always include a robust CSS reset for the `<button>` and set `pointer-events: none` on its inner `<svg>` when migrating pure decorative SVGs into interactive semantic elements.
