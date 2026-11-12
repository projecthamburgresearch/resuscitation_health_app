## 2024-11-12 - Converting Div-Based Icons to Buttons
**Learning:** When retrofitting legacy applications by converting div-based icons to semantic buttons, the inner SVGs will frequently intercept pointer events, which breaks structural event delegation (e.g., `e.target.closest(".header-icon")`).
**Action:** Always apply `pointer-events: none` to the inner child elements (e.g. `<svg>`) inside buttons, and ensure proper CSS button resets (`background: transparent; border: none; padding: 0`) are used to maintain visual fidelity without altering existing styling structures.
