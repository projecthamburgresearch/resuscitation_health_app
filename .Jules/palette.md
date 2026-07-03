## 2024-05-18 - Semantic Wrapper Refactoring for Icon Controls

**Learning:** When migrating pure SVG/div elements to semantic `<button>` wrappers for accessibility, care must be taken regarding event delegation (`data-action`) and click targets. If the inner SVG captures the click, the parent button's `data-action` might not trigger properly in generic event listeners. Additionally, syntax errors inside JS template literals (e.g. escaping single quotes inappropriately) can entirely break SPA rendering.

**Action:** When wrapping SVG icons with semantic `<button>` elements, always apply `pointer-events: none` to the child `<svg>` to ensure the button itself registers the click and propagates its `data-action` attribute. Also, thoroughly test bundle outputs (`pnpm build`) after string-based refactoring to catch template literal syntax errors early.
