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

## C2a — Automatic field placement in the existing Send path

Starting HEADs: Send `f6f2fbd5` (`agent/c1b-counterparty`), Board `ec46ae9`
(`agent/sign-s1`). Changes remain unstaged and uncommitted. Sign and the recipient
proxy are untouched. There are no new public routes or database migrations.

`backend/dealroom_sign/placement.py` ports the prototype's text/line rules to
`pdfplumber==0.11.9` and `pdfminer.six==20251230`. Their MIT notices are retained in
`backend/dealroom_sign/licenses/`; PyMuPDF is not a Send dependency. The parser uses
positioned words, drawn lines, thin rectangle edges and underscore blanks, nearby
names/company headings, and role definitions. It returns SIGNATURE, DATE and empty
NAME fields in the same 1-based page/top-left percentage units the native API uses,
with confidence and the matched label/line geometry. Already printed names are
identity evidence, not NAME blanks. TITLE fields remain outside C2a.

Assignment is a bounded, one-to-one maximum-weight matching. Confidence uses the
**actual assigned block**, with score ≥4 and a ≥2 margin against the best feasible
assignment excluding that pair. Generic email providers supply no company hint.
Missing dates, ambiguous matches, overlapping/invalid boxes and unreadable PDFs
hold the send. The supplied `bare.pdf` contains unnamed Signature/Date blanks;
without attributable cues it returns `bare` and never calls a model. Documents
with no cues behave the same way.

Only unusual local labels with independently clear signer identity can reach the
model. OpenRouter receives selected signer hints and extracted local labels with
coordinates, not opening paragraphs or the PDF. `PLACE_MODEL` must specify the
operator's cheap-tier model; there is no hard-coded model default. The key is read
from `OPENROUTER_API_KEY`. Missing configuration, timeout, HTTP errors, oversized or
invalid responses produce a visible `needs_sender` reason. The client has a
30-second HTTP timeout, bounded input/output, no redirects or tools, and a strict
candidate-ID response validator. Invented IDs, duplicate assignments, missing
signers, low confidence and unsupported evidence cannot become placements. All
model tests are offline, using injected clients or a fake HTTP client. No real
provider run or deployed acceptance is claimed.

Board `Dealroom.send` now requests `placement: auto` and supplies no fixed boxes.
Send also defaults to automatic placement when fields are absent; explicit
sender fields and NDA policy fields retain their existing path. Placement runs
before a workflow is queued. `bare` and `needs_sender` return HTTP 409 with
`status: needs_sender`, a plain reason and suggestions, creating no workflow or
native distribution. The board preserves that typed result, leaves the form
open, displays the message beside Send, and records no sent state.

For a placed result, one transaction persists the fields and a
`placement.resolved` workflow event containing the full analysis, source hash and
recipient/field digest. History includes the evidence and renders “Fields placed
by Fleet” with the label and page. Idempotent retries compare the original inputs
and reuse the stored analysis. The worker validates the saved evidence and fields
before remote writes. The existing source-byte checks still run before upload,
on adoption of the native original and before completed-artifact publication.
Placement uses those same source bytes; no PDF rewriting is introduced. Internal
company/title hints are removed from the native recipient DTO.

C2a intentionally uses the current C1b send seam. Cropped, rotated or nonzero-origin
pages require review; silently transforming them would outrun the separately
approved normalized-prepare work. The future review/Adjust UI is not implemented.
Only requested signers are placed: the live Lee-only case does not infer or invite
Dan from another visible block.

### C2a red → green evidence

| Item | Failing evidence | Passing evidence |
| --- | --- | --- |
| Rules, five prototype goldens, live Lee placement, unusual-label model and failure controls | [Engine red](c2a/engine-red.txt): **26 failed** before implementation | [Engine green](c2a/engine-green.txt): **40 passed**, including later validation/provider controls |
| Pinned dependencies, MIT notices, explicit CI golden job; invalid page/extra signer/duplicate/low-confidence fields | [Validation red](c2a/validation-red.txt): **5 failed / 10 passed** | Same engine green; existing bounds/overlap controls remain intact |
| Default API placement, typed holds, durable History evidence, idempotency and source/evidence checks | [Send red](c2a/send-red.txt): **10 failed** against unchanged production code, after supplying real staff/config test prerequisites | [Final placement run](c2a/placement-green.txt): **51 passed** (40 engine + 11 integration) |
| Keep placement-only company/title hints out of the native recipient payload | [Native DTO red](c2a/native-red.txt): **1 failed** | Final placement run above |
| Board removes fixed fields and preserves HTTP 409 without recording a send | [Board red](c2a/board-red.txt): **4 failed** | [Board focused green](c2a/board-green.txt): **93 passed**, including signing and shipped UI controls |
| Plain typed error, intelligible History evidence, persistent unsent form message | [Error red](c2a/board-ui-red.txt), [History red](c2a/board-history-red.txt), [form red](c2a/board-form-red.txt): each fails its behavioral assertion | [UI green](c2a/board-ui-green.txt); included in the 93-test run |
| Preserve bounded generic errors while allowing typed placement responses | [Bounded-error red](c2a/board-error-red.txt): **1 failed** | Board focused green above |
| Unavailable-model message describes the current review hold, without promising an available review UI | [Message red](c2a/model-message-red.txt): **1 failed** | Final placement run above |

No existing test assertion was weakened, skipped or deleted. The early Send full
run used a relative `PYTHONPATH`; settings subprocesses changed directory and
imported `backend/backend/celery.py` as `celery`, causing **52 environment failures /
438 passes**. [That run is retained](c2a/send-suite-environment-error.txt). The
reproduction script now uses an absolute backend path; this needed no product or
test change.

Full Send `dealroom_sign/tests`: **495 passed, 0 failed, 0 skipped** ([log](c2a/send-suite.txt)).
Full Board: **271 passed, 3 unchanged baseline failures, 58 inherited skips**
([log](c2a/board-suite.txt)). The failures are
`test_detail_pages_program_and_epic`,
`test_function_serves_the_same_endpoints_and_shapes`, and
`test_relay_publishes_the_tailnet_payload`, all in `test_cloud_edition.py`.
Temporarily substituting unchanged HEAD `app.py`, `dealroom.py` and `static/app.js`
reproduced **the same 3 failures / 14 passes** ([baseline log](c2a/board-baseline.txt));
the C2a files were restored in `finally`. No inherited skip condition was changed.
Both worktrees pass `git diff --check`, and staging is empty.

### C2a fixtures and renderings

The five prototype PDFs and signer files are checked in under
`backend/dealroom_sign/tests/fixtures/placement/`, with independent expected boxes
and a **2-point tolerance** in `expected.json`. The sixth PDF was decoded from the
provided live fictional `send.json`; it is byte-identical to prototype `nda.pdf`,
but has its own **Lee-only** golden. The seventh, reproducible `unusual.pdf`, uses
“Hand of the covenanting party:” and a mocked model. Its body-text sentinel is
asserted absent from provider input.

[All fixtures contact sheet](c2a/contact.png). Individual renders are **1020 × 1320
pixels**, and the contact sheet is **1680 × 1088**, all below the 2000-pixel limit:
[bare](c2a/bare-p1.png), [NDA](c2a/nda-p2.png), [offer](c2a/offer-p1.png),
[roles](c2a/roles-p3.png), [witness](c2a/witness-p2.png),
[live Harbor NDA](c2a/harbor-p2.png), [unusual label, mocked](c2a/unusual-p1.png).
The [recorded results](c2a/placements.json) include each field's evidence. Visual
inspection confirms Lee's signature is directly above “Lee Harbor, COO” on page 2,
with its adjacent Date blank filled; offer decoy rules receive no fields.

### C2a reproduction and scope limits

From the Send root, install `backend/requirements.txt` into a local environment.
The evidence run used `.agent/c2a-venv` (Python 3.13.14); the CI golden job uses the
repository's Python 3.12 job and explicitly runs `test_placement.py` offline. The
same CI step/environment reproduced locally with **40 passes** ([log](c2a/ci-goldens.txt));
no hosted GitHub Actions execution is claimed.

```sh
# Local preview Redis/core dependencies use 127.0.0.1:16379 and :18080.
docs/implementation/c2a/run_send_tests.sh backend/dealroom_sign/tests
# Override C2A_PYTHON to use a different installed test environment.
docs/implementation/c2a/run_send_tests.sh \
  backend/dealroom_sign/tests/test_placement.py \
  backend/dealroom_sign/tests/test_placement_send.py
PYTHONPATH=backend .agent/c2a-venv/bin/python docs/implementation/c2a/render_fixtures.py
bash /root/work/sign-product/run-board-tests.sh /root/worktrees/board-s1
```

