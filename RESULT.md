# Dealroom room prototype — direction d + Google Drive

Built on `agent/room-proto` from `0cdc9567`. Uncommitted. No migration files or Sign source files changed. This is a product prototype for Dan’s taste pass, not a deployment.

## What is real

- Existing React app and Fleet/Coneshare components, tokens, buttons, cards, dialogs, file icons and progress indicator. The redundant Rooms/Activity/Approvals subnav is hidden inside a room.
- Series A outline: eight numbered folders and twelve usual-document slots. The Harbor Light fixture yields **10 matched, 2 unsure, 2 missing** (team bios and IP assignments). Both unsure files are still imported. Empty slots/folders are hidden from visitors.
- Whole-tree import through `list_files(path)` + `download_file(id)`, including nested folders, duplicate folder names, multiple roots and repeat-import deduplication. Without a template, Drive structure is kept. With a template, confirmed files move into numbered template folders; other files keep their source folders. Review uses signed, room-bound tickets and imports only after confirmation. Slot dropdowns and drag/drop allow corrections.
- Matching uses names, folder paths and file types. No AI service is called. Ambiguous files and duplicate slot candidates stay unsure.
- Real room documents, vault storage, document versions, source links and `modifiedTime`. Docs → PDF, Sheets → xlsx, Slides → pptx use the existing Google export mapping. Original exported Office files are retained; the existing Office-to-PDF job creates their reader previews.
- Check Drive for updates re-reads the snapshot tree. Checking changes neither bytes nor primary versions. **Publish new version** promotes only the selected change and checks for stale reviews/concurrent publication.
- Welcome note, ordered “Start here”, persisted slot assignments and “Not needed”. Moving an existing file into a slot updates its real room folder.
- Named invitations grouped by email domain, with a note per firm. Each invitation gets a reusable signed personal link, expires after 30 days, and respects grant revocation and room closure. It requires an explicit Continue click, no account or email code. Existing email-code entry remains available for ordinary room links. Sending invitations uses the existing mail adapter; no invitation was actually sent during development.
- NDA setup calls the existing Sign NDA-policy API. New prototype rooms require the NDA setup before visitor content becomes available. The visitor uses the existing Sign workflow and handoff; signed-copy delivery remains Sign’s responsibility. Existing `/signing/room/...` and `/signing/nda/...` return links redirect to the same React visitor room through application URL aliases, without edits in `backend/dealroom_sign/`.
- Full-width reader uses the existing protected server-rendered watermarked page endpoint. Ask and Get a copy create real, access-checked requests. Copy requests do **not** enable downloads or release files. Answers are private to the asking firm by default; “also publish to all firms” makes a room FAQ. Public-mailbox addresses are separate subjects for answer privacy.
- One “Needs you” list, plus a link to existing room activity. Close by date / close now / reopen use the current room policy.
- Visitor return view lists tappable published additions/updates, answers and a resume-page action.

## What is simulated or deliberately limited

- **DriveSnapshotProvider is the source adapter.** No Google OAuth client, consent flow or live Google access is configured. It reads `<DEALROOM_DRIVE_SNAPSHOT_DIR>/<folderId>/manifest.json` and exported local files. Empty setting disables it. Checking Drive sees changes only after the manager replaces the local snapshot. The importer itself accepts ordinary providers; GoogleDriveProvider now returns timestamps/source links and follows pagination.
- The checked-in Harbor Light files are fictional test exports, with a six-page pitch deck. The real fictional AmForge snapshot from the other host has not been supplied here.
- Import is synchronous and bounded to ten roots, 2,000 tree nodes, 30 nesting levels and existing 50 MiB/file upload limits. Large/background import jobs, deleted-file reconciliation, and newly added files during update checks are deferred. To add new files, repeat the import; existing source IDs are skipped.
- Prototype outline/preferences and requests/answers use existing Activity JSON records; version provenance uses DocumentVersion metadata. There is no new schema or migration. A production pass should give these workflows dedicated records and durable jobs.
- “Since your visit” and resume-page state are browser-local, keyed by room and visitor. Cross-device resume is deferred.
- The six default decisions are implemented. Optional First look, whole-domain admission, emailed-PDF entitlement, and a polished per-firm override editor are deferred. Existing grant/file-policy APIs still exist. No copy-approval/delivery composer or question-answer email notification was added; replies appear in the room.
- Signature placement in the prototype settings is explicitly a lower-left signature on the last page. Use a demo NDA with that area clear. Sign’s consent/signing implementation is unchanged.
- Full outline reordering, answer attachments, firm reading-summary metrics, archive export and a 30-day reopen limit remain deferred. Start-here ordering, slot reassignment and normal room closure work.
- Browser screenshots/smoke tests use the built product with intercepted fictional API responses and a fixture page image. They verify UI behavior/layout, **not** live Sign/mail/LibreOffice integration. Backend tests exercise real DB records but substitute storage/task delivery where appropriate.

## Screens and paths

