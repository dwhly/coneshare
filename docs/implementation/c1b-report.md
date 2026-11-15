# C1b Gate 3 implementation report

2026-11-15. Gate 3 r3 changes are **uncommitted** in the three supplied worktrees, whose HEADs match Send `f9fef317`, Sign `d596af665` and Fleet deploy `c0401af`. Actual existing branches are Send `agent/c1b-counterparty`, Sign `agent/c1b-listener` and Fleet deploy `agent/c1b-deploy`; the latter two differ from the brief’s shared branch label. Branches were preserved. This report supersedes the r2 implementation report and applies all 8 major, 14 minor and 7 nit findings, including the manager decisions. No deployed database, private env/key file, production Compose file or project memory was changed. No live acceptance result is claimed.

## Per-item evidence

`G3` = `backend/dealroom_sign/tests/test_gate3.py`; `Routes` = `test_gate3_routes.py`; `Proxy` = `test_recipient_proxy.py`. Numbers count test cases, not assertions. Shared tests are identified rather than added twice. Coverage-only and live-only work is distinguished from behavior fixes. All existing assertions remain active; fixtures now model the approved read-back, SMTP wire format and retry-clock contracts. The only conditional skip is the explicitly approved cross-repository drift test when `SEND_REPO` is absent.

| ID | Fix | Test | Red → green |
| --- | --- | --- | --- |
| M1 | Leave preparation in `draft`; mark `distributing` immediately before native POST. Honor `next_attempt_at`, retain the safe real error and publish a History error. Attempted release remains fail-closed. | G3 `m1_preparation_failure`, `m1_attempt_marker`; existing unexpected-error backoff assertions retained with the clock advanced to each due time | **2 failed → 2 passed** |
| M2 | Preparation/definite transient rejection returns to pending; exponential 45/90/180/360/720-minute delays, six attempts over 23h15m plus processing time, then failed History alert. Human sender Retry email requeues only failed effects; permissions and actual acting staff identity are audited. Uncertain acceptance stays held. | G3 preparation (2), SMTP (3), six-attempt limit, role endpoint (3), link recomposition, reader visibility, non-owner writer audit | **12 failed → 12 passed** across the initial and follow-up red runs |
| M3 | Final mail lists only non-CC parties' display names and recorded companies; missing name falls back to requester display name, never email. Completion times use sender timezone. | G3 `m3_private_final_mail_and_nit5_distinct_copy` | **1 failed → 1 passed** |
| M4 | Reload workflow with `select_for_update`; hold the row through staging/publication; save explicit projection fields. Preserve lease, attempts, error and schedule. Done workflows only inspect audit, without downloading or staging again. | G3 concurrent lease/state preservation and completed no-restaging | **2 failed → 2 passed** |
| M5 | Routine preview startup preserves `9445:8994`. | Fleet `test_m5_proto_up_preserves_recipient_route` | **1 failed → 1 passed** |
| M6 | Supply a matching source PDF to the unconsented negative test, add a consented forwarded-byte control, wrong Origin and non-JSON negatives. | Proxy `test_native_post_requires_origin_json_consent_and_source_hash`; consent-removal mutation | **1 mutation failure → 1 restored pass**; mutation reached the upstream client, so the test fails for the intended reason |
| M7 | Restore Django HTTP coverage for checking, awaiting seal and verified NDA publication, ending at the exact :9443 room destination. | Routes `test_m7_nda_return_only_redirects_after_verified_publication`; redirect-removal mutation | **1 mutation failure → 1 restored pass** |
| M8 | Repair all three live suites for marker stripping and file-backed proxy key. Staff denies stay explicit; ownership/byte controls execute on keyed 3001. Mutation baseline must pass before mutation; 3001 mutant changes route rejection while keeping key checks intact. | `http.test.mjs`, `recipient-artifact-access.spec.ts`, `mutate-runtime.py` | **Manager runs live**. JS/TS/Python syntax checks passed; no live red/green claimed |
| Minor 1 | SIZE 552 from MAIL FROM (`SMTPSenderRefused`) and DATA can recompose the pair once as links. Cap and hash actual CRLF SMTP bytes. | G3 two relay rejection variants and CRLF boundary; existing actual-message hash assertion updated to CRLF | **2 failed / 1 passed → 3 passed** |
| Minor 2 | Final Date uses publication/completion time, stable across retries; invitation Date retains release time. | G3 `minor2_final_date` | **1 failed → 1 passed** |
| Minor 3 | Disable HTML escaping only for the text/plain template; retain HTML escaping. | G3 `minor3_plain_text` | **1 failed → 1 passed** |
| Minor 4 | SMTP timeout defaults to 30s, configured within 1–60s. | G3 `minor4_smtp_timeout` | **1 failed → 1 passed** |
| Minor 5 | Verify both empty auth arrays in editor read-back; verify NONE and every false mail flag after distribution and on uncertain-release reconciliation. | G3 auth (2), post-release flags (3), uncertain-release retry; Sign actual-schema test | **6 failed → 6 passed**, plus **1 schema test passed**. Corrected nested-auth contract separately reproduced 4 failures before correction |
| Minor 6 | Missing/blank capability key fails closed; no SECRET_KEY fallback. Preflight requires identical nonblank keys across web/poll/worker and a distinct proxy key. | G3 key unset/blank/null; Fleet capability preflight | **4 failed → 4 passed** |
| Minor 7 | CC room deadline starts at local final publication, then adds a calendar year. | G3 `minor7_cc_deadline` | **1 failed → 1 passed** |
| Minor 8 | Default due time is converted to sender timezone before formatting. | G3 `minor8_default_due_time` | **1 failed → 1 passed** |
| Minor 9 | Sweep done workflows for late native EMAIL_SENT audit alerts, with a 15-minute interval and no file-back repeat. | G3 `minor9_sweep_observes_late_native_mail` | **1 failed → 1 passed** |
| Minor 10 | Enqueue a separate requester copy: R7 incoming requester, otherwise sending staff. Same published artifacts; its own copy-only personal capability, no native token and no recipient's bearer link. | G3 requester incoming/outgoing, dedup, destination, paired attachments and separate capability; Routes download/native-write boundary | **2 failed → 2 passed**, plus **1 HTTP boundary pass** |
| Minor 11 | Expire prior grants instead of cascade-deleting their rows on rotation/revocation; delete the old Django session transport. Preserve challenge attempts and usage history. | G3 `minor11_code_history`; existing rotation, revocation, lockout tests | **1 failed → 1 passed** |
| Minor 12 | Check every service for proxy-key leakage, exact loopback 8990/8994 publication, private 3001, read-only mounts and runtime-user readability. Explicit checks survive `python -O`. | Fleet four preflight regressions using fictional resolved config and a fake Docker executable | **4 failed → 4 passed**; actual preflight is **manager runs live** |
| Minor 13 | Add HTTP CSRF/Origin, consent, alternate access, handoff/cookie/replay, five-attempt lockout, wrong-session challenge, planted-cookie, invalid-hop/missing-key, HMAC purpose-separation coverage. | Six Routes cases (multiple positive/negative assertions each) | **6 passed** on existing behavior; coverage addition, no production behavior change required |
| Minor 14 | Pin `main.js` wiring and all forwarded/real-IP/marker stripping. Drift uses only `SEND_REPO`; absent skips clearly, empty or invalid fails, configured checkout runs. | Sign `gate3.test.ts`, `gate3-drift-runner.test.ts`, actual configured drift | **3 drift-runner failures → 3 passes**; **2 wiring/header tests passed**, configured drift passed |
| Nit 1 | Case-insensitive staff path checks, including `.DATA` and configured base path, in first-party listener only. | Sign `nit1 staff boundary` | **1 failed → 1 passed** |
| Nit 2 | Rate-limit keys use validated canonical `client_ip`, rejecting multi-hop/invalid XFF. | Routes `nit2_rate_keys` | **1 failed → 1 passed** |
| Nit 3 | Parse nginx blocks and check effective marker clearing for every staff proxy location, including inheritance. Server default also covers MCP; a new location overriding headers without clearing is detected. | Fleet effective-location test plus mutation control | **1 failed / 1 passed → 2 passed** |
| Nit 4 | Remove unused `nda` transport argument; both workflows share one NONE release contract. | Existing distribution and workflow tests, with auth and post-release controls | Refactor; no behavior change, all assertions retained |
| Nit 5 | Final mail has its own preheader and completed-documents footer. | Shared M3 regression | **1 failed → 1 passed** (shared with M3) |
| Nit 6 | Each attempt and outcome receives a distinct event identity; repeated failures remain visible. | G3 `nit6_each_failed_delivery_attempt_has_history` | **1 failed → 1 passed** |
| Nit 7 | Boundary rejection requires exactly 403. | Proxy host/listener combinations (4 cases) | **4 passed**, stronger coverage assertion |

