# C2a r26 results

**Exact cand5 implemented as `c2a.26`; coder rc=1. Not release-ready. No commit.**

Base HEAD `701f6aeeabfc47bf5b997b1187705b039aea4f40`; implemented source SHA-256 `50e8c0e2d87717f7e509902eff98bf35eff69124638a8d44cbc251780273ac31`.

**Release blocker:** the full suite completed with 20 failures in the unchanged r13 L-2 positive controls. They require a company-only placement on a page with three non-witness blocks and two unclaimed blocks—the exact condition cand5 must hold. All replay safety bars pass, but the required zero-failure full-suite bar does not. [Conflict reproduction](suite-conflict.json).

## Change and failing first

The existing unclaimed-block flag now also arms when another non-witness block on the same page is unclaimed and that page has at least three non-witness blocks. The final company-only placement becomes an `ambiguous_identity` hold. Scoring, assignment and margins are unchanged. The implementation of `prepare_blocks` is AST-identical to the reviewer’s cand5. The hold message now covers both same-page and cross-page ambiguity. [Equivalence](cand5-equivalence.json).

**Unchanged c2a.25: 62 failed / 2,757 passed**: 55 exact Q3c cases and seven real-worker cases. Failures cover `same_named` (both signer sets), `same_harbour` (both), `same_caption_nocompany` (both), and `same_msa_supplier_nocompany` (Pat only). The two MSA-with-company controls and MSA-without-company/both-signers already held. [Failing-first log](failing-first.txt), [source/test hashes](failing-first-provenance.json).

**Final new-test run: 2,819 passed. Full Send suite: 50,454 passed, 20 failed, 0 errors, 0 skipped**, completed without `-x`, deselection, test edits or fixture edits. All 47,655 old IDs remain; 2,819 new IDs are in the new r26 test file. All 40 r19 identity-before-veto score cases pass. [Full log](full-suite.txt), [JUnit](full-suite.xml), [commands](run-provenance.json).

The 20 failures are `test_placement_r13.py::test_l2_separate_own_company_line_preserves_scoring` with Pat alone: four headings × five captions. The original fixture has By blocks at y=270, 310 and 560 on page 1. Their scores are `[0], [0], [4]`; none is a witness. The middle block has an uncertain printed-name identity, so it remains unclaimed. r21/r24/r25 place at y=560 with score=4 and margin=4; exact cand5 sets the guard and holds. All 40 original positive/hold controls were replayed across four versions, with **160 real-worker evaluations matching in-process results**. Tests and input fixtures remain unchanged. No exception was added merely to restore these placements. [Measured conflict](suite-conflict.json), [reproducer](suite_conflict.py).

## Exact reviewer inputs and count corrections

Generator bodies were extracted byte-for-byte from the supplied r24/r25 transcripts, with full commands, line numbers and SHA-256 hashes retained. Tests execute their original generator bodies with only the evaluator replaced by a case collector; no axis is reconstructed. Q3a/Q3b body hashes, excluding the heredoc trailing newline, match review prefixes `e41a8ab17b73` / `431acfa07d6c`. [Provenance](review-provenance.json).

The review prose has two arithmetic errors: Q3a’s 42 shapes × 108 combinations generate **4,536**, not 3,888 cells; Q3c’s 26 shapes × 18 same-page combinations generate **468**, not 324 cells. The six Q3c layouts total 2,808. The transcript output itself totals 468 same-page cells and reproduces all 55 wrong placements. Every generated cell is retained and evaluated, including all controls. Q3b is exactly 2,430 cells.

## Comparison against r25 live, r24 and r21

**82,450 replay cells across 27 collections; 980 real-worker evaluations.** Every family has `n → p = 0` and `c → w = 0` against all three baselines. **Raw wrong placements remaining: 0.** All seven goldens and their native fields are exact except `analysis_version`, both in-process and through real workers. All retained baseline results equal their prior archived outputs. External HTTP calls are zero; new-family model calls are zero (historical golden/control stubs retain exactly their expected calls). Report transitions use raw geometry: closing an accepted historical wrong cell is counted as wrong → hold, not correct → hold. The original harness logs are retained.

