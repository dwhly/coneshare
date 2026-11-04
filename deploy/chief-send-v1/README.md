# Send phase-one review deployment

Staff: http://send-v1.100-110-241-2.sslip.io/
Recipient: http://send-v1.100-110-241-2.sslip.io/view/project-atlas
MCP (staff listener only): http://send-v1.100-110-241-2.sslip.io/mcp/

This is an isolated review deployment, not an accepted production release. No prototype database or volume is reused. `app.local.env` and `.env` are untracked; the staff login is the supplied throwaway `admin@amforge.test` login. Rotate it before any real data.

## Build and run

On h-mini2, run the frontend build natively (`fnm exec --using=24 npm run build --prefix frontend`), then build `Dockerfile` and `MCP.Dockerfile` from repository root. The application image overlays the existing native arm64 `amforge-send-dev:latest` dependency image. Native multi-architecture pinned release images are a separate D/manager gate; this local dependency image is not a reproducible release claim.

Use `docker compose -f deploy/chief-send-v1/docker-compose.yml ...`. Stop only this project's web/celery before migration. Every service and one-shot inherited web job has a memory limit. Run `web python manage.py migrate --noinput`, restart web/celery, then `exec -T web python manage.py seed_dealroom`. `SEED_STAFF_PASSWORD` must be supplied through the local env file. The seed's three PDFs are fictional and labeled as such.

The existing edge container has a stale bind to the old product-repository path. See `docs/status/B-send.md` in chief-dealroom for the observed reload issue and temporary runtime config. Do not restart or recreate the existing proxy as part of this worker's task.

## Interfaces and policy

`dealroom.policy.evaluate(request, link, document_id=None, download=False)` returns an immutable Decision. It checks the OTP member proof, absolute and idle timeouts, active room/link, explicit member denial, active member-over-org grant, file membership/visibility, and minimum grant/file download ceiling. Grants are reused `ShareLinkAccessGrant` rows on the room's canonical entry link; every additional entry link uses that room's policy and grants.

All DRF dispatches cross `dealroom.hooks` regardless of `permission_classes` or `get_permissions`. `dealroom.registry.OperationSchema` supplies stable spectacular operation IDs; `operations.json` inventories every served DRF operation. `manage.py dealroom_registry` fails on route drift. Unknown operations deny. Legacy recipient metadata, bearer/session bypasses, Q&A, ZIP, raw-page/capability and file-request routes deny in phase 1. The two retained legacy render/download views use central policy. Admin and DRF session-login routes are disabled.

Human-only means a staff user authenticated by SimpleJWT, never an API key. The approval request stores the exact path/method/payload hash and requesting key, emits local approval/Drift facts, and notifies the staff email. Approval executes under a row lock, rechecks key tier/scope/expiry and object ownership, and uses a process-only approval context; no request header can forge it. Every successful agent call records `agent.action` in the same database transaction. Key creation returns raw material once to the approving staff response; it is redacted from stored approval results. Child tier/lifetime cannot exceed the parent; ancestor expiry/revocation is enforced.

S1 edit classification is in `widens_access`: increased download ceiling; extended/cleared expiry (UTC instant comparison); restored grants/members/rooms/links; email or recipient/org rebinding; new org domains; loosened invitations/password/scope; changed automation/webhook destination; relaxed email/watermark enforcement. Unclassified edits widen. File visibility to existing grantees does not widen. Invitations, Sign key issuance and automation routes are disabled rather than exempted. Approvals are human-only. First-domain confirmation records Unicode/A-label, confirming staff and time. Lists are pinned with SHA256 and licenses in `dealroom/data` and fail closed if missing or changed. Unicode labels use a conservative single-script subset; the complete UTS #39 confusables dataset is not implemented.

## Recipient routes for D's default-off exposure listener

- UI `GET /view/<slug>` and built `/assets/*`, `/brand-mark.svg`.
- `GET /api/v1/dealroom/brand/` (public brand configuration; no identities).
- `GET /api/v1/public/settings/`, `GET /api/v1/languages/` (existing shell plumbing).
- `GET|POST /api/v1/dealroom/recipient/<slug>/challenge/`.
- `POST /api/v1/dealroom/recipient/<slug>/confirm/` and `/logout/`.
- `GET /api/v1/dealroom/recipient/<slug>/room/`.
- `GET /api/v1/links/<slug>/render-page/<page>/` and `/download-file/` with room-document IDs.
- `POST /api/v1/dealroom/recipient/<slug>/original/<exception UUID>/` (bounded explicit exception; not normal download).

No `/api/*` wildcard. No `/upload/*`, `/files/*`, `/media/*`, staff, MCP or admin on a recipient listener. Public exposure remains off. HTTP is deliberately the requested tailnet demo URL; set `DEALROOM_HTTPS=true` with TLS to make the host-only HttpOnly recipient session cookie Secure. Original downloads return unchanged source bytes plus a hashed receipt in a ZIP; the exception is version/member/grant bound and consumed before streaming.

## Tools and tests

Regenerate OpenAPI with `manage.py spectacular --file /src/deploy/chief-send-v1/out/openapi.yaml`, then run `mcp-server/scripts/generate_registry_tools.py`. It generates an individual typed MCP tool for each enabled business/recipient operation, not a caller-selected HTTP dispatcher. `list_rooms` is an ergonomic alias. Each invocation uses a new HTTP client, so recipient cookie jars are not shared. Recipient challenge/confirmation tools carry the CSRF token and returned cookie proof explicitly. Protected rendering returns bytes as base64. Uploads accept supplied bytes, never a host path or remote URL.

`test-backend.sh tests/dealroom` runs focused security tests in an isolated capped test network. `test-backend.sh` runs the complete backend suite with phase-one enforcement enabled. The inherited suite is migrated to explicit denial contracts for excluded legacy routes and non-staff users, while service/model tests remain enabled. `out/inherited-test-migration.md` maps all 818 original failures and 5 fixture errors to their disposition and real final counts. No test is skipped, xfailed, filtered out, or converted to success at runtime. `mutation-check.py` reproduces the isolated negative checks documented in `out/r2-mutation-evidence.md`; run it only in an otherwise idle worktree.

`e2e.cjs` uses Mailpit and headless Chromium; `SEND_PASSWORD` supplies the throwaway password. It writes B-prefixed screenshots to the shared product status folder. No real third-party email is sent. New UI tests are in the whitelist. CI/static parity is implemented as tests/commands; remote CI upload is blocked by the credential workflow scope reported by D.

Remaining release evidence: independent review, native two-architecture image pins, formal 30-session memory/load run, coordinated backup/restore of this release, full UTS #39 profile, and any production SMTP/exposure decisions. The bound original-delivery test is real; the live original-download UI remains API/tool-driven. Phase-two invitations, Q&A, templates and analytics are not enabled.

## r2 recipient lifecycle

Revoking a named grant only revokes that grant; org-derived access remains. `POST /api/v1/dealroom/grants/deny-member/` and `restore-member/` take room and member IDs, have matching MCP tools, require approval for agent callers, and record member.denied/member.restored. Used recipient orgs are archived instead of deleted. Only active grants are unique per canonical room entry and subject. Agent writes require application/json, except the room upload multipart endpoint. Magic-link challenge/token values travel in the URL fragment and are removed from browser history before confirmation.