## Local validation

Final local results: No stack deployment, SMTP relay acceptance, real browser signing, live mutation result or screenshot is implied by these checks.

- Send signing suite: **295 passed, 2 inherited webhook baseline failures**; subsequent requester HTTP boundary follow-up **1 passed**.
- Sign inventory/listener/schema/drift suite, `SEND_REPO=/root/worktrees/send-c1b`: **137 passed, 0 failed, 0 skipped**.
- Fleet topology: **5 passed**. Fictional resolved-config preflight: **5 passed**.
- Operation inventory: **311 total / 102 staff**, including human-only `dealroom_sign_SignatureEmailRetryView_endpoint_post`; registry regenerated without changing scope rules.
- Live-harness syntax: `node --check` (HTTP), TypeScript transpilation diagnostics (artifact-access Playwright), Python AST/compile (mutation/preflight), `bash -n` (proto-up): passed.
- No model or migration change. Existing `0003_counterparty` remains additive and unchanged. Disposable test databases used the existing migration chain only.
- All three worktrees pass `git diff --check`; branch and starting HEADs are unchanged, with no staged changes.

Commands:

```sh
# Fictional test-only capability key; the runner and webhook baseline remain unchanged.
SIGN_CAPABILITY_KEY=fictional-local-test-key \
  /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
cd /root/worktrees/sign-c1b
SEND_REPO=/root/worktrees/send-c1b CI=true node --import tsx --test chief/inventory/*.test.ts
cd /root/worktrees/fd-c1b
/root/work/sign-product/send-venv/bin/python deploy/do1/test_c1b_topology.py
python3 deploy/do1/test_gate3_preflight.py
```