| Collection | Cells | r21 raw W | r24 raw W | r25 raw W | r26 raw W | r25 correct → hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| historical | 17204 | 0 | 0 | 0 | 0 | 236 |
| review | 12760 | 102 | 102 | 102 | 0 | 1757 |
| layouts | 5680 | 0 | 0 | 0 | 0 | 0 |
| wrapped | 5280 | 0 | 0 | 0 | 0 | 0 |
| new | 420 | 24 | 0 | 0 | 0 | 0 |
| stress | 2706 | 288 | 156 | 52 | 0 | 0 |
| q2 | 5280 | 48 | 0 | 0 | 0 | 166 |
| extra | 1680 | 0 | 0 | 0 | 0 | 72 |
| workers | 72 | 6 | 0 | 0 | 0 | 0 |
| attack | 2880 | 0 | 0 | 0 | 0 | 58 |
| boundary | 2400 | 24 | 0 | 0 | 0 | 32 |
| h1_review | 2160 | 96 | 0 | 0 | 0 | 0 |
| veto | 1260 | 0 | 0 | 0 | 0 | 26 |
| workers24 | 5 | 0 | 0 | 0 | 0 | 0 |
| workers_h1_uncaptioned | 1 | 1 | 0 | 0 | 0 | 0 |
| h1 | 2160 | 90 | 0 | 0 | 0 | 0 |
| q3a | 4536 | 292 | 248 | 0 | 0 | 0 |
| q3b | 2916 | 178 | 166 | 0 | 0 | 0 |
| workers25 | 8 | 7 | 7 | 0 | 0 | 0 |
| q3b_aligned | 2430 | 104 | 96 | 0 | 0 | 0 |
| ordinary_ndas | 216 | 0 | 0 | 0 | 0 | 0 |
| exact_q3a | 4536 | 292 | 248 | 0 | 0 | 0 |
| exact_q3b | 2430 | 92 | 84 | 0 | 0 | 0 |
| exact_q3c | 2808 | 257 | 248 | 55 | 0 | 10 |
| exhibits | 576 | 0 | 0 | 0 | 0 | 0 |
| three_party | 36 | 0 | 0 | 0 | 0 | 6 |
| workers26 | 10 | 7 | 7 | 7 | 0 | 0 |

The inherited `q3a`, `q3b`, and `q3b_aligned` rows retain the r25 reconstructions; `exact_*` rows separately use transcript generators. Overlapping collections are intentionally not deduplicated. [All family counts](family-comparison.json), [all transitions](vs-live.json).

| Baseline | n → p | c → w | Correct → hold | Wrong → hold |
| --- | ---: | ---: | ---: | ---: |
| r25 | 0 | 0 | 2363 | 216 |
| r24 | 0 | 0 | 5675 | 1362 |
| r21 | 0 | 0 | 7355 | 1908 |

## Medium and low items

**M-1:** remeasured all 192 misspelled-recital cells: r21 48 W, r24 48 W, r25 16 W, r26 0 W. No separate spelling heuristic shipped. The same-page guard supplies any improvement shown. Total remaining historical raw flags: 0. Any residual flags are restricted to the previously accepted classes and each complete result equals r21 except `analysis_version`. [Remaining flags](remaining-flags.json).

**L-1:** the proposed explicit-company exemption was measured on all 576 exact NDA/exhibit cells. It has zero wrong placements there but creates **28 n → p** versus both r25 and cand5: seven each for personal guarantees, company guarantees, blank forms and joinders. It is rejected under the monotonic-hold bar; no broader safety claim is made for this unshipped candidate. [Candidate source](low-exemption-source.py.txt), [complete measurement](low-exemption-measurement.json).

## Hold cost

**Ordinary two-party NDAs with attached exhibits:** 504 cells, plus 72 no-exhibit controls. cand5 adds zero holds versus r25. The 42 correct → hold cost versus r24 remains (28 explicit-company and 14 domain-only signers). The exact generator corrects the review prose’s claimed 21 explicit-company cases. [Detailed hold cost](hold-cost.json).

| Attached page (72 cells each) | r24 correct | r25 correct | r26 correct | New holds vs r25 |
| --- | ---: | ---: | ---: | ---: |
| none | 42 | 42 | 42 | 0 |
| personal_guarantee | 36 | 22 | 22 | 0 |
| guarantee_company | 36 | 22 | 22 | 0 |
| employee_ack | 22 | 22 | 22 | 0 |
| blank_form | 29 | 22 | 22 | 0 |
| joinder | 29 | 22 | 22 | 0 |
| notary | 36 | 36 | 36 | 0 |
| witness_only | 42 | 42 | 42 | 0 |

