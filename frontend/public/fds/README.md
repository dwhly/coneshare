# Vendored fleet-design-system

Source: `dwhly/fleet-design-system` at commit **7855f54** (v0.5.0 baseline: outline edges, 6px controls,
"Fleet | Product" lockup). Copied verbatim: `fonts.css`, `fonts/`, `tokens.css`, `components.css`, `theme.js`,
`marks/fleet.svg`, `brands/amforge.css` → `brand-amforge.css`; `../../fds.preset.cjs` = `tailwind.preset.cjs`.
`theme-boot.js` is the inline boot snippet from the footer of `theme.js`, as a file.

One copy serves both surfaces: the React console links these from `index.html`, and the Django glue pages
(`backend/dealroom_sign/templates`) link the same `/fds/...` URLs (nginx serves `frontend/dist` at `/`).
Prototype only: the gated build replaces this copy with the package dependency. Do not edit here.
