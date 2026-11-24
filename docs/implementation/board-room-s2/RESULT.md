# S2 — Dealroom create/import result

Implemented on `agent/board-room-s2`, based on `bed45588`. Changes remain
uncommitted. No running Board, preview, Dealroom stack, or Sign fork was changed.
No real Google request or mail was sent.

## Changes

- Reused the S1a `BoardRoom` draft/hash/state/revision columns and default-empty
  binding capabilities. Added `staged_import` and durable `RoomCommandReceipt`
  records. Creation, canonical restricted link, assignment, and receipt commit
  atomically. Deleted rooms retain receipt tombstones; changing command keys
  cannot recreate the same draft.
- Added scoped BoardProxy handling to create, folders, upload, imports and complete.
  Current organization/board scope, binding, human via, role and write capability
  are checked before receipt replay. Room locking precedes upload receipt lookup;
  matching retries return the original result before revision checks. Create
  uniqueness conflicts are recovered inside a savepoint or return retryable 409.
- Stored manifests govern parent-first folders, sibling positions, filenames,
  purposes, checksums, access and completion. Caller manifests cannot replace an
  approval. Completion verifies all steps, current primary versions, checksums,
  tree/order, render readiness and the 500-page bound. NDA-on commands remain
  building with “NDA comes next”; no NDA policy or invitations are published.
- New folder/document settings are hidden on every link until atomic completion.
  A building room fails recipient policy. An existing ready room keeps its old
  content available during a staged batch. Explicitly approved empty folders are
  exposed with parent IDs/order after completion; legacy empty/evidence folders
  remain private. Legacy JWT/key mutation paths resolving the affected room,
  grant, link, file policy, document or NDA policy are locked during building or
  staging; ready-room staff behavior remains available.
- Uploads preserve DOCX originals, reject `.doc` with “save as .docx”, bound PDF
  pages and Office packages, use command/hash-addressed storage and explicitly
  enqueue the renderer after commit, including Office. Board multipart HMAC hashes
  the exact bounded bytes without Django's smaller generic body-limit failure.
- Added bounded NDA preparation on supplied bytes only: read capability,
  15 MiB/50 PDF pages, bounded parser subprocess and ten requests per binding per
  minute. It returns a checksum and a deferred NDA state, with no policy write or
  automatic field publication.
- `reap_board_staging --storage-root ...` is an operator-only dry run by default.
  With `--apply`, it removes only old unreferenced S2 files, under the room lock,
  and preserves referenced bytes and every active staged room.
- Registered the exact new operations, regenerated OpenAPI/MCP inventory and typed
  completion/import bodies. The shared v1 contract retains its read examples and
  gains a versioned command section plus bounded preparation metadata. All three
  copies are byte-identical.

## Validation and failing-first evidence

| Evidence | Result |
| --- | --- |
| `failing-first.txt`, before implementation on `bed45588` | 27 failed |
| `extended-base-red.txt`, final acceptance cases replayed in an untouched base archive | 50 failed |
| `placement-red.txt` | Four preparation-bound cases failed before the route existed |
| `final-postgres.txt` | **50 passed**, including concurrent create/upload, replay, tombstones, recipient visibility, DOCX, bounds and migration reverse/forward |
| `dealroom-suite.txt` | 317 passed, two regressions found; both fixed below |
| `recipient-auth-fix.txt` | 69 passed, including all original `test_review_r2.py` cases |
| `final-focused.txt` | **75 passed**, including final new cases, legacy regressions and static MCP parity |
| Shared contract check | All three copies byte-identical |
| Preview preflight fixtures | 49 passed; includes all S-A env/secret/bind, origin, Mailpit and key-separation refusals |

The two broader-suite regressions were (1) exposing legacy empty/evidence folders
and (2) changing invalid legacy credentials from 401 to 403 after adding Board
authentication first. The fixes retain legacy folder visibility and the original
legacy authentication challenge. Existing tests were not weakened, skipped or
deleted. Existing test-source diff is empty; only the vendored contract changed.

The requested `deploy/send-dev/run-backend-tests.sh` runner requires the local
`amforge-send-dev-backend:devtest` image, which is absent (`test-images.txt`). I did
not let that script create its unrelated named Redis/core containers. I used the
S1a interpreter/settings wrapper for the focused and Dealroom suites. PostgreSQL
acceptance used a new disposable `postgres:16` container, a random loopback port,
tmpfs data, and a unique `board-room-s2-pg-test-*` name. Its exact container was
removed by a trap after every run. Existing containers and volumes were untouched.

