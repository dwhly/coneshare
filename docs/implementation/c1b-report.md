# C1b implementation report

2026-11-15. Candidate changes are uncommitted in the three requested worktrees. The read-back STOP is resolved. This report replaces `c1b-r1b-stop.md`. Production Compose, deployed services/databases, `.agent/memory.md`, and `room.html` are unchanged. Preview acceptance remains a manager deployment gate; local tests do not establish live SMTP or signing acceptance.

## Implemented behavior

- Every release uses NONE and nine false email flags. Send persists disabled reminders and 30-day expiration, reads them through authenticated editor-get, validates ID/team/correlation/settings, and only then distributes with the recipient-origin return URL. Missing or mismatched values prevent distribution.
- HMAC-derived personal capabilities and grouped 80-bit alternate codes use separate purpose keys and keyed lookup hashes. Entry, successful code verification, and affirmative document-bound consent rotate Django sessions and invalidate the previous ID. Sessions enforce generation, eight-hour absolute lifetime, optional-code idle lifetime, revision and state. Scanner GETs are generic and do not enter or consent. Revocation rotates the generation and deletes session grants; the human sender endpoint enforces owner, board and writer/manager role.
- Signing expiry is release +30 days, shortened to an earlier native expiry with a History alert. Native release audit time (or the native expiry-derived release time) is used for delayed initial reconciliation. A signer's room deadline is set once at their completion +12 calendar months; CC uses final completion. Signing expiry does not invalidate a completed signer's room. Void invalidates all access.
- A dedicated Django ingress checks the configured Host and fixed nginx listener marker for every recipient route. `/s` mutations use Django CSRF and exact Origin; native tRPC uses exact Origin and JSON content type, preserving Sign's existing Origin-based CSRF contract. All request identities, fields, items, tokens, secondary document IDs and batch members are scoped. Writes require native eligibility, current consent and a fresh source hash. Unknown routes/procedures, identity changes, legacy readers, native OTP, report/reassign/assistant and external attachments are denied.
- Proxy forwarding uses an allowlist: trusted single-IP XFF, configured recipient host/scheme, checked browser Origin and browser UA. Browser credentials, cookies, caller key and alternative IP headers are never forwarded. The private file-backed key is added server-side. Responses discard native cookies and unsafe redirects, bound/spool bytes, preserve native bytes/nonces, and enforce no-store/no-referrer/no frames. Document reads and writes commit local audit events before bytes/actions. Unsessioned native URLs show the helpful deny without document metadata or an upstream fetch. Django recipient diagnostics redact request details.
- NDA enter remains on :9443 and produces a hashed, single-use, 60-second handoff bound to verified viewer/workflow/revision/recipient/generation. :9445 consumes it, rotates the session and 303s to `/sign/{token}`. That route displays Send consent until accepted. Only reconciled, verified NDA completion returns to the configured :9443 `/signing/nda/{room_id}`. The existing real signing harness now performs the consent interaction; its timing and file-back assertions remain.
- Invitations and Fully-signed mail use durable unique effects, stable Message-ID/Date/MIME boundaries and payload hashes. Invitations contain requester identity, sender context, note, document card, due/timezone, explicit effort estimate, preheader, one primary CTA, account-free copy, alternate code, report mailto and plain text, without attachments or external images. R7 names the approved incoming requester separately from the sending staff member, and uses requester Reply-To. Missing incoming identity stops release before distribution.
- Final mail loads only published, checksummed signed PDF and certificate artifacts. It attaches both or neither at the 10,000,000-byte raw / configured MIME / advertised SMTP SIZE limits. Names are cleaned, including timestamp suffixes. The same personal link offers scoped final/certificate downloads when oversized. Expired/revoked links hold delivery. Definite SIZE rejection can recompose once as link-only; uncertain acceptance and interrupted running effects are held without blind retry. Successful means relay acceptance, never reading/inbox delivery. History records delivery outcomes.
- Return and terminal pages reconcile native truth and ignore browser completion flags. Signed, checking, waiting, declined, expired and withdrawn states are Send-rendered. Late sealing remains pending. The `EMAIL_SENT` native fact is normalized into a deduplicated History alert, including the product History projection.
- Sign 3001 reads a file-backed key on each request, returns unconditional 503 for missing/blank configuration, constant-time compares caller keys and removes the key before handlers. Sign 3000 denies EDD (a)–(e), including token-only and dual-mode batches, token-file aliases and terminal `.data` paths. Staff download/attachment modes remain allowed. Staff forwarded host/proto are rebuilt from configured staff origin; caller IP authority is removed.
- Preview nginx 81 routes every path to Django and is published at loopback 8994. Staff 80/8990 clears the marker. Sign 3001 has no host publication. Only send-web and Sign mount the proxy key. A resolved-config preflight catches accidental inheritance from private env files.

