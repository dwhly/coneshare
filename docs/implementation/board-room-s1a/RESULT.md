# S1a — board room adoption and scoped reads

Implemented S1a only on `agent/board-room-s1a`, based on `3b15354a`. Changes are uncommitted. No live stacks were touched. No new failing tests were introduced in the compared suites.

## Contract decisions

- Routes and the five operation IDs match the build brief. `{pk}` is the existing **Dataroom ID**, not the BoardRoom row ID. `{item_id}` is the **DataroomDocument ID**. `version_id` is required on both page actions and must belong to the item's document.
- List and visits use `{items: [...], next_cursor: string|null}` with 50 rows per page. Cursors are scoped IDs: room ID for list, stored ViewSession ID for visits. Invalid or out-of-scope cursors return 404. Ordering is descending stored creation/view time, then ID. There are no storage URLs or page proxy paths in the metadata response; callers construct the exact paths from the brief.
- Room summaries: `id`, `name`, `board_id`, `build_state`, `revision`, `lifecycle`, `archived`, `ever_invited_at`. Detail adds `folders`, `items`, `people`, `grants`, `nda`, `activity`. Folder entries use `folder_id`, `parent_id`, `name`, `position`; items use `item_id`, `document_id`, `version_id`, `folder_id`, `name`, `position`, `type`, `lifecycle`. Missing stored order is null. S1a has no command receipts/status beyond build state/revision.
- Visit cards: `id`, `time`, `email`, `ip`, `city`, `country`, `browser`, `device`, `duration` (seconds), `pages` (sorted page numbers), `downloaded`, `activity`. Unrecorded facts are null. In particular, legacy default-zero duration without page evidence is null, and absence of a recorded download is null. Browser/device are parsed conservatively from stored UA. Coordinates, raw UA, page URLs, tokens and link capabilities are omitted.
- Activity projections contain only `id`, `event_type`, `time`, `actor_kind`, `actor_id`, `target_id`; arbitrary event JSON is never emitted. Visit facts join only on stored `view_session_id` or `visit_id` plus room and organization.
- Page metadata is exactly `{status: ready|processing|failed, page_count: integer|null}`. Not-ready bytes return 409 with that object; unavailable rendering returns a generic 503. Successful images are PNG and carry `X-Dealroom-Copy-ID: preview-<uuid>`, private/no-store, nosniff and no-referrer. Each page issuance gets its own Copy ID and audit fact, stamped with the bound login; no recipient session or recipient IssuedCopy is fabricated.
- Wrong credentials, binding/capability or protected evidence return 403. Rooms/items/versions outside scope return 404. List hides assignments from other boards/organizations. Staff can inspect archived room metadata; page membership still excludes removed documents and the Executed subtree.
- Adoption is idempotent for the same board and refuses reassignment or undo from another board. It seeds `ever_invited_at` with the earliest grant (including revoked), historical room activity, or stored session. There is no separate invitation model in the base; invitation facts live in Activity. Prior adoption/undo bookkeeping is excluded from evidence. Undo deletes only the BoardRoom assignment and appends an audit fact.
- The default build state for future-created BoardRoom rows is `building`; operator-adopted rows are explicitly `ready`. Both migrations are included. Existing bindings get an empty capability list and no reads until explicitly enabled.

## Failing-first evidence

`failing-first.txt`: all **106 cases failed** against detached base `3b15354a`, before any implementation was added. Each case is listed in the log. The base received only the new test file for this run; that file was then removed before regression suites. A later validation edge-case assertion (empty JSON object/string) also failed before its fix, both on the base and on the first implementation; see `empty-capabilities-base-red.txt` and `empty-capabilities-red.txt`. The final focused/full-suite runs include that assertion.

## What changed

- Added BoardRoom and default-empty validated room capabilities, with schema migrations and database uniqueness coverage.
- Added the audited operator adoption/undo command, the scope helper, five explicit read actions, and safe room/session projections.
- Added a bounded staff image fetch/stamping service. The shared render semaphore covers key resolution, fetching, stamping and issuance; `finally` releases it on every outcome. PDF and converted DOCX use the existing internal renderer key path. Missing previews never fall back to source downloads.
- Extracted the existing protected-document predicate without changing the DocumentViewSet decision. Board page actions additionally exclude every ExecutedArtifact and the Executed folder subtree.
- Generated the operation registry and typed MCP inventory using the existing commands. MCP regeneration also reconciles existing schema drift (the two existing Sign retry/revoke tools and existing envelope input fields); it changes no Sign routes or Documenso implementation.
- No recipient route, room template, recipient telemetry capture, global authentication default, or legacy analytics/preview/download classification changed. No live stack or deployment was touched. Changes remain uncommitted.

