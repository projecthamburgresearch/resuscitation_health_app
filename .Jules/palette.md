## 2024-05-18 - Semantic HTML for Icon-Only Buttons
**Learning:** Found multiple instances where interactive icons (header icons and overflow menu) were implemented as `<svg>` or `<div>` elements without proper `role` or `tabindex`. This breaks keyboard navigation and screen reader accessibility for core navigation features.
**Action:** Replaced these elements with semantic `<button>` tags and `aria-label` attributes, and applied CSS resets (`background: none; border: none;`) to maintain existing design while getting native focus states and keyboard activation for free.
