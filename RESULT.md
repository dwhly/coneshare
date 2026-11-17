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

## Round 2 — 17 November 2026

Polish against deployed HEAD `bd78b9d6` on `agent/room-proto`. Changes remain uncommitted. Existing cards, subnavigation, pills, dropdowns, buttons and file icons are reused; no new visual system, migrations, Sign changes or Vite/Vitest configuration changes.

| Item | Result |
| --- | --- |
| 1. Visitor entry | Tenant logo/name now come from the existing challenge/brand response on both the invitation and NDA gate. A known inviter reads “Dan Whaley invited you”; signed invitation metadata supports a different inviter from the owner. The action is **Review the NDA**, with plain next-step copy. **Kept the explicit invitation step** because it confirms which personal identity to use without silently replacing an existing visitor session or redeeming scanner GETs. The pre-verification response contains no room name or documents; the NDA/privacy checks remain authoritative. |
| 2. Missing slots | The sender summary names every missing document. Each empty outline slot is named and offers **Add file**, with a specific accessible label. The API explicitly returns missing slots and ignores assignments to removed documents. Visitors receive neither checklist slots nor empty folders. |
| 3. Needs you | Uses the existing count pill, shown only while unanswered questions/copy requests exist. The API exposes the pending count; answering removes an item from it. |
| 4. Selected tabs | Reuses the existing neutral selected subnavigation treatment. **Documents stays selected throughout Drive import**, and each other room section has the same treatment. |
| 5. Invite priority | Invite investors is secondary for empty rooms and throughout import setup/review. It becomes primary when files exist and no import is pending. Navigation and placement controls are disabled during the import request. |
| 6. Drive updates | The Documents sidebar starts with **Check Drive for updates** and a persisted **Last checked** timestamp (or “Not checked yet”). Checking records its successful completion without publishing versions. |
| 7. Pins | Pin/unpin controls use the existing Lucide pin icon to match the wording. Start-here rows have up/down arrows, boundary disabling and labeled removal. Every icon-only control added/changed here has an accessible name and native tooltip. |
| 8. Review edits | Every file can be excluded, restored, or moved to another reviewed folder or checklist slot. The confirm count follows the included files; zero-file imports are disabled. The backend checks file/folder IDs against the signed review, omits excluded downloads and creates destination folders before moving files into later sibling folders. |
| 9. Confirmation | A sticky bottom confirmation bar stays visible in the review’s scroll container, including before scrolling. |
| 10. Folder tree | The default review nests each folder’s files and subfolders beneath it, with recursive included-file counts. Moving or excluding a file updates the tree/counts. |
| 11. File wording | Review metadata describes the actual export: “Google Doc, saved as a PDF copy”, Sheets → Excel, Slides → PowerPoint, or “PDF, added as is”. Converted files show their final filename/extension. |
| 12. Skipped items | A separate list names shortcuts, Forms, other unsupported types, oversize files, unavailable exports and files already in the room, with a reason for each. Snapshot listing now reports actual export size instead of always reporting zero. |
| 13. PDF icons | Passes the final file type to the existing FileTypeIcon, so ordinary and exported PDFs use its PDF icon. |
| 14. Checklist switch | The default review visibly offers **Match to a Series A checklist instead**. This obtains another signed review and exposes Matched, Unsure and Missing. Exclusions and explicit folder moves survive the switch. A reverse switch keeps Drive folders. |

No requested item was deferred. Existing prototype limits remain: snapshot-based Drive access, synchronous bounded imports, and the existing Sign integration. Live Google OAuth, live signing and real email delivery were not exercised. Changing the snapshot during import can still require a fresh review; full content validation remains on the upload path.

### Round 2 verification