**Three-party same-page controls:** 36 cells; six correct → hold versus r25 (four named third-party controls, two unnamed), leaving 12 correct / 24 hold and zero wrong. The 468-cell same-page Q3c layout adds ten correct → hold among matching controls while closing all 55 wrong placements. H-1’s 2,160 states are unchanged versus r25: 774 correct / 1,386 hold.

## Preservation and blockers

**2,594/2,594 other originally tracked files are SHA-256 identical** to the starting inventory. This includes every earlier test, fixture, evidence file and `.done` marker. Only `placement.py` changed among existing files. The two test-tree additions are `placement_r26_review_cases.py` and `test_placement_r26.py`; their hashes are unchanged since the failing-first run. No staging, commit, migration/config change or memory write. [Preservation audit](preservation-summary.json).

**Blocker: 20 full-suite failures.** Exact cand5 and the existing r13 placement requirements cannot both hold for the measured inputs. Resolving that policy conflict requires a changed guard requirement or changed test expectations; neither is authorized by this task. The review’s count discrepancies are disclosed above; the exact generator inventories were executed in full. [Release checks](release-bars.json).

Replay commands are recorded in `run-provenance.json`. For reruns, use a fresh output directory: evidence writers open files exclusively and never replace earlier results.


## r26b — preserve the live r13 L-2 control

**coder rc=0; all required bars pass.** This section supersedes the earlier r26 release-blocker conclusion; earlier evidence and the original `.done` marker remain unchanged. HEAD `701f6aeeabfc47bf5b997b1187705b039aea4f40`; `VERSION = 'c2a.26'`; source SHA-256 `5683ff7bfc5a77b8a268198d689953c9fedc70b981ae83e64c7fb321f34a5c91`. No commit or staging.

### Rule chosen and measured alternatives

Keep the c2a.25 cross-page guard exactly. For the additional same-page arm, exclude a peer from the independent-party count only when it has printed names and **every** printed name equals the signer receiving the candidate's company-only score of 4. A vetoed stack bearing that signer's own name therefore does not create a third party. Unknown names, other names, mixed names and unnamed parties still count. The remaining page must still contain the candidate plus at least two non-witness peers, with an unclaimed peer. Scores, margins, assignment, model eligibility and output redaction are unchanged.

The actual immutable L-2 fixture has **no recital mapping** (`roles={}`). A recital-company exemption alone closes Q3c but still holds all 20 L-2 positives, so it was rejected. The selected own-name exclusion closes Q3c and restores all 20 L-2 placements to the complete c2a.25 result except `analysis_version`: signature y=560, date y=600, score=4, margin=4. Fleet's block remains a peer; the own-name stack no longer inflates the page to three independent parties. The additional two-signer L-2 controls all remain held. No sender-company name, signer name or coordinate is hardcoded. [Candidate measurements](r26b/candidate-measurement-v2.json), [selected source](r26b/r26b-source.py.txt).

The pilot also measured the recital-only direction: eight Q3c matching-control holds and six three-party holds recovered, but L-2 remained 0/20 placed. The selected rule is the smallest measured change to cand5 satisfying both required controls. The first pilot result is explicitly invalid: its extraction mock rejected the deadline keyword and produced unreadable-PDF holds. The corrected v2 harness asserts the live 55 Q3c wrong cases and 20 L-2 positives before recording evidence. Release counts come from the unchanged full replay harness, not that initial pilot. [Run provenance](r26b/run-provenance.json).

### Validation

Failing first on cand5: unchanged L-2 test **20 failed / 20 passed**; new generalized regression file **6 failed / 18 passed**. The new controls vary signer/company identity and heading, distinguish own names from another person's name, and preserve cross-page holds. After the fix, targeted tests: **2,883 passed**. Full Send suite completed **without `-x`, deselection or retries: 50,498 passed, 0 failed, 0 errors, 0 skipped**. L-2 positives: **20/20 placed**; L-2 two-signer controls: **20/20 held**; r19 competition score controls: **40/40 passed**. [Full log](r26b/full-suite.txt), [JUnit](r26b/full-suite.xml), [targeted log](r26b/targeted.txt).

