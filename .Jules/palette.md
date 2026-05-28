## 2026-05-28 - Accessible Semantic Icons
**Learning:** Found a widespread pattern of non-semantic `div` and `svg` elements functioning as buttons without keyboard access or screen reader announcements, relying entirely on CSS classes and inline event handlers for interactions.
**Action:** Always wrap interactive icon elements in a semantic `<button>` tag with an `aria-label` and apply a comprehensive CSS reset (`background: transparent; border: none; padding: 0;`) to preserve existing visual layout while gaining native focus, keyboard, and accessibility tree support.