- Backend: **164 passed** (106.20 seconds; 186 existing test-secret warnings), recorded in `docs/room-proto/round2-verification.txt`. Coverage includes all existing `dealroom/tests`, `tests/dealroom` (including the unchanged `test_review_v09_send.py`) and `tests/cloudfiles/test_tasks.py`. New tests cover named missing slots, answered/unanswered counts, exclusions, moves, signed-tree boundaries, all three export descriptions, skipped reasons, repeat imports, persisted checking time, inviter preview without redemption and visitor filtering.
- Frontend: **23 passed across 6 files**: RoomPolish, RoomOnramp, DealroomRecipient, DealroomRoomDetail, DealroomPages and GlueShellSelect. Existing tests remain intact except the personal-link test’s required button-label expectation, changed from “Continue to room” to “Review the NDA”; its identity and explicit-action assertions are unchanged.
- Production: **`npx vite build` passed in the scratch frontend copy**, using unchanged configs and copied dependencies. The worktree also built with `npx vite build --configLoader native`. The ordinary loader in the worktree cannot write `.vite-temp` through the required read-only dependency symlink. No npm install was run in the worktree and neither protected config was edited. Existing bundle-size/Browserslist warnings remain.
- Chromium: built app at **1440×1000** and **390×844**, with intercepted fictional APIs. Verified selected tabs, named missing slots, sticky confirmation, exclusion counts, folder moves, checklist switch/groups, import payload, branded invitation/NDA and room-name privacy. No page errors or horizontal phone overflow. Browser smoke source: [`round2-smoke.py`](docs/room-proto/round2-smoke.py); it expects Vite preview on port 4175 and Python Playwright with Chromium.
- Screenshots: [Documents](docs/room-proto/round2-screenshots/sender-outline.png), [missing slots](docs/room-proto/round2-screenshots/sender-missing-slots.png), [Drive review](docs/room-proto/round2-screenshots/drive-review.png), [checklist groups](docs/room-proto/round2-screenshots/checklist-review.png), [phone invitation](docs/room-proto/round2-screenshots/visitor-invitation-phone.png), [phone NDA](docs/room-proto/round2-screenshots/visitor-nda-phone.png).

Backend uses the supplied runner and the same Bash `mktemp` redirection documented above. Frontend tests/build use a disposable `.testtmp/frontend` copy, with no config changes. Scratch files and `frontend/node_modules` are removed at completion. No deployment, staging, commit or project-memory update was made.

## Round 3 — 17 November 2026

Implemented on `agent/room-proto` at `582a03ba4a93024e3da4c7a752311ef132ed2325`, without committing or deploying. This round changes the Dealroom application and its `dealroom_sign` adapter; **the Documenso fork is untouched**. The existing Fleet cards, menus, buttons, pills, typography and file icons are reused.

| Request | Result |
| --- | --- |
| NDA placement | Seed placement uses the existing bounded `dealroom_sign.placement` engine with the demo visitor's identity. Runtime starts and resets place for the verified visitor, ignoring legacy policy coordinates. Automatic workflows retain placement evidence and validate it before dispatch. Uncertain seed placement raises a clear `CommandError`; runtime returns the existing `needs_sender` response and a visible host-review message. The sender's NDA picker no longer submits coordinates. |
| Signing return | The existing per-envelope `redirectUrl` still points to the authenticated signing return callback. A signed NDA now returns to `/view/<slug>?nda=complete`, including while sealing is pending. The Dealroom confirmation has **Enter the data room**, the requested email line, and **Download your signed NDA**. While the copy is pending, **Preparing your copy…** is disabled and polls until ready. Entry is enabled only when the backend permits room access. |
| Personal NDA | **Your signed NDA**, with the signed date, appears separately at the bottom of the visitor room. The endpoint binds room, member ID and email to the verified visitor session. It downloads the canonical sealed PDF with a hash check and attachment headers, without watermarking or the room's document download ceiling. Room closure does not block this legal-copy endpoint. Other visitors cannot retrieve it; executed artifacts are excluded from the ordinary document list. |
| Copy | Updated the React room/reader, legacy Dealroom room/gate templates, and the email-gate notice in all six locale catalogs to company-and-individual wording. Removed the email-gate inline translation fallback. No existing test needed a copy expectation change. |
| Watermark style | Settings now holds one organization-wide **Diagonal / Edge** default. Room Settings offers **Workspace default**, **Diagonal**, or **Edge**. The choice reaches the actual server-rendered page image and downloaded PDF through the shared issued-copy identity. Diagonal retains the current low-opacity treatment. Edge draws one small horizontal line at the bottom, retaining the existing brand-file identity + Copy ID template. Settings use existing Activity/outline JSON records; no schema or migrations were added. |
| Note and folders | The note precedes the return-visit panel and documents. Visitor folders are recursive, collapsible sections, with their files. Saved sender order is respected; folders without order records use sender creation order. Empty/inaccessible folders remain hidden. The repeatable demo seed already creates the Series A folders; new coverage confirms that it does. |