Reproduce locally:

```sh
cd backend
sh ../docs/implementation/board-room-s1a/run-tests.sh tests/dealroom/test_room_commands_s2.py tests/dealroom/test_review_r2.py -q
```

From the repository root, `bash docs/implementation/board-room-s2/run-isolated-postgres.sh`
repeats the PostgreSQL checks. Alternatively use `run-postgres-tests.sh` with an
isolated `S2_POSTGRES_TEST_URL`, `S2_PYTHON`, and the normal test-only Django secrets.
`check-base.py` replays the new cases in a temporary archive of `bed45588` without
changing the worktree. All Google/storage integrations are faked in these tests.

## Migration and rollout

`dealroom.0006_roomcommandreceipt` adds one BoardRoom column and the receipt table
with unique board/key and import/operation/item constraints. It is reversible;
reverse and forward were exercised on the disposable PostgreSQL test database.
Existing adopted rooms remain ready with nullable draft IDs. No schema or data in
any running stack was migrated.

`BOARD_ROOM_WRITES_ENABLED` defaults to false. The preview env **template**, not its
runtime env, now includes this switch. Disable it to stop new commands and all
continuations while retaining reads, receipts and closed building rooms.

Manager preview steps:

1. Back up the isolated preview database/storage and Board private state. Build a
   Send image from this complete checkout. The old four-file S1a r2 delta Dockerfile
   does not include S2 modules, migration or settings and must not be reused as-is.
2. Update only the preview image pins in Compose, preflight allowlist and fixtures
   together. Use the existing isolation preflight and deployment wrapper; preserve
   the S-A URL/path/Mailpit/global-key checks. No live/proto target is authorized.
3. Apply `dealroom.0006_roomcommandreceipt` in the isolated preview. Enable
   `BOARD_ROOM_WRITES_ENABLED=true` there, and give its fictional binding
   `room_capabilities=["read","write"]` and role `writer` or `manager`.
4. Start the reviewed Board checkout with its private S5 state directory and the S2
   switches documented in the Board RESULT. The manager owns restarting previews;
   this session did not touch ports 8814, 8817 or 8818.
5. With a configured fictional Drive fixture, review a nested paginated tree with
   an empty folder and Restricted subtree; create an NDA-off private room. Verify
   hashes, DOCX rendering, tree/order and absence of grants/mail. Exercise Add from
   Drive, response loss, restart/Resume, and binding revocation. NDA-on stays blocked.

Operational rollback is to disable both sides' write switches while keeping S2
visibility guards and receipt schema. Do not reverse the receipt migration after
commands exist: deleting replay history is not a safe operational rollback.

## Limits and residual acceptance

The manager still needs the real isolated-preview Drive/Office-render journey;
this session intentionally performed no deployment. The Board screenshots are
from an offline browser fixture, not a deployed integration claim. Staging reap
requires an explicitly selected core storage root and operator scheduling.
NDA field publication, invitations/mail, lifecycle and duplicate/copy operations
remain outside S2. No project memory was saved.

## r2

Gate 3 r1 recovery and approval findings are addressed as file edits; the manager
owns staging and commits. Work is limited to the supplied Dealroom and Board
worktrees and the canonical contract under `fd-board-dealroom/docs/edd/contracts/`.
No preview or existing stack was changed.