The OpenRouter request shape follows its [official API reference](https://openrouter.ai/docs/api_reference/overview);
the parser uses the [documented pdfplumber geometry API](https://github.com/jsvine/pdfplumber).
No key was retrieved, no real document was sent to a provider, no invitation was
sent, and no deployment was performed. Model acceptance against a configured live
provider and the complete native signing/sealing walk remain deployment checks.

## C2a r2 — Gate 3 fixes and native field rendering

Starting HEADs: Send `8b79285e`, Board `ce62d68`. Sign and the recipient proxy
remain unchanged. All work is unstaged. The test environment is outside the
repository at `/tmp/send-c2a-r2-venv`; tracked `.agent/` content is preserved.

In r2, printed full names retained inside the narrow extraction window vetoed a
different signer before company/domain scoring. The completed r3 section below
documents the expanded raw-evidence check.
Names match whole tokens, surname-only matching is removed, and company/domain
hints require at least four characters. Case, initials, apostrophes, long captions
and incomplete identities fail closed where a full match cannot be established.
Role definitions start at their explicit `by`/`between`/`and`/`with` boundary.
All seven original `expected.json` golden regions and their tolerance are unchanged.

Placement has a configurable 12-second total deadline, including the model.
Parsing runs in a killable child interpreter with a default three-second budget
inside that deadline. Raw per-page limits are 5,000 edges, 20,000 characters and
4,000 words, checked before grouping/de-duplication. Word extraction happens once;
edge de-duplication uses neighboring spatial buckets. The 100,000-hairline test
asserts a hold within four seconds. Timeout returns `needs_sender`, empty fields,
`reason_code: placement_timeout`, and exactly “Placement took too long”.

Only bounded name/company/role patterns and fixed field labels leave extraction.
The model receives opaque signer IDs and names, with no emails or unnecessary
company/title hints. A sentence immediately above a signature line is absent from
both model input and persisted History. Caption ownership cannot cross a previous
signature block; companion dates require local label adjacency and column ownership.
User-visible parser reasons come from fixed codes. Model outcomes distinguish
`not_configured`, `timeout`, `invalid_reply`, and `error`.

Automatic workflows have a durable `auto` marker in their existing correlation ID,
so deleting the placement fact cannot bypass the worker check. New manual workflows
have a `manual` marker. Legacy room-document workflows whose placement mode cannot
be established also hold if evidence is missing; no schema migration is required.
The worker still checks source and recipient digests before remote writes.

Board treats socket/read timeouts as `outcome_unknown` and keeps this message by
the form: “We couldn't confirm whether it was sent. Check History before trying
again.” The submission key hashes room, PDF SHA-256, ordered signers, board and card.
A SQLite mapping beside Board's state file persists the uploaded version before
send, so retries and restarts reuse the same source. Existing room files obtain
their hash through the authorized selected-source query. Replayed successful
responses do not append duplicate local History records.

The complete pdfplumber runtime dependency closure is pinned: pypdfium2 5.15.2,
cryptography 50.0.2, charset-normalizer 3.5.2, cffi 2.1.1 and pycparser 3.12,
with the existing Pillow 13.0.0 pin. Distribution licences, including PDFium's
third-party notices and Pillow's bundled notices, are retained in
`backend/dealroom_sign/licenses/`.

### C2a r2 red → green

| Item | Red evidence | Final coverage |
| --- | --- | --- |
| H1 reviewer cases, fixture-wide wrong-signer properties; N4 anchored roles | [H1 red](c2a-r2/h1-red.txt): 19 failed, 32 passed | [H1 green](c2a-r2/h1-green.txt): 91 passed; all original goldens intact |
| H1 uppercase, lowercase, initials, apostrophes and long captions | [Variants red](c2a-r2/identity-variants-red.txt): 5 failed; [unrecognized-caption red](c2a-r2/unrecognized-red.txt): 2 failed | Final placement suite |
| M1 total deadline; M2 caps and 100,000 hairlines; M3 nearby sentinel and opaque IDs; L1/L2 attribution; L3 dependencies; N1/N2 reasons/outcomes; signature anchoring | [Engine red](c2a-r2/engine-red.txt): 17 failed, 51 passed | Final placement suite |
| M3 History sentinel; N3 missing fact; date-only envelope and native metadata | [Send red](c2a-r2/send-red.txt): 3 failed | Final placement suite |
| Authorized selected-source content hash for Board retries | [Source red](c2a-r2/source-red.txt): 1 failed | Final placement suite |
| M1 Board open/read timeouts, wrapped socket timeout, retry key/source, key inputs and persistent form message | [Board red](c2a-r2/board-red.txt): 8 failed, 43 deselected | [Board focused](c2a-r2/board-focused.txt), including restart/concurrent-retry checks |

No test was skipped, deleted or weakened. Existing model stubs now return the
opaque ID supplied by the payload; the no-configuration assertion requires its
specific outcome; the HTTP timeout assertion requires the remaining deadline
instead of 30 seconds. The native position assertion checks the corrected box;
the independent golden region assertions remain unchanged.

### C2a r2 overlays and Sign schema evidence

Sign was inspected read-only: `packages/lib/types/field-meta.ts` supports
`fontSize` for signature/date fields but has no signature alignment option;
`render-signature-field.ts` centres signature text vertically. Send converts the
unchanged measured region into an 18 pt native signature box ending on the rule,
with signature fontSize 18 and DATE fontSize 10. Only these exact internal metadata
values are accepted; caller-supplied rich metadata remains refused.

Sign's `document-meta.ts` and `constants/date-formats.ts` allow `yyyy-MM-dd` at
envelope level; `dd MMM yyyy` is absent from the allowlist. The date-only option is
passed through the existing create payload.

[Seven-fixture contact sheet](c2a-r2/contact.png),
[recorded placements/native fields](c2a-r2/placements.json),
[Harbor native boxes](c2a-r2/harbor-overlay.png).
The [before detail](c2a-r2/harbor-before-detail.png) and
[after detail](c2a-r2/harbor-after-detail.png) come from Sign's actual
`insertFieldInPDFV2` export renderer, merged onto Harbor page 2. The
[measured ink gap](c2a-r2/render-metrics.json) falls from **8.2 pt to 1.7 pt**;
the native box bottom is on the rule at **367.2 pt**. The date fits on one line.
[Full after rendering](c2a-r2/harbor-after-rendered.png) and
[rendered PDF](c2a-r2/harbor-after-rendered.pdf) are retained.

These are native rendering proofs, not a live invitation, deployment or newly
sealed production PDF. No provider request or real signing transaction was made.
[Reproduction commands and settings](c2a-r2/README.md) are included.

Board final full suite: **281 passed, 3 unchanged baseline failures, 58 inherited
skips** ([log](c2a-r2/board-suite.txt)). The failures are
`test_detail_pages_program_and_epic`, `test_function_serves_the_same_endpoints_and_shapes`,
and `test_relay_publishes_the_tailnet_payload` in `test_cloud_edition.py`.
Restoring starting-HEAD production files reproduced **the same 3 failures / 14
passes** ([baseline](c2a-r2/board-baseline.txt)); r2 files were restored in `finally`.
The focused signing/timeout/retry/browser suite has **53 passes**.
The [100,000-hairline timing](c2a-r2/hairline-timing.json) is **3.01 seconds**.

The [first full Send run](c2a-r2/send-first-run.txt) had **571 passes / 1 failure**:
an exact envelope metadata assertion still expected the previous dictionary without
`dateFormat`. Its exact expected dictionaries (local metadata and the captured native payload)
were extended with the required date-only format; no other assertion was relaxed.

A final L1 boundary regression covers a heading above an unlabeled previous rule:
[red](c2a-r2/heading-red.txt) **1 failed** →
[green](c2a-r2/heading-green.txt) **18 passed**, including the original goldens and
caption cases. Both headings and captions now stop at a preceding signature rule.
The full suite below was rerun after this final change.

The L2 close-column regression also covers an **unlabeled** right-hand signature
rule. Date ownership checks raw rules as well as recognized blocks, so a narrow
column gutter cannot let the left signer borrow that column's date:
[column red](c2a-r2/column-red.txt) **1 failed** →
[complete engine green](c2a-r2/engine-green.txt) **117 passed**. This is included in the final full run.

**Final Send `dealroom_sign/tests`: 576 passed, 0 failed, 0 skipped**
([full log](c2a-r2/send-suite.txt), 270.36 s). This run includes all final heading
and close-column fixes. The complete placement engine has **117 passes**; the
five reviewer wrong-signer cases and the 42 fixture-wide identity checks pass.
The seven original expected placements are unchanged.

Both worktrees pass `git diff --check`. Starting HEADs are unchanged and staging
is empty. [Footprint evidence](c2a-r2/footprint.txt) confirms Sign is clean, the
recipient proxy and tracked `.agent/memory.md` are unchanged, and `expected.json`
is byte-identical to the starting version. The only remaining test failures are
the three reproduced Board cloud-edition baseline failures described above.

## C2a r3 — stopped on an existing-test/spec conflict

Starting HEADs: Send `adc218d7`, Board `58599f1`. The entire Gate 3 r2 review
was read before implementation. **This round is blocked; no production code or
existing tests have been changed.** The brief explicitly requires: “If an
existing test contradicts a finding, stop and explain in the report.”

### B1 conflict requiring a decision

The review's concrete B1 fix says: “An above-line that fails `identity_label`
makes the block uncertain, mirroring `:245`.”

The existing
`backend/dealroom_sign/tests/test_placement_r2.py::test_nearby_body_is_redacted_and_model_identity_is_minimal`
(lines 158–168) requires the opposite behavior for its fixture:

- `nearby_body_pdf()` prints `Lee Harbor, Harbor Light Analytics` at y=390,
  then `PRIVATE NEARBY SENTINEL: the special terms remain confidential.` at
  y=370, then the unusual signature label at y=350 and rule at y=348.
- The body line is in the same column, within 90 pt above that rule, with no
  intervening rule. It fails `identity_label`.
- The existing test requires one model call and `status == 'placed'`.
- Applying the review's unconditional uncertainty rule makes the block
  uncertain. `score()` then returns zero; model eligibility fails; the result
  holds. That contradicts both existing assertions.

The review's broader principle specifically restricts **company/domain-only**
confidence, whereas this existing fixture also has the signer's matching printed
name. A decision is needed on whether a matching full name permits a separately
recognised body sentence to be redacted without making the block uncertain, or
whether this existing test must change to require a hold. Neither interpretation
has been silently selected, and the existing test has not been weakened.

### r3 verification and finding status

The specified Send runner initially exited 127 because
`.agent/c2a-venv/bin/python` does not exist. Its supported `C2A_PYTHON` override,
using the r2 environment already documented above, ran the conflicting existing
test successfully:

```sh
C2A_PYTHON=/tmp/send-c2a-r2-venv/bin/python \
  bash /root/worktrees/send-c1b/docs/implementation/c2a/run_send_tests.sh \
  backend/dealroom_sign/tests/test_placement_r2.py::test_nearby_body_is_redacted_and_model_identity_is_minimal
```

Result: **1 passed in 0.80 s**. This is a baseline verification, not an r3 fix
or red→green result. No new regression tests or implementation changes were made
after identifying the conflict.

| Finding | r3 status / red→green evidence |
| --- | --- |
| B1 raw identity extent and fixture-wide property | Stopped on the conflict above; existing behavior verified green; no fix claimed. |
| H1 upload version/hash binding | Not started following the required stop. |
| M-a child memory/concurrency bounds | Not started following the required stop. |
| M-b title-case text redaction | Not started following the required stop. |
| L-a full company/domain matching | Not started following the required stop. |
| L-b disconnected POST outcome | Not started following the required stop. |
| L-c SQLite busy response | Not started following the required stop. |
| L-d child environment/cwd/health check | Not started following the required stop. |
| N-a model total deadline and slot recovery | Not started following the required stop. |
| N-b missing placement evidence quarantine | Not started following the required stop. |
| N-c report accuracy | The r2 claim above must be read as applying only to names retained inside its narrow evidence window. B1 remains unfixed. |

**r3 final counts:** Send focused baseline **1 passed, 0 failed, 0 skipped**;
Send full suite **not run**; Board suite **not run**. The earlier r2 full-suite
counts are historical and are not represented as r3 results. No live service
calls were made. Golden fixtures, date-only metadata, baseline anchoring, project
memory, and both indexes remain unchanged. No commit or push was performed.

## C2a r3 — manager decision applied; second existing-test conflict

The manager decision resolves the previous `nearby_body_pdf` conflict: a matching
printed full name permits nearby non-person-like body text to be redacted without
holding placement. That test remains unchanged and passes. The review and the
updated r3 brief were read in full. Starting HEADs remain Send `adc218d7` and
Board `58599f1`.

**Implementation stopped under the brief's explicit rule: “If an existing test
contradicts a finding, stop and explain in the report.”** A separate conflict
exists between the manager's unconditional rule, “Company or domain evidence
alone never yields `high`,” and the requirement to preserve all seven goldens.

### Concrete conflict: company-only goldens

`backend/dealroom_sign/tests/test_placement.py::test_golden[roles]` and
`::test_golden[witness]` both call `assert_golden`, which requires `placed`, the
expected fields/coordinates, and confidence `high` or `model-high`. Neither
fixture contains either signer's printed name, as verified directly from the
PDF text rather than `block.identity`:

| Fixture | Actual identity evidence | Current result |
| --- | --- | --- |
| `roles.pdf` | Blank printed-name lines beneath `RECIPIENT` / `DISCLOSER`; opening role definitions map those headings to Harbor Light Analytics, Inc. / Fleet Test Co. | Both signers score 4, margin 4, confidence `high`; six fields; `placed`. |
| `witness.pdf` | Company headings above blank `By`, `Name`, `Title`, and `Date` lines; no printed person names. | Both signers score 4, margin 4, confidence `high`; six fields; `placed`. |

[Raw-PDF and scoring evidence](c2a-r3/company-only-evidence.json) records the
extracted pages, absence of both signer names, headings, role mappings, and
assignments. No provider was called. Changing these cases to hold would break
both existing goldens. Keeping their current confidence would violate the
manager's unconditional company/domain-only prohibition. No exception was
silently inferred.

The review itself allows company/domain-only confidence when the entire block
extent has no person-like or unaccounted-for text. A decision is pending on
whether that exception remains permitted (preserving the goldens), or whether
the two goldens are now explicitly authorized to require a hold. No existing
test, fixture, or production file has been changed.

### Verification and finding status

Command used with the supplied Python environment:

```sh
C2A_PYTHON=/root/work/sign-product/send-venv/bin/python \
  bash /root/worktrees/send-c1b/docs/implementation/c2a/run_send_tests.sh \
  'backend/dealroom_sign/tests/test_placement.py::test_golden[roles]' \
  'backend/dealroom_sign/tests/test_placement.py::test_golden[witness]' \
  backend/dealroom_sign/tests/test_placement_r2.py::test_nearby_body_is_redacted_and_model_identity_is_minimal
```

[Baseline log](c2a-r3/conflict-baseline.txt): **3 passed in 1.35 s**. This verifies
the conflict and the already-resolved sentinel case; it is not red/green fix
evidence. No implementation or new regression tests were added after the stop.

| Finding | This resumed r3 attempt: test / red → green |
| --- | --- |
| B1 | Existing `test_golden[roles]` / `[witness]` verified green; specification conflict above prevents a compliant fix. No red → green claimed. |
| H1 | Not started after the required stop; no upload/collision regression or live recheck claimed. |
| M-a | Not started; memory and concurrency bounds remain unresolved. |
| M-b | Not started; title-case body redaction remains unresolved. |
| L-a | Not started; generic domain/company matching remains unresolved. |
| L-b | Not started; disconnected POST outcome remains unresolved. |
| L-c | Not started; SQLite busy handling remains unresolved. |
| L-d | Not started; child environment/cwd/health checks remain unresolved. |
| N-a / N1 | Not started; model deadline/slot recovery remains unresolved. |
| N-b / N2 | Not started; missing-evidence quarantine behavior remains unchanged. |
| N-c / N3 | The earlier r2 name-veto claim applies only to retained evidence, not the full raw-text extent. B1 is still unfixed; this report makes no broader claim. |

**Final counts for this resumed r3 attempt:** Send focused baseline **3 passed,
0 failed, 0 skipped**; full Send suite **not run**; Board suite **not run**.
Historical r2 suite counts are not r3 results. All seven fixtures, all existing
tests, date-only metadata, signature baseline anchoring, and project memory
remain unchanged. No calls to real services, commits, or pushes were made. Only
this report, its evidence files, and the requested completion marker are written;
the marker explicitly records the blocked outcome rather than successful fixes.

## C2a r3 — completed fixes after both manager decisions

This section supersedes the two r3 stop reports above. Starting HEADs are still
Send `adc218d7` and Board `58599f1`. The full Gate 3 r2 review and both manager
decisions were applied. Existing tests and all seven golden PDFs/expected boxes
remain intact. [Final placement evidence](c2a-r3/placements.json) records all
seven outcomes against the unchanged golden assertions. The Board's existing shared fake gained the two new upload response
fields and returns a fresh version ID on each upload, preserving the existing
retry test's ability to detect an accidental re-upload. No existing assertion was
weakened, skipped, or deleted.

### Identity and privacy

Identity decisions now use every raw text row in the signature column, bounded
by the previous rule or 90 points above, and the next signature rule or 125 points
below. This deliberately includes the full lower window even when a companion
occurs sooner. Inline names, intervening company headings, role suffixes, spaced
captions, and NAME/TITLE companions participate before any redaction. Multiple
names on one raw line also participate. Unknown person-like text holds; any other
person's name vetoes that signer. A matched full name can coexist with non-person
prose, preserving the unchanged nearby-body sentinel test.

Company/domain-only confidence requires fully accounted, unnamed raw evidence
and exactly one matching signer in the whole send. The `roles.pdf` and
`witness.pdf` goldens retain their original placements under that exception.
Single generic company words cannot match a longer company name; full company
names and compound domains such as `harborlight` still work.

Scoring runs in the disposable parse worker. Before its response, it clears raw
evidence and emits a person string only when its tokens match a supplied signer;
other person-like strings become `[printed name]`, and arbitrary prose becomes
`[redacted]`. Recognized company, role and field labels remain available. The
model receives sanitized candidates, opaque signer IDs and names. Result fields,
placement facts and History use that same sanitized evidence. Holds expose no
partial fields.

**N-c / N3 correction:** the earlier r2 claim about a printed-name veto applied
only to names retained in r2's narrow evidence window. The r3 claim applies to
raw evidence throughout the bounded column extent described above, before
redaction; it is not a claim to interpret all text on arbitrary PDF pages.

### Upload identity and resource handling

Send upload responses now include the exact upload's `version_id` and `sha256`,
matching the version metadata and `document.uploaded` fact. Board uses that ID,
checks the response hash against its PDF, and checks the authorized source hash
again before sending, including on retries. Filename polling has been removed.
Collision-renamed uploads and unrelated uploads with the original name cannot
change the selected version. The SQLite mapping still persists the version
before a send, so uncertain retries keep the same deterministic key and source.

Each parser child has a 768 MiB address-space ceiling and a CPU ceiling (four
seconds for the default three-second wall budget, capped at eight seconds).
Two parse slots per application process are acquired without waiting; excess
requests hold as `placement_busy`. A timed-out child is killed and reaped and its
slot released. Empty/malformed output, failed exits and launch failures report
`placement_unavailable`. Recognized parser allocation failures report
`parse_limit`; malformed documents still report `unreadable_pdf`.

The child receives only `LANG` and `LC_ALL`, with an explicit backend working
directory. Its `--health` command verifies parser import and the enforced OS
limits without credentials or service calls. [Health output](c2a-r3/worker-health.json)
reports 805306368 bytes and eight CPU seconds. HTTP model calls now check a
monotonic total deadline as chunks arrive and close the transport on that deadline,
including when no decoded chunk arrives, allowing the model thread to release its
slot. The existing bounded request deadline remains in force.

Dropped POST connections produce `outcome_unknown` with the existing “Check
History” message. SQLite operational errors produce a retryable 503 busy response;
lock contention waits at most one second instead of 90. Missing automatic
placement evidence now quarantines a workflow before any remote write, matching
the changed-evidence behavior.

### Test-first evidence, red then green

Tests were added before each implementation group. After correcting two test
fixture issues (overlapping inserted PDF text and an overly broad SQLite mock),
the final regression fixtures were also replayed against the original Send HEAD,
with working changes restored in `finally`: [baseline replay](c2a-r3/final-regressions-red.txt)
**43 failed, 13 passed**. Five additional raw-suffix/role assertions were then
red before their fixes: [suffix red](c2a-r3/raw-suffix-red.txt). The final r3 Send
regression group is [green](c2a-r3/final-regressions-green.txt). Initial intermediate
logs are retained; they are not substitutes for the final suite results below.

| Finding | Regression that pins the behavior | Red → green evidence |
| --- | --- | --- |
| **B1** | `test_other_person_in_whole_raw_extent_never_gets_high` (12 layouts); `test_inserted_raw_person_vetoes_across_fixtures` (raw PDF text, all seven fixtures); `test_company_only_requires_every_raw_line_accounted_for`; `test_matched_name_does_not_override_unresolved_person_like_line`; `test_second_person_in_same_raw_line_also_vetoes`; unique-company-signer check | All 12 review layouts fail on HEAD; the raw fixture property fails on `roles` and `witness`; unknown prose/person suffix cases fail too. [Red](c2a-r3/final-regressions-red.txt), [suffix red](c2a-r3/raw-suffix-red.txt) → [green](c2a-r3/final-regressions-green.txt). Existing positive-name/non-name, company-only goldens, date metadata and baseline anchoring tests remain unchanged. |
| **H1** | Board `test_two_cards_same_pdf_same_minute_use_own_uploaded_versions`, `test_same_name_foreign_upload_never_selected`, both `test_hash_mismatch_holds_without_send` cases; Send upload/version/activity test and two-workflow integration test | [Board red](c2a-r3/board-red.txt), [Send red](c2a-r3/final-regressions-red.txt) → [Board focused green](c2a-r3/board-green.txt), [Send green](c2a-r3/final-regressions-green.txt). Both cards return 200, zero polling calls, distinct uploaded versions, matching hashes. |
| **M-a** | `test_parse_burst_beyond_slots_holds_without_starting_child`; failed-child cases; health/resource test; `test_flate_expansion_is_bounded_and_parent_rss_stays_flat`; timeout kill/reap/slot test | [Resource red](c2a-r3/resources-red.txt), [timeout red](c2a-r3/timeout-red.txt) → [resource green](c2a-r3/resources-contract-green.txt). A 611,954-byte PDF expanding to 600 MiB holds in 2.09 s with 0 KiB measured parent peak-RSS growth in the recorded run. |
| **M-b** | `test_title_case_body_never_leaves_local_evidence` (all three review strings, including an unselected unusual candidate); `test_title_case_body_not_persisted_to_history`; fixed role/company/label checks | The original implementation leaks the nearest title-case line in the model payload. [Red](c2a-r3/final-regressions-red.txt) → [green](c2a-r3/final-regressions-green.txt); model input, result, persisted facts and History are checked. |
| **L-a** | `test_single_company_word_is_not_domain_identity` (light, ventures, capital, partners, group, holdings, global), with compound/full-company controls | Seven failed on HEAD in [red](c2a-r3/final-regressions-red.txt) → [green](c2a-r3/final-regressions-green.txt). |
| **L-b** | Board `test_disconnected_post_is_unknown_outcome`: `RemoteDisconnected`, `ConnectionResetError`, `IncompleteRead` | Three failures in [Board red](c2a-r3/board-red.txt) → [Board green](c2a-r3/board-green.txt), including exact status and History message. |
| **L-c** | Board `test_sqlite_busy_is_retryable_and_never_uploads`, `test_busy_route_is_service_unavailable` | [Board red](c2a-r3/board-red.txt) → [Board green](c2a-r3/board-green.txt); 503 and no upload/send. |
| **L-d** | `test_child_has_minimal_env_and_works_outside_backend`, `test_worker_health_reports_enforced_memory_and_cpu_limits` | [Red](c2a-r3/resources-red.txt) → [green](c2a-r3/resources-contract-green.txt); placement works from a temporary cwd and credentials/PYTHONPATH are absent from child env. |
| **N-a / N1** | `test_slow_dripping_model_releases_slot_at_total_deadline`, `test_model_total_budget_closes_transport_even_without_decoded_chunks` | [Slow-drip red](c2a-r3/resources-red.txt), [transport red](c2a-r3/model-transport-red.txt) → [green](c2a-r3/resources-contract-green.txt); transport closes and model slot is available again. |
| **N-b / N2** | `test_missing_auto_evidence_is_quarantined_before_remote_write` | Original state remains `queued`; [red](c2a-r3/send-contract-red.txt) → [green](c2a-r3/resources-contract-green.txt), with `placement_evidence_missing` and no create/distribute calls. |
| **N-c / N3** | Documentation correction above | No behavior change or artificial test. Historical claim is qualified and the actual r3 boundary is stated. |

The existing hairline test exposed a narrow compatibility issue during the
resource work: allocation exhaustion must remain `parse_limit`, and
`TimeoutError` must be caught before `OSError` (its superclass). A regression
captured kill/reap/slot recovery before that fix. No existing test was changed to
accept a different result. Both manager decisions remain honored; no further
specification conflict required stopping.

### Final verification and limits

- **Send signing suite:** **639 passed, 0 failed, 0 skipped**, 319.33 s
  ([final log](c2a-r3/send-signing-suite.txt)). This includes all 576 pre-existing
  signing tests plus 63 r3 regression cases, including the unchanged date-only
  stamp, baseline anchoring and seven fixture outcomes.
- **Board full suite:** **290 passed, 3 failed, 58 skipped**, 37.11 s
  ([final log](c2a-r3/board-suite.txt)). The only failures are the three supplied
  `test_cloud_edition` baseline cases: `test_detail_pages_program_and_epic`,
  `test_function_serves_the_same_endpoints_and_shapes`, and
  `test_relay_publishes_the_tailnet_payload`.
- **r3 regression groups:** Send **63 passed** ([log](c2a-r3/final-regressions-green.txt));
  Board's existing signing tests plus the nine new cases **62 passed**
  ([focused log](c2a-r3/board-green.txt)). The final full suites above include them.
- `git diff --check` passes in both repositories. [Footprint evidence](c2a-r3/footprint.json)
  confirms the original HEADs, empty indexes, unchanged goldens, unchanged existing
  Send placement tests, and unchanged project memory.

An additional expanded run covering `backend/dealroom_sign/tests` plus
`backend/tests/dealroom` produced **743 passed, 1 failed, 0 skipped** before the
last seven regression additions ([expanded log](c2a-r3/send-suite.txt)). The one
failure is `test_schema_mcp_static_parity`: the static MCP tool list omits the
already-served `SignatureEmailRetryView` and `SignatureSignerRevokeView`
operations. The exact same failure was verified against original Send HEAD
`adc218d7` ([baseline evidence](c2a-r3/foundation-baseline-and-unique-red.txt)).
Those route definitions and the static MCP inventory are outside this C2a fix
and remain unchanged. This is an additional pre-existing foundation failure,
not a passing check or a regression introduced by r3.

The baseline check also demonstrates that the company-only uniqueness test
fails when a model confirms both assignments; the final implementation holds it
([green](c2a-r3/company-unique-green.txt)).

The Board runner's hard-coded `/root/.hermes/cache/scratch` directory is read-only
in this session. The exact supplied runner was used with an exported shell
`mktemp` wrapper directing only its disposable home to `/tmp`; the runner itself
was not edited:

```bash
function mktemp() { command mktemp -d /tmp/c2a-boardhome.XXXXXX; }
export -f mktemp
bash /root/work/sign-product/run-board-tests.sh /root/worktrees/board-s1
```

Send uses the supplied interpreter and runner:

```bash
C2A_PYTHON=/root/work/sign-product/send-venv/bin/python \
  bash /root/worktrees/send-c1b/docs/implementation/c2a/run_send_tests.sh \
  backend/dealroom_sign/tests
```

The additional foundation run used the same command with `backend/tests/dealroom`
appended; its baseline failure is reported separately above.

No live-service recheck was performed, per the prohibition on calls to real
services. Its replacement is the Board collision fake plus the Send integration
check using real Django document/version/workflow records and local PDF bytes,
with storage, rendering and external transports stubbed. That check creates two
workflows from two same-named uploads and verifies both `source_sha256` values.
The parser concurrency ceiling is per application process; deployment worker
count still determines the aggregate ceiling. The health check assumes the
Linux resource module used by deployment.

No schema/dependency changes, migrations, commits, pushes, or Sign-repository
operations were made. All implementation and test changes are unstaged. Deploy the Send upload-response
change before or together with Board; a new Board receiving an older upload
response holds with 409 rather than guessing a version. Project
memory remains unchanged unless the separate optional memory draft is explicitly
approved. The completion marker is written beside the r3 brief after verification.

## C2a r4

This round addresses Gate 3 r3 against Send `ef62c4da` and Board `11d1606`.
The fixes remain uncommitted. The review was read in full, including the cases
that already held. No existing test was weakened, skipped, or deleted. The only
edit to an existing test extends the r3 seven-fixture insertion property with a
name at `line.x1 + 30` on the rule's own row; its original above/below checks
remain. The parser analysis version is now `c2a.4`.

### Identity fixes, in review order

**B-1:** raw identity evidence includes the row band on either side of a rule,
including printed names below its x-span. Neighbouring rule columns bound the
band, and text in a shared gap participates in both blocks. Names are scored
before any redaction, so company evidence cannot defeat a different printed
person. A full `Name:` caption also no longer gets classified as an empty `bare`
label when there is no company heading. Tests cover the single-row and 2×2 grid
forms, names on the left and under the rule, matching and mismatched signers,
with and without a company, plus separate and ambiguous side-by-side columns.

**H-1:** `Title:` and `Its:` never yield a printed person. Recognized role phrases
are accounted; an unrecognized remainder such as `Title: Lee Harbor` stays
unresolved and holds. Role recognition covers the review's head words,
modifiers, connectors, abbreviations and common department suffixes. Ordinary
field labels, authorized/authorised signatory, party headings with colons,
acceptance wording, duly authorized/authorised, legal-form words and parsed
`Date:` values are accounted. ASCII spaced hyphens split name/role suffixes.
`Name / title` remains one caption prefix during splitting. Heading selection
prefers actual identity evidence over standalone block wording. All review title
and wording variants are checked against Harbor's unchanged golden boxes. The
extra-long title fixture reduces only its caption font and restores the font
before the date, avoiding overlapping text or altered underscore geometry.

**H-2:** stacked hosts are partitioned using the previous host's last companion
or close caption and the next host's first attributable label. The previous
extent ends before that label group; the next excludes the previous caption.
Equidistant identities remain uncertain for both hosts. Without a separator,
the existing previous-caption ambiguity guard remains. Individual headings and
below-rule names with side dates place for Dan and Lee at both 80- and 110-point
rule spacing; Pat still holds. The twelve r3 raw-extent mismatch cases and all
r2 caption/previous-rule tests are retained.

### Red → green evidence by finding

Each behavior group was exercised before its fix. The final test fixtures were
also replayed against the reviewed committed production files, restored in
`finally` by [replay_baselines.py](c2a-r4/replay_baselines.py). The final Send
baseline replay is **52 failed, 41 passed**; Board's three initial reservation
cases are **1 failed, 2 passed** on its starting commit. Passing baseline cases
are positive/negative controls, not claimed regressions. Initial iteration logs
are retained, including fixture corrections; the final replay and final suite
results are the authoritative evidence.

| Finding | Baseline failure and final behavior | Evidence |
| --- | --- | --- |
| **B-1** | 11 same-row identity cases, shared-gap uncertainty, and `roles`/`witness` right-side insertion cases fail on `ef62c4da` (14 failures). Correct names place; different or ambiguous names hold with no fields/high assignment. | [Baseline red](c2a-r4/baseline-send-red.txt), [new regressions green](c2a-r4/regressions-green.txt), [full Send suite](c2a-r4/send-signing-suite.txt) |
| **H-1** | 27 role/wording/suffix cases fail on the starting implementation. All review wording is accounted without moving golden boxes; `Title: Lee Harbor` still holds. | [Initial red](c2a-r4/h1-red.txt), [final baseline red](c2a-r4/baseline-send-red.txt), [green](c2a-r4/regressions-green.txt) |
| **H-2** | Three of the four named stacked layouts fail on the starting implementation; all four now place on their exact respective rules. Mismatched signers and equidistant rows hold. | [Initial red](c2a-r4/h2-red.txt), [final baseline red](c2a-r4/baseline-send-red.txt), [green](c2a-r4/regressions-green.txt) |
| **L-1** | A real loopback HTTP socket drips chunks then blocks: the old implementation retains its model slot past the two-second grace. Set the HTTP client's timeout to `httpx.Timeout(remaining, read=min(2, remaining), pool=min(1, remaining))`; the caller still returns at the total deadline. | [Socket red](c2a-r4/l1-red.txt), [socket and existing deadline controls green](c2a-r4/l1-green.txt), [final regression green](c2a-r4/regressions-green.txt) |
| **L-2** | Four final privacy cases fail on baseline: selected/unselected model candidates and both corresponding History paths. Company-like prose is now `[company]` unless it is a mapped role value or the heading contributing to a local identity score. The same restriction applies to company suffixes and all emitted label/heading/companion paths. Raw text remains local. | [Baseline red](c2a-r4/baseline-send-red.txt), [History red](c2a-r4/l2-history-red.txt), [model/result/History/log green](c2a-r4/regressions-green.txt) |
| **L-3** | An unrelated concurrent upload gets 503 on Board baseline. A committed per-key reservation now releases the SQLite write lock before upload, then stores the verified version. Same-key retries wait at most one second for completion, otherwise return busy without another upload. | [Baseline red](c2a-r4/baseline-board-red.txt), [focused signing green](c2a-r4/l3-green.txt), [full Board suite](c2a-r4/board-suite.txt) |
| **L-4** | As the review explicitly recommends for this slice, upload idempotency is deferred and the orphan risk is documented. A lost response can leave an unreferenced upload; retries still use only their own hash-verified version. No unsupported claim of orphan cleanup is made. | [Operator runbook](c2a-runbook.md#upload-reservations-and-uncertain-responses). Documentation-only; no artificial test. Existing unknown-outcome and hash checks remain in the suites. |
| **N-1** | Three leading-domain-token examples fail on baseline. `acme` now matches `Acme Holdings, Inc.` and analogous generic suffixes; later tokens and omitted distinctive words remain rejected. | [Baseline red](c2a-r4/baseline-send-red.txt), [green](c2a-r4/regressions-green.txt), unchanged r3 single-token controls |
| **N-2** | The finite 90-point-above/125-point-below row-start window is explicitly documented, including the 100-point-above example. No page-wide identity guarantee is claimed. | [Runbook](c2a-runbook.md#identity-extent) and EDD counterparty §4.4. Documentation-only, as requested. |
| **N-3** | Deployment arithmetic documents per-process slots: synchronous workers × 768 MiB child address-space ceiling, plus parent/stack overhead; threaded workers × min(threads, 2) × 768 MiB. A synchronous worker does not exhaust its own two parse slots. | [Runbook](c2a-runbook.md#parser-and-model-capacity). No semaphore behavior change. |

The Board reservation table is created automatically in its existing local
SQLite store; completed mappings need no conversion. Reservations expire after
120 seconds following a crash. Owner tokens prevent an expired uploader from
overwriting a newer reservation. Additional tests cover expiry and stale-owner
rejection. There is no Django schema change, dependency change, migration,
external model call, or deployment in this round.

### Golden outcomes and retained safeguards

[Exact comparison](c2a-r4/golden-comparison.json) and
[recorded placements](c2a-r4/placements.json) compare every field's signer, type,
page, x/y/w/h and confidence with the r3 artifact, using exact equality, not only
the existing golden tolerance. Native field dictionaries also match exactly,
including the date-only metadata and baseline-anchored 18-point signatures.
The fixture PDF bytes and expected geometry files are unchanged.

| PDF | Outcome | Fields | Exact r3 field/native geometry |
| --- | --- | ---: | --- |
| `bare` | `bare`, held | 0 | unchanged |
| `nda` | `placed` | 4 | unchanged |
| `offer` | `placed` | 2 | unchanged |
| `roles` | `placed` | 6 | unchanged |
| `witness` | `placed` | 6 | unchanged |
| `harbor` | `placed` | 2 | unchanged |
| `unusual` | `placed` with local model stub | 2 | unchanged |

The review's phrase “all seven goldens are placed” is corrected here: the bare
fixture intentionally holds, as it did before. No existing test/product-rule
conflict required a relaxation. Previous inline-name, distant-caption,
second-person, unknown-person, company-only uniqueness, parser-resource,
transport, hash-verification, retry, and missing-evidence-quarantine assertions
remain part of the unchanged mandatory suites. Company-only confidence still
requires unnamed, fully accounted local evidence and a unique matching signer.

### Final verification

- **Send:** **725 passed, 0 failed, 0 skipped**, 328.12 s
  ([full log](c2a-r4/send-signing-suite.txt)): all 639 existing tests plus 86
  new r4 cases. The extended seven-fixture property is included.
- **Board:** **295 passed, 3 failed, 58 skipped**, 33.13 s
  ([full log](c2a-r4/board-suite.txt)): all 290 baseline passing tests plus five
  new reservation cases. The only failures are the three supplied
  `test_cloud_edition` baseline cases: `test_detail_pages_program_and_epic`,
  `test_function_serves_the_same_endpoints_and_shapes`, and
  `test_relay_publishes_the_tailnet_payload`.
- **New Send regressions:** **86 passed**, 37.91 s
  ([focused log](c2a-r4/regressions-green.txt)); final baseline replay was
  **52 failed, 41 passed**, 50.69 s, including the extended fixture property.
- **Goldens:** all seven outcomes preserved; every field and native field
  dictionary matches r3 exactly. Six place and `bare` holds with no fields.
- `git diff --check` passes for Send, Board, and the edited EDD document.
  [Footprint](c2a-r4/footprint.json) records source/test hashes, unchanged HEADs,
  empty Git indexes, unchanged fixtures and project memory, and the sole
  existing-test change (the stronger r3 insertion property).

Both supplied runner scripts are used verbatim. Their hard-coded scratch root
is read-only in this sandbox, so the evidence wrappers export a
shell `mktemp` function directing only disposable directories to `/tmp`:

```bash
bash docs/implementation/c2a-r4/run-send-tests.sh dealroom_sign/tests
bash docs/implementation/c2a-r4/run-board-tests.sh
/root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r4/check_goldens.py
```

These invoke the requested `/root/work/sign-product/run-send-local.sh
/root/worktrees/send-c1b dealroom_sign/tests` and `bash
/root/work/sign-product/run-board-tests.sh /root/worktrees/board-s1` respectively.
The scripts under `/root/work/sign-product` were not edited. No work was done in
`send-style` or `sign-style`. No Git staging or commits were performed. The
completion marker is written beside `counterparty-c2a-r4.md` after verification.

## C2a r5

This round implements Gate 3 r4 against Send `079e2957` and Board `104a2b2`.
The complete review, including its ruling on the finite-window limit and the
cases that already held, was read. No existing test was edited, weakened,
skipped or deleted. Production changes are confined to Send's placement parser
(`analysis_version = c2a.5`); Board's reservation behavior is unchanged.

### Changes in review order

- **B-1:** unnamed blocks now have a company-only veto walk above and below
  their local extent, within the existing column band. A rule or prose stops
  the walk; an unobstructed page edge continues into the adjacent page,
  including a row starting exactly at its edge. Person-like or unresolved rows
  set `company_only_blocked`, which can only remove confidence. Distant names
  never become labels, headings, positive identity, fields or model evidence.
  Locally named blocks retain their behavior. Tests cover names 100/150/200 pt
  above, 150/200 pt below, prose/rule stops, both page-break directions,
  matching distant names supplying no positive evidence, column isolation,
  named-block controls and exact comparison of all seven goldens.
- **B-2:** annotations are inspected inside the bounded parser. Non-links
  hold the whole document as `form_fields`; normal appearances on links hold
  too. The reason is “Form fields or annotations require placement review.
  Nothing was sent.” Empty widgets pass only with an explicitly empty `/V`
  in an acyclic, bounded field/parent chain, no nonempty value anywhere in that
  chain, and proven text-free appearances. The proof accepts simple
  rectangle/border operators only. Missing values, text operators, XObjects,
  images, appearance-state dictionaries, cycles and unsupported content hold.
  An unresolved `/V` reference uses a distinct sentinel: pdfminer's default
  `None` cannot be mistaken for proof of an empty field.
  ReportLab's empty text widget and ordinary links retain placement. Tests
  include own/inherited values, parent appearances, FreeText/Stamp/Ink/Text,
  a link with an appearance, and an annotation on another page. Existing
  page-size/resource checks retain precedence over annotation checks.
- **H-1:** a matching printed name allows unrecognized `Title:`/`Its:`
  remainders unless they meet the review's person-like predicate. Company-only
  scoring remains strict. Roles accept hyphens and `Co-`; the table's ordinary
  titles are recognized. Execution clauses using “for and on behalf of” supply
  accounted company evidence and heading candidates, with the optional person
  extracted and checked locally. Sentence-final lines are neither people nor
  unresolved people and remain unaccounted prose for company-only scoring.
  Tests compare title, wording and wrapped-witness variants against Harbor's
  exact signature/date geometry; another person's execution clause still holds.
- **M-1:** compound name captions use the proposed caption expression. The
  unreadable-identity guard applies only to a nonempty, non-label remainder
  that is not a person. Filled mismatched captions still hold.
- **M-2:** a previous block with its own person/company heading and no close
  caption can separate stacked blocks at its rule-row bottom. Side-date
  headings place on their own rules at both 80 and 110 pt spacing; Pat holds.
  Previous-caption ambiguity and shared boundary evidence are preserved.
- **L-1:** empty Email/Address/Phone/Company/Witness captions are accounted;
  filled values remain unaccounted. **L-2:** an underscore run ends its text
  group, so a typed Signature/Date row yields two correctly labeled rules.
  L-2 is implemented now, not deferred.
- **N-1:** role acronyms use the proposed case-sensitive scoped patterns,
  including `C[A-Z]{1,2}O`; mixed-case two-word names are no longer roles.
  **N-2:** partitioning clears uncertainty only when it came from the
  ambiguous-heading guard. Independent boundary flags survive later pairs.

### Interpretations and small deviations

No finding was skipped. H-1's sentence-final rule was pulled forward while
closing B-1 because the new walk otherwise misread the existing `witness`
golden's witness sentence as a person. This preserves the required golden and
does not narrow the veto. The table's role words were added to the vocabulary:
without `Proprietor`, for example, the written remainder predicate itself
classifies “Sole Proprietor” as a person; suffix-form “Account Executive” also
needs recognition to meet the requested `harbor_variant(title=...)` test.

The typed `Name: ________ Title: ________` Harbor variant adds a real blank name
rule. It retains the existing NAME-companion behavior rather than suppressing
a legitimate field solely to make the variant's field count equal the original.
Its original signature/date fields remain exact, and the test separately
requires the added NAME field. The seven original PDFs remain byte-for-byte
unchanged, with exact original field counts and native geometry.

The empty-widget exception is deliberately conservative: even an appearance
with text operators that might render nothing holds. The supported empty
ReportLab appearance has only border/background/clip operations. This keeps
the exception provable without flattening or interpreting annotation text.

### Privacy and retained safeguards

The new walk stores only a boolean outside its local raw evidence; annotation
values never become placement labels. New workflow checks verify that distant
identity and annotation holds create no workflow or History event and expose no
other person's name in the result, exception response, model call or logs.
Existing same-row, gap-between-columns, second-person, caption-boundary,
company-only uniqueness, raw-prose redaction, resource, deadline, transport,
hash-verification, retry and Board reservation tests remain unchanged.

The EDD's r4 limit-acceptance paragraph has been replaced with the r5 confidence
rule. The [runbook](c2a-runbook.md#identity-extent) describes the veto, annotation
hold and empty-widget proof. Existing orphan-upload and per-process capacity
dispositions remain documented. No schema, dependency, migration, deployment
or external model change was made. No work was done in `send-style`,
`sign-style` or another host; no Git staging or commits were performed.

### Verification evidence

The supplied Send and Board runners are invoked unchanged through the local
wrappers, which only redirect their read-only scratch-directory creation to
`/tmp`, as in r4:

```bash
bash docs/implementation/c2a-r5/run-send-tests.sh dealroom_sign/tests
bash docs/implementation/c2a-r5/run-board-tests.sh
/root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r5/check_goldens.py
```

They execute `/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b
dealroom_sign/tests` and `bash /root/work/sign-product/run-board-tests.sh
/root/worktrees/board-s1`. The runners themselves were not edited.

The final new tests were replayed against the reviewed production file from
`079e2957`, restored in `finally` by
[replay_baseline.py](c2a-r5/replay_baseline.py): **85 failed, 47 passed**, 49.48 s.
Passing baseline cases are controls, not claimed regressions. Initial per-group
red/green logs are retained; the final baseline replay and final full suite are
the authoritative results. The first full verification attempt was interrupted
after the exact-page-edge regression was discovered, then restarted after its
fix; the interrupted log is not counted as verification.
The subsequent 856-test run passed before the missing-value-reference check
was added. Its log is retained as intermediate evidence; final verification
below includes that correction and its additional test.

| Finding | Failures on `079e2957` | Final behavior checked |
| --- | ---: | --- |
| B-1 | 13 | Distant/cross-page person evidence vetoes company-only; rule/prose stops, column bands, named controls and all seven exact goldens hold |
| B-2 | 15 | Filled, inherited, visible or unproven annotation evidence holds; proven empty widgets/plain links preserve placement |
| H-1 | 33 | Review titles, execution clauses, title-remainder predicate and wrapped sentence preserve exact boxes; mismatches still hold |
| M-1 | 8 | Compound captions parse; filled mismatches hold; typed Name/Title retains its legitimate NAME companion |
| M-2 | 2 | Both stacked heading/side-date spacings place each person on their own rule |
| L-1 | 5 | Empty contact/company/witness labels are accounted; filled values hold |
| L-2 | 1 | One typed Signature/Date row yields both fields |
| N-1 | 4 | Mixed-case person names are not roles; uppercase CHRO is recognized |
| N-2 | 1 | Independent uncertainty survives partitioning |
| History | 3 | These new holds create no workflow/event and disclose no other person's name |

[Baseline log](c2a-r5/baseline-send-red.txt),
[machine-readable counts](c2a-r5/baseline-summary.json),
[exact-page-edge red](c2a-r5/page-edge-red.txt) and
[green](c2a-r5/page-edge-green.txt) record the regressions.
[Missing-value red](c2a-r5/missing-value-red.txt) and the
[18 annotation cases green](c2a-r5/missing-value-green.txt) verify the strict
empty-widget exception, including an unresolved value reference.
[Golden comparison](c2a-r5/golden-comparison.json) and
[placements](c2a-r5/placements.json) record exact equality with r4 for every
field and native field dictionary: `bare` holds with zero fields; `nda`, `offer`,
`roles`, `witness`, `harbor` and the stubbed-model `unusual` place unchanged.

### Final verification

- **Send:** **857 passed, 0 failed, 0 skipped**, 361.41 s
  ([full log](c2a-r5/send-signing-suite.txt)): all 725 existing tests and all
  132 new r5 cases (129 placement cases and three workflow/History cases).
- **Board:** **295 passed, 3 failed, 58 skipped**, 33.06 s
  ([full log](c2a-r5/board-suite.txt)). The failures are exactly the supplied
  `test_cloud_edition` baseline cases: `test_detail_pages_program_and_epic`,
  `test_function_serves_the_same_endpoints_and_shapes`, and
  `test_relay_publishes_the_tailnet_payload`. Board code and tests are unchanged.
- **Goldens:** all seven r4 outcomes, field counts, coordinates, confidence
  and native field dictionaries remain exact. Six place; `bare` holds.
- **Failing first:** final baseline replay is **85 failed, 47 passed** on
  `079e2957`; every new case passes in the final full Send suite.
- `git diff --check` passes for Send, Board and the edited EDD document.
  [Footprint](c2a-r5/footprint.json) records the verified source/test hashes,
  unchanged HEADs, empty Git indexes, clean Board worktree, and unchanged
  existing tests, fixture PDFs and project memory.

All changes remain unstaged and uncommitted. The completion marker is
`/root/worktrees/dealroom-sign-edd/docs/edd/briefs/counterparty-c2a-r5.done`.

## C2a r6

Implemented the [Gate 3 r5 follow-ups](../../../dealroom-sign-edd/docs/edd/reviews/counterparty-c2a-gate3-r5.md)
from Send base `1efaca25`, in the requested order: H-2, H-1, then the medium
findings and nits. `analysis_version` is now **`c2a.6`**. Changes are confined to
Send placement, new tests/evidence, this report/runbook, and the explicitly
requested EDD rule paragraph. Board, `send-style`, `sign-style`, other hosts,
existing tests, fixture PDFs, dependencies, migrations and project memory were
not changed. Nothing was staged or committed.

### Fixes and failing-first evidence

| Finding | Failures on `1efaca25` | Implemented behavior |
| --- | ---: | --- |
| H-2 | 18 | `Email`, `E-mail`, `Address`, `Phone`, `Tel`, `Company` rules have `OTHER` semantics. All companion kinds are excluded from hosts, heading boundary candidates, following/neighbor boundaries, side-date blockers and walk rule stops. Each of the review's three identity outcomes is exercised for all six labels; a matched signer uses the original By rule. Empty E-mail/Tel captions are accounted like the other empty contact captions. |
| H-1 | 2 | An upward walk stops at rows whose top falls in another host's `(rule.y, rule.y + 125]` extent in the same band. Stacked named-sender/company-only-counterparty blocks place at both 110 and 140 pt spacings; a different name inside the counterparty block still holds (two passing baseline controls). |
| M-1 | 13 | Page-number rows and digit-normalised rows repeated at y ±2 pt on at least two distinct pages are neutral in the walk. Repeated headers place, including ±2 pt offsets and changing digits. Footer patterns do not hide the next page's name. Nonrepeated headers and a 3 pt shift retain the veto (two passing baseline controls). Local evidence is unchanged. |
| M-2 | 13 | Added every proposed company suffix. Execution-clause names use the capitalised PERSON predicate and exclude roles; `the Director`, `The Director` and `Managing Director` become role wording. All cases retain the exact Harbor boxes. |
| M-3 | 1 | Apply `BLOCK_WORDING.fullmatch` after splitting the name head; the comma witness paragraph keeps the exact Harbor boxes. |
| N-1 | 2 | Apply the title-remainder predicate to the head before a comma; both Title/Its with a different person's name hold. |
| N-2 | 2 | Bare capitalised person rows ending in a period retain the second-person veto, in uppercase and title case. |
| History/privacy | 4 | Contact-rule, cross-page-footer, title-remainder and period-name holds create no workflow or History event, return no fields, call no model and expose no other person's name in results, exceptions or logs. |

Each production fix followed a failing test. Initial red/green group logs are
under [c2a-r6](c2a-r6/). The final tests were also replayed against the **exact
review base** by [replay_baseline.py](c2a-r6/replay_baseline.py), restoring the
working production file in `finally`: **55 failed, 4 passed**, 28.84 s.
The four passing cases are preservation controls, not claimed regressions.
[Full baseline log](c2a-r6/baseline-send-red.txt) and
[machine-readable counts](c2a-r6/baseline-summary.json) record every case.

### Accepted deferral and narrow deviation

- **L-1:** retained the conservative annotation hold accepted by the reviewer
  for v1. Absent-`/V` empty-widget relaxation and `/Sig` placement hints are
  deferred to C2b exactly as suggested. Changing this now would contradict the
  existing explicit absent-value hold test and the review's annotation-chain
  preservation requirement. Existing annotation tests remain unchanged.
- **N-2:** preserved the exact known prose fragment `Effective Date.`. A literal
  PERSON-plus-period exclusion would classify that wrapped witness-clause
  ending as a person, violating existing tests. Other bare capitalised person
  rows retain their veto; no existing test was weakened or changed.

No other finding was skipped. The EDD §4.4 and
[runbook](c2a-runbook.md#identity-extent) document these rules. No new raw PDF text
crosses the parser boundary: running-text detection remains local, and only the
existing boolean veto affects company-only scores.

### Verification

The requested runner is invoked unchanged via
[run-send-tests.sh](c2a-r6/run-send-tests.sh), which redirects only its read-only
scratch-directory creation to `/tmp` (the same workaround used in r5):

```bash
bash docs/implementation/c2a-r6/run-send-tests.sh dealroom_sign/tests
# Executes /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
/root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r6/check_goldens.py
```

The 184-case r5+r6 targeted placement run passed. The independent
[golden comparison](c2a-r6/golden-comparison.json) records all seven exact r5
outcomes, coordinates, confidence and native field dictionaries; six place and
`bare` holds. [Placements](c2a-r6/placements.json) include the new analysis version.
The unusual-label fixture uses the existing model stub; no live model was called.
The unchanged r5 checks cover rule/prose stops, inclusive adjacent-page edges,
neighbour column bands, named blocks ignoring distant evidence, distant names
never adding confidence, bare-document holds, annotation privacy and parent
chains, and preservation of independent partition uncertainty. The final suite
also retains all earlier resource, transport, assignment and workflow checks.

The initial full run recorded **914 passed, 2 failed**: both failures were in
new workflow fixtures passing the golden-only `side` property to an API that
rejects it before placement. The corrected fixtures now use accepted API fields;
the final baseline replay above confirms both cases fail on the intended missing
placement hold. The [initial full log](c2a-r6/send-signing-suite-initial.txt) is
retained as diagnostic evidence, not final verification. Existing tests were
unchanged. Running rows are skipped before the previous-host row stop so they
remain neutral even where their geometry overlaps another host's extent.

### Final result

- **Send: 916 passed, 0 failed, 0 skipped**, 384.30 s; all **857 existing**
  tests and **59 new** cases (55 placement, four workflow/History).
  [Full log](c2a-r6/send-signing-suite.txt) records the result and 82 warnings.
- **Failing first:** the final r6 tests on `1efaca25` produce **55 failures and
  four passing preservation controls**; every case passes on `c2a.6`.
- **Seven goldens:** exact outcomes, field geometry/confidence and native fields
  against r5, which already matched r4. Six place; `bare` holds with no fields.
- **Scope/checks:** Send and the edited EDD pass `git diff --check`.
  [Footprint](c2a-r6/footprint.json) records the final code/test/doc hashes,
  unchanged HEAD, empty Git index and unchanged existing tests/fixtures.
  Board and other hosts were not accessed or modified for this patch.
- **Completion marker:**
  `/root/worktrees/dealroom-sign-edd/docs/edd/briefs/counterparty-c2a-r6.done`.

All changes remain unstaged and uncommitted.

## C2a r7

Implemented Gate 3 r6 H-1, L-1, L-2 and N-1 from Send base `be30d623` on
`agent/c1b-counterparty`. `analysis_version` is **`c2a.7`**. All edits are inside
`/root/worktrees/send-c1b`; existing tests, fixture PDFs, r4/r5 placement
artifacts and project memory are unchanged. Nothing was staged or committed.

### Changes and failing-first evidence

| Finding | Failures on `be30d623` | Result |
| --- | ---: | --- |
| H-1 | 13 | Replaced the closed contact vocabulary with the structural short-caption predicate. Such rules are `OTHER`, never hosts or boundaries. Their own blank captions are neutral locally and in the walk, so `Notice Address:` cannot masquerade as a person. All five requested captions exercise the three typed-identity outcomes; matching identities use the original By/Date rules at 400/430 pt. |
| L-1 | 4 | Repeated rows are neutral only where `top < 72` or `bottom > height - 72`. The duplicated body name at y=300 holds. Tests cover strict margin edges and page-number neutrality anywhere; existing running-header cases still place. |
| L-2 | 7 | Period-ending prose uses the last-word set `date`, `agreement`, `above`, `below`, `hereof`. Closing/Execution/Commencement Date and the other endings retain exact Harbor boxes. Uppercase/title-case Dan Whaley with a final period still holds. |
| N-1 | 1 | Hold reasons use “sign and date” for multiple named subjects and “signs and dates” for one, including one missing signer in a larger request. |
| Workflow/privacy | 6 | Each new contact hold and the repeated body-name hold creates no workflow/History event, returns no fields, calls no model and exposes no other person's name in results, exceptions or logs. |

The requested four regressions were written and run before production edits:
[initial failing-first log](c2a-r7/failing-first.txt). That initial run also
contained a mistaken preservation-control fixture: the Harbor PDF contains
both named signers, so it could not exercise “one missing signer.” The test now
uses the single-block contact PDF and retains its exact singular-reason
assertion. No existing test was edited or weakened.

The final **51 new cases** (45 placement and six workflow/privacy) were replayed
against the exact `be30d623` production file by
[replay_baseline.py](c2a-r7/replay_baseline.py), which restores the working file
in `finally`: **31 failed, 20 passed**, 27.79 s. The passing cases are preservation
controls, not claimed regressions. The [baseline log](c2a-r7/baseline-send-red.txt)
and [failure inventory](c2a-r7/baseline-summary.json) record every failure.

### Required golden preservation and narrow deviation

The literal proposed H-1 predicate also matches the existing model-reviewed
signature caption `Hand of the covenanting party:`. Applying it literally made
the mandatory `unusual` golden `bare`, as recorded in
[initial targeted results](c2a-r7/initial-targeted.txt). To satisfy the explicit
requirement that all seven goldens remain exact, that already-recognized caption
retains its existing host/model path alongside the Witness host exception.
There is no new contact-label vocabulary and no change to the golden fixture,
`assert_golden`, expected fields, confidence, or model stub.

The same run showed that `Notice Address:` must be treated as an attached blank
caption when its rule becomes `OTHER`; otherwise its two capitalised words
cause a false identity hold. Only labels actually attached to `OTHER` rules are
excluded from scoring/walking. Unattached text, filled values and surrounding
typed identities retain their checks. `OTHER` rules also cannot shorten the
upper extent boundary.

The [runbook](c2a-runbook.md#identity-extent) and
[local EDD note](c2a-r7/edd-note.md) document the resulting rules and exception.
The external EDD worktree was not edited. Because this worktree has no EDD brief,
the [local brief record](c2a-r7/counterparty-c2a-r7.md), EDD note and completion
marker are kept together under `docs/implementation/c2a-r7/`.

### Verification

The supplied runner is invoked directly and unchanged, with the requested URL:

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
/root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r7/check_goldens.py
```

- **Targeted r6/r7:** **106 passed**, 43.35 s
  ([log](c2a-r7/targeted-green.txt)).
- **Seven goldens:** all exact against **both r4 and r5**, on outcome, signer,
  type, page, x/y/w/h, confidence and native field dictionaries. Six place;
  `bare` holds with zero fields. Each placed fixture also passes `assert_golden`.
  [Comparison](c2a-r7/golden-comparison.json),
  [placements](c2a-r7/placements.json),
  [checker](c2a-r7/check_goldens.py). The unusual fixture uses the existing stub;
  no live model was called.
- **Full signing suite:** **922 passed, 45 failed, 0 skipped**, 426.16 s;
  all 967 cases ran, including all 51 new cases. The
  [full log](c2a-r7/send-signing-suite.txt) records 74 warnings. This is **not a
  green full-suite verification** in the current sandbox.
- **Environment/baseline check:** all **45 failures reproduce on untouched
  `be30d623`**, 60.23 s ([baseline replay](c2a-r7/baseline-infrastructure.txt)).
  Forty-three failures report denied Redis access at `127.0.0.1:16379`
  (`Operation not permitted`); the transport test cannot create its loopback
  HTTP socket. The remaining preview-dispatch assertion also reproduces on
  baseline; its renderer reads dynamic settings through the same Redis cache
  and its wrapper suppresses dispatch exceptions. The separate
  [route recheck](c2a-r7/route-failure-recheck.txt) confirms the socket denial.
  No tests were skipped, changed, or given replacement mocks. Socket access
  must be available to obtain a green full-suite result with the supplied runner;
  approval escalation is unavailable in this environment.
- **Scope/checks:** `git diff --check` passes; HEAD remains `be30d623`, the index
  is empty, and existing tests, fixture PDFs, r4/r5 artifacts and memory remain
  unchanged. [Footprint](c2a-r7/footprint.json) records source/test/document
  hashes and [verification summary](c2a-r7/verification-summary.json) records
  the identical full-suite/baseline failure inventory.
- **Completion marker:**
  [counterparty-c2a-r7.done](c2a-r7/counterparty-c2a-r7.done), beside the local
  brief record. It explicitly records implementation completion and the
  outstanding full-suite environment limitation.

All changes remain unstaged and uncommitted.

## C2a r8

Implemented Gate 3 r7 B-1, mandatory company-identity defence, M-1, L-1 and
N-1 from `b651e646` on `agent/c1b-counterparty`. `analysis_version` is
**`c2a.8`**. All writes are inside `/root/worktrees/send-c1b`; nothing is staged
or committed.

### Fixes and failing-first evidence

The 52 initial regression/control cases ran against unchanged r7 production
code before edits: **47 failed, 5 passed**, with no collection errors. The five
passing cases are the `Signature:` preservation controls. Text rows in these
fixtures use top-down row coordinates; signature/date coordinates identify
their actual PDF rules. The final file adds 18 boundary/preservation cases,
for **70 new tests**, without editing any existing test.

| Item | Initial failures | Final behaviour |
| --- | ---: | --- |
| B-1 | 25 | All five requested captions in C4, C8, C10, C12 and C13 preserve the unusual host and return `needs_sender / model_not_configured`, with no fields. Unknown short captions become `OTHER` only when subordinate to a recognised signature/Witness in the same band at `5 < gap <= 125`, without an intervening identity heading. The six contact captions remain unconditional `OTHER`. |
| Independent defence | 15 | With the subordinate rule forced back to r7 behaviour, C8, C12 and C13 each retain only the neighbouring host, mark it `uncertain_identity`, score it zero and hold without a model call. |
| M-1 | 5 | C7 retains both 340 and 400 in the confirming stub's candidate payload. Dan places `model-high` on 400, with Date 430; never on Witness 340. |
| L-1 | 1 | The sole `Authorised signatory:` host places `model-high` on 400 with Date 430. |
| N-1 | 1 | `MODEL_SIGNATURE_CAPTION` is removed. The unusual golden remains exact through the ordinary host path; the pre-existing `safe_label` allowlist entry retains its meaning. |

[Failing-first counts](c2a-r8/failing-first-summary.json) and
[51 review-layout outcomes](c2a-r8/regression-placements.json) contain compact
evidence. No raw suite logs are retained.

Two details are necessary to meet the requested C7/C8 outcomes. In C7, the
three stated conditions alone would still classify 400 as subordinate to
Witness 340 because blank `Name:` 352 is not a person heading. A Witness's
intervening name caption, including a blank one, also closes that identity
group. In C8, the earlier company heading lies outside the neighbour's local
90-point window. The independent defence follows leading typed names back
through up to 90 points of contiguous block rows to that heading, stopping at a
real host or unaccounted prose. This check only removes confidence and emits no
additional text. It runs after partitioning, so the resulting uncertainty
cannot be cleared by a later partition. It counts standalone company-heading
rows, preserving the existing interpretation of behalf wording and neutral
legal-form wording such as `LLC`.

### Preservation and verification

- **Targeted r6/r7 plus initial r8 cases:** 152 passed in 36.02 s.
- **Final r8 file:** 70 passed in 11.23 s, including strict distance edges,
  column separation, all four identity-heading types, and the six contact
  captions without a preceding host.
- **Final production-code targeted check:** 101 passed in 21.36 s: all 70 r8
  cases plus the 31 unchanged r4 Harbor block-wording controls.
- **Seven goldens:** exact against both r4 and r5 on status, signer, type, page,
  x/y/w/h, confidence and native field dictionaries. Existing golden
  assertions remain unchanged; the unusual fixture uses the existing stub.
- **Signature controls:** C12 places `high` on 360/395. C4, C8, C10 and C13 hold,
  matching r7. Existing r6/r7 typed-contact identity tests are unchanged.
- **Scope:** existing tests, fixture PDFs, r4/r5 placement baselines and project
  memory are unchanged. `git diff --check` passes and the index is empty.

Evidence: [targeted summary](c2a-r8/targeted-summary.json),
[r8 summary](c2a-r8/r8-summary.json),
[final targeted summary](c2a-r8/final-targeted-summary.json),
[golden comparison](c2a-r8/golden-comparison.json),
[golden placements](c2a-r8/placements.json),
[preservation checks](c2a-r8/preservation-summary.json), and
[reproducible evidence checker](c2a-r8/check_evidence.py).
The [runbook](c2a-runbook.md#identity-extent) and
[local EDD note](c2a-r8/edd-note.md) record the final semantics.

The first complete run found four existing neutral legal-form controls that
the new check treated as different company names: **1,033 passed, 4 failed**.
The guard now excludes existing `BLOCK_WORDING` before comparing company
headings. Those tests remain unchanged. The
[initial full-suite summary](c2a-r8/initial-full-suite-summary.json) records
the complete failure inventory.

**Final full signing suite: 1,037 passed, 0 failed, 0 skipped, 82 warnings,
426.69 s.** This is the original 967 tests plus all 70 r8 cases, using the
supplied runner and URL:

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```

The invocation additionally used `--junitxml` only to collect counts; the
temporary XML was converted to the
[verification summary](c2a-r8/verification-summary.json) and removed.
The [completion marker](c2a-r8/counterparty-c2a-r8.done) is beside the
[local brief](c2a-r8/counterparty-c2a-r8.md). Implementation and verification
are complete. HEAD remains `b651e646`; no staging or commits were performed.

## C2a r9

Implemented the manager-selected main Gate 3 r8 B-1/H-1 fix on
`agent/c1b-counterparty` at `5e5ee6ea`; `analysis_version` is **`c2a.9`**.
The full review was read, including L-1, N-1 and the previously held cases.

When `subordinate_caption` makes a rule `OTHER`, a `person_text` row in that
rule's own caption slot (`0 <= top - rule.y < 22`, `abs(x - column) < 35`)
vetoes every host whose extent contains it. The veto sets
`uncertain_identity` after block partitioning, so later attribution cannot
clear it. Affected hosts score zero and the requested layouts hold with no
fields or model call. The six unconditional contact captions bypass this
veto. No new text or fields cross the parser-worker boundary.

### Failing first and requested executions

Before the production edit, **115 failed, 17 passed**, with no errors or
skips. All 105 new regression cases reproduced a placement instead of a
hold; the ten manager-approved existing H-1 cases failed for the same reason.
All twelve Signature controls and the other five existing H-1 cases passed.
[Failing-first summary](c2a-r9/failing-first-summary.json).

| Review matrix | Cases | Required final outcome |
| --- | ---: | --- |
| B-1: C12/C13 × six headings × five captions | 60 | Hold, no fields, zero identity score, no model call |
| B-1: behalf line on caption row at x=300, all five captions | 5 | Hold, no fields |
| H-1: both party mirrors × Title: Director / Title: / blank Name: / no row × five captions | 40 | Hold, no fields, zero identity score, no model call |
| Signature controls: both layouts × six headings | 12 | C12 remains high on 360/395; C13 holds |
| Caption-slot strict edges and a row overlapping two host extents | 9 | Exact bounds; both containing hosts vetoed |

The only existing test edit changes Lee/LEE and Pat/PAT to holds in
`test_h1_short_contact_caption_preserves_typed_identity`: **10 of 15 cases**,
with the required Gate 3 r8 B-1 comment. Its five other expectations, all
other existing tests, fixture PDFs and r4/r5 placement baselines are intact.
There are **126 new tests**. [Preservation checks](c2a-r9/preservation-summary.json).

The [runbook](c2a-runbook.md#identity-extent) documents the new veto and L-1:
the second-company defence can hold correct single-block layouts, intentionally
in the safe direction. [Local brief](c2a-r9/counterparty-c2a-r9.md).

### Verification

- Targeted r6/r7/r8 plus the initial r9 matrix: **287 passed**, 88.919 s.
- Nine additional exact-boundary/overlapping-host checks: **9 passed**, 0.870 s.
- [Executed review placements](c2a-r9/regression-placements.json) cover every
  B-1 heading/layout/caption, the right-side behalf cases, H-1 stacks and
  Signature controls, addressing N-1.
- [Golden placements](c2a-r9/placements.json) and
  [comparison](c2a-r9/golden-comparison.json) compare all seven goldens with
  both r4 and r5 on status, geometry, confidence and native fields.
- [Preservation placements](c2a-r9/preservation-placements.json) replay column
  bands, recognised headings, blank/absent names, the original C layouts,
  forced subordination, C7/L-1 model stubs, and contact captions.
- [Evidence checker](c2a-r9/check_evidence.py) uses real reportlab PDFs and the
  real parser subprocess, except the explicitly isolated forced-subordination
  checks. Model paths use stubs; no external model is called.

The full signing suite uses the requested runner and URL:

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```

Only compact summaries and placements are retained. The
[summary runner](c2a-r9/run_summary.py) captures suite output in memory, converts
temporary JUnit XML to counts, then removes the XML. It adds `--tb=short` and
`--junitxml` for reporting only.

The executed evidence checker passed **117 requested matrix/control outcomes**
and **275 preservation outcomes**: 16 column-band cases, 50 recognised-heading
cases, 120 blank/absent-name cases, 25 original C layouts, 15 forced-subordination
holds, 10 C7/L-1 stub placements and 39 contact cases. All seven goldens are
exact against both baselines, including native fields; none classifies a rule
as subordinate. The unusual golden evaluates the predicate once and returns
false. [Placement summary](c2a-r9/placement-summary.json).

**Final full signing suite: 1,163 passed, 0 failed, 0 errors, 0 skipped,
82 warnings, 489.330 s** (the original 1,037 plus 126 new tests).
[Full-suite summary](c2a-r9/full-suite-summary.json) and
[verification summary](c2a-r9/verification-summary.json).

`git diff --check` passes; the existing report is preserved with this section
appended. HEAD remains `5e5ee6ea`, the index is empty, and project memory is
unchanged. The [completion marker](c2a-r9/counterparty-c2a-r9.done) is beside the
local brief. Implementation, executed evidence and full-suite verification are
complete. All changes remain unstaged and uncommitted.

## C2a r10

Applied Gate 3 r9 B-1/M-1 on `agent/c1b-counterparty` at `4db63354`;
`analysis_version` is **`c2a.10`**. Read Blocking B-1, M-1, L-1 and N-1 in
full. Production changes are limited to the version and the exact prescribed
`absorbed_names` predicate: `top - rule.y >= -12`, `x1 > column - 5`, and
`person_text`. Collection remains subordinate-only; the six unconditional
contact captions remain exempt. Host-extent containment is unchanged.

The [runbook](c2a-runbook.md#identity-extent) now describes **a typed name at
or below a subordinated rule, within the absorbing host's extent**. It also
names the accepted single-signer Fax-style hold next to L-1, including the
out-of-slot forms under the seven non-exempt contact captions.

### Failing first

The final tests ran against unchanged production code at `4db63354` before
the fix: **391 failed, 116 passed, 0 errors/skips, 127.882 s**.
[Executed summary and representative failures](c2a-r10/failing-first-summary.json).
The production hash matches the base commit; test hashes are recorded.

| New test group | Cases | Required r10 outcome |
| --- | ---: | --- |
| Four out-of-slot forms × C12/C13 × six headings × five captions | 240 | `needs_sender/ambiguous_identity`, no fields, score zero, no model calls |
| dy +22/+24/+26/+28/+30/+34 × both layouts × five captions | 60 | Same hold |
| Signature controls × four forms × both layouts × six headings | 48 | C12 high on 360/420; C13 holds; no model calls |
| Additional H-1 forms × both mirrors × five captions | 40 | Hold, no fields, no model calls |
| M-1: four forms × seven non-exempt contacts × Lee/LEE and Pat/PAT | 56 | Same identity hold |
| Six exempt contacts × four forms × both matching signers | 48 | High on 400/430; no model calls |
| Exact seven-golden comparison | 7 | Status, geometry, confidence and native fields match r4/r5 |

All 356 B-1/M-1 cases failed first by placing instead of holding. Thirty new
out-of-slot H-1 variants also placed with the original stack Date at 395;
ten already held. These extensions are separate from the original 40 H-1
tests, which remain untouched. The 48 Signature controls, 48 exempt-contact
controls and seven goldens passed before the fix.

There are **499 new tests**. The **only existing-test edit** is the approved
eight-case `test_caption_identity_slot_edges`, retargeted to inclusive
`dy = -12` and strict `x1 > column - 5`, preserving its structure. Five of
those boundary assertions failed first. No other existing tests or golden
fixtures/baselines were edited. The [EDD note](c2a-r10/edd-note.md) explains
the initial new-test draft, the final stack fixture, and reproduction.

### Verification

**Full signing suite: 1,662 passed, 0 failed, 0 errors, 0 skipped,
82 warnings, 560.649 s** (1,163 existing plus 499 new tests).
[Full-suite summary](c2a-r10/full-suite-summary.json). Both test-file hashes
match the failing-first run. The original H-1 stacks still hold and all seven
goldens are exact against r4 and r5 on status, geometry, confidence and native
fields.

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```

The [summary runner](c2a-r10/run_summary.py) adds only `--tb=short` and temporary
JUnit XML for count collection. Raw output is held in memory and discarded;
the XML is removed after writing the compact summary.

The [evidence checker](c2a-r10/check_evidence.py) passed **532 executed matrix
and control cases**, including the original 40 H-1 stacks, with **zero external
model calls**. [Grouped outcomes](c2a-r10/review-placements.json) retain every
case ID with its asserted result; [placement summary](c2a-r10/placement-summary.json)
records the counts. [Golden placements](c2a-r10/placements.json) and
[comparison](c2a-r10/golden-comparison.json) confirm seven exact goldens;
the unusual golden uses one local model stub, and no golden subordinates a rule.

[Preservation audit](c2a-r10/preservation-summary.json): the production diff is
exactly the requested predicate/version change, only the approved existing
test function changed, fixtures/baselines are intact, the report is appended,
and the index and project memory are unchanged. `git diff --check` passes.
HEAD remains `4db63354`; no staging or commits were performed.

Implementation, full-suite verification and executed evidence are complete.
[Completion marker](c2a-r10/counterparty-c2a-r10.done).


## C2a r11

Applied Gate 3 r10 B-1/M-1/N-1 on `agent/c1b-counterparty` at `945ad159`;
`analysis_version` is **`c2a.11`**. The absorbed-identity veto now records the
SIGNATURE/Witness rule that subordinated each caption, collects person rows
strictly below that rule, and retains only names within that rule's own host
extent. A rule without a block retains its collected names (fail closed).
Every host containing a retained name is vetoed after partitioning. The
caption dy/column filters are removed; the six unconditional contact captions
remain exempt. [Implementation note](c2a-r11/edd-note.md).

The Boolean `subordinate_caption()` wrapper and its classification gate are
preserved, so all existing r8 tests keep their forcing hook. Host collection
uses the new `subordinating_host()` helper. No scoring, extent geometry,
worker payload, or ordinary signature classification changes are included.
The [runbook](c2a-runbook.md#identity-extent) names the absorbing host explicitly.

### Failing first

Finalized tests on byte-for-byte `945ad159` production: **1,017 failed,
239 passed, 0 errors/skips, 318.318 seconds**. There are 1,000 B-1 placements
instead of holds, 12 M-1 holds instead of placements, and five failing
boundary assertions. Twenty B-1 layouts already hold because extraction
merges the name into a long heading. All 204 measured Signature controls,
four side-above controls, and the Witness-without-block control pass.
[Executed summary](c2a-r11/failing-first-summary.json).

New-test draft corrections and the interrupted initial verification attempt
are documented in the [EDD note](c2a-r11/edd-note.md). Only the new r11 B-1
assertion was adjusted to require the specified observable hold without an
unnecessary internal flag assertion. No existing test outside the approved
r9 function was changed. The unchanged r11 implementation was restored
before the complete final suite.

The new file adds 1,241 cases. B-1 spans 17 forms × C12/C13 × six headings ×
five captions: plain/prefixed caption-baseline names at 13/14/16/18 pt,
raised names from dy −13 to −28, an indented caption, and a left-margin name.
M-1 covers four captions with two signer configurations in stacked layouts,
plus both side-by-side name positions. All holds require no fields and zero
model calls; placements require the correct signer, lines, and confidence.

The only existing-test change is the approved
`test_caption_identity_slot_edges`, retaining its structure and all eight
original cases, flipping the three specified expectations, and adding seven
host-boundary probes. All r8/r10 tests and golden fixtures remain untouched.

**Baseline discrepancy:** the new C12 Signature forms do not all place on
r10. Across the 204 new controls, unchanged r10 produces 198 holds and six
placements; C12 places only the six margin cases. The new tests preserve
these measured outcomes, while the existing r10 Signature controls still
require C12 placement on 360/420 and C13 holds. The initial draft failures and
compact executed baseline are retained in the [EDD note](c2a-r11/edd-note.md).

### Verification

**Full signing suite: 2,910 passed, 0 failed, 0 errors, 0 skipped,
82 warnings, 879.909 seconds** (1,662 existing + 1,241 new + seven additional
boundary parameters in the approved r9 function).
[Full-suite summary](c2a-r11/full-suite-summary.json). Final test hashes match
the failing-first run, and the production hash matches the executed evidence.

All 1,020 B-1 cases hold with no fields and zero model calls. All 16 M-1
cross-host probes place correctly. Both 40-case H-1 matrices, every r8/r10
test, and the overlapping-host veto pass unchanged. All seven goldens match
the complete r10 results exactly except `analysis_version`; geometry,
confidence, and native fields also match r4/r5 exactly.
[Golden comparison](c2a-r11/golden-comparison.json).

[Compact placement evidence](c2a-r11/placement-summary.json) includes 34 B-1
representatives, all 16 cross-host cases, all 204 new Signature controls,
and seven goldens. External model calls are forbidden; only the unusual
golden uses one local confirming stub. Raw logs and temporary XML are absent.

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```

The [preservation audit](c2a-r11/preservation-summary.json) confirms the sole
permitted existing-test edit, unchanged r8/r10 tests and golden baselines,
append-only report, unchanged project memory, empty index, and unchanged
HEAD `945ad159`. `git diff --check` passes. No staging or commits were performed.
Implementation, executed evidence, and verification are complete.
[Completion marker](c2a-r11/counterparty-c2a-r11.done).


## C2a r12

Applied Gate 3 r11 B-1 **fix A only**, with `analysis_version = c2a.12`, on
HEAD `0c190e9b`. Absorbed names now retain their caption label alongside the
actual subordinating host. A name survives the filter when its own host extent
contains it, **or any block extent on that page contains both the absorbed
caption label and the name**. A rule without a block still retains its names
(fail closed). This replaces the host-only retention description in r11.
The veto still runs after partitioning and cannot add identity confidence.
Host iteration order is unchanged; fix B is not included.
[EDD note](c2a-r12/edd-note.md).

Failing first on unchanged `0c190e9b`: **256 failed, 135 passed, 0 errors/skips**
among 391 new real-worker tests. The failures are all 120 Matrix 1 cases, all
135 PAT-only Matrix 2 cases, and the same-band right-host regression. All
135 Dan+Pat cases already held. Every new case requires
`needs_sender/ambiguous_identity`, no fields, and zero model calls.
[Summary](c2a-r12/failing-first-summary.json) ·
[Per-case results](c2a-r12/failing-first-summary-cases.json).

The review names eight Matrix 2 forms but its 270 total requires nine. The
additional form here is a 10 pt caption-baseline name; the EDD note and test
generator document that assumption. The reproduced counts match the review.
The right-host probe deliberately uses two rules at the same y: r11 and a
nearest-first fix B still place, while fix A holds. This pins containment
independently of host iteration order.

The **1,750-case executed evidence** reproduces the review table: Matrix 1
changes 120 placements to holds; Matrix 2 changes 135 placements to holds;
all 1,020 r11 B-1 holds, 204 Signature controls, 16 M-1 placements, 72 r9 heading
cases, 40 r9 H-1 holds, and seven goldens preserve their full results except
the version. Dan+Pat Matrix 2 holds also lower Pat's assignment score to zero.
All seven complete real-worker golden results equal **r4/r5 exactly except
`analysis_version`**, including evidence and model metadata; native fields
also match. Only the unusual golden calls its local stub once; external model
calls are zero. [Counterfactual summary](c2a-r12/counterfactual-summary.json) ·
[Per-case full results](c2a-r12/counterfactual-cases.json) ·
[Golden comparison](c2a-r12/golden-comparison.json).

**Review L-1:** The corrected control baseline is preserved: **198 holds and
six correct C12 margin placements on 360/420**, with no model calls and zero
full-result differences from r11. No test expectation was changed for it.

**Review N-1:** The duplicate host search remains intentional: existing r8
tests force the `subordinate_caption()` Boolean hook. The subsequent
`subordinating_host()` lookup supplies the actual tuple host and still uses
the same helper. Fix A changes the later retention filter, preserving that
hook and all existing test targets without adding a second lookup policy.

**Full signing suite: 3,301 passed, 0 failures/errors/skips, 82 warnings,
961.055 seconds**: all 2,910 existing cases plus 391 new cases.
[Summary](c2a-r12/full-suite-summary.json) ·
[Every test result](c2a-r12/full-suite-summary-cases.json).

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```

The summary runner adds `--maxfail=1` and reporting arguments. No existing
test failed. The [preservation audit](c2a-r12/preservation-summary.json) confirms
all 50 existing test/fixture files are byte-for-byte unchanged, only `extract`
changed among product functions, and execution hashes match the delivered
source. The report is append-only, project memory and index are unchanged,
and HEAD remains `0c190e9b`. No staging or commit was performed.
[Completion marker](c2a-r12/counterparty-c2a-r12.done).

The local marker is written. Copying it to the requested `dealroom-sign-edd`
brief path failed with **Read-only file system**; the external marker remains
undelivered. Code, tests, evidence, and the local payload are complete.


## C2a r13

Applied Gate 3 r12 B-1 **fix A′ exactly** on `4ad9f7e2`, with
`analysis_version = c2a.13`. At absorbed-name collection the caption rectangle
now spans its label and rule:
`[min(label.x0, line.x0), label.y0, max(label.x1, line.x1), line.y]`.
Fix A's existing same-page containment clause uses this union. Host selection,
scoring, extents, exemptions, partitioning, and worker payload are unchanged.
[EDD note](c2a-r13/edd-note.md).

Failing first on unchanged r12: **573 failed, 376 passed, 0 errors/skips** in
234.430 seconds. Failures were the exact review reproduction (1), the
seven-caption × x150/200/260 × dy0/20 grid (32 of 42), and the short-caption
sweep (540 of 864). The new file contains **949 real-worker tests**, including
42 Low controls. Every B-1 case requires `needs_sender/ambiguous_identity`,
zero fields, and zero model calls. No existing test was changed or skipped.
[Summary](c2a-r13/failing-first-summary.json) ·
[Per-case outcomes](c2a-r13/failing-first-summary-cases.json).

The **2,699-case counterfactual execution** reproduces the reviewer table:
all 864 sweep cases now hold, with exactly 540 full-result changes from r12;
the reproduction and 32 same-band cases also change from placements to holds.
There are **zero other full-result differences from r12**, comparing all keys
except `analysis_version`. Matrix 1, Matrix 2, all 1,020 r11 B-1 cases, 204
Signature controls, 16 M-1 cases, 72 r9 heading cases, 40 r9 H-1 cases, the
original same-band probe, all Low controls, and the seven goldens preserve
r12 results. The original table totals 1,750 cases, despite the review's
1,751 prose count. [Executed table](c2a-r13/counterfactual-summary.json) ·
[Full per-case results](c2a-r13/counterfactual-cases.json).

All **seven complete real-worker goldens equal r4/r5/r11/r12 exactly except
`analysis_version`**, including native fields. Six place; bare stays bare.
Only unusual uses one local confirming stub; external model calls are zero.
[Golden comparison](c2a-r13/golden-comparison.json).

**Review L-1:** Two controls pin the existing printed-name policy when both
label and rule end before the right block's extent. Pat still places at
signature y290/date y400 with high confidence and no model call. This is the
review's nonblocking residual, outside B-1; scoring policy remains unchanged.
The tests do not claim to reproduce the unspecified 36-case Low grid.

**Review L-2:** Forty controls add Pat's separate HARBOR line at y560 to
Matrix 1: 20 PAT-only placements on that line (score 4, margin 4), and 20
Dan+Pat holds. All match r12 in full and make zero model calls.

**Review N-1:** The r12 EDD note's `HEAD remains 0c190e9b` and its
`HEAD_unchanged` audit refer to the coder's pre-commit execution. The manager
subsequently committed r12 as `4ad9f7e2`, which is the base for this r13 run.
Historical evidence is preserved; those older statements do not describe the
current HEAD. No staging or commit is performed for r13.

**Full signing suite: 4,250 passed, 0 failures/errors/skips, 82 warnings,
1,178.745 seconds** (3,301 existing + 949 new).
[Summary](c2a-r13/full-suite-summary.json) ·
[Every test outcome](c2a-r13/full-suite-summary-cases.json).

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```

Only reporting arguments were added. The
[preservation audit](c2a-r13/preservation-summary.json) confirms 51 existing
test/fixture files unchanged, the exact requested product edit, matching
execution hashes, append-only report, unchanged memory, empty index, and
unchanged HEAD `4ad9f7e2`. `git diff --check` passes. No staging or commit was
performed. [Completion marker](c2a-r13/counterparty-c2a-r13.done).

The local r13 marker is written. The subsequent copy to the requested external
`dealroom-sign-edd/docs/edd/briefs/counterparty-c2a-r13.done` failed with
**Read-only file system**; that destination is outside this session's writable
roots and approval escalation is unavailable. The ready local payload records
this blocker. Implementation, verification, and evidence are complete; external
marker delivery is the only unfinished action.


## C2a r14 — mixed-heading blocks cannot lend a printed name

Review: `counterparty-c2a-gate3-r13.md` (B-1, L-1, N-1), on committed r13
`2ff90be102b4a4a3f65cee15a3f8258fcb445685`. Production version: `c2a.14`.

Both requested candidates were executed before editing production:
**6,518 cases per candidate/baseline**, with 30 additional real-worker
checks across the reproduction, correct controls, and goldens.
[Both counterfactual tables and choice](c2a-r14/edd-note.md) ·
[Summary](c2a-r14/counterfactual-summary.json) ·
[All full results](c2a-r14/counterfactual-cases.json).

**Chosen: (b), shared-name veto.** When mixed company headings veto a block,
its physical printed-name rows also veto any other extent containing those
rows on that page. The second pass makes this independent of traversal order.
A separately printed occurrence of the same name remains eligible. Only
`extract` and `VERSION` change in the product; scoring and worker output
schemas stay unchanged.

Candidate (a), the column-gutter bound, has zero wrong placements and preserves
all earlier results/goldens, but fails the explicitly required reproduction
hold: it places Pat correctly on the counterparty rule. Candidate (b) also
passes the required hold, so it is the eligible choice. No third candidate
was introduced. [Candidate a](c2a-r14/candidate-a.patch) ·
[Candidate b](c2a-r14/candidate-b.patch).

**Failing first:** the final new 3,823-test file, run on unchanged r13, had
**105 failures, 3,718 passes, zero errors/skips**: reproduction 1, grid 84,
and dense fixed sweep 20. [Summary](c2a-r14/failing-first-summary.json) ·
[Every outcome](c2a-r14/failing-first-summary-cases.json).

The selected candidate holds the real-worker reproduction with zero fields
and model calls. The **3,456-case grid has zero wrong placements and 2,256
holds** (1,200 placed). Its r13 baseline has the review's 84 wrong placements.
The **360-case fixed sweep has zero wrong placements and 232 holds**.
Unambiguous staggered controls remain placed. The grid is explicitly defined
in the new tests; the note documents the review's omitted generator details.

Every full result in the **2,699-case r13 table remains exact except
`analysis_version`**, including the original 1,750 preserved cases and all 864
r12 sweep cases. No wrong-to-hold preservation exceptions are needed. All
seven counterfactual real-worker goldens remain exact except version.
Only the unusual golden invokes a local stub once; external calls are zero.

The new grid's conservative cost is 72 previously correct mixed-heading
placements becoming holds, alongside the 84 wrong placements becoming holds.
Another 180 grid holds change assignments. The fixed sweep adds 20
wrong-to-hold and 20 hold-to-hold changes; the reproduction adds one.
There are **no new placements** under (b) in the executed families.
[Every difference](c2a-r14/counterfactual-differences.json).

**L-1:** the existing authoritative printed-name policy remains pinned by two
new real-worker controls and the unchanged original tests. **N-1:** this run
uses r14 completion-marker names and leaves prior markers intact. The two
additional separate-name tests cover same-page and cross-page locality.

No existing test is changed, skipped, or weakened. No staging or commit is
performed; HEAD remains `2ff90be102b4a4a3f65cee15a3f8258fcb445685`.

**Full signing suite: 8,073 passed, 0 failures/errors/skips, 82 warnings,
1,339.898 seconds** (4,250 existing + 3,823 new).
[Summary](c2a-r14/full-suite-summary.json) ·
[Every outcome](c2a-r14/full-suite-summary-cases.json).

The final production worker's **seven goldens exactly match r13 except
`analysis_version`**, including native fields.
[Placements](c2a-r14/placements.json) ·
[Comparison](c2a-r14/golden-comparison.json).

The [final preservation audit](c2a-r14/preservation-summary.json) confirms
**52 existing test/fixture files unchanged**, exact failing-first/final test
hashes, exact candidate/final product hashes, only `extract` changed as a
product function, append-only report, unchanged memory and HEAD, empty index,
and a clean whitespace check. Implementation and evidence are uncommitted.

The [local completion marker](c2a-r14/counterparty-c2a-r14.done) was written
first. The subsequent external r14 briefs-marker write failed with
**Read-only file system**. The local marker records this blocker.
Implementation, verification, and evidence are complete; external-marker
delivery is blocked by the read-only destination.