## Contract decisions

1. **Approved read-back correction:** use `POST /api/deal/envelope/editor/get` with `{envelopeId}` and the existing team credential. `ZGetEditorEnvelopeResponseSchema` preserves reminders and expiration; native `ZGetEnvelopeResponseSchema` drops reminders. Both facts are asserted against the actual pinned schemas in `counterparty-readback.test.ts`. The first-party deal adapter retains native authentication/authorization and already classifies `envelope.editor.get` as `deal`. No upstream schema change.
2. **Completion's legacy parameter:** the existing, classified `recipient.completeDocumentWithToken` expects numeric `documentId`, even in v2. `envelope-signing-complete-dialog.tsx` calls `mapSecondaryIdToDocumentId(envelope.secondaryId)`; `packages/lib/utils/envelope.ts` maps `document_42` to `42`. Send checks this exact mapping. Optional values serialized by SuperJSON as undefined are accepted only for explicitly optional fields, with all other annotations rejected. Defined recipient overrides/next-signer changes remain denied. No endpoint, authority or upstream change.
3. **Native read batches:** the existing classified item-list, attachment-list and status procedures can share one tRPC query batch. Send checks each member, then projects the freshly validated envelope into the pinned response schemas. Attachment results are empty because C1b's approved manifest contains one PDF and no external attachments. Status comes from reconciliation, including the sealing interval. This avoids forwarding an unapproved external attachment URL and preserves the native batch format. The drift contract pins these schemas, all tRPC router wiring, native file handlers, classified procedures and token-file inventory in both repositories.
4. **Staff origin:** stripping caller forwarding headers must not erase the configured staff origin used by existing theme/CSRF handling. The first-party 3000 wrapper reconstructs only host/proto from `NEXT_PUBLIC_WEBAPP_URL`; it continues to discard client-IP authority. A regression covers that distinction. No middleware/upstream edit.
5. **Native audit alert projection:** raw `EMAIL_SENT` and a separate alert with the same source ID would compete in the existing History projection. The native event mapping now normalizes that event to `native_email.alert`, preserving its source type/payload and a single visible alert. A History-level regression verifies the alert survives projection.

## Validation

Final local results:

| Check | Result |
| --- | --- |
| Full Send signing suite, unchanged `run-send-local.sh` | **247 passed, 2 failed** (the two declared webhook baseline failures only) |
| Expanded C1b distribution/capability/session/mail/proxy subset | **50 passed, 0 failed** |
| Final proxy follow-up, including the added expired-link terminal-state regression | **17 passed, 0 failed** |
| Sign inventory/listener/schema/drift suite | **130 passed, 0 failed** |
| Preview deployment topology | **2 passed, 0 failed** |
| Generated Send operation inventory | **310 operations / 101 staff; exact registry match** |
| Migration/model comparison | **No unrepresented `dealroom_sign` model changes** |
| Whitespace checks | **All three worktrees pass `git diff --check`** |

