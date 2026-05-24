
## 2024-05-24 - Preserving Layout when Converting Icons to Semantic Buttons
**Learning:** When converting global shell icons (like `.header-icon` or `.overflow-btn`) from generic elements (like `div` or `svg`) to semantic `<button>` elements to improve accessibility, the new button wrappers can disrupt layout due to default browser button styling.
**Action:** Always apply a comprehensive CSS reset (`background: transparent; border: none; color: inherit; padding: 0; display: inline-flex; align-items: center; justify-content: center;`) to the new button class, and ensure child SVG elements are explicitly sized (e.g., `width: 100%; height: 100%;`) to perfectly preserve the existing visual hierarchy and component sizing.
