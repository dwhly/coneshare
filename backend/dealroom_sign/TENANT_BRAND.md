# Deployment tenant branding

All settings are optional and identical in Send and Sign. Set them in each app's runtime environment (including Send's mail workers), mount the same logo file read-only, and restart the processes when changing the configuration or logo bytes. There are no tenant assets in the source tree.

| Environment variable | Default | Accepted value |
| --- | --- | --- |
| `FLEET_TENANT_NAME` | `Fleet` | Trimmed, nonempty text, at most 120 characters, no control characters |
| `FLEET_TENANT_LOGO` | unset | Readable regular `.png` file containing valid PNG data, strictly smaller than 204800 bytes |
| `FLEET_TENANT_LOGO_BASELINE` | `0.8` | Finite decimal number in `[0, 1]`; fraction of image height occupied above the letters' baseline |
| `FLEET_TENANT_CHROME` | unset | `#RGB` or `#RRGGBB` |
| `FLEET_TENANT_CHROME_RULE` | unset | `#RGB` or `#RRGGBB` |
| `FLEET_TENANT_SURFACE` | unset | `warm` |
| `FLEET_TENANT_POWERED_BY` | unset | `1` |

An empty value means unset. Invalid fields fall back independently and log the setting name once per process; the invalid value and filesystem path are not logged. PNG structure and chunk checksums are validated. SVG and all other non-PNG content are rejected, even with a `.png` extension. An invalid logo warns once per process and falls back to the mark and configured tenant name.

Pages use the fds dark chrome, rule and warm surface switches. Hex values become HSL triplets for fds; email styles retain hex. The logo replaces the mark and family name but keeps the product label. Its displayed height is 20px, or 17px at widths up to 420px; its configured letter baseline aligns with the product text baseline. With no logo, the mark and name remain. Product selection remains Sign while signing and Dealroom for completed copies/rooms.

Both apps serve `GET /chief/tenant-logo?v=<sha256>` from the validated bytes kept in memory. It takes no file path, requires the matching content hash, sets an immutable cache header and `nosniff`, and returns 404 when unavailable. The Send recipient listener serves it without creating a signer session. No remote/data image source or CSP relaxation is needed.

Send's HTML emails use `multipart/alternative` containing plain text and a `multipart/related` HTML/logo pair; completed PDFs remain outside that pair as attachments. The CID and MIME boundaries are stable. A configured chrome colour sets the header band and primary button, and a configured rule adds a 2px bottom border to that band. The From display name uses the tenant name. `POWERED_BY=1` adds an HTML email/visitor footer line; the explicit plain-text preservation requirement takes precedence, so plain text changes only its existing Fleet name.

Sign passes only the validated public brand object through its existing `createChiefPublicEnv` root-loader mechanism. Filesystem paths and logo bytes stay server-side. Its provider and html attributes apply only on recipient routes. Public-env script serialization escapes `<`.

For the neutral staff Rooms link, Sign now reads `NEXT_PUBLIC_FLEET_SEND_URL`.

The regression scanners accept extra comma-separated tenant names through `FLEET_TEST_TENANT_NAMES`, in addition to their neutral test fixture. They scan the Send glue runtime tree and Sign chief presentation tree; historical test/e2e/deployment material is outside those runtime scans.
