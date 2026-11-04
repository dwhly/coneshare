# Chief glue v1 (isolated acceptance deployment)

Source is the Coneshare `chief/glue-v1` branch stacked on `chief/send-v1`. This is a Django app, not the old bridge service. Web and control processes use the same new Send database. Existing prototype containers are untouched.

- Staff: http://glue-v1.100-110-241-2.sslip.io/signing/
- Recipient: `/view/<entry-link-slug>` (rewrites to the served Django `/signing/room/<slug>` page).
- MCP: `/mcp`, with the owning staff's scoped Dealroom key.
- Current Sign: http://sign-v1.100-110-241-2.sslip.io, API v2 at port 8796.

Use `docker compose -f deploy/chief-glue-v1/docker-compose.yml build` and `up -d`. The web build overlays this branch's entire backend on the existing native-dependency prototype image; it is a local one-day build, not the multi-architecture release image. Source, migrations and tests are included. Every container has a memory limit. Database and Redis stay on the private network; raw file/media endpoints are denied at Nginx. Public exposure is OFF. `backend/dealroom_sign/recipient_routes.json` describes the additional real recipient routes for D's separate listener, not a wildcard `/api` allow-list.

Create `.env` with POSTGRES_DB/USER/PASSWORD and `app.env` with SECRET_KEY, DATABASE_URL, INTERNAL_API_TOKEN, SITE_DOMAIN, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, REDIS_URL (no database suffix), SMTP and SIGN_* configuration. Use `CORE_API_URL=http://chief-glue-v1-web-1:8080`: generic `web` aliases can collide on the shared amforge-net. Back up the database, data volume and SECRET_KEY; the latter decrypts staff credentials and cached NDA tokens. Never commit env/provisioning files.

The fixture command `seed_sign_fixture` is explicitly restricted to deployment ID chief-glue-v1. It consumes a JSON object on stdin with `token`, `teamId`, `password`, and prints a fixture JSON containing a newly created scoped agent key. Redirect output into an ignored 0600 file. PDFs are clearly labeled integration fixtures, not production legal documents. The signatures and sealed bytes are real.

`manage.py sign_poll` sweeps durable commands every 15s. A private, constant-time-secret webhook also enqueues hints through Celery; polling works without webhook registration or Redis. A pending signature never opens the room until authoritative completion, all expected recipients, matching original hash, cryptographic PDF signature, certificate and audit evidence have been checked. The native completion audit ID deduplicates final activity. Network calls occur before the atomic local file/acceptance publication. Ambiguous create/distribute is never blindly repeated.

Tests: run `pytest dealroom_sign/tests tests/dealroom --ds=dealroom_sign.test_settings` with a Redis service reachable as `redis`; use the repository Docker test image and a fresh test database. Browser scripts under `backend/dealroom_sign/e2e/` use real Playwright and the Mailpit test inbox; the fixture JSON and session state stay under `.local/`. Screenshots go to product `docs/status/shots/C-*.png`. `mcp_probe.py` uses actual Streamable HTTP with an agent key.

Limitations: one PDF item and basic SIGNER fields in this slice; rich field metadata uses native Sign editor and is rejected by this API. No recipient editing or automatic retries of ambiguous distributions are exposed. Native standalone envelope discovery, supplemental Sign CRUD parity and explicit original-evidence export are outside this glue slice. `sign_credential_configure` explains its human-staff-only endpoint; it never accepts raw team tokens from MCP. Recipient NDA operations are browser-only and excluded from the agent catalog. Staff can reset failed/stuck, cancelled or declined NDAs on the Signing page; pending envelopes are cancelled and unsent drafts are deleted before a fresh generation is issued. Already-completed native records are preserved unchanged; a quarantined local workflow can be superseded without accepting the old evidence. Agreement evidence is staff-only; NDA evidence is staff/subject private.

The inherited full Send backend gate remains B's responsibility; it is not replaced by this focused suite. Independent manager review and multi-architecture/release gates remain outstanding.

Edge caveat on h-mini2: the running Caddy container still binds the old renamed repo path. `/etc/caddy/Caddyfile` may be stale; loading the current product config via stdin preserves all sibling blocks. D must repair the mount during an authorized edge lifecycle change. Do not restart existing containers to work around it.


Gate 3 r2 regression proof: `python3 deploy/chief-glue-v1/review_mutations.py` temporarily restores one r1 implementation at a time, requires its targeted test to fail, restores the implementation in `finally`, then requires a pass. Run from a quiescent worktree; never alongside builds or other tests. `--only 01` selects one check; `--base` overrides the reviewed r1 commit. Logs remain under ignored `.local/r2/`.

The web listener binds only `100.110.241.2:8797`. C's edge hostname forwards to that address (the existing edge container is not on `amforge-net`). Recipient/staff origins are still shared on this internal demo; separate origins remain a coordinated deployment follow-up.

`e2e/review_guards.cjs` verifies two real OTP members have disjoint NDA folders and private evidence pages. `e2e/reset_stuck.cjs` requires a fresh named grant and `MEMBER_EMAIL=r2-…`; it verifies real OTP, creates a native draft, explicitly injects the persisted lost-distribution state, and uses the human staff page to reset it. It checks actual draft deletion and fresh workflow creation. Then run `e2e/flows.cjs` with the same email to sign the replacement and verify access. The fault fixture simulates only the stuck distribution state; signatures, sealing and acceptance remain native and authoritative.
