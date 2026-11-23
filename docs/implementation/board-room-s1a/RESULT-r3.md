# S1a r3 result — Dealroom

Complete. All requested Gate 3 r2 findings (1, 2, 5, 6, 8a–d, 9) are addressed. Changes are uncommitted for the manager; no staging or commit commands were run. No migrations or project-memory updates were authored.

## Scope and baselines

- Dealroom baseline: `c38ccbff06b59ae758df2d3691477be5f87a6bf2`.
- Board baseline: `f1f921818121d72e3cf605643f012148fc46198c`.
- Preview audit baseline: `46bab191`. Actual starting HEAD was `ec5a39e723f66659680d3f8b0cfcd6691095dcf7`; the intervening changes only add the r3 brief and Gate 3 r2 review/brief. Existing untracked manager logs/markers were preserved.
- Findings 3, 4, 8e and 10 remain scheduled for S1b. Duplicate hover-card rows remain for S1b.

## Changes and regression coverage

| Finding | Implementation and evidence |
| --- | --- |
| 1 | Vendored `board-rooms-v1.json` in both golden directories; both tests resolve their own repository copy. `deploy/do1/check-board-rooms-contract.sh DEALROOM_REPO BOARD_REPO` byte-compares all three copies and fails on differences/missing files. Tested with paths containing spaces, byte-different equivalent JSON, missing files and wrong argument count. `test_contract_is_vendored` covers each product. Dealroom's generated page comparison checks status, content type, PNG signature, successful decoding and dimensions; all other JSON retains exact equality. `test_page_golden_accepts_different_png_encoding` proves another valid compression stream passes. Board retains exact equality between its static golden examples and vendored contract. |
| 2 | Unknown activity/session actors are null. Operator and agent map to “Operator” and “Agent key”. Summary, activity text, accessible label and hover title omit a null actor and capitalise the first letter. Added a deterministic null-actor adoption to real API fixture generation; regenerated and copied all seven examples and updated contract examples/documentation. Tests cover unknown/stale staff/member actors, operator, agent, blank stored visits, summary/detail/list and Board rendering. |
| 5 | Removed the document Views column and “See who viewed it” action; document tables now have four columns. Scoped desktop grid keeps the remaining columns aligned; mobile behavior remains covered by the browser walk. |
| 6 | Replaced the absent `WRONG_IP` decoy assertion with `assert.doesNotMatch(visit,/pat@harborlight\.test/)`; retained the exact expected IP and ID/cursor assertions. |
| 8a | Document activity checks protection by document ID even when the room item was removed or belongs to another room. Six tests cover removed/other-room snapshot, audit and signed artifacts. Existing protection of Executed-folder items remains. |
| 8b | Excluded item visits, PageViews and activity facts are omitted from page/download aggregation. A session-wide download marker cannot establish a visible download when item evidence was excluded. Eight regression cases cover pages/downloaded across snapshots, signed/audit artifacts and Executed folders, followed by visible-item positive assertions. |
| 8c | Staff preview uses `Image.open(..., formats=['PNG', 'JPEG', 'GIF', 'WEBP'])`. BMP/TIFF are rejected without an issuance audit; PNG still succeeds. |
| 8d | Adoption requires an enabled binding in the room's organization. Disabled/cross-organization cases fail without `--force`; the explicit force path remains tested. |
| 9 | Removed Event ID and obsolete member/facts rows from hover cards. Tests assert each removal. Existing visit telemetry/null presentation and duplicate rows remain. |

## Failing-first evidence

- Dealroom `r3-red.txt`: **26 failed**, all newly added cases, against unchanged r2 implementation and original r2 golden test. Includes a specific `AssertionError: page` for re-encoded PNG bytes.
- Board `r3-red.txt`: **5 failed**, all newly added cases, against unchanged r2 UI and contract path.
- Preview `deploy/do1/tests/r3-contract-red.txt`: five failing subcases before the comparison script existed; green after implementation.
- `r3-golden-red.txt` records the adoption example drifting from old goldens. `r3-golden-generate.txt` records generation followed by the expected missing-vendored-contract bootstrap failure; the completed focused suite verifies the generated files and all vendored examples.
- `r3-live-walk-red.txt` records the old preview missing the null-actor adoption scenario. The final walk uses real preview APIs. An intermediate selector ambiguity between unknown and Operator adoptions is retained in `r3-live-walk-selector.txt`; anchoring the selector resolved the harness issue.

## Validation

| Check | Result |
| --- | --- |
| Dealroom focused (`test_board_rooms.py`, `test_board_rooms_r2.py`, `test_board_rooms_r3.py`) | **165 passed** (`r3-focused.txt`) |
| Dealroom `tests/dealroom/` | **277 passed** (`r3-dealroom.txt`) |
| Board focused room suites | **48 passed** (`r3-targeted.txt`) |
| Board full r2 baseline | **505 passed, 8 failed, 60 skipped, 622 subtests passed** (`r3-r2-full.txt`) |
| Board full r3 | **510 passed, 8 failed, 60 skipped, 622 subtests passed** (`r3-full.txt`) |
| New Board failures vs r2 | **0** (`r3-suite-comparison.json`) |
| Preview checks, including contract comparison test | **49 passed** (`deploy/do1/tests/r3-preflight.txt`) |
| Three contract copies and seven golden copies | Byte-identical |
| Syntax / whitespace | Board Node, preview shell syntax and all three `git diff --check` pass |
| Real browser at 1440px and 390px | Pass, no page errors (`r3-live-walk.txt`, `r3-live-walk.json`) |

