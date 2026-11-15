# C1b Gate 3 implementation report

**Current revision: r6.** The r6 section below records the live-acceptance fixes. Earlier sections retain their historical evidence; r6 corrections take precedence.

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
# r4 test fixtures provide fictional keys; no capability-key environment variable is needed.
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
   import re
   from pathlib import Path
   env = Path('deploy/do1/proto/send.env')
   proxy = Path('deploy/do1/proto/fleet-proxy-key')
   text = env.read_text()  # manager must create this ignored preview file first
   if any(re.match(r'^\s*(?:export\s+)?SIGN_CAPABILITY_KEY\s*=', line) for line in text.splitlines()) or proxy.exists():
       raise SystemExit('Preview keys already exist; preserve them or handle rotation explicitly')
   with proxy.open('x') as output:
       proxy.chmod(0o600)
       output.write(secrets.token_urlsafe(48) + '\n')
   env.chmod(0o600)
   with env.open('a') as output:
       output.write('\nSIGN_CAPABILITY_KEY=' + secrets.token_urlsafe(48) + '\n')
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


## C1b r4 — Gate-3 re-review r2

The r4 starting HEADs are Send `65153e67`, Sign `2b12cbd04`, Fleet deploy `2daee98`. Changes remain uncommitted. The r3 sections above are historical evidence; the corrections below supersede their party fallback, requester-copy scope, polling, test-key setup and runbook claims.

### Concurrency and mutation limits

Reconciliation holds the workflow row lock through native get/audit pagination and completed-file staging (up to approximately 40 seconds of network work). Consequently parallel tRPC calls and co-signers wait for that same workflow lock, including read-only proxied requests. This preserves the existing atomic publication and no-restaging guarantee; no claim of concurrent read throughput is made. Static requests bypass reconciliation. A later change would need an independently verified observation/publication split before moving network I/O outside this lock.

Live mutant 3 changes the listener's route-rejection **status** from 404 to 200, while still refusing to forward. It does not prove that removing the listener route gate is detected: native middleware repeats that check, and could mask a missing listener check. The keyed HTTP baseline and status mutation remain useful but are not proof of layer independence. Local listener tests directly observe non-forwarding; live layer-removal acceptance remains a separate test.

