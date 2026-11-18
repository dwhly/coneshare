# C2a r28 results

**coder rc=0.** `VERSION = 'c2a.28'`. Base HEAD is `1c425e1bfc7b508cc977eb5e5e3fffefb1eba0b7` (c2a.27); the working tree is uncommitted. Tested source SHA-256: `e5dc8ef0c406b2e5e5fd22f91c7d7327bb80db185b658771f0fccb4eeead6733`. All required release checks passed. [Release checks](release-bars.json), [source and commit provenance](source-provenance.json).

## Shipped

B-1: broaden only `unclaimed_signing_peers`. The next aligned name row may match `NAME_CAPTION`, contain person text, or contain person text after an unfamiliar colon label. A following aligned labelled rule may end the stack regardless of its caption or semantic type; it need not say Date. The existing 22-point name-row and 125-point companion bands remain. When there is no closing rule, retain the reviewer's `cand27` 60-point fallback, covering a name followed by Title text alone.

This covers bare names, `Nom:`, `Nombre:`, `Print name:`, `Name (print):`, and the supplementary unfamiliar `Identité:` caption, with `Title:`, `Its:`, `Fecha:` and `Datum:` tails. `Name des Unterzeichners:` is also safe; the existing unreadable-name validation already holds these rows. No global caption vocabulary, identity scoring, assignment, field geometry, model eligibility, or serialization logic changed. Hidden peers remain unscored and may only veto a company-only placement. The existing recital-bound name exemption and immutable r13 L-2 policy remain in force.

N-3: use the same label-rectangle fallback for closing rules as for the other structural checks. A dedicated unit regression reproduced the old `KeyError` before this fix. [Product source](r28-source.py.txt).

## Failing first and exact reviewer sources

On untouched c2a.27, the final new tests yielded **446 failed / 820 passed / 0 errors / 0 skipped**:

- Exact 700-cell matrix: **220 failed / 480 passed**.
- Exact five real-worker shapes: **5 failed**; all put Pat on the affiliate line.
- Supplementary name/tail matrix: **220 failed / 340 passed**.
- Missing label rectangle: **1 failed**.

The unchanged assertions now pass. Targeted run, including all r13 and r27 tests: **4,141 passed / 0 failed / 0 errors / 0 skipped**. [Failing-first log](failing-first-final.txt), [JUnit](failing-first-final.xml), [targeted log](targeted.txt).

Reviewer Bash inputs and Python heredoc bodies were extracted byte-for-byte from `counterparty-c2a-gate3-r27.jsonl`; new test fixtures live only under `backend/dealroom_sign/tests/fixtures/r28/`. Capture adapters execute the exact generator loop bodies and retain their original oracles. [Extraction provenance](extraction-provenance.json), [extraction verification](extraction-verification.json).

The transcript corrects two prose counts: call 33's **700** cells include a fifth `name_far` tail; call 38's measured `cand27` subset has **560** cells. Call 38's ordinary cohort contains **300**, not 324, cells. The first test draft used that 560-cell subset (446 failed / 680 passed); the final failing-first run added the 140 `name_far` controls to reproduce all 700. The draft and both runs are preserved; no assertion was weakened.

Independent source replay reproduces **220 WW** between r26 and r27. Exact `cand27` closes **130**, leaving **90**; r28 closes all **220**, with **700 holds / 0 wrong**. All five real workers now hold, with worker/in-process equality and 0 model or HTTP calls. [Variant comparison](measured-variants/summary.json), [worker comparison](measured-workers/summary.json).

## Monotonic comparisons and inherited families

**82,450 inherited cells across 27 collections: 0 raw wrong in every collection.** The live r27, r26, and r21 sources were verified against their git commits and executed independently. Historical baseline results match the preserved r27 evidence cell-for-cell. Seven goldens and native fields are exact except `analysis_version`; all inherited real-worker outputs match their in-process results. Collections overlap and are not deduplicated.

The following transitions use the unchanged raw geometry oracle. A raw flag in a retained name-authoritative or L-2 control is not classified as a new wrong placement; those controls are identified separately below.

| Cohort | Baseline | n → p | c → w | Unflagged placement → hold | Raw flagged placement → hold |
| --- | --- | ---: | ---: | ---: | ---: |
| Inherited | r21 | 0 | 0 | 7335 | 1908 |
| Inherited | r26 | 0 | 0 | 0 | 0 |
| Inherited | r27 | 0 | 0 | 0 | 0 |
| Review / supplementary | r21 | 0 | 0 | 956 | 1824 |
| Review / supplementary | r26 | 0 | 0 | 46 | 1293 |
| Review / supplementary | r27 | 0 | 0 | 0 | 445 |

[All comparison counts](vs-live.json), [per-family evidence](family-comparison.json).

