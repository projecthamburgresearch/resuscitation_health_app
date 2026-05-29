## 2024-05-24 - Converting SVGs to Semantic Buttons
**Learning:** When converting top-level interactive SVGs into accessible `<button>` wrappers, any structural JS selectors (e.g., `document.querySelector('.header-icon:last-child')`) need to be considered. The class must be moved to the wrapper button to keep structural queries intact, while internal child logic updates its target to the wrapper.
**Action:** Always verify if an element being wrapped is the target of JS pseudo-class structural selectors (`:last-child`, `:first-of-type`) before shifting classes between child and parent.
