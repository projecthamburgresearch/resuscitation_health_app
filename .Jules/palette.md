## 2024-05-28 - Migrating structural icons to semantic buttons

**Learning:** When migrating layout-dependent div or svg elements to semantic `<button>` wrappers for improved a11y, preserving the original CSS class structural order and inline/block visual behavior is critical. In this app, many scripts target elements by positional selectors (e.g. `last-child`) and data attributes rather than IDs.

**Action:** Always wrap the icon in a semantic `<button>`, but ensure that the original class names, IDs, data attributes (`data-action`, `onclick`), and structural ordering are moved to the new wrapper. Additionally, always apply a comprehensive CSS button reset (`background: transparent; border: none; padding: 0; display: inline-flex; align-items: center; justify-content: center; color: inherit;`) and ensure the inner SVG takes 100% size of the new button container.
