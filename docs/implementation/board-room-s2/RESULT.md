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
