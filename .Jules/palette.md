## 2025-06-16 - Semantic Header Icons
**Learning:** When wrapping existing generic container/svg elements in `<button>` to improve semantics and accessibility in this app, ensure `pointer-events: none` is added to the inner svg to maintain accurate event delegation paths for click handlers.
**Action:** Always add `pointer-events: none` to inner svgs when converting unsemantic icons to accessible buttons.