The inherited webhook failures are `test_webhook_hint_auth_and_no_payload_trust[unit-test-secret-202]` and `test_webhook_enqueue_failure_retryable`. Their assertions and configuration-sensitive baseline have not been changed or skipped. Intermediate fixture corrections (nested auth arrays, CRLF hash expectations, trusted XFF, retry clock advancement) are not counted as product fixes in the table.

## Contract and implementation decisions

1. **Release read-back:** the already-classified `POST /api/deal/envelope/editor/get` retains reminder/expiration settings and returns auth arrays under `authOptions`. Native `distribute` returns an acknowledgement, so post-release verification uses the existing classified `GET /api/v2/envelope/{id}`, whose schema retains `distributionMethod` and `emailSettings`. Actual pinned schemas are tested. Zero native upstream lines; no new authority. Whether editor-get accepts the team API credential and returns a bare object still requires the manager's live check.
2. **Retry persistence:** existing `ObservedSignEvent` records hold attempts, manual retry boundaries and outcomes. Backoff is derived from durable attempts and the effect timestamp, under the effect row lock. A deliberate retry resets the attempt window without erasing History, retaining Message-ID and effect identity. The final write cannot overwrite a stale worker's `delivery_uncertain` hold. No migration is needed.
3. **Requester copies:** use the existing CC/final-copy capability model with synthetic recipient ID `requester`, empty native token and its own effect. It can reach only the existing final-copy surfaces; it does not appear in the parties list. This implements the explicitly authorized requester copy without sending someone else's capability. The signed PDF/certificate come from the same checksum-verified publication manifest.
4. **History and sender retry:** request detail exposes safe `last_error` plus human `email_effects` (`state`, error and `can_retry`). Retry email is `POST /api/v1/dealroom-sign/requests/{request_id}/emails/{effect_id}/retry` with `{}`, through the existing trusted human board proxy. Request/board scope is rechecked; writer/manager or eligible owning staff only, reader/service/API-key actors excluded. Only `failed` is accepted; uncertain effects cannot be retried through this operation. The audit records the actual actor, including a non-owner writer.
5. **Reconciliation:** preserve the lease/retry fields from the freshly locked row and save only the fields owned by reconciliation. The completion guard now precedes original/sealed-PDF fetches and staging. Ongoing native POSTs still perform their intentional fresh-source-hash check.
6. **Retention:** rotated grants remain expired to retain challenge history; their old Django sessions are deleted and cannot authorize requests. Revocation also expires grants and increments generation. Capability roots must persist across restarts; routine revocation uses generation, not root-key rotation.