The full run preceded the final expired-link-only follow-up; that branch and all proxy regressions were checked in the 17-test follow-up. No deployed migration or preview signing acceptance is claimed. The full suite's two failures are exactly `test_webhook_hint_auth_and_no_payload_trust[unit-test-secret-202]` and `test_webhook_enqueue_failure_retryable`.

All test assertions remain active; no skips or weakening. Existing tests that expected raw NDA tokens, an empty ordinary return URL or the old one-call distribution were updated to assert the approved handoff/return/read-back contracts instead.

- Inherited baseline: Send **195 passed, 2 known webhook failures**; Sign **102 passed**.
- Inherited red proof: distribution **6 failed → 6 passed**; Sign listener boundary **24 failed → 24 passed** (recorded by the prior STOP report).
- This continuation reproduced **9 failed / 20 passed** in the expanded Send distribution/capability/proxy subset, then **29 passed** after wiring. The original capability/proxy subset had been **8 passed / 9 failed**.
- Actual-schema read-back: **1 failed / 1 passed → 2 passed**, retaining native GET's stripping behavior as a passing assertion.
- Mail/proxy first run: **20 passed / 1 failed**; that failure exposed a pre-consumed MockTransport response in the streaming fixture. The fixture now supplies a real byte stream; production streaming behavior was retained.
- Full intermediate Send: **219 passed / 7 failed → 234 passed / 5 failed → 242 passed / 2 known failures**. Fixes cover the approved URL/handoff contracts, shared page assets and generated operation registry.
- Drift mutation: adding an unclassified new recipient procedure to the first-party inventory caused **1 failure**; restoring the reviewed inventory gave **1 pass**.
- Deploy mutation: putting the key path into the shared Send anchor caused **1 failure / 1 pass**; restoring send-web-only configuration gave **2 passes**.

Commands:

```sh
/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_c1b_distribution.py dealroom_sign/tests/test_counterparty.py dealroom_sign/tests/test_recipient_proxy.py dealroom_sign/tests/test_counterparty_mail.py
cd /root/worktrees/sign-c1b
CI=true node --import tsx --test chief/inventory/*.test.ts
cd /root/worktrees/fd-c1b
/root/work/sign-product/send-venv/bin/python deploy/do1/test_c1b_topology.py
```

No sandbox IPC or loopback block occurred in these runs. `node --check` passed for the new browser harness. Generated operation registry verification and `git diff --check` are included in the final checks.

## Sign upstream accounting

Measured against the actual working tree with the existing `chief/spike/first-party-directories.txt` exclusions unchanged:

| Comparison | Upstream files | Added + deleted lines |
| --- | ---: | ---: |
| C1b vs `6c4757feb` | 1 | 4 (+2/-2) |
| C0 plus C1b vs `d3b7f7c6` | 11 | 525 |
| Entire fork vs `v2.21.1` | 98 | 4,505 |

The sole C1b upstream file is the explicitly authorized `apps/remix/server/main.js` import/application of `staffFetch`. The editor-get correction and all subsequent C1b changes use **zero additional upstream lines**. No changes to upstream schemas, `middleware.ts`, recipient components, completion/layout pages or certificate code. C1a and later slices are not in this worktree, so these actuals are not a claim that their eventual combined total fits 20/822. The inherited whole-fork budget failure remains; exclusions and budget thresholds were not altered.

## Migration

`backend/dealroom_sign/migrations/0003_counterparty.py`, additive after `0002_signature_requests`, creates `SignerAccess`, `SignerSession`, `SignerHandoff`, `SignerChallenge` and `CounterpartyEffect`, with unique capability lookup and effect identities. No data migration or network operation. Only disposable test databases applied it. The manager must back up the fictional preview DB and apply the migration before starting new producers. Do not reverse it or remove signatures/artifacts during rollback.

## Manager preview deployment