| Path | Screen / action |
| --- | --- |
| `/datarooms` → Create room | Name, default Series A checklist, or Start from Google Drive |
| `/datarooms/<room-id>` | Outline checklist, welcome note, Start here, room rules |
| `/datarooms/<room-id>?drive=1` | Drive links → keep folders / Series A → import review → confirm |
| Same room → Investors | Domain grouping, per-firm notes, send personal links |
| Same room → Needs you | Questions, copy requests, private reply / FAQ |
| Same room → Settings | Existing Sign NDA policy, closing date, close/reopen |
| Same room → Check Drive for updates | Changed files and per-file Publish new version |
| `/view/<slug>#personal=<signed-token>` | Personal invitation → existing NDA gate → room |
| `/view/<slug>` | Note, ordered picks, numbered folders, reader, Ask, copy request, return view |
| `/signing/room/<slug>`, `/signing/nda/<room-id>` | Compatibility redirects to `/view/<slug>` |

Screenshots in [`docs/room-proto/screenshots/`](docs/room-proto/screenshots/): [sender](docs/room-proto/screenshots/sender-outline.png), [import review](docs/room-proto/screenshots/import-review.png), [firm invitation](docs/room-proto/screenshots/invite-firm.png), [phone home](docs/room-proto/screenshots/visitor-home-phone.png), [phone reader](docs/room-proto/screenshots/visitor-reader-phone.png), [copy request](docs/room-proto/screenshots/copy-request-phone.png).

## Seed a demo room

Use an existing configured application database, staff account, Go file service and Celery worker. No migrations are needed for this change. Enable Office preview and keep LibreOffice/Poppler available in the normal worker image.

Set this for the backend process (use a mounted container path when running in Docker):

```bash
DEALROOM_DRIVE_SNAPSHOT_DIR=/root/worktrees/room-proto/backend/dealroom/tests/fixtures/drive
```

Then, in the backend environment with its normal database/core credentials:

```bash
cd /root/worktrees/room-proto/backend
python manage.py seed_room_onramp --owner <existing-staff-email>
```

The repeatable command creates **Harbor Light Analytics · Series A**, imports twelve files, pins model then deck, writes Dan’s note, configures the fictional NDA and prints the sender URL and Maya’s personal visitor URL. It sends no email and creates no staff credentials. `--keep-folders` skips template placement; use a fresh demo room/database when comparing both initial structures.

For the manager’s snapshot, point the setting to its parent directory and pass `--folder-id <Drive-folder-id>`. Or use the app directly: Create room → Start from Google Drive → paste `https://drive.google.com/drive/folders/<id>`.

Configure the room owner’s **existing Sign credentials** to complete the real NDA flow. The seed keeps the gate enforced. For an update demo, change a file/export and its `modifiedTime` in a copied snapshot, then Check Drive for updates → Publish new version. No visitor update occurs at check time.

## Verification

- Backend: **149 passed** across `dealroom/tests`, the full existing `tests/dealroom` suite, and `tests/cloudfiles/test_tasks.py` (94.45 seconds). Includes tree/import structure, template matching, all three Workspace export mappings, version publication, repeatable seeding, provider pagination/interface, access/revocation, NDA setup, private answers and snapshot path boundaries. Existing test-secret JWT-length warnings remain.
- Frontend: **11 passed**, four Dealroom test files, including review confirmation, drag correction, protected reader URLs, page navigation, draft retention, copy-request semantics, return/resume and personal-link identity handling.
- `cd frontend && npx vite build`: **passed**. Vite’s CJS entry wrapper loads the unchanged shared config without writing temporary ESM files through the read-only dependency symlink. Existing bundle-size/Browserslist warnings remain.
- Chromium at 1440×1000 and 390×844: import confirmation, grouping, visitor home/reader, draft retention and copy requests passed; no page errors or horizontal phone overflow.
- Generated operation registry and MCP catalog updated; catalog generation also filled two already-served Sign operation entries that were absent from the old catalog. No Sign source changed.
- `git diff --check`: passed. No staging or commits. Dependency symlink removed at completion. Project memory remains unchanged unless separately approved.

Backend command (the supplied runner hardcodes an unwritable host scratch directory, so only `mktemp` is redirected into the worktree):

```bash
mkdir -p /root/worktrees/room-proto/.testtmp
function mktemp() { command mktemp -d /root/worktrees/room-proto/.testtmp/sendlocal.XXXX; }
export -f mktemp
/root/work/sign-product/run-send-local.sh /root/worktrees/room-proto \
  dealroom/tests tests/dealroom tests/cloudfiles/test_tasks.py
```

Run that block in Bash. Frontend tests used `npx vitest run --cache=false` with `src/tests/pages/{DealroomPages,DealroomRoomDetail,DealroomRecipient,RoomOnramp}.test.jsx`.

## STOP / external dependencies

No implementation or test blocker remains. Live Google OAuth is intentionally out of scope. A live visitor demonstration still needs the manager’s mounted snapshot (or the supplied fixture), working core/preview workers, and the owner’s existing Sign credentials. Live signing, email delivery and the external host snapshot were not exercised. Nothing has been deployed.
