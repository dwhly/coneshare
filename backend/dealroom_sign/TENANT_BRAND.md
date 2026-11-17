# Deployment tenant branding

All settings are optional and identical in Send and Sign. Set them in each app's runtime environment (including Send's mail workers), mount the same logo file read-only, and restart the processes when changing the configuration or logo bytes. There are no tenant assets in the source tree.

| Environment variable | Default | Accepted value |
| --- | --- | --- |
| `FLEET_TENANT_NAME` | `Fleet` | Trimmed, nonempty text, at most 120 characters, no control characters |
| `FLEET_TENANT_LOGO` | unset | Readable regular `.png` file containing valid PNG data, strictly smaller than 204800 bytes, at most 2000 × 600 pixels; requires valid CHROME |
| `FLEET_TENANT_LOGO_BASELINE` | `0.8` | Finite decimal number in `[0, 1]`; fraction of image height occupied above the letters' baseline |
| `FLEET_TENANT_CHROME` | unset | `#RGB` or `#RRGGBB`, white-text contrast ≥ 4.5:1 (WCAG AA) |
| `FLEET_TENANT_CHROME_RULE` | unset | `#RGB` or `#RRGGBB` |
| `FLEET_TENANT_SURFACE` | unset | `warm` |
| `FLEET_TENANT_POWERED_BY` | unset | `1` |

An empty value means unset. Invalid fields fall back independently and log the setting name once per process; the invalid value and filesystem path are not logged. PNG structure (including the 13-byte IHDR), dimensions and chunk checksums are validated. Files are opened nonblocking and checked by descriptor, so FIFOs/devices cannot stall a worker. Configuration is warmed at process startup. A logo without valid dark CHROME warns once and falls back to name-only identity in both page themes and email. SVG and all other non-PNG content are rejected, even with a `.png` extension. An invalid logo warns once per process and falls back to the mark and configured tenant name.

Pages use the fds dark chrome, rule and warm surface switches. Hex values become HSL triplets for fds; email styles retain hex. The logo replaces the mark and family name but keeps the product label. Its displayed height is 20px, or 17px at widths up to 420px; its configured letter baseline aligns with the product text baseline. With no logo, the mark and name remain. Product selection remains Sign while signing and Dealroom for completed copies/rooms.

Send serves `GET /signing/tenant-logo?v=<sha256>` (also available at the compatibility alias `/chief/tenant-logo`). The `/signing/` prefix already reaches Django on both staff/room and recipient origins, including older preview proxies; in-repo nginx configurations also explicitly proxy the alias. Send v1 proxies only the two exact logo paths, without exposing the rest of /signing/. Sign serves its own `GET /chief/sign-tenant-logo?v=<sha256>`, which Send forwards through the existing authenticated recipient asset path without consulting Send's logo hash. Both routes serve from the validated bytes kept in memory. It takes no file path, requires the matching content hash, sets an immutable cache header and `nosniff`, and returns 404 when unavailable. The Send recipient listener serves its own logo without creating a signer session. Different Send and Sign logo configurations cannot shadow each other. Failed browser image loads fall back to the tenant name. No remote/data image source or CSP relaxation is needed.

Send's HTML emails use `multipart/alternative` containing plain text and a `multipart/related` HTML/logo pair; completed PDFs remain outside that pair as attachments. The CID and MIME boundaries are stable. A configured chrome colour sets the header band and primary button, and a configured rule adds a 2px bottom border to that band. The From display name uses the tenant name. `POWERED_BY=1` adds an HTML email/visitor footer line; the explicit plain-text preservation requirement takes precedence, so plain text changes only its existing Fleet name.

Sign passes only the validated public brand object through its existing `createChiefPublicEnv` root-loader mechanism. Filesystem paths and logo bytes stay server-side. Its provider and html attributes apply only on recipient routes. Public-env script serialization escapes `<`.

For the staff Rooms link, Sign reads `NEXT_PUBLIC_FLEET_SEND_URL` first. The old deployment key is deprecated and remains supported through the single `DEPRECATED_SEND_URL_KEY` constant in `apps/remix/app/chief/public-env.server.ts`. Empty new values also fall back to that key. The fallback is resolved server-side and its deprecated key is never serialized or bundled for browsers. Only authenticated staff pages with a Rooms tab receive the resolved neutral URL; recipient origins and recipient routes never receive it. With neither set, Sign warns once and hides Rooms. New deployments should use the neutral key. `SIGN_INTERNAL_URL` is required at startup only in the dedicated Dealroom Sign runtime. Plain Send can start without it; constructing the Sign client then raises a clear configuration error before transport. There is no guessed internal hostname.

The regression scanners accept comma-separated `FLEET_TEST_TENANT_NAMES`, `FLEET_TEST_TENANT_COLOURS` and `FLEET_TEST_TENANT_DOMAINS`, matching case-insensitively and checking short/long hex, RGB forms and HSL triplets (four-decimal and rounded forms). The single upstream colour-example comment is exempt only in the exact hash-pinned vendored tokens.css; modified assets and relocated copies are scanned in full. They cover Send glue/templates/email, settings/URLs and public dealroom/fds assets; Sign app/recipient/chief routes, server, public chief assets, fleet-ui, shared UI/lib and email code. Only tests/fixtures are excluded from these code trees. Sign's scanner allows exactly one deprecated key declaration at its exact file path; duplicate or relocated literals still fail.

After deployment, check the real public proxy (GET, since the asset handlers accept GET only):

```sh
python3 deploy/check-tenant-logo.py https://send.example.test /run/tenant/logo.png
python3 deploy/check-tenant-logo.py https://recipient.example.test /run/tenant/logo.png
python3 deploy/check-tenant-logo.py https://sign.example.test /run/tenant/sign-logo.png --app sign
```

The Sign recipient proxy requires the existing signing session; use the Sign public listener for this standalone Sign smoke, or perform its request in the authenticated browser journey. The Send smoke works on both listeners without a session. No deployment or proxy outside the supplied worktrees is changed by this patch.