1. Build/pin the reviewed Send/Sign images and preserve the prior immutable manifest. Use only `compose.proto.yml` / the fictional preview project. Coordinate the NONE/mail/routing/listener cutover; stop new sends and drain native jobs first. Retire old fictional native invitations (including NDA workflows) or replace them with bound personal links; there is no legacy token bypass.
2. Create a random, nonblank proxy key in ignored `deploy/do1/proto/fleet-proxy-key`. Use at least 32 random bytes; arrange owner/group/mode so both container runtime users can read it and other users cannot. Do not place the value **or `FLEET_PROXY_KEY_FILE`** in shared `proto/send.env`. Compose supplies `/run/secrets/fleet-proxy-key` only to send-web and Sign. Verify `test -r` in both containers without printing the file.
3. In ignored `proto/send.env`, configure `SIGN_RECIPIENT_ORIGIN=https://h-do1.tailb554cd.ts.net:9445`, `SIGN_RECIPIENT_INTERNAL_URL=http://sign:3001`, existing `SIGN_INTERNAL_URL` to Sign's private 3000, `SITE_DOMAIN` to :9443, and a persistent independent random `SIGN_CAPABILITY_KEY` shared by Send web/poll/worker. Rotating that root key invalidates existing capabilities; routine revocation uses generation instead. Ensure the recipient hostname is allowed by Django.
4. Set Send mail to Mailpit only: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=mailpit`, `EMAIL_PORT=1025`, `EMAIL_USE_TLS=false`, no external relay credentials. Set `SIGN_FROM_EMAIL=sign@fleet.test`, `SIGN_REPORT_EMAIL=support@fleet.test`, `SIGN_MESSAGE_DOMAIN=fleet.test`, `SIGN_MAIL_MAX_BYTES=14680064`. `SIGN_SMTP_SIZE` is an optional conservative configured cap; the actual EHLO SIZE is inspected before composition. Keep the existing native SMTP sink on Mailpit for negative assertions.
5. Run `python3 deploy/do1/c1b-preflight.py` on the manager host after private configuration exists. It resolves Compose without printing env/key values and rejects key leakage to poll/worker/migrate, blank/missing/world-readable key files and any host publication of 3001. Apply the additive migration, then start the matching preview images. Production Compose is untouched.
6. Change tailscale preview HTTPS **`:9445` to loopback `http://127.0.0.1:8994`** (for the existing Serve service, e.g. `tailscale serve --bg --https=9445 http://127.0.0.1:8994`). Preserve NDA/Send :9443, staff Sign :9444 and Mailpit :9446. Remove the prior :9445→8992 target. Port 81 passes tailscale's overwritten single-hop XFF/Host/Proto; staff 8990 clears the recipient marker.
7. Exercise missing/wrong-key 3001, missing configured key 503, direct :9444 token bypasses, staff downloads/attachments and helpful denies before sending the fictional acceptance fixture. Confirm no key or native token is exposed in logs/MIME. Missing runtime key must be tested, not inferred from config.
8. Run the **real** existing `backend/dealroom_sign/e2e/flows.cjs` with `SIGN_FIXTURE_FILE`, `GLUE_URL`, `MAILPIT_URL`, `PLAYWRIGHT_MODULE` and `SHOTS` set to the preview fixture/endpoints, preserving its signing→room/file-back timing checks. Run `counterparty-audit.cjs` with a private JSON config and `PLAYWRIGHT_MODULE` pointing to installed Playwright. That config supplies `recipientUrl`, `nativeOrigin`, `credentialFile`, `envelopeId`, `recipientId`, `expectedIp`, `name`, `shots`, `mailpitOrigin`, `mailRecipient`. Use a new one-signer fictional request. The script signs with a distinct UA and alternate caller forwarding headers, checks the native recipient-completed audit's real browser IP/UA, waits for jobs, asserts no native `EMAIL_SENT`, checks Send invitation/final-mail presence, and writes scrubbed audit/Mailpit IDs. It never prints credentials or personal URLs. Inspect raw MIME attachment names/hashes and the size fallback in Mailpit as part of acceptance.

