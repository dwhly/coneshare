# Vendored fleet-design-system

Source: `dwhly/fleet-design-system` **v0.8.1** (commit `7ec5225`), copied with `scripts/vendor.sh` (which never copies the
prototype-only `fds-lab.js`). `fds.lock` pins the version, commit and a sha256 per vendored file; verify with
`scripts/check-vendored.sh frontend/public/fds` from the package. Do not edit vendored files here: change the system
upstream, bump its version, re-vendor.

Vendored (listed in `fds.lock`): `tokens.css`, `components.css`, `theme.js`, `fonts.css`, `tailwind.preset.cjs`, `fonts/`,
`marks/`. Vendored with `--brands none` (recorded in `fds.lock`): Fleet Dealroom loads no brand layer, base Fleet tokens only.

Product-owned (not in `fds.lock`):
- `README.md` (this file);
- `theme-boot.js`: the inline boot snippet from the footer of `theme.js`, as a file (CSP-strict pages load it first in `<head>`);
- `../../fds.preset.cjs`: a one-line wrapper that re-exports `tailwind.preset.cjs` for `tailwind.config.js`.

One copy serves both surfaces: the React console links these from `index.html`, and the Django glue pages
(`backend/dealroom_sign/templates`) link the same `/fds/...` URLs (nginx serves `frontend/dist` at `/`).
Both write `<html data-edge="outline" data-density="spacious">` statically (DESIGN.md §10).