## Test counts

| Run | Current worktree | Detached base `3b15354a` |
| --- | --- | --- |
| S1a focused | **106 passed** | **106 failed** before implementation |
| `tests/dealroom dealroom_sign/tests` | **58,428 passed** | **58,321 passed, 1 failed** |
| Full configured suite (`tests/` + `bdd/`, no filters) | **1,597 passed, 2 failed** | **1,490 passed, 3 failed** |

The package baseline failure is `tests/dealroom/test_foundation.py::test_schema_mcp_static_parity`: the old MCP inventory lacks `dealroom_sign_SignatureEmailRetryView_endpoint_post` and `dealroom_sign_SignatureSignerRevokeView_endpoint_post`. Regeneration resolves it. The final focused rerun also covers the empty JSON validation correction made while the larger package run was in progress; the subsequent full run includes the final source.

The two retained full-suite failures occur on both checkouts under the same isolated settings:

1. `tests/core/test_reencrypt_data.py::test_reencrypt_data_models_and_fields_configured` — the existing re-encryption command omits the encrypted models `SignCredential`, `Workflow`, and `SignerAccess` from its configuration.
2. `tests/documents/test_tasks.py::test_prepare_pages_data_watermark_suppression` — an unmocked legacy preview request attempts the fixture fileserver at `127.0.0.1:18080`, where no fileserver is running. This is an environment-dependent baseline failure; no live fileserver was used.

`comparison.json` and `pre-existing-failures.txt` contain the exact node-ID comparison: **no new failures**, and the inventory parity failure is resolved in both compared suites. No existing test was weakened, skipped or deleted. The full configured suite ran once per checkout; the separate Sign package is covered in the larger package run above.

Retained logs: `failing-first.txt`, `empty-capabilities-base-red.txt`, `empty-capabilities-red.txt`, `targeted.txt`, `packages.txt`, `base-packages.txt`, `full.txt`, and `base-full.txt`. Package runtimes were 3,035.11 seconds current / 3,065.52 seconds base; full-suite runtimes were 1,323.75 seconds current / 1,324.91 seconds base. The final targeted run passed in 18.03 seconds. Source hashes and the exact base commit are in `source-evidence.txt`.

Operator command interface (implemented and exercised only against test databases here):

```sh
python manage.py adopt_board_room --board BOARD_ID --room ROOM_ID
python manage.py adopt_board_room --board BOARD_ID --room ROOM_ID --undo
```

## Validation environment

Run from `backend/` using `sh ../docs/implementation/board-room-s1a/run-tests.sh ...`. The wrapper executes exactly `/root/work/sign-product/send-venv/bin/python -m pytest`, with fixture credentials and the checked-in test support settings. These extend the existing `dealroom_sign.test_settings` with an in-memory cache and Celery broker/result backend; database migrations run against in-memory SQLite. No service from a live stack is used. The detached base used the identical wrapper/settings with its own source directory first on PYTHONPATH. It was created with `git worktree add --detach .scratch/board-room-base 3b15354a` and removed after validation; the evidence logs remain in this folder.

The initial startup attempts without isolated cache settings were discarded; they are not counted as behavioral test runs. The retained failing-first log is the complete 106-failure run using the final isolated setup.

`manage.py dealroom_registry --write`, `manage.py spectacular --file ../deploy/chief-send-v1/out/openapi.yaml`, and `mcp-server/scripts/generate_registry_tools.py` regenerated the inventories. Schema generation has no errors. Registry verification reports **316 operations, 107 staff operations**. `manage.py makemigrations --check --dry-run` reports **No changes detected**. No live migration was applied.

## Residual risks

- Private fileserver responses are mocked in the automated S1a preview tests; they exercise real image stamping and renderer key selection, but do not constitute a deployed PDF/LibreOffice/fileserver integration smoke test.
- Migration/constraint tests use SQLite; PostgreSQL deployment migration and live adoption remain operator actions.
- Existing telemetry gaps are intentional: old zero-default durations and absent downloads stay null, unknown UA formats remain null, and activity without an exact stored session/visit ID is not attributed. S1b capture remains deferred.
- Issuance is a staff Activity fact with a distinct preview Copy ID per returned page. It is intentionally separate from recipient IssuedCopy/ViewSession records.
- No preview-stack deployment or board-side proxy/UI validation is included in this Coneshare-only build.
