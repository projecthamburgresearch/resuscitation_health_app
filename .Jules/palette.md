
## 2024-06-24 - Wrapped SVG Icons in Button Tags
**Learning:** For interactive icon buttons that utilize SVG elements, wrapping them in semantic `<button>` tags with the appropriate `aria-label` guarantees that screen readers are able to understand what the element does. In addition, setting `pointer-events: none;` on the child SVG ensures click events successfully bubble up to the parent button to trigger attached listeners correctly.
**Action:** When updating non-semantic SVGs to be accessible, apply `<button>` wrappers with `aria-label` attributes and make sure to transfer sizing styles or use CSS resets to avoid altering the component's visual footprint. Add `pointer-events: none` to the child SVG to maintain expected event delegation behavior.