Dealroom commands run from `backend/` using `sh ../docs/implementation/board-room-s1a/run-tests.sh ... -q`. Only `board_rooms.py`, `staff_preview.py` and `adopt_board_room.py` production code changed, so the full backend suite was not needed.

Board uses the supplied `bash /root/work/sign-product/run-board-tests.sh /root/worktrees/board-room` via the existing `run-tests-r2.sh` wrapper. That wrapper only redirects the runner's temporary home creation from the read-only `/root/.hermes/cache/scratch` to `/tmp`; test selection, Python, flags and plugin paths are unchanged. The eight failures match the fresh r2 run exactly: three CloudEdition cases plus Sign UI modes `sign_history`, `sign_send_states`, `sign_send_upload`, `sign_send_suggested`, `sign_send_suggestion_error`.

## Preview acceptance

Only `fleet-dealroom-preview-boardroom` was built/stopped/restarted. Image: `sha256:1bf4d0a7caf738576c83ce13da38d624bb2ce79ec0ed2225a0c98dc624c78e43`. The build used the existing `Dockerfile.send-r2` recipe and this Dealroom backend context; `BUILDX_CONFIG=/tmp/boardroom-r3-buildx` avoided a read-only Docker cache path. Compose, preflight image pins and both fixture models were updated together. The digest-checked `up-preview-boardroom.sh` performed the restart. Its first attempt refused a still-occupied 9080 after stop; once the port cleared, the unchanged wrapper passed. Logs are under Preview `deploy/do1/tests/r3-*.txt`.

Existing preview volumes and fictional rooms were retained. `seed-preview-boardroom-r3.py` added one explicitly fictional unknown-actor adoption fixture to Project Harbor; the existing Operator adoption remains. `r3-runtime-hashes.json` proves all three changed backend files match the running container. No proto/live service was changed, and port 8817 was not restarted or reconfigured.

The temporary Board process ran on **127.0.0.1:8818**, using the preview key without printing it, and was stopped after acceptance. The walk shows “Added the room to the board” and “Operator added the room to the board”, no “Not recorded” activity actor, no Views column/action, and no Event ID. Two rooms, three Harbor documents, folder counts 2/1, PDF and DOCX PNG 200, and foreign-version 404 all pass. Priya's Seattle/Safari/Desktop/14 min/download details and Pat's absent telemetry remain covered.

Board evidence: `live-walk-r3.cjs`, `r3-list-desktop.png`, `r3-room-desktop.png`, `r3-pat-desktop.png`, `r3-room-mobile.png`, and `r3-stamped-preview.png` in `docs/implementation/board-room-s1a/`.

## Test-line audit against r2

The check is `git diff --unified=0 <r2-head> -- '*test*'`, including fixtures. It is **not** a diff against the pre-S1a base. No tests were deleted or skipped. Dealroom has **8 removed lines** (4 fixture lines, 4 source lines); Board has **7** (4 fixture lines, 3 source lines); Preview has **8**, all sender-image fixture pins. Every exact removed line, original line number and justification is recorded in each repository's `r3-test-weakening.json`; full diffs are alongside them. Preview audit artifacts are in `deploy/do1/tests/`.

| File / r2 line | Exact removed line | Justification |
| --- | --- | --- |
| `backend/tests/dealroom/golden/detail.json:88` | `"at": "2026-11-20T12:00:00Z",` | Regenerated from real Dealroom views after adding a later null-actor adoption fixture; last_activity now records that adoption with a capitalised phrase. |
| `backend/tests/dealroom/golden/detail.json:89` | `"phrase": "pat@harborlight.test visited the room"` | Regenerated from real Dealroom views after adding a later null-actor adoption fixture; last_activity now records that adoption with a capitalised phrase. |
| `backend/tests/dealroom/golden/list.json:12` | `"at": "2026-11-20T12:00:00Z",` | Regenerated from real Dealroom views after adding a later null-actor adoption fixture; last_activity now records that adoption with a capitalised phrase. |
| `backend/tests/dealroom/golden/list.json:13` | `"phrase": "pat@harborlight.test visited the room"` | Regenerated from real Dealroom views after adding a later null-actor adoption fixture; last_activity now records that adoption with a capitalised phrase. |
| `backend/tests/dealroom/test_board_rooms_r2.py:5` | `from datetime import datetime, timezone as dt_timezone` | Extend the import with timedelta to give the adoption fixture a deterministic later timestamp. |
| `backend/tests/dealroom/test_board_rooms_r2.py:26` | `CONTRACT = Path(__file__).resolve().parents[4] / 'fd-board-dealroom/docs/edd/contracts/board-rooms-v1.json'` | Resolve the checked-in contract inside this repository instead of assuming a sibling worktree. |
| `backend/tests/dealroom/test_board_rooms_r2.py:246` | `assert json.loads((GOLDEN / (name+'.json')).read_text()) == value, name` | Keep exact JSON equality for every non-page example; replace page byte equality with status, content type, PNG signature, successful decode and dimensions checks for portability. |
| `backend/tests/dealroom/test_board_rooms_r2.py:248` | `assert contract['examples'] == examples` | Retain exact example-key coverage and per-example equality, with the same portable PNG comparison for page. |


## Handoff

All changes remain in the working trees for manager review and commit. The success marker is `/root/worktrees/fd-board-dealroom/docs/edd/briefs/board-room-s1a-fix-r3.done`, containing `coder rc=0`.