## Sign upstream accounting

The original first-party-directory exclusion file and thresholds are unchanged. The requested `packages/app-tests/e2e/api/chief/recipient-artifact-access.spec.ts` was introduced by this fork (`8d1bfc294`) and is absent from `v2.21.1`, but its directory is **not** in those exclusions. Consequently the mechanical path-based budget counts its requested test edits. It is explicitly accounted for rather than hidden by a new exclusion.

| Comparison, actual working tree | Mechanically counted files | Added / deleted | Total churn |
| --- | ---: | ---: | ---: |
| r3 vs `d596af665` | 1 (fork-authored E2E test) | +27 / −5 | 32 |
| C1b vs `6c4757feb` | 2 (`main.js` and that test) | +29 / −7 | 36 |
| C0 + C1b vs `d3b7f7c6` | 12 | +68 / −489 | 557 |
| Entire fork vs `v2.21.1` | 98 | +2779 / −1748 | 4527 |

**Native upstream-owned C1b edit remains only `apps/remix/server/main.js`, +2/−2. r3 changes to it: zero.** All runtime r3 Sign edits are in first-party `recipient-listener.ts`. No native middleware, schema, component, certificate or route implementation was edited. The inherited whole-fork budget excess remains; this does not claim eventual C1a-and-later combined compliance.

## Manager preview deployment runbook — manager runs live

1. **Prepare the matching candidate.** Build/pin all three reviewed images and preserve the previous immutable manifest. Use only the fictional preview Compose project. Stop new sends and drain old native jobs for the coordinated NONE/mail/listener cutover. Existing raw native invitations must be retired or replaced with bound Send links. Back up the fictional preview database; apply unchanged migration 0003 if not already applied. There is no r3 migration.
2. **Create private configuration as manager.** The manager creates ignored `deploy/do1/proto/send.env` and `proto/fleet-proxy-key`; do not commit values. `SIGN_CAPABILITY_KEY` is a persistent independent secret shared by web/poll/worker, with no SECRET_KEY fallback. Proxy key path/value must not enter shared Send env: Compose supplies its file mount/path only to send-web and Sign. Arrange owner/group/mode (or ACLs) so Send's `coneshare` worker user and Sign's configured runtime user can read the file; no world permissions. These are separate keys.

   Fictional-preview-only generator example, run by the manager from Fleet deploy after creating the ignored env file. It appends only when no capability key is already configured, refuses to overwrite a proxy key and prints neither value:

   ```sh
   umask 077
   python3 - <<'PY'
   import secrets
   from pathlib import Path
   env = Path('deploy/do1/proto/send.env')
   proxy = Path('deploy/do1/proto/fleet-proxy-key')
   text = env.read_text()  # manager must create this ignored preview file first
   if any(line.strip().startswith('SIGN_CAPABILITY_KEY=') for line in text.splitlines()) or proxy.exists():
       raise SystemExit('Preview keys already exist; preserve them or handle rotation explicitly')
   with env.open('a') as output:
       output.write('\nSIGN_CAPABILITY_KEY=' + secrets.token_urlsafe(48) + '\n')
   with proxy.open('x') as output:
       output.write(secrets.token_urlsafe(48) + '\n')
   PY
   ```

   Set the actual file ownership/read permissions after generation. Root-key rotation invalidates existing personal links; it is not a routine deploy step.
