# C2a r32 results

**coder rc=1. `VERSION = 'c2a.32'`. M-1 is fixed in the worktree; the requested release bar is blocked.** HEAD remains `8dd65f82ae560c8563d29f16a0b3d4fad936d9e2`; live base is c2a.29 (`0aa3cbbb`). No staging, commit, deployment or memory update. Source SHA-256 `a433e6f1a64a2300223c82be7948849b3752ce86482a797f5b4f5141b423361d`.

The exact r31 Q3 matrices have **0 wrong / 30,150 cells**, including all 576 affiliate regressions now held. **486/686 M-1 recoveries survive**; 200 return to holds. All live-r29 correct placements are retained in the release matrices; every family has **c → w = 0 and n → W = 0**. All newly placed cells are correct and recorded in [every-n-to-p.json.gz](every-n-to-p.json.gz).

The complete Send suite finished without `-x`: **94,488 passed / 200 failed / 0 errors / 0 skipped**. All 200 failures are the immutable `test_placement_r30_recoveries.py` expectations for the 200 domain-only/no-recital recoveries now required to hold. No test was changed, weakened, skipped or retargeted. [Full completion](shipping-full-suite-completion.json), [exact failing IDs](test-audit.json).

## Worktree implementation

Only `extended_date_names_owned` changes behavior. The >22 pt band requires an explicit company with identical normalized word tokens, allowing trailing legal-suffix folding, or a recital that maps the block to that signer. Word boundaries, substantive words and digits remain significant; no prefix, sub-span or joined-token match can establish explicit ownership. A domain alone cannot certify an unrecited company, including `HARBORLIGHT, LLC`. Recital mapping retains the existing unique domain association and conflicting-party veto.

An unclaimed ruled block on any other page vetoes expansion when its direct company heading is stronger than the current role heading, or is an exact company match where the current heading is only a hint. This includes drawn lines and underscore rules, in either page order. Existing same-page, intervening-rule and unclaimed-stack checks remain in effect. A failed guard returns to the r29 22 pt hold. Unrequested names retain their existing non-signable competition behavior.

N-2 is a comment-only clarification: 110 pt is the extraction floor that excludes unlabelled header rules. N-1 is verified by both Git HEAD/diff and SHA-256. An AST comparison confirms that every function outside the widened-band ownership predicate is unchanged from r31. [Structural proof](structural-proof.json), [tested source](shipping-source.py.txt), [source provenance](source-provenance.json).

## Exact extraction and failing first

Extracted 55 Bash command payloads, their 27 heredoc bodies, all four Write payloads, and both Edit payloads from the requested Gate 3 r31 JSONL. The original `own.py`, the exact successful filter edit, `aff_repro.py` and `b1_close.py` are preserved byte-for-byte under `backend/dealroom_sign/tests/fixtures/r32/`. Twelve copied r30 scripts were reconstructed using the exact r31 transcript transformation; the inherited `inh.py` wrapper was reconstructed by executing the exact line-286 transformation against the frozen r29 payload with in-memory I/O. The generator bodies remain unchanged. [Extraction provenance](extraction-provenance.json), [byte verification](extraction-verification.json), [inherited wrapper](inherited-generator-provenance.json), [body equality](generator-body-verification.json).

Before production edits, untouched c2a.31 produced **593 failed / 14,007 passed / 0 errors / 0 skipped**:

- Exact affiliate matrix: 576 failed / 14,004 passed; six exact real-worker variants: six failed.
- Exact-company and cross-page checks: nine failed / three passed.
- Underscore-rule cross-page checks: two failed.

All new assertions and fixtures used in failing-first runs are hash-identical to their snapshots. The subsequently reconstructed inherited wrapper is verified separately against its extraction hash. Three new test files add 14,600 cases; one helper loads the exact reviewer generators. [Failing first](failing-first.txt), [ownership](ownership-failing-first.txt), [underscore rules](rules-failing-first.txt), [preservation](preservation-summary.json).

## M-1 recovery tradeoff

Retained: **486**. Given up: **200**, all with no parsed recital (120 domain-only Pat cases; 80 two-signer cases). This affects no placement live r29 already made. The immutable 686-recovery test explicitly demands the former r30/r31 behavior, so the requested stricter ownership rule and a zero-failure unmodified suite cannot both be satisfied. [All 2,844 cells](shipping-date-cases.json.gz), [breakdown](date-recovery-breakdown.json).

| Axis | Retained recovery counts |
| --- | --- |
| recital | `{'parsed': 366, 'none': 120}` |
| signer | `{'domain': 122, 'explicit': 242, 'both': 122}` |
| datefirst | `{'30': 366, '20': 72, '12': 48}` |
| layout | `{'side': 219, 'stacked': 267}` |

## Measurement only: the live 16–20 pt policy

**1,692 / 5,832 cells** in the affiliate Q3 generator place Pat under an affiliate heading at gap 16 or 20 pt on live c2a.29. This measurement changes only the gap axis of the archived generator, from `(24, 30, 36, 44, 50)` to `(16, 20)`; the fixture itself is untouched. The other cells are 3,582 holds and 558 oracle-correct placements. Separately, the reviewer’s exact five-heading/signer worker-sweep subset gives **72 wrong / 90 cells** (18 holds). These are distinct inventories, not additive unique cases.

r32 produces identical outputs to live on both narrow-band inventories, except `analysis_version`; no narrow-band policy change ships. [5,832-cell measurement](shipping-narrow_affiliate_matrix-summary.json), [90-cell measurement](shipping-narrow_affiliate-summary.json).

The 1,692 measured flags split evenly by gap: 846 at 16 pt and 846 at 20 pt. By heading: `HARBOR LIGHT GROUP, INC.` 558; `HARBORLIGHT, LLC` 558; `HARBOR LIGHT ANALYTICS HOLDINGS, LLC` 576.

