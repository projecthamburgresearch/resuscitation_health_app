## 2024-05-22 - Header Icon Accessibility
**Learning:** Replacing direct SVG click handlers with semantic `<button>` elements improves accessibility but introduces default user-agent styles (border, padding, margin) that can shift layout.
**Action:** When refactoring clickable icons, always apply a robust CSS reset (`appearance: none`, `border: none`, `background: none`, `padding: 0`, `margin: 0`) and verify layout with pixel-perfect comparisons if possible.