3. **Set preview endpoints and Mailpit.** `SIGN_RECIPIENT_ORIGIN=https://h-do1.tailb554cd.ts.net:9445`, `SIGN_RECIPIENT_INTERNAL_URL=http://sign:3001`, `SIGN_INTERNAL_URL` remains private Sign 3000, `SITE_DOMAIN` remains Send :9443; allow the recipient hostname in Django. Configure Django SMTP to Mailpit only: backend SMTP, host `mailpit`, port `1025`, TLS false, `EMAIL_TIMEOUT=30`, no external relay credentials. `SIGN_FROM_EMAIL=sign@fleet.test`, `SIGN_REPORT_EMAIL=support@fleet.test`, `SIGN_MESSAGE_DOMAIN=fleet.test`, `SIGN_MAIL_MAX_BYTES=14680064`. Optional `SIGN_SMTP_SIZE` is an additional conservative cap. Preserve native Mailpit delivery for negative assertions.
4. **Run the actual preflight.** On the manager host, run `python3 deploy/do1/c1b-preflight.py`. It resolves the preview config without displaying values, checks all service mounts/env, compares capability keys, requires loopback 8990/8994 and private 3001, and runs disposable `--no-deps` containers to check key readability as `coneshare`/Sign's configured user. This needs Docker, candidate images and private config; local fake-Docker tests are not a substitute. Then start the matching candidate stack.
5. **Confirm routing persists.** :9443 → 8990 (Send staff/NDA); :9444 → 8991 (Sign staff); **:9445 → 8994** (Django recipient 81); :9446 → 8993 (Mailpit). `proto-up.sh` now preserves this mapping. Never publish Sign 3001. Staff nginx clears the marker in every effective proxy location; recipient 81 supplies the marker and the trusted single-hop XFF/Host/Proto.
6. **Run live Sign checks with the real proxy-key file.** `http.test.mjs`, Playwright artifact-access, and `mutate-runtime.py` are **manager runs live**. Use the fictional preview credential/database fixtures. The test runner must reach private 3001; on the Linux manager host, use the candidate Sign container's private bridge IP (obtained with Docker inspect) or a runner on that private network. Do not publish 3001 to make tests work. Set `FLEET_PROXY_KEY_FILE` to the manager-readable ignored file, `SIGN_BASE` to staff 3000/8991, `SIGN_RECIPIENT_BASE` to private 3001, `SIGN_RECIPIENT_ORIGIN` to public :9445, `CHIEF_E2E_RECIPIENT_URL` to that same private 3001 endpoint, and `SIGN_CONTAINER` to the candidate container for mutations. Configure the Playwright test environment's `NEXT_PUBLIC_WEBAPP_URL` and database for this same fictional stack.

   ```sh
   # From Sign, with the manager's private fixture/env already configured:
   CI=true node --test chief/inventory/http.test.mjs
   CI=true npm run test:dev -w @documenso/app-tests -- e2e/api/chief/recipient-artifact-access.spec.ts
   python3 chief/inventory/mutate-runtime.py
   SEND_REPO=/root/worktrees/send-c1b CI=true node --import tsx --test chief/inventory/counterparty-drift.test.ts
   ```

   Missing/wrong request keys must fail 403; a separate candidate instance with absent/blank configured key must fail 503. Confirm 3000 marker stripping, token-route denial and staff download controls. The 3001 route mutation receives the key, changes the route-rejection status, and leaves both key checks and downstream middleware intact; its baseline must pass first. No live mutation was run in this coding session.
7. **Run real signing and mail acceptance.** Execute unchanged `flows.cjs` with private `SIGN_FIXTURE_FILE`, `GLUE_URL`, `MAILPIT_URL`, `PLAYWRIGHT_MODULE`, `SHOTS`; run `counterparty-audit.cjs` with its private config. Check original signing/file-back timing assertions, bound consent and NDA return, actual browser IP/UA audit, no native EMAIL_SENT, and actual team-token editor-get behavior. Inspect raw MIME: no party emails/CCs, correct sender timezone, final Date/preheader/footer, paired filenames and hashes, CRLF size boundary and MAIL FROM/DATA 552 fallback. Confirm a separate requester delivery (incoming requester and staff fallback), including oversized link-only copies, with no shared signer capability.
8. **Exercise recovery and History.** Cause a definite pre-distribute error: draft/backoff and the real safe History error must persist. A native POST with unknown outcome must stay held. Cause preparation/SMTP 4xx failures: inspect the six-attempt schedule and final alert, then use the trusted sender Retry email operation and verify actual actor History. Confirm reader, cross-board, service and uncertain-effect retries are denied. Uncertain SMTP acceptance must be investigated by stable Message-ID against Mailpit; never blindly reset it. Observe a late native EMAIL_SENT on a done workflow and confirm the History alert without republishing artifacts.
9. **Rollback if needed.** Stop new sends/effects; preserve data, signatures, artifacts, capability roots and access enforcement. Do not reverse 0003, restore raw native bypasses, publish 3001 or replay uncertain delivery/distribution. Keep reconciliation available for held outcomes.

## Remaining acceptance limits

All live checks above, including visuals, relay behavior and real signing, remain manager acceptance work. C3 interim copies/full request room, C4 polished recipient UI, C5 optional-code issuance/UI and reminder scheduling, and C6 questions/paper/decline remain the previously agreed later slices. Public exposure, external SMTP delivery and public seal trust are outside this fictional preview scope.