Definite failed effects remain held for correction/review; uncertain effects must be reconciled by their stable Message-ID against Mailpit before any deliberate retry. Never reset an uncertain effect to pending merely because a worker restarted. Rollback stops new sends/effects while preserving access enforcement and reconciliation; do not restore raw native URLs or publish 3001.

## Deferred and acceptance limits

- **Not run here:** coordinated preview deployment, real `flows.cjs`, actual Mailpit lifecycle negatives/final attachment delivery, browser staff dialogs, audit-IP/UA harness, or visual screenshots. They require the matching candidate images, private fixture/config and manager routing cutover. These remain acceptance gates, not claims of success.
- C3's immediate/interim copies and full request room, C4's polished recipient UI, C5's optional-code issuance/UI and reminder/resend scheduling, and C6's questions/paper/decline workflows remain their approved later slices. C1b includes code-verification rotation and expiry enforcement, but does not expose native OTP. The minimal final/certificate download fallback ships here so oversized final mail links are usable.
- The two inherited webhook failures are configuration-sensitive and remain visible under the unchanged local runner; they were not hidden, skipped or changed by C1b.
- Public exposure, public SMTP deliverability and a publicly trusted seal remain outside this preview scope.

## Files per repository

### Send

- `backend/backend/settings.py`
- `backend/dealroom/operations.json`
- `backend/dealroom_sign/apps.py`
- `backend/dealroom_sign/client.py`
- `backend/dealroom_sign/counterparty.py`
- `backend/dealroom_sign/counterparty_mail.py`
- `backend/dealroom_sign/e2e/counterparty-audit.cjs`
- `backend/dealroom_sign/e2e/flows.cjs`
- `backend/dealroom_sign/e2e/signature.cjs`
- `backend/dealroom_sign/evidence.py`
- `backend/dealroom_sign/migrations/0003_counterparty.py`
- `backend/dealroom_sign/models.py`
- `backend/dealroom_sign/operations.py`
- `backend/dealroom_sign/recipient_contract.json`
- `backend/dealroom_sign/recipient_logging.py`
- `backend/dealroom_sign/recipient_proxy.py`
- `backend/dealroom_sign/templates/dealroom_sign/base.html`
- `backend/dealroom_sign/templates/dealroom_sign/emails/mail.html`
- `backend/dealroom_sign/templates/dealroom_sign/emails/mail.txt`
- `backend/dealroom_sign/templates/dealroom_sign/recipient.html`
- `backend/dealroom_sign/tests/test_c1b_distribution.py`
- `backend/dealroom_sign/tests/test_counterparty.py`
- `backend/dealroom_sign/tests/test_counterparty_mail.py`
- `backend/dealroom_sign/tests/test_pages.py`
- `backend/dealroom_sign/tests/test_product_reads.py`
- `backend/dealroom_sign/tests/test_recipient_proxy.py`
- `backend/dealroom_sign/tests/test_review_r2.py`
- `backend/dealroom_sign/tests/test_workflows.py`
- `backend/dealroom_sign/tool_map.json`
- `backend/dealroom_sign/urls.py`
- `backend/dealroom_sign/views.py`
- `backend/dealroom_sign/workflows.py`
- `docs/implementation/c1b-report.md`


### Sign

- `apps/remix/server/chief/recipient-listener.ts`
- `apps/remix/server/main.js`
- `chief/inventory/counterparty-contract.json`
- `chief/inventory/counterparty-drift.test.ts`
- `chief/inventory/counterparty-readback.test.ts`
- `chief/inventory/counterparty.test.ts`
- `chief/inventory/fixes.test.ts`
- `chief/inventory/review-r1.test.ts`
- `chief/inventory/review-r2.test.ts`


### Fleet deploy

- `deploy/do1/c1b-preflight.py`
- `deploy/do1/compose.proto.yml`
- `deploy/do1/send-nginx.conf`
- `deploy/do1/test_c1b_topology.py`