### Fixtures, real behavior and limits

- The **existing** `backend/dealroom_sign/tests/fixtures/placement/harbor.pdf` remains unchanged. A new runtime regression signs as its fictional counterparty, Lee Harbor, and checks page 2 and the signature field's y-band against the actual PDF text/rule geometry. It also verifies placement evidence was stored.
- The on-ramp's separate `drive/harbor-light/nda.pdf` was a two-page placeholder without signature lines. It now contains a deterministic fictional agreement and attributable Dan/Maya signature blocks. `make_nda.py` regenerates it, and `make_snapshot.py` uses that generator. A second geometry test verifies the seeded Maya field against this PDF's text layer. Existing imported copies are immutable: replacing a previously seeded placeholder still requires publishing/selecting the new NDA source through the normal document flow; rerunning an import does not overwrite issued source bytes.
- Placement, settings persistence, authorization, polling UI, original-copy download, folder ordering, and both watermark renderers are real product code. No coordinates are inferred by the frontend, and a browser redirect never grants room access.
- Browser screenshots use intercepted fictional APIs. Their watermark images were produced by the **real product renderer** using the checked-in fictional NDA and brand-file template. The browser's example download serves a fixture PDF, not a genuinely Sign-sealed document. Backend tests assert exact bytes against a stored artifact fixture. Live signing/sealing, worker reconciliation, and real email delivery were not exercised; those continue to use the existing adapter and mail queue.
- The private copy still requires a valid verified visitor session. The existing session lifetime and identity checks remain in force. No new public download capability was introduced.
- No requested feature is deferred. Existing prototype constraints from rounds 1–2 remain, including snapshot-based Drive access and JSON-backed prototype preferences. No deployment or live invitation was performed.

### Round 3 verification and screenshots

**Requested suites: 179 backend tests and 28 frontend tests passed. The production build and both Chromium viewport runs passed.** An extra signing-adapter run passed 78 tests and reproduced one pre-existing route-manifest failure on both this worktree and unchanged HEAD. See [`docs/room-proto/round3-verification.txt`](docs/room-proto/round3-verification.txt) for commands, failing-first evidence, the baseline reproduction, and cleanup checks. Existing test files are unchanged; all new regression cases are in `test_room_round3.py`, `RoomRound3.test.jsx`, and `RoomWatermarkSettings.test.jsx`.

Chromium captures use **1440×1000** and **390×844** viewports. Full-page companions preserve the complete room hierarchy and complete PDF page where they exceed the viewport. Twenty captures are in [`round3-screenshots/`](docs/room-proto/round3-screenshots/), including:

- Confirmation: [desktop](docs/room-proto/round3-screenshots/confirmation-desktop.png), [phone](docs/room-proto/round3-screenshots/confirmation-phone.png), [preparing copy](docs/room-proto/round3-screenshots/confirmation-preparing-phone.png).
- Visitor note, nested folders and personal NDA: [desktop](docs/room-proto/round3-screenshots/visitor-room-desktop.png), [phone](docs/room-proto/round3-screenshots/visitor-room-phone.png).
- Diagonal: [desktop full page](docs/room-proto/round3-screenshots/watermark-diagonal-desktop-full.png), [phone](docs/room-proto/round3-screenshots/watermark-diagonal-phone.png). Edge: [desktop full page](docs/room-proto/round3-screenshots/watermark-edge-desktop-full.png), [phone](docs/room-proto/round3-screenshots/watermark-edge-phone.png).
- Workspace default: [desktop](docs/room-proto/round3-screenshots/workspace-settings-desktop.png), [phone](docs/room-proto/round3-screenshots/workspace-settings-phone.png). Room override: [desktop](docs/room-proto/round3-screenshots/room-settings-desktop.png), [phone](docs/room-proto/round3-screenshots/room-settings-phone.png).

The screenshot runner is `round3-smoke.py`; `round3-watermark-assets.py` creates its temporary renderer assets. The browser checks preparation polling, a real browser attachment download, explicit room entry, folder collapse, nested file placement, personal NDA separation, and persistence payloads for both settings controls. No page errors or phone horizontal overflow were observed.

## Round 4 — 17 November 2026

Built on `agent/room-proto` at `57bf8a62c597d7763e6422213408ad23b55e94e6`. Changes remain uncommitted and undeployed. Product code is brand-neutral and reuses Fleet controls and the existing PDF page renderer. The Documenso fork is untouched.

**Room Settings → Entry NDA** now accepts a separate PDF upload or an existing room PDF. A separate upload stays outside ordinary room content. The new deterministic [Investor NDA fixture](<backend/dealroom/tests/fixtures/Investor NDA (fictional).pdf>) names Harbor Light Analytics, Inc. as discloser, with a fictional pre-signed Dan Whaley, CEO block and blank recipient Signature, Name, Company and Date rules. Its [generator](backend/dealroom/tests/fixtures/make_investor_nda.py) is checked in; the existing company-to-company NDA remains an ordinary Legal document.

The existing `dealroom_sign` placement engine runs with a placeholder recipient. Geometry is accepted only for the blank recipient block. When identity placement holds, a bounded text-layer pass finds labelled blank rules and shows **Suggested — check**. The sender can drag, resize, delete, or add Signature, Name, Company, Date and Initials boxes, with keyboard movement/resizing as well. **Use these positions** is the explicit confirmation step. Documents without clear blank rules remain manually placeable; suggestions never authorize signing.

Confirmed positions persist in the existing `NdaPolicy.fields` JSON list. Confirmation is an existing Activity JSON record bound to the policy revision, source hash and field hash. **No migration or schema change is needed**, and the native field-list shape remains compatible with the older preview process sharing the database. Selecting another file clears confirmation; a stale editor cannot confirm an older revision.

Every visitor start and reset uses the confirmed geometry without name-based placement. Native Name fields use the invitation name; Company fields receive editable native text defaults when known. Invitations and grant/link creation are blocked until a required entry NDA is confirmed, and the sender sees **Place the NDA fields**. Reset checks confirmation before contacting the existing remote envelope.

`seed_room_onramp` now uploads the separate investor fixture, suggests and explicitly confirms it through the same policy helper as the sender, and prints **`confirmed 4 fields on page 1`**. Repeating it retains confirmed positions and the twelve ordinary room documents. Existing room/Sign credentials and the snapshot setting described above still apply; no live invitation was sent.

Round-four verification: **191 backend tests and 32 frontend tests passed; the production build and both Chromium viewport runs passed**. Commands, failing-first results, the four requirement-driven changes to existing round-three backend tests, and limitations are recorded in [round4-verification.txt](docs/room-proto/round4-verification.txt). All existing frontend tests are unchanged. The extra adapter selection still has the previously documented route-manifest failure: 78 passed, one failed; the same failure was reproduced on unchanged HEAD. Live Sign sealing and deployed-host operations were not exercised.