## Every live comparison

`Wrong` below is the unadjusted reviewer oracle, with no inherited-policy exemptions. The release inventories overlap; counts are not deduplicated. Narrow-band measurement families are listed separately at the end. Every n → p is oracle-correct; all n → W and c → w counts are explicit. [Machine-readable comparisons](family-comparison.json), [every raw-oracle flag](every-strict-wrong.json.gz).

| Family | Cells | Wrong live / r32 | n → p correct | c → w | n → W | c → hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| review/affiliate_sender | 14,580 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/date | 2,844 | 0 / 0 | 486 | 0 | 0 | 0 |
| review/geometry | 1,728 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/hidden | 1,008 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/misspell | 6,480 | 0 / 0 | 612 | 0 | 0 | 0 |
| review/misspell_sender | 1,080 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/no_rule | 648 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/ordinary_offsets | 792 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/plain | 9,216 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/prev_column | 4,050 | 0 / 0 | 348 | 0 | 0 | 0 |
| review/role_other | 2,610 | 0 / 0 | 576 | 0 | 0 | 0 |
| review/ruleless_name | 810 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/same_company | 1,350 | 0 / 0 | 144 | 0 | 0 | 0 |
| review/stray | 2,916 | 12 / 12 | 0 | 0 | 0 | 0 |
| review/swap | 9,216 | 0 / 0 | 0 | 0 | 0 | 0 |
| review/two_columns | 288 | 0 / 0 | 0 | 0 | 0 | 0 |
| prior/extended | 560 | 0 / 0 | 0 | 0 | 0 | 0 |
| prior/notices | 14,112 | 94 / 94 | 0 | 0 | 0 | 0 |
| prior/ordinary | 300 | 0 / 0 | 0 | 0 | 0 | 0 |
| prior/r27 | 4,461 | 206 / 206 | 0 | 0 | 0 | 0 |
| prior/recitals | 3,354 | 120 / 120 | 0 | 0 | 0 | 0 |
| prior/stacks | 5,376 | 444 / 444 | 0 | 0 | 0 | 0 |
| prior/variants | 700 | 0 / 0 | 0 | 0 | 0 | 0 |
| prior/workers | 6 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/attack | 2,880 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/boundary | 2,400 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/exact_q3a | 4,536 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/exact_q3b | 2,430 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/exact_q3c | 2,808 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/exhibits | 576 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/extra | 1,680 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/h1 | 2,160 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/h1_review | 2,160 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/historical | 17,204 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/layouts | 5,680 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/new | 420 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/ordinary_ndas | 216 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/q2 | 5,280 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/q3a | 4,536 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/q3b | 2,916 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/q3b_aligned | 2,430 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/review | 12,760 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/stress | 2,706 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/three_party | 36 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/veto | 1,260 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/workers | 72 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/workers24 | 5 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/workers25 | 8 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/workers26 | 10 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/workers_h1_uncaptioned | 1 | 0 / 0 | 0 | 0 | 0 | 0 |
| inherited/wrapped | 5,280 | 0 / 0 | 0 | 0 | 0 | 0 |

The inherited raw-oracle flags are unchanged outputs from live. Some are the historical L-2 own-company controls; others include actual name-authoritative/affiliate placements, such as the r27 A-family placement under `HARBOR LIGHT GROUP, INC.`. They are disclosed as raw flags, not relabelled into a zero-wrong claim. Eliminating the pre-existing cases would require widening this task’s scope and resolving the preserved policy controls. The r13 L-2 test remains intact and passes.

| Measurement-only family | Cells | Wrong live / r32 | n → p correct | c → w | n → W | c → hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| review/narrow_affiliate | 90 | 72 / 72 | 0 | 0 | 0 | 0 |
| review/narrow_affiliate_matrix | 5,832 | 1692 / 1692 | 0 | 0 | 0 | 0 |

All seven goldens and native-field conversions are exact except `analysis_version`. All 21 inherited reviewer worker cases remain holds and equal in-process results; the full suite also includes all 36 B-1 workers and the six new affiliate worker cases. HTTP calls are zero in the comparison runs; model-call counts match live per cell. [Goldens](golden-audit.json), [workers](shipping-exact-workers.json).

The current reviewer matrices execute fresh live-r29, r31 and r32 modules. The 27 inherited collections and eight prior-review families execute r32 on every generated cell and compare against immutable r29 output archives, with case keys/axes checked and baseline sources verified against Git. Historical r21/r28 columns remain available in their evidence; release comparisons use r29.

## Full-suite completion and preservation

Command: `PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r32/run_full_suite_shipping.py`.

Four isolated pytest processes completed all **94,688 collected IDs**, with separate scratch SQLite databases, no `-x`, retries, skip filters or omitted test IDs. All **80,088 pre-existing IDs** are preserved, plus 14,600 new IDs. The merged JUnit IDs match collection exactly. [Manifest](shipping-full-suite-manifest.json), [JUnit](shipping-full-suite-complete.xml), [completion](shipping-full-suite-completion.json).

SHA-256 verifies **5,249/5,250 pre-existing tracked files unchanged**; only production `placement.py` differs. Every old test, fixture, implementation evidence file and `.done` marker is preserved, including all 363 old test-tree files. No staging or commit. Every new evidence file is under 20,000,000 bytes. [Preservation](preservation-summary.json), [size audit](evidence-size-audit.json).

**Blockers:** (1) 200 frozen all-686 recovery assertions conflict with the exact-ownership requirement; (2) the absolute strict-oracle zero-wrong bar includes pre-existing live placements outside the authorized >22 pt change. No existing tests or evidence were altered to conceal either conflict. The `.done` marker therefore reports `coder rc=1`.