| Finding | Fix | Regression evidence |
| --- | --- | --- |
| B1 | Human writer/manager `POST rooms/{id}/imports/{import_id}/abandon/` binds the actor, approval, import, room, expected revision and idempotency key under the room lock. Deletes that batch's unpublished items/folders/order rows, releases staging, advances revision and stores a receipt. Building rooms are deleted; their receipts survive. Old create keys remain tombstoned, while a fresh review/key can create the same draft. | Both render-failure → abandon → fresh review variants; existing published content survives, staff editing resumes, old create returns 410, abandon replay survives deletion. |
| B1 response loss | An abandon against a completed batch records a harmless receipt reporting `abandoned:false`; Board reconciles completion without deleting published content. | Lost-completion regression; Board additionally tests lost-abandon reply replay. |
| S1 | Reject root position overlaps at approval with “Room changed; review again”. Only named receipt/BoardRoom uniqueness races receive retry wording. | Position 0 on a populated room; unrelated IntegrityError is a definite 409. |
| S2 | Board classifies definite 400/404/409/422 as `needs_attention` with review wording and Cancel; transport uncertainty remains resumable. | Board start/continuation status matrix. |
| S3 | Validate file extensions against the upload allowlist before approving. | Four unsupported filename forms return 400 without receipts. |
| S4 | Adopted rooms require download-off and matching current expiry; create-backed rooms require their approved access. | Actual `adopt_board_room` command, followed by a rejected download-widening batch. |
| S5 | Require a string `board_draft_id`; receipt draft IDs are strings. | Numeric and boolean IDs rejected; Board checks draft ID type too. |
| S6/S7 | Board retries its lease and recovers abandoned running states; traversal deduplicates reached roots with “Already included”. | Board lease takeover, failed error-save and overlapping selection tests. |
| N1 | Hash uploaded chunks incrementally. | Chunk-by-chunk hashing assertion. |
| N2 | Reaper uses `is_storage_key_referenced`. | Both Document and DocumentPage references survive reaping. |
| N3 | Validate mutation-body shape and room identifiers before the legacy lock query. | List body, invalid room ID and list-valued dataroom return 400. |
| N4 | Amend unshipped migration 0006 and model: `room_import_step` applies only when `client_item_id != ''`. | Empty item receipts coexist, duplicate actual steps still fail; isolated PostgreSQL forward/reverse coverage. |
| N5 | Execute rechecks the write switch and human transport, independently of hooks. | Direct execute calls reject nonhuman and disabled writes. |
| N7/N8/N9/N10/N13 | Board bounds pagination, uses manifest hashes for readiness, wraps Drive availability errors, identifies the prepared draft explicitly, and scales multipart timeout with bytes. | Board focused regressions. |

Abandon is included in the operation inventory, typed OpenAPI request schema and
generated MCP tools (121 tools). The contract command version is 3; its three
copies pass `deploy/do1/check-board-rooms-contract.sh` byte-for-byte. The two
existing exhaustive operation-set assertions were extended with `abandon`; no
test was weakened, skipped or deleted.

Failing-first evidence is in `r2-red.txt`: initial run **18 failed, 3 passed**.
The strengthened malformed-ID test and lost-completion case then ran red
(**2 failed, 2 passed** in that focused follow-up) before their fixes.

| Validation | Result |
| --- | --- |
| S1a wrapper, S2 + all prior Board room reads + legacy review regressions (`r2-focused.txt`) | **261 passed** |
| Registry/MCP foundation suite (`r2-registry.txt`) | **80 passed** |
| Disposable PostgreSQL via `run-isolated-postgres.sh` (`r2-postgres.txt`) | **72 passed** |
| Final adopted-room command and typed MCP assertions (`r2-final-assertions.txt`) | **2 passed** |
| Final PostgreSQL recovery/adoption/schema checks (`r2-final-recovery.txt`) | **4 passed**; both recovery variants re-upload and publish the actual DOCX after cancellation |
| Shared contract and whitespace | Passed |

PostgreSQL used only the script's disposable test container, removed on exit.
Migration 0006 was explicitly authorized to be amended while unshipped. For an
environment that already applied its old form, the manager must add/apply a new
constraint migration before rollout; do not reverse a database containing receipts.
No migration was applied to a running product database.

Board's full-suite and browser counts are recorded in its matching r2 RESULT.
Optional N6, N11 and N12 remain deferred. No project memory was changed.

Board validation finished with **205 focused tests passed**. Its single full run
was **669 passed, 8 failed, 58 existing skips, 622 subtests passed**. The three
Cloud failures match the brief. The five additional Sign UI subcases reproduce
on the exact unchanged starting head `a255e69` (**5 failed, 1 passed, 7 subtests
passed**), so no new failures were introduced. Evidence and offline browser
screenshots are in the Board r2 RESULT; unrelated Sign code was not changed.


## r3

Gate 3 r2 S-a (both parts), S-b, N-a and N-b are addressed. File edits only,
starting from Dealroom `2bbdf564` and Board `4bb4d68`; the manager owns staging
and commits. Existing previews and stacks were untouched. Optional N-c remains
deferred: Cancel still waits for the current runner step rather than returning
an asynchronous 202.