The [browser runner](docs/room-proto/round4-smoke.py) uses fictional intercepted room APIs, real backend suggestion geometry and the real PDF rendered by the existing PDF.js components. It verifies drag/resize, confirmation and reopening saved positions at **1440×1000** and **390×844**, with no page errors or horizontal overflow. Captures:

| State | Desktop | Phone |
| --- | --- | --- |
| Suggestions | [Viewport](docs/room-proto/round4-screenshots/placement-suggestions-desktop.png) · [Full page](docs/room-proto/round4-screenshots/placement-suggestions-desktop-full.png) | [Viewport](docs/room-proto/round4-screenshots/placement-suggestions-phone.png) · [Full page](docs/room-proto/round4-screenshots/placement-suggestions-phone-full.png) |
| After a drag | [Desktop](docs/room-proto/round4-screenshots/placement-after-drag-desktop.png) | [Phone](docs/room-proto/round4-screenshots/placement-after-drag-phone.png) |
| Positions confirmed | [Desktop](docs/room-proto/round4-screenshots/positions-confirmed-desktop.png) | [Phone](docs/room-proto/round4-screenshots/positions-confirmed-phone.png) |
| Blocked sharing | [Desktop](docs/room-proto/round4-screenshots/blocked-share-desktop.png) | [Phone](docs/room-proto/round4-screenshots/blocked-share-phone.png) |

Vite/Vitest configs, dependency lockfile and project memory are unchanged. Temporary dependencies and test files are removed at completion. No commit, staging, migration or deployment was performed.

## Round 5 — 17 November 2026

Built on `agent/room-proto` at `90948b76726344d71076047bfcc8407f2de87265`. Changes remain uncommitted and undeployed. Product code is brand-neutral; Fleet components and the existing signer gateway are reused. The Documenso fork is untouched.

**Review the NDA now starts signing in the same tab.** The explicit personal-invitation click verifies that visitor, creates or resumes their NDA request, waits for signing readiness, then opens the existing one-time handoff. Email delivery is independent of entry. The gateway and returning visitor screen say **We’ve also emailed you this link** after recorded delivery; the preparation screen explains that email is a backup. Returning unsigned offers **Continue signing**. The honour-system room-entry button is removed. Preparation errors and a bounded readiness wait leave an explicit retry path.

**The shared gateway now returns to the workflow’s room confirmation.** Creating or continuing an NDA in the room application stores its configured origin and room ID in an existing `ObservedSignEvent` JSON record bound to the workflow. The gateway reads that record and constructs the confirmation route using the workflow’s room entry link. Its own `SITE_DOMAIN`, browser `return_url`, and browser completion claims cannot replace the binding. Callback, native completion and session-context terminal pages all use this return after authoritative signing confirmation, including while sealing is pending. The round-three confirmation retains **Enter the data room**, **Download your signed NDA**, and the copy-by-email line; access/download readiness remains server-checked.

**Names now follow the owner’s display name.** NDA mail uses `User.name` rather than Django’s unused first/last-name fields, retains the tenant/From and Reply-To conventions, and identifies room NDA invitations as Dealroom mail. Room invitations identify the owner in the body and branded From name. Invitation previews read the current owner even when an older personal link contains “Fleet Admin”. The seed changes only blank or “Fleet Admin” owner names to **Dan Whaley**.

**Room polish:** the requested watermark sentence sits beside the NDA badge, with no contradictory footer notice. Unfiled rows live in an aligned **Other documents** section. Per-list number badges are removed while sender order remains intact. Spreadsheets show a verified sheet count or no count. Folders have compact rows and a single outer border; nested rows/folders no longer create card-in-card borders.

### Gateway porting requirement

The shared recipient origin `:9445` is served by the preview Send image. This worktree does not update that running image. Port **all seven** adapter files below to its branch/image before the live walkthrough:

- `backend/dealroom_sign/room_return.py` — new workflow-bound room-origin helper.
- `backend/dealroom_sign/workflows.py` — bind new NDA workflows.
- `backend/dealroom_sign/views.py` — bind resumed/entered workflows; expose backup-email delivery status.
- `backend/dealroom_sign/recipient_proxy.py` — use the binding for terminal pages, including session context.
- `backend/dealroom_sign/counterparty.py` — snapshot the actual owner display name.
- `backend/dealroom_sign/counterparty_mail.py` — room NDA From name uses the Dealroom convention.
- `backend/dealroom_sign/templates/dealroom_sign/recipient.html` — backup-email acknowledgement on signing entry.

Keep the room application's `SITE_DOMAIN` set to its own `:9447` origin. New NDA requests bind it automatically. For an already-created legacy workflow, choose **Continue signing** through the room once to establish its binding; unbound legacy workflows retain the configured-site fallback. Run the existing `seed_room_onramp --owner <existing-staff-email>` to update placeholder fictional owner names. Already-sent mail and stored sender snapshots are not rewritten; use a new visitor NDA request to inspect corrected mail. No migration is needed.

### Round 5 verification

**207 backend tests and 36 frontend tests passed; the production build and both Chromium viewport runs passed.** Sixteen new backend cases and four new frontend cases cover the loop, names and polish. The finalized new backend file produces **14 failures / 2 passes on unchanged HEAD**; the initial tests were also run before the corresponding product edits. The extra adapter selection is **78 passed / 1 pre-existing failure**, reproduced unchanged on the baseline. Registry validation passed (328 operations); OpenAPI has zero errors and the existing warnings.

The [verification record](docs/room-proto/round5-verification.txt) contains the same round-four command selections, failing-first evidence, the two requirement-driven changes to existing tests, and the unchanged-HEAD reproduction of the known signing-adapter route-manifest failure. No existing test was weakened or skipped. Vite/Vitest configs, dependency lockfile and project memory are unchanged.

The [browser runner](docs/room-proto/round5-smoke.py) captures the built application at **1440×1000** and **390×844**, including Back/Continue, same-tab entry, confirmation polling/download, and the revised room. It uses fictional intercepted APIs and the **real gateway consent/entry template**. Native Documenso editing/completion, SMTP and live sealing are external boundaries and were simulated, not exercised. Backend regressions separately test actual DB binding, one-time handoffs, gateway handlers and sealed-copy access.

| State | Desktop | Phone |
| --- | --- | --- |
| Invitation | [Desktop](docs/room-proto/round5-screenshots/invite-desktop.png) | [Phone](docs/room-proto/round5-screenshots/invite-phone.png) |
| Signing entry, same tab | [Desktop](docs/room-proto/round5-screenshots/signing-desktop.png) | [Phone](docs/room-proto/round5-screenshots/signing-phone.png) |
| Return unsigned | [Desktop](docs/room-proto/round5-screenshots/continue-signing-desktop.png) | [Phone](docs/room-proto/round5-screenshots/continue-signing-phone.png) |
| Dealroom confirmation | [Desktop](docs/room-proto/round5-screenshots/confirmation-desktop.png) | [Phone](docs/room-proto/round5-screenshots/confirmation-phone.png) |
| Room top | [Desktop](docs/room-proto/round5-screenshots/room-top-desktop.png) | [Phone](docs/room-proto/round5-screenshots/room-top-phone.png) |
| Room bottom | [Desktop](docs/room-proto/round5-screenshots/room-bottom-desktop.png) | [Phone](docs/room-proto/round5-screenshots/room-bottom-phone.png) |
| Full room | [Desktop](docs/room-proto/round5-screenshots/room-full-desktop.png) | [Phone](docs/room-proto/round5-screenshots/room-full-phone.png) |

No staging, commit, migration, deployment or memory update was performed. Temporary dependencies and `.testtmp` are removed at completion.
