# Vendored fleet-design-system

Source: `dwhly/fleet-design-system` at commit **61540c6** (v0.5.1: v0.5.0 baseline + lockup mark optically centred). Copied verbatim: `fonts.css`, `fonts/`, `tokens.css`, `components.css`, `theme.js`,
`marks/fleet.svg`; no brand layer (Fleet Dealroom uses the base Fleet tokens); `../../fds.preset.cjs` = `tailwind.preset.cjs`.
`theme-boot.js` is the inline boot snippet from the footer of `theme.js`, as a file.

One copy serves both surfaces: the React console links these from `index.html`, and the Django glue pages
(`backend/dealroom_sign/templates`) link the same `/fds/...` URLs (nginx serves `frontend/dist` at `/`).
Prototype only: the gated build replaces this copy with the package dependency. Do not edit here.