**82,450 replay cells across all 27 inherited r16–r25/reviewer collections, 980 real-worker evaluations. Zero raw wrong placements in every collection.** Exact Q3a: 4,536; Q3b: 2,430; Q3c: 2,808 including **468 same-page cells and all 55 live errors**; H-1: 2,160 in each retained generator. Seven goldens and native fields are exact except the required `analysis_version`, in-process and through workers. Baseline outputs match the preserved r26 replay cell for cell. External HTTP calls: 0; model calls retain only the expected historical test stubs, with 0 in new/reviewer families. [Release audit](r26b/release-bars.json), [family evidence](r26b/family-comparison.json).

| Baseline | n → p | c → w | Correct → hold | Wrong → hold |
| --- | ---: | ---: | ---: | ---: |
| r25 | 0 | 0 | 2343 | 216 |
| r24 | 0 | 0 | 5655 | 1362 |
| r21 | 0 | 0 | 7335 | 1908 |

### Hold cost versus cand5

Across the same 82,450 replay cells: **20 cand5 holds restored to correct live placements; 0 additional holds; 0 wrong restorations**. Every restored result equals c2a.25 except `analysis_version`; every unchanged-state result equals cand5 completely. The 20 L-2 positive controls are included in this total through the historical collection; their separate pilot and pytest runs are not added again. Collections overlap and are not deduplicated. [Cell-level hold comparison](r26b/hold-cost-vs-cand5.json).

Same-page Q3c retains cand5's ten correct → hold cells versus live while closing all 55 wrong placements. Three-party controls retain its six correct → hold cells (12 correct / 24 held). H-1 is unchanged from cand5/live (774 correct / 1,386 held). Exhibit controls add no holds versus cand5/live; the earlier 42 correct → hold cost versus r24 remains. **M-1 stays 0/192 wrong** (r25: 16; r24/r21: 48), with 0 n → p. No separate spelling or explicit-company exemption is introduced.

| Collection | Cells | r26b raw W | Correct → hold vs live | Holds recovered vs cand5 |
| --- | ---: | ---: | ---: | ---: |
| layouts | 5680 | 0 | 0 | 0 |
| review | 12760 | 0 | 1757 | 0 |
| new | 420 | 0 | 0 | 0 |
| historical | 17204 | 0 | 216 | 20 |
| wrapped | 5280 | 0 | 0 | 0 |
| extra | 1680 | 0 | 72 | 0 |
| stress | 2706 | 0 | 0 | 0 |
| workers | 72 | 0 | 0 | 0 |
| q2 | 5280 | 0 | 166 | 0 |
| attack | 2880 | 0 | 58 | 0 |
| boundary | 2400 | 0 | 32 | 0 |
| workers24 | 5 | 0 | 0 | 0 |
| workers_h1_uncaptioned | 1 | 0 | 0 | 0 |
| veto | 1260 | 0 | 26 | 0 |
| h1_review | 2160 | 0 | 0 | 0 |
| h1 | 2160 | 0 | 0 | 0 |
| workers25 | 8 | 0 | 0 | 0 |
| q3b | 2916 | 0 | 0 | 0 |
| ordinary_ndas | 216 | 0 | 0 | 0 |
| q3a | 4536 | 0 | 0 | 0 |
| q3b_aligned | 2430 | 0 | 0 | 0 |
| exact_q3b | 2430 | 0 | 0 | 0 |
| exhibits | 576 | 0 | 0 | 0 |
| three_party | 36 | 0 | 6 | 0 |
| workers26 | 10 | 0 | 0 | 0 |
| exact_q3c | 2808 | 0 | 10 | 0 |
| exact_q3a | 4536 | 0 | 0 | 0 |

### Preservation and blockers

SHA-256 verification before this required report append: **2,781/2,781 pre-existing files other than placement.py unchanged**, including both uncommitted r26 test files, all earlier tests, fixtures, evidence, and `.done` markers. The report receives only this appended section. All 50,474 pre-existing r26 test IDs and all 47,655 live test IDs remain; the only r26b test-tree addition is `test_placement_r26b.py` with 24 IDs, unchanged since its failing-first run. The r26 additions remain byte-identical. [Preservation audit](r26b/preservation-summary.json), [final append verification](r26b/final-preservation.json).

**Blockers: none.** No earlier tests, fixtures or evidence were edited. No migration, configuration, memory, staging or commit change.