| Inherited collection | Cells | r28 raw wrong | Added correct holds vs r27 |
| --- | ---: | ---: | ---: |
| attack | 2,880 | 0 | 0 |
| boundary | 2,400 | 0 | 0 |
| exact_q3a | 4,536 | 0 | 0 |
| exact_q3b | 2,430 | 0 | 0 |
| exact_q3c | 2,808 | 0 | 0 |
| exhibits | 576 | 0 | 0 |
| extra | 1,680 | 0 | 0 |
| h1 | 2,160 | 0 | 0 |
| h1_review | 2,160 | 0 | 0 |
| historical | 17,204 | 0 | 0 |
| layouts | 5,680 | 0 | 0 |
| new | 420 | 0 | 0 |
| ordinary_ndas | 216 | 0 | 0 |
| q2 | 5,280 | 0 | 0 |
| q3a | 4,536 | 0 | 0 |
| q3b | 2,916 | 0 | 0 |
| q3b_aligned | 2,430 | 0 | 0 |
| review | 12,760 | 0 | 0 |
| stress | 2,706 | 0 | 0 |
| three_party | 36 | 0 | 0 |
| veto | 1,260 | 0 | 0 |
| workers | 72 | 0 | 0 |
| workers24 | 5 | 0 | 0 |
| workers25 | 8 | 0 | 0 |
| workers26 | 10 | 0 | 0 |
| workers_h1_uncaptioned | 1 | 0 | 0 |
| wrapped | 5,280 | 0 | 0 |

The review/supplementary runs contribute **14,756 cells**, including the complete r27 review A–E loops, Q4 recital controls, 5,376 non-signing stacks, the exact 700 variants, five workers and 560 supplementary rows. Required blocking scope: **0 wrong** throughout. All raw oracle flags remain visible in the compressed case evidence:

| Collection | Cells | Wrong in required scope | Raw geometry flags |
| --- | ---: | ---: | ---: |
| variants | 700 | 0 | 0 |
| workers | 5 | 0 | 0 |
| ordinary | 300 | 0 | 0 |
| stacks | 5,376 | 0 | 444 |
| recitals | 3,354 | 0 | 240 |
| r27 | 4,461 | 0 | 346 |
| extended | 560 | 0 | 0 |

Retained raw flags are the reviewer's explicitly name-authoritative controls and immutable L-2 own-company controls. Each retained flagged r28 output is identical to r27 except `analysis_version`; none is a new or moved placement. These are separately reported, not removed from the generators or passed off as zero raw flags. [Full review comparisons](new-family-comparison.json), [retained-control counts](release-bars.json).

## Ordinary documents, lows and nits

**Ordinary two-party documents: 0 added holds versus c2a.27 and c2a.26.** This covers the 216 inherited ordinary NDAs, 576 exhibit/guarantee/witness/notary/joinder controls, ordinary MSA subsets, and all 300 exact call-38 controls. [Ordinary hold-cost evidence](ordinary-hold-cost.json).

**L-2 table-row exhibit cost remains separately visible:** r27 versus r26 added **44 correct → hold + 24 wrong → hold** among 1,344 table cells. R28 versus r27 adds **0 correct → hold + 0 wrong → hold** in that layout. Those original holds are retained; removing them would introduce prohibited n → p transitions. [5,376-cell stack evidence](measured-stacks/summary.json).

**L-1 retained:** the Q4 own-company cohort includes the 280 r26 placements held by r27 under misspelt or conflicting recitals. Restoring those placements would create 280 n → p transitions against live c2a.27. No exemption relaxation ships. Immutable r13 L-2 remains **20/20 placed at y=560/600 with score=4 and margin=4; 20/20 both-signer holds**, also exercised in the full suite.

**N-1:** this session verified git HEAD, status, source hashes and unstaged scope directly. **N-2:** all HTTP counts are 0; synthetic model-client calls are reported rather than assumed absent. The exact r27 A–E replay records 600 Mock calls per revision, unchanged between r26/r27/r28. Q4 records 780 per revision. Other new cohorts record 0. **N-3 ships** as described above, with no new placement transitions in the measured families.

## Full suite and preservation

The full Send suite completed without `-x`, deselection, retries or skips: **53,690 passed / 0 failed / 0 errors / 0 skipped**. All **52,424 prior test IDs** remain; the two new Python test-tree files add **1,266 test IDs**. Their assertions and all new source fixtures are hash-frozen from the final failing-first run through completion. [Full log](full-suite.txt), [JUnit](full-suite.xml), [counts](full-suite-summary.json).

Command: `PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r28/run_tests.py dealroom_sign/tests --junitxml=../docs/implementation/c2a-r28/full-suite.xml`. The runner supplies the established isolated Send environment and a repository-local scratch SQLite database.

SHA-256 verification: **3,310/3,310 pre-existing tracked files other than placement.py unchanged**, including every test, fixture, earlier evidence file and `.done` marker. No existing test was changed, skipped, weakened, deleted or retargeted. Every new evidence file is below 20 MB. [Preservation audit](preservation-summary.json).

The first inherited replay driver encountered log-name collisions for `new` and `workers`, whose filenames were already owned by the new-review runs. Its executor still drained the other 24 jobs. The two unstarted collections were then run completely with distinct log names. The original driver error remains in the evidence; successful per-job completion logs and the two direct return codes form the [effective replay ledger](effective-replay-ledger.json). No product source or test was changed to address this harness issue.

**Blockers: none.** No staging, commit, deployment, migrations, configuration or project-memory edits.