Retry email deliberately permits scoped human board writers/managers, including a non-owner writer (r3's approved behavior and actor audit). Revoke additionally requires workflow ownership because it invalidates recipient access. The unreachable JWT-owner retry fallback has been removed; no role or ownership assertion was relaxed.


### Per-item fixes and red → green evidence

`R4` = `backend/dealroom_sign/tests/test_gate3_r4.py`; `G3` = `test_gate3.py`; `Routes` = `test_gate3_routes.py`; `Report` = `test_gate3_r4_report.py`. Counts are test cases, except explicitly labelled subtests/mutation runs. Coverage-only mutations restore the exact original file in `finally`; no mutation remains. The corrected `Requester` → `Signer 1` assertion is the explicitly requested contract correction. All other existing assertions remain active.

| Review item | Final change and evidence | Red → green |
| --- | --- | --- |
| Major 1 | Staff gate decodes once, strips `.data` before all trailing slashes, strips configured base path, rejects ambiguous encodings, doubled slashes and semicolon parameters, and denies the entire `/sign/` namespace. Procedure comparisons are case-insensitive. `gate3-r4.test.ts` covers every (a)–(e) surface, mixed case, suffix/encoding variants and real installed router behavior. | **8 initial failures + 3 suffix follow-up failures → 13 passed** |
| Major 2 | `mail.attempt` is written only after eligibility passes. Waiting uses a durable `mail_waiting` effect state detail, checks at most every 15 minutes, wakes on eligible reconciliation, creates zero History across 50 sweeps, and consumes no drain delivery slot. Deferred effects are filtered in SQL before attempt-history queries. Preparation errors have separate `mail.preparation_attempt` facts and retain the bounded failure policy. R4 `major2_*`. | **2 failing cases + 1 query-cost follow-up failure → 2 passed** |
| Major 3 | Party rows use neutral `Signer N`, never requester identity; skip CCs and suppress address-valued names/companies. Final concern reporting uses Reply instead of a body mailto address. Corrected G3 expectation plus multi-signer/header/body and address-valued-label regressions. | **3 failed → 3 passed** |
| Minor 1 | New autouse fictional capability-key fixture; standalone Django process still fails closed with no key. Documented runner needs no key env var. The two inherited webhook failures also now set their own fictional webhook secret in those tests, without changing any assertion. | **1 capability fixture failure → pass**; **2 inherited webhook failures → pass**; standalone and three existing missing-key negatives pass |
| Minor 2 | Command validation accepts bounded optional `company` metadata, preserves it for mail and request fingerprints, and leaves absent-company fingerprints unchanged. R4 `company_survives_command_validation`. | **1 failed → 1 passed** |
| Minor 3 | Case-insensitive requester-address dedup reuses that recipient's existing completion capability/effect when the requester is a signer or CC. R4 `requester_copy_reuses_existing_recipient`. | **2 failed → 2 passed** |
| Minor 4 | NDA workflows do not enqueue a room-owner/requester copy; the member retains their normal final copy. R4 `nda_has_no_requester_copy`. | **1 failed → 1 passed** |
| Minor 5 | Validate capability-key availability in draft before native distribute or the attempted-release marker. R4 asserts no distribute call and unchanged draft state. | **1 failed → 1 passed** |
| Minor 6 | Watch late native mail for 24 hours after completion, poll at 15-minute intervals, prioritize active work, and keep completed-workflow errors out of History. R4 expiry/priority and both SignError/unexpected-error tests. | **3 failed → 3 passed** |
| Minor 7 | Explicitly document the network-under-row-lock tradeoff, read-only request serialization and publication guarantee above. `Report` disclosure check. | **1 failed → 1 passed** (documentation) |
| Minor 8 | Resolve bind sources and reject parent-directory mounts exposing the proxy key, including extra directory mounts on legitimate holders. Fictional preflight test checks mailpit, send-web and Sign. | **1 failing test / 3 failing subtests → all pass** |
| Minor 9 | Add published-3001, writable-mount, renamed-env-value and equal-key negatives. Disable each guard in turn to prove those assertions fail, then restore. | **4 mutation runs fail → 2 restored tests pass** |
| Minor 10 | Document that live mutant 3 is status-only and does not establish layer independence. Local removal of the listener gate fails the direct non-forwarding test even though downstream middleware could mask this live. | **1 documentation failure + 1 gate-removal mutation failure → restored passes**; live runtime remains manager acceptance |
| Minor 11 | Waiting-state write reacquires the effect row lock and requires `running`, preserving a stale worker's `delivery_uncertain`. R4 interrupted-worker regression. | **1 failed → 1 passed** |
| Nit 1 | Wiring test associates each wrapper with its serve call, port variable/default and private-port expression. Swapping the two wrappers fails. | **1 mutation failure → 1 pass** |
| Nit 2 | Ownership E2E explicitly labels staff blanket denial and keyed recipient ownership, with an own-token control on each listener. All original assertions remain. Harness structure test detects the old incomplete controls. | **1 local harness failure → 1 pass**; actual E2E manager runs live |
| Nit 3 | Missing-asset live assertion requires exactly 404. Execute the assertion against 301/403/500 and 404 to prove its strength. | **3 failed / 1 passed → 4 passed**; actual HTTP manager runs live |
| Nit 4 | Reject empty native tokens before comparing tRPC scope, including all three allowed read operations. R4 empty-token cases. | **3 failed → 3 passed** |
| Nit 5 | Remove unreachable owner fallback from retry permissions; retain board writer/manager authorization and document its intentional difference from revoke. Existing reader/non-owner/actor audit assertions remain. | **1 failed → 1 passed**, existing permission tests pass |
| Nit 6 | Final-copy alternate-access footer refers to a link; invitations retain their button wording. R4 checks text and HTML. | **1 failed → 1 passed** |
| Nit 7 | Alternate-access CSRF negative supplies correct Origin, isolating missing CSRF. Removing the CSRF rejection makes this specific assertion fail. | **1 mutation failure → 1 pass** |
| Nit 8 | Exercise capability, alternate, both lookups, session, OTP verification, handoff issuance/consumption and rate-limit call sites against independently derived HMACs. Changing call-site labels while retaining the hash function fails all eight cases. | **8 mutation failures → 8 passes** |
| Nit 9 | Proxy-secret leakage check rejects substring values such as `Bearer <key>` under any env name; errors print no values. | **1 failed → 1 passed** |
| Nit 10 | Topology parser recursively checks nested proxy blocks, rejects unresolved includes at every level and requires a staff server. | **4 failed → 4 passed** |
| Nit 11 | Execute the actual documented generator against disposable files: proxy creation precedes env append, both modes are 0600, ordinary/export/spaced existing assignments are preserved, failed proxy creation leaves env unchanged. | **4 failed / 1 passed → 5 passed** |
| Nit 12 | A post-release mail-settings mismatch records one error and quarantines the workflow for operator review. It cannot distribute again or keep adding scheduled History. | **1 failed → 1 passed** |

### Contract corrections and limits

- **Message-ID exception:** under the standing contract-mismatch authority, retain the stable protocol Message-ID (`<opaque-effect-hash@configured-domain>`), which requires `@`. The multi-signer test checks all MIME-part headers, excluding only To/From/Reply-To and this separately validated opaque Message-ID. The multi-signer regression requires no `@` in subject, other headers, text and HTML; no recipient address enters the Message-ID. Removing Message-ID would conflict with the existing stable-identity/uncertain-delivery contract. No existing Message-ID assertion was removed.
- **NDA scope:** requester completion mail is for room-document requests, not member NDAs. Deduplication never creates a second capability for the same requester address.
- **Late mail:** the 24-hour automatic watch is bounded. Native mail occurring after that window requires operator audit; active reconciliation still records any native mail it observes. Done-workflow failures retain safe `last_error` and a 15-minute schedule without History spam.
- **Mismatch recovery:** `release_mail_settings_mismatch` is quarantined after the first failure; an operator must investigate native release settings before recovery. No automatic resend or fallback is introduced.
- **Router decoding:** installed Node/Hono constructs a WHATWG URL; Hono `getPath` uses `decodeURI`, preserving encoded `/`, and parameter access decodes it. React Router normalizes `.data` and trailing slash, decodes each segment, preserves encoded separators during matching, and matches routes case-insensitively with trailing slashes allowed. Semicolons remain literal parameter text. The staff gate is deliberately stricter: leftover percent encodings, semicolons, backslashes and doubled slashes fail closed. Encoded dots/separators cannot reach recipient loaders.
- No production key/env, deployed database, schema/migration, project memory, or native upstream Sign implementation was changed. All deployment, real browser, SMTP and live runtime mutation acceptance remains manager work.

### r4 upstream accounting

Existing first-party exclusions and budgets are unchanged. `recipient-artifact-access.spec.ts` is fork-authored (absent upstream), but its path is mechanically counted; its r4 changes are **+8/−3**, all test labels/controls. Native upstream-owned r4 churn is **zero**. `main.js` remains the sole C1b native-owned edit, **+2/−2**, unchanged by r4.

| Comparison against actual r4 working tree | Mechanically counted files | Added / deleted | Churn |
| --- | ---: | ---: | ---: |
| r4 vs `2b12cbd04` | 1 fork-authored E2E test | +8 / −3 | 11 |
| C1b vs `6c4757feb` | 2 | +37 / −10 | 47 |
| C0 + C1b vs `d3b7f7c6` | 12 | +76 / −492 | 568 |
| Entire fork vs `v2.21.1` | 98 | +2784 / −1748 | 4532 |

The inherited whole-fork budget excess remains. No exclusion or threshold was added to hide it.

### r4 final validation

- Send signing suite, with **no capability-key environment variable**: **333 passed, 0 failed, 0 skipped**. The inherited webhook tests now pass using explicit fictional test settings. The runner emits 43 inherited JWT test-key length warnings.
- Final Send follow-up after filtering deferred mail effects before attempt-history queries: **77 passed**. This includes all R4 mail/workflow regressions, G3, counterparty-mail and executable report checks. The standalone missing-key test still fails closed outside pytest's fixture.
- Sign inventory/listener/schema/drift/harness suite with `SEND_REPO` set: **155 passed, 0 failed, 0 skipped**.
- Fleet: **9 preflight tests + 9 topology tests passed**. Four guard-removal mutations failed before restoring preflight.
- HTTP harness JS syntax, artifact E2E TypeScript transpilation, Python mutation-script parsing and all three `git diff --check` runs passed.
- All supplied HEADs are unchanged; all changes are unstaged/uncommitted. Native upstream-owned Sign runtime diff against r4 HEAD is empty. No migration was created or modified.

Commands used:

```sh
/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b \
  dealroom_sign/tests/test_gate3_r4.py dealroom_sign/tests/test_gate3.py \
  dealroom_sign/tests/test_counterparty_mail.py dealroom_sign/tests/test_gate3_r4_report.py
cd /root/worktrees/sign-c1b
SEND_REPO=/root/worktrees/send-c1b CI=true node --import tsx --test chief/inventory/*.test.ts
cd /root/worktrees/fd-c1b
python3 deploy/do1/test_gate3_preflight.py
/root/work/sign-product/send-venv/bin/python deploy/do1/test_c1b_topology.py
```

[Local failure/pass summaries](c1b-r4-test-evidence.txt) retain the failing regression names and mutation results. Live E2E/HTTP/SMTP/runtime mutations are still manager-run acceptance, with the limitations explicitly described above; local harness checks do not claim those live results.

## r5 — Gate-3 re-review r3

Starting HEADs: Send `999129a7`, Sign `f0cb8d0f1`, Fleet deploy `97b91ab`. Changes remain uncommitted. This revision addresses the one major, one minor and two nits in `counterparty-c1b-gate3-r3.md`.

### Boundary and compatibility decisions

The staff listener on 3000 validates every supplied JSON tRPC input, including every indexed member of `batch=1`, on GET and POST. Envelope keys are limited to `json` and `meta`; metadata keys are limited to `values` and optional version `v: 1`. Every annotation must be exactly `['undefined']`. Root undefined (the installed client's encoding of a no-argument call), dotted nested undefined paths and array element undefined are supported. Unknown envelope/metadata keys, referential equalities, other annotations and malformed batch membership fail closed. A no-input GET still reaches native staff authentication/schema checks. Input bytes are preserved for the native handler.

The existing token-field/recipient-access/user-mode predicate runs both on raw `json` and on the result of the installed `SuperJSON.deserialize` for both dual-mode procedures. Token-only procedures remain denied. The shape and deserialization layers are independent: temporary source variants remove each guard alone and still deny both reference payloads, with single/batched GET/POST coverage; removing both forwards those same payloads as the mutation control. No runtime switch disables either layer.

**Annotation audit:** inspected tRPC request schemas and staff UI call sites. Analytics requests use calendar strings (`from`/`to`); their Date schemas are response data. Embedding-presign and email-auth expiry Dates are responses. The request Date at `templateUpdatedAt` belongs to direct-template recipient signing (`createDocumentFromDirectTemplate`), not a staff-only flow. Staff editor Maps/Sets are local lookup collections. No non-undefined annotation exception is granted, including for token-capable procedures. Both drift-contract copies now pin installed **superjson 2.2.5**; drift checks compare the actual package resolved from both the native transformer and listener with the contract and lockfile.

**Multipart transport:** existing staff upload callers use the native tRPC FormData handler, which does not call SuperJSON. Preserve only single, unbatched POSTs to the eight inspected authenticated upload procedures: `envelope.create`, `envelope.use`, `envelope.item.createMany`, `envelope.item.replacePdf`, `document.create`, `template.createTemplate`, `team.settings.updateBrandingLogo`, and `organisation.settings.updateBrandingLogo`. This is a transport distinction, not a metadata exception: JSON calls to these same procedures receive both checks. Token-capable routes cannot use this allowance. Tests preserve the uploaded body byte-for-byte through the boundary.

### Waiting and retry decisions

Waiting re-checks have their own `waiting_limit=20` cap per drain, independent of the delivery `limit`. SQL selects only the oldest due waiting effects up to that cap; remaining due effects retain their timestamp for the next pass. Waiting checks that remain ineligible still consume no delivery slot. Tests cover delivery limits 1 and 3, 25 due waiting effects, delivery progress in the same pass and the remaining five re-checks on the next pass.

**Nit 2 — waiting-plus-outage:** retain the existing fail-closed preparation-attempt policy. If a waiting invitation's re-check encounters a Sign outage, that failure counts as `mail.preparation_attempt` even when the signer **never became eligible**. Six failures separated by 45, 90, 180, 360 and 720 minutes exhaust retries **23 hours 15 minutes** after the first preparation failure (plus scheduling/processing delay; the first waiting re-check is due after 15 minutes). The effect becomes `failed`, produces the existing failure History and requires **manual Retry email** by an authorized sender/writer after recovery. It is not automatically awakened by later eligible reconciliation while failed. No delivery is attempted during this outage. The clock-driven regression pins all six transitions, elapsed time and zero SMTP sends; this revision documents the behavior rather than changing its retry budget.

### Per-item red → green evidence

| Review item | Regression evidence | Red → green |
| --- | --- | --- |
| Major 1 | `chief/inventory/gate3-r5.test.ts`: both dual-mode procedures, GET/POST, single and each of three batch positions; shape negatives for every inventoried procedure plus an unknown future procedure; malformed batches; ordinary staff/undefined/multipart controls. `counterparty-drift.test.ts` checks the installed version. | Initial **22 failed / 4 passed → 26 passed**: 16 reference-payload failures, 4 shape/batch failures, 1 missing version pin, 1 missing independent-guard test prerequisite. |
| Major 1, independent layers | Temporary module variants remove the shape guard alone, the decoded guard alone, then both. One remaining guard denies all 8 reference-payload combinations; removing both forwards all 8 controls. Additional tests show permitted undefined annotations can create a `token` field, requiring the decoded check even without referential equalities. | Both-layer control confirms forwarding; each single-layer variant confirms denial. Removing the decoded guard causes **2 additional failures → 2 restored passes**. Final focused set: **28 passed**, included in the 182-test suite below. |
| Minor 1 | `test_gate3_r5.py::test_waiting_rechecks_have_independent_per_pass_cap`: 25 due waiting effects and delivery limits 1/3. Old code performs 26/28 reconciliations; fixed code performs 21/23, preserves the five deferred rows, makes delivery progress and services the remainder next pass. | **2 failed → 2 passed** |
| Nit 1 | Existing R4 50-drain assertions remain intact; advance to 16 minutes after the first wait, prove another native reconciliation occurs, then assert zero added Activity/History and zero mail facts. A mutation logs only on that later re-check. | Existing behavior passes; **1 re-check-only mutation failure → 1 restored pass** |
| Nit 2 | `test_report_discloses_waiting_outage_retry_exhaustion` plus a six-failure clock-driven behavior control with no SMTP send. Document the retained bounded preparation-attempt policy above. | **1 documentation failure → 1 pass**; existing outage behavior control passes |

### r5 final validation and footprint

- Send: **98 targeted tests passed**, including R5, R4, G3, counterparty mail, recipient proxy and executable report checks. No failure or skip. This is a targeted run, not a claim to have rerun the entire Send backend.
- Sign: **182 inventory/listener/schema/drift/harness tests passed, 0 failed, 0 skipped**, with `SEND_REPO=/root/worktrees/send-c1b`. Strict scoped TypeScript checking of the listener and changed tests passed with no diagnostics.
- Fleet deploy: **9 preflight + 9 topology tests passed**. No Fleet source change was necessary.
- Sign r5 footprint against `f0cb8d0f1`: **zero upstream files, +0/−0 lines**, including mechanically counted paths. Every changed/new Sign file is within the existing first-party exclusions; those exclusions and budgets are unchanged. `main.js` is unchanged, retaining the historical C1b +2/−2 integration. The inherited whole-fork budget excess described in r4 remains.
- No existing assertion was weakened, skipped or deleted. R4's History test only gains assertions. Temporary mutation sources are removed/restored; no mutation remains.
- All three supplied HEADs are unchanged, all changes remain unstaged/uncommitted, and all three `git diff --check` checks pass. No migration, production configuration, secret or deployed database was changed. Project memory remains unchanged without explicit confirmation.
- Live browser/HTTP/SMTP/deployment acceptance remains manager-run; these local results do not claim live acceptance.

[r5 failure/pass evidence and exact commands](c1b-r5-test-evidence.txt) record the red runs, mutation outcomes, final suites and footprint check.


## r6 — Live-acceptance fixes

Starting HEADs: Send `99a97ef1`, Sign `5b29ff6c9`, Board `07257f1`. Changes are unstaged and uncommitted. Sign has **zero changed files and +0/−0 upstream lines**. No database schema, migration, production data or project memory was changed.

### Per-item red → green

`R6` below is `backend/dealroom_sign/tests/test_live_acceptance_r6.py`. Initial Send regressions: **38 failed / 35 passed**; the additional room-page regression: **1 failed / 6 controls passed**. nginx policy checks subsequently reproduced **2 failures**. Missing-name consistency reproduced **1 failure / 7 controls passed**. The exact preview Dockerfile follow-up reproduced **5 failures** against the unchanged proxy before restoration. Final R6 set: **95 passed**. All assertions remain active; fixture corrections supplied the configured recipient origin, parsed forms with implicit actions, and used the actual `/signing/room/<slug>` route behind nginx's `/view/` rewrite.

| Item | Change and regression | Red → green |
| --- | --- | --- |
| 1. Consent / Origin | HTML headers **and the shared meta tag** use `same-origin`. The proxy keeps exact Origin and CSRF checks; null, absent and foreign Origins still return 403. Room/NDA pages and both Send nginx configs no longer override the page with `no-referrer`. The glue nginx header applies only to its static HTML fallback, preserving Django's PDF/JSON policy. R6 reads actual form controls and the effective document policy to submit entry, consent, alternate access and final/certificate downloads; covers code verification fetch, NDA handoff, return, and 21 noncanonical-Origin negatives. | **11 policy/flow failures → passes**, plus unchanged security controls. Real Chromium evidence is recorded below. |
| 2. Assets | `SIGN_RECIPIENT_ASSET_ROOTS` is an ordered settings override; `None` searches `frontend/{dist,public}` under `BASE_DIR` and its parent. An explicit empty list disables serving. Root containment, extension allowlist and fail-closed missing-file behavior remain. Tests serve real CSS/JS/SVG bytes from repo public, repo dist, glue image, preview image and custom roots; destinations are parsed from both `deploy/chief-glue-v1/Dockerfile` and `deploy/sign-product-preview/Dockerfile`, plus the frontend COPY in `deploy/chief-send-proto/Dockerfile`. | **11 failed / 10 passed**, then **5 preview-layout failures → 26 passed**. |
| 3. Missing sender names | Shared display normalization removes blank/whitespace and literal `None` name parts, retaining real parts or falling back to `Requester`. Applied when snapshotting and when rendering already-stored sender names. Incoming/outgoing requester names share the same fallback; requester email is retained. | Staff names: **3 failed / 2 passed → 5 passed**. Requester names: **1 failed / 7 passed → 8 passed**. |
| 4. Human sender | Board supplies authenticated `user.name` / `user.email`; Send validates and stores `requester` for outgoing requests and uses it for From display name, Reply-To, page sender and requester copies. `workflow.owner` and the creator FK retain the service identity; absent requester retains owner fallback. Incoming/outgoing snapshots share email, shape, length and CR/LF validation. Signer routes cannot write this metadata. | Send outgoing/mail/API plus validation: **10 failed / 2 passed → 12 passed**, with 6 additional input/auth controls. Board: **5 failed / 2 passed → 7 passed**; the complete signing module has **37 passes**. |
| 5. Display title | Board forwards its clean `stem` separately from the timestamped storage filename. Send binds title and requester into the idempotency digest and persists the clean workflow/request title. Replays changing either fail. Mail and pages also clean older stored board suffixes. | Board/Send metadata tests above fail before the change and pass afterward; shared coverage, not added twice. |
| 6. Grammar | Text mail, HTML mail/preheader and context pages pluralize pages, signatures and estimated minutes. Covers zero, one and two signatures. | **3 failed → 3 passed**. |
| 7. Timezone | Keep the zone already formatted by `display_time`; remove the duplicate parenthesized zone. UTC and `America/Los_Angeles` (PST) are covered in both mail formats and pages. | **2 failed → 2 passed**. |
| 8. Context heading | Shared title normalization removes `.pdf` and the known legacy board timestamp suffix when rendering existing snapshots as well as provisioning new ones. | **1 failed → 1 passed**, shared with item 5's older-snapshot coverage. |

### Exact Board changes

- `hermes_board/app.py::sig_send_impl` constructs `requester = {"name": user.name, "email": user.email}` from the authenticated `User`, then passes `requester` and `title=stem` to `dealroom.send` in both the existing-room and upload/Drive branches. Timestamped `fname` is retained solely for the uploaded file and version lookup.
- `api_signatures_new` already passes its authenticated `user` into `sig_send_impl`; that call remains intact and receives the new behavior, as does the card-specific route. Both routes are tested with a browser-supplied requester that is ignored in favor of the authenticated identity.
- `hermes_board/dealroom.py::Dealroom.send` adds optional keyword arguments `requester` and `title` and forwards them in the outgoing Send envelope body. This transport change is required to carry the two fields from `app.py` to Send. It does not assert a verified `creator_login` or change the board's read-authority model.
- `tests/test_dealroom_sign.py` extends the fake transport's signature and adds upload/existing-room coverage for both routes, disconnected-Drive rejection controls, and a transport payload test. Existing assertions are unchanged.

### Header and data audit

The actual entry script posts `FormData` with the hidden CSRF token. Consent, alternate access and download are native HTML form posts. Code verification is a JSON fetch with the CSRF header. NDA room fetches inherit the room document's `same-origin` policy; JSON response policy does not replace the document's policy. NDA handoff and return GETs preserve session scope and existing publication checks. Proxied native HTML receives the same response policy without rewriting upstream bytes. PDFs/downloads and JSON retain `no-referrer`; DRF's negotiated media type is used before response rendering. No `Origin: null` allowance was added.

New metadata is accepted only through the authenticated board send path and its configured owner/team/room mapping; API keys cannot supply requester/title/board metadata. Missing requester uses the owner; an explicitly invalid requester fails validation. Existing service-account metadata cannot recover a historical human sender: new board sends carry that identity; old snapshots receive display cleanup only.

### Validation and reproduction

**Local results:** the complete signing suite plus `tests/dealroom/test_foundation.py` ran **498 passed / 1 baseline failure / 0 skipped**. The final r6-only run has **95 passes**, including eight additional blank-requester cases and five preview-image cases added after the broader run started. The browser regression has **1 old-policy mutation failure → 1 pass**. The browser harness uses a disposable HTTPS Django server and Chromium iPhone emulation. Native reconciliation and the final native page are fixtures, so this is evidence for entry, assets, consent, session rotation and redirect—not deployed native signing or SMTP acceptance.

```sh
/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b \
  dealroom_sign/tests/test_live_acceptance_r6.py
/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b \
  dealroom_sign/tests tests/dealroom/test_foundation.py
bash /root/work/sign-product/run-board-tests.sh /root/worktrees/board-s1 tests/test_dealroom_sign.py
bash /root/work/sign-product/run-board-tests.sh /root/worktrees/board-s1
```

The supplied board runner is not executable, so it was invoked with `bash`. Full Board results: **265 passed, 3 failed, 58 inherited skips**. All three failures are unchanged baseline failures in `tests/test_cloud_edition.py`: `test_detail_pages_program_and_epic`, `test_function_serves_the_same_endpoints_and_shapes`, and `test_relay_publishes_the_tailnet_payload`. Replacing only `app.py` and `dealroom.py` temporarily with their unchanged HEAD contents reproduced **the same 3 failures / 14 passes**; the r6 files were restored in `finally`. No test assertions or skip conditions were changed.

Evidence: [Send initial red](c1b-r6-send-red.txt), [additional red](c1b-r6-send-additional-red.txt), [nginx red](c1b-r6-deployment-red.txt), [name fallback red](c1b-r6-name-fallback-red.txt), [preview Dockerfile red](c1b-r6-preview-assets-red.txt), [95 R6 passes](c1b-r6-send-green.txt), [Send suite](c1b-r6-send-suite.txt), [Board red](c1b-r6-board-red.txt), [Board signing green](c1b-r6-board-green.txt), [Board full suite](c1b-r6-board-suite.txt), [Board unchanged-HEAD baseline](c1b-r6-board-baseline.txt).


Real Chromium (Playwright **1.65.1**, iPhone 13 emulation) sent `Origin: null` with no Referer under the old-policy test mutation and received **403** on `/s/session/consent`. Restoring the new document policy, without changing the assertions, sent the actual HTTPS origin and `/s/session/context` Referer, received **303**, persisted consent and reached the native-page fixture. **All 16 requested recipient assets returned 200.** The test runs on an ephemeral HTTPS port; its self-signed certificate is trusted only by this test browser. [Browser red](c1b-r6-chromium-red.txt), [browser green](c1b-r6-chromium.txt), [iPhone context screenshot](c1b-r6-context-iphone.png).

Browser reproduction (the temporary dependencies used for this run were removed from the working tree afterward):

```sh
npm install --prefix .agent/r6-browser --cache .agent/r6-npm-cache \
  --no-audit --no-fund --ignore-scripts playwright@1.65.1
PLAYWRIGHT_BROWSERS_PATH=/root/worktrees/send-c1b/.agent/r6-browser/browsers \
  node .agent/r6-browser/node_modules/playwright/cli.js install chromium
# Prefix the following with R6_TEST_OLD_REFERRER_POLICY=1 for the expected red run.
PLAYWRIGHT_MODULE=/root/worktrees/send-c1b/.agent/r6-browser/node_modules/playwright \
PLAYWRIGHT_BROWSERS_PATH=/root/worktrees/send-c1b/.agent/r6-browser/browsers \
RECIPIENT_SCREENSHOT=/root/worktrees/send-c1b/docs/implementation/c1b-r6-context-iphone.png \
  /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b \
  dealroom_sign/e2e/recipient_form_policy.py -s
```

The extra foundation-suite failure is `test_schema_mcp_static_parity`: its static MCP schema omits the existing `SignatureEmailRetryView` and `SignatureSignerRevokeView` operation IDs. This is unrelated to requester/title input properties or recipient policy. [Unchanged-HEAD reproduction](c1b-r6-send-baseline.txt) records its baseline check; the r6 production files were restored in `finally`. Neither that assertion nor either endpoint was removed or weakened.

Final footprint checks: Send, Board and Sign pass `git diff --check`; all three starting HEADs remain unchanged and staging is empty. Sign remains completely unchanged. Deployment still requires the manager's usual rollout and full native signing/SMTP acceptance; these results do not claim a deployed signature or delivered email.

## Manager live acceptance, preview, 15 Nov 2026

**Deployed (fictional preview `fleet-dealroom-proto`):**
- Sign `proto-c1b-5b29ff6c9`.
- Send `proto-c1b-9005dbd6`.
- Board preview on h-af: `hermes-board-sign-preview`, `app.py` and `dealroom.py` from board `ec46ae9`. The backups are
  `*.bak-c1b-r6`.

**Before cutover:**
- The preview database was backed up to `/root/work/sign-product/preview-backup-c1b-20261115T023802Z/`.
- Migration 0003 is applied.
- 138 stale native jobs that were PENDING since 4 Nov were set to FAILED, including one unsent native signing email.
- The preview Send organisation was renamed from "Chief Glue Review" to "Fleet Test Co.".

**Walk:** fictional signer `lee.c1b2@harborlight.fleet.test`, sent through the board preview and signed on an
emulated iPhone 13 (Chromium). Evidence is at `http://100.122.202.37:8765/dealroom-sign/c1b/`.

| Check | Result |
|---|---|
| Invitation comes from Send, "Dan via Fleet Dealroom", with Reply-To the requester | PASS |
| No native Documenso email | PASS |
| Personal link → entry → context and consent → signing page → document loads | PASS (after fixes A–C) |
| Signing completes | PASS |
| Fully-signed email goes to the signer and separately to the sender | PASS |
| No party addresses or CCs in the headers or bodies (the only `@` is the Message-ID) | PASS |
| Attachments are "… — signed.pdf" and "Signing certificate.pdf" | PASS |
| PDF seal is "Fleet Dealroom Sign (preview)" and valid | PASS |
| The same link afterwards shows the copy page, and its download is the sealed PDF | PASS |
| Sign 3001 is not published; 9443–9446 route correctly | PASS |

**Fixes found live:**
- **A. Sign crashed on boot.** Rollup tree-shook `staffFetch`. Fixed in Sign `5b29ff6c9` with a guard test.
- **B. Codex r6 fixes:**
  - browsers sent `Origin: null` under `no-referrer`, so consent got a 403;
  - asset roots used the wrong image layout;
  - "None None" sender name;
  - the requester wasn't passed from the board;
  - title timestamp, pluralization and the doubled zone.

  These are in Send `85682a54` and board `ec46ae9`.
- **C. The viewer PDF route allowlisted the wrong versions** (`original|pending|signed` where Sign serves
  `initial|current`). Fixed in Send `9005dbd6`.

All three passed Gate 3 (reviews `counterparty-c1b-gate3-r5.md` and `-r6.md`).

**Follow-ups (non-blocking):**
1. Pages send **two** `Referrer-Policy` headers: `same-origin`, then `strict-origin-when-cross-origin` from the
   image's nginx. Browsers apply the last one. Cross-origin requests get the bare origin only, never the token path,
   but there should be exactly one `same-origin`.
2. Requester name fallback: strip "(via …)", and use the email when the name is missing (r5 minor 1).
3. Run title cleanup only for older stored titles; the `\d{4}` pattern eats years (r5 nit).
4. "Unknown page" should read "Unknown pages" (r5 nit).
5. Bundle guard: cover every `./hono/server/**` import and add a check against the built bundle; update the
   `router.ts` comment (r6 nits).
6. No Staff Sign UI 404 sweep has been run yet: editor autosave and save, distribute, team and organisation
   settings (r4 nit).

**Signer UX leftovers, belonging to later slices:**
- **C2:** signature placement on the signer's line, and the date fields.
- **C4:**
  - the theme toggle and doubled "Next field" / "Complete";
  - Documenso's stock consent wording;
  - a done headline that says "will follow" while the copy is ready;
  - raw byte sizes in mail;
  - the green email button.
