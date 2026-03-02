1. **Change header icons to buttons with ARIA labels**
   - The `.header-icons` currently use naked `<svg>` tags with click listeners (or intend to).
   - I will wrap them in `<button>` elements with `aria-label` attributes for accessibility ("Search protocols" and "Menu").
   - Update `app/index.html` and `app/Resuscitation_App_Complete.html`
   - Update `app/src/ui/menu.ts` to attach the listener to the `<button>` rather than the `.header-icon` directly, or just update the selector to match the new button element.
   - Ensure the CSS correctly renders `<button>` without default borders/backgrounds (add CSS to `app/src/styles/layout.css` and the embedded styles in `app/Resuscitation_App_Complete.html`).

2. **Verify changes**
   - Run `pnpm lint` and format
   - Check parity `pnpm run check:devmode:parity`
   - Verify visually/functionally by building