- **S-b:** Abandon uses this batch's upload receipt `document_id` values to
  hard-delete the organization-scoped Documents and cascade their versions/pages.
  These vault uploads carry no personal quota charge. Storage deletion remains
  with `reap_board_staging` after the cancellation transaction commits. Both a
  building room and an import into an existing room are tested: the staff document
  endpoint changes from 200 to 404, all document references disappear, the old
  published document survives, and the reaper removes the staged key. Receipt
  replay still succeeds after deletion.
- **N-a:** Added an actual adopted-room positive control with the matching
  `download_ceiling: "none"`; it returns 201 beside the existing widening rejection.
- **S-a / N-b (Board):** Persist cancellation intent independently of the abandon
  payload. A definite abandon 4xx discards the stale payload, allowing the next
  Cancel to read the current revision with the same key. Transport uncertainty
  retains the exact body. Resume and run refuse after cancellation begins, also
  after restart; the UI hides Resume and refreshes after failed Cancel. A retried
  uncertain start stays paused; a definite rejection cancels locally on that click.

The command contract is version 4 and documents cancellation intent, retry,
start recovery and document cleanup. Canonical and both vendored copies have
SHA-256 `795fc4da106b67e04fddb830ec9d34a64611c7b7e2fe94dd26d5632ba05acf8d`.
No existing test was changed or weakened; new cases are in
`backend/tests/dealroom/test_room_commands_s2_r3.py` and Board's r3 module/browser
harness. There are no schema, migration, environment or deployment changes.

| Validation | Result / evidence |
| --- | --- |
| Failing-first, before Dealroom implementation | **2 failed, 1 passed**, `r3-red.txt`; both failures show the abandoned document still returning 200 |
| New Dealroom regressions | **3 passed**, `r3-green.txt` |
| S1a wrapper: S2/r2/r3, all Board room read suites and legacy review r2 | **264 passed**, `r3-focused.txt` |
| Disposable PostgreSQL: original S2/migration/concurrency suite plus r2/r3 | **75 passed**, `r3-postgres.txt` |
| Foundation/registry | **80 passed**, `r3-registry.txt` |
| Board focused room suites | **220 passed**, Board `r3-focused.txt` |
| Board full suite (one run) | **684 passed, 8 failed, 58 skipped, 622 subtests passed**, Board `r3-full-suite.txt` |
| Offline browser | Passed; Board `r3-ui-walk.txt`, `r3-cancel-mobile.png`, `r3-cancel-desktop.png` |

Commands from Dealroom `backend/`:

```sh
sh ../docs/implementation/board-room-s1a/run-tests.sh \
  tests/dealroom/test_room_commands_s2.py tests/dealroom/test_room_commands_s2_r2.py \
  tests/dealroom/test_room_commands_s2_r3.py tests/dealroom/test_board_rooms.py \
  tests/dealroom/test_board_rooms_r2.py tests/dealroom/test_board_rooms_r3.py \
  tests/dealroom/test_review_r2.py -q
sh ../docs/implementation/board-room-s1a/run-tests.sh tests/dealroom/test_foundation.py -q
```

From Dealroom root:

```sh
bash docs/implementation/board-room-s2/run-isolated-postgres.sh \
  tests/dealroom/test_room_commands_s2_r2.py tests/dealroom/test_room_commands_s2_r3.py
```

The PostgreSQL script created only its disposable test container and removed it
on exit. The original migration rollout caveat remains unchanged: the manager
must determine whether 0006's earlier form has been applied before rollout.

The Board full run has the three expected Cloud failures plus the same five Sign
UI subcase failures recorded in r2. Despite the updated runner's environment,
these still fail: the Node fake-DOM harness does not use Playwright and expects
an old title/button. `r3-check-baseline.py` reproduced all five on the exact
unchanged Board starting commit `4bb4d68` with the updated runner (**5 failed,
1 passed, 7 subtests passed**). Board `r3-baseline-sign.txt` includes direct
per-mode diagnostics with NODE_PATH/PLAYWRIGHT_BROWSERS_PATH set explicitly.
No Sign code or tests were changed and the full suite was not repeated. Thus the
measured baseline still differs from the brief's three-failure expectation, with
no new r3 failures. See the Board r3 RESULT for the exact failure names.
