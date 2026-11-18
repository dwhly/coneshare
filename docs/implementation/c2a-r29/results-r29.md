# C2a r29 results

**coder rc=0.** `VERSION = 'c2a.29'`. Base HEAD `3e3f33de3f06742b13b4d8a85c7cbf48e7538598`. Final source SHA-256 `866637df797137e74b748c85a644629edda206544a6bc8a3b685e31f1c29bae6`. Changes remain unstaged and uncommitted. [Release checks](release-bars.json), [tested source](release-source.py.txt), [baseline provenance](source-provenance.json).

## Shipped

A hold-only guard prevents printed-name borrowing across a separate column, a different party heading, an intervening party heading, or a completed Date stack. Legal company headings and recital-mapped roles both bound ownership. The guard checks rows that the existing scorer would attribute to that column, after stacked-block partitioning.

An unresolved borrowed name also vetoes company-only placements on its page, preventing an affiliate from bypassing the hold after a mixed-company sender block loses its score. Names outside every rule column remain unresolved even when they lie outside every host's text band. Other independently named blocks retain their existing policy.

The strict rule-span variant broke live controls. The measured narrower implementation preserves the established signing group: Name/Signature cells on the rule's own caption row, and a bare name extending up to 24 points left of a `Signature:` caption. Separately captioned `Name:` rows receive no outdent allowance; the new 24 close-edge tests cover both sides, By/Signature captions, and domain/explicit-company signers. The six explicitly exempt contact captions remain exempt in their own local group, provided no party heading intervenes. A Name immediately following Date retains the existing 22-point companion band; more distant names are separated by Date. These constraints preserve all live controls while closing every required H-1 cell.

Original identity scores, competition, assignment, margins, model eligibility, geometry and validation are unchanged. New metadata is read only by an added hold branch after otherwise successful acceptance and validation. It cannot turn a live hold into a placement or move an existing placement. Keeping identity evidence as competition preserves immutable r13 L-2. [Structural audit](release-hold-only-proof.json).

## Exact generators and failing first

Extracted **45 Bash command inputs and 37 Python heredoc bodies byte-for-byte** from the specified Gate 3 r28 transcript into `backend/dealroom_sign/tests/fixtures/r29/`. Capture adapters execute the exact loop bodies and PDF drawing functions. [Provenance](extraction-provenance.json), [verification](extraction-verification.json).

| Failing-first run | Failed | Passed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| H-1 matrices + six workers, untouched c2a.28 | 680 | 2,656 | 0 | 0 |
| Additional exact hidden-shape family, initial H-1 candidate | 60 | 948 | 0 | 0 |
| Close-edge separate Name rows, untouched c2a.28 | 24 | 0 | 0 | 0 |

The first row comprises 84 conformed, 288 no-rule, 256 geometry, 48 ruleless-name and four worker failures. [H-1 log](failing-first.txt), [hidden-family log](hidden-failing-first-final.txt), [close-edge log](columns-failing-first.txt).

Two review-prose counts differ from the exact transcript: call 41 generates **810 ruleless-name cells**, not 540; call 34 reproduces **288 wrong no-rule cells**, not 282. All cells are retained. The 48 ruleless-name wrong placements reproduce the reported 32 + 16 split. Other H-1 matrix sizes are exactly 144, 648 and 1,728.

The wider call-32 generator additionally exposes 60 pre-existing wrong placements in `two_col_rows`: its heading/name rows move to x=320, but its five-element uncaptioned-rule tuple stays at x=72. It differs from call 33's correctly moved rules. All 1,008 call-32 cells now have 0 wrong. No source fixture was corrected or retargeted.

The new hidden-test draft initially had incorrect Mock-call expectations, adding 60 assertion failures. Its source/log are preserved; the final expectations assert the exact measured 36 calls for uppercase own-page headings. The final hidden assertions were frozen before the fix. No pre-existing test was changed. [Draft](hidden-draft-test.py.txt), [draft output](hidden-failing-first.txt).

## Variant measurements and live controls

Wrong placements under the unchanged raw geometry oracle:

| Matrix | Cells | c2a.28 | Column + heading suggestion | Plus Date boundary, selected block only | Shipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| conformed | 144 | 84 | 72 | 12 | 0 |
| no_rule | 648 | 288 | 228 | 48 | 0 |
| geometry | 1728 | 256 | 48 | 0 | 0 |
| ruleless_name | 810 | 48 | 32 | 0 | 0 |

The selected-block-only variant leaves company-only affiliate placements; the final page-local company-only veto closes them. The outside-all-columns guard closes the extra 60 call-32 cells. Every measured variant comparison records zero `n → p` and `c → w`; incomplete variants did not ship. [Suggestion](suggested-source.py.txt), [Date variant](bounded-source.py.txt), [final source](release-source.py.txt).

The broad guard's full-suite attempt exposed valid inline/contact controls. A separate unchanged 13,334-test control sweep identified 13 remaining compatibility failures (six margin controls, six rule-row controls and one Name-after-Date control). All are fixed without changing their tests. The 316 r4/r10/r11 source comparisons are exact against c2a.28, and the final focused run of the 13 failed controls plus all 24 close-edge cases is **37 passed / 0 failed / 0 errors / 0 skipped**. Every control also passes in the final full suite. [Control sweep](live-controls.txt), [316 comparisons](narrow3-legacy-controls.json), [final focused run](corrected-controls.txt).

## Required families and baseline comparisons

**82,450 inherited cells across 27 collections: 0 raw wrong in every collection.** The final candidate executes every cell. Historical comparison outputs come from the immutable c2a.28 replay archive; all three baseline sources match their git commits, archive source hashes match, and archived case keys/results are preserved. Fresh reviewer families independently execute c2a.28, c2a.27, r21 and the final candidate. Candidate real workers reparse their PDFs and agree with in-process results. The seven goldens and native-field conversions are exact except `analysis_version`.

The exact r27 700-cell matrix has 700 holds and 0 wrong. All four H-1 matrices, all additional hidden shapes and all six new real-worker reproductions have 0 wrong. The new worker runs make no model or HTTP calls.

| Cohort | Baseline | n → p | c → w | Correct → hold | Raw flagged → hold |
| --- | --- | ---: | ---: | ---: | ---: |
| Inherited | r21 | 0 | 0 | 7336 | 1908 |
| Inherited | r27 | 0 | 0 | 1 | 0 |
| Inherited | r28 | 0 | 0 | 1 | 0 |
| Review / supplementary | r21 | 0 | 0 | 2822 | 2909 |
| Review / supplementary | r27 | 0 | 0 | 188 | 1524 |
| Review / supplementary | r28 | 0 | 0 | 8 | 1084 |

[Comparison totals](vs-live.json), [inherited details](family-comparison.json), [fresh-family details](new-family-comparison.json). Collections overlap and are not deduplicated.

| Inherited family | Cells | r29 raw wrong | Added correct holds vs c2a.28 |
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
| historical | 17,204 | 0 | 1 |
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

| Review/supplementary family | Cells | Wrong in required scope | Raw geometry flags | Added correct holds vs c2a.28 |
| --- | ---: | ---: | ---: | ---: |
| conformed | 144 | 0 | 0 | 0 |
| extended | 560 | 0 | 0 | 0 |
| geometry | 1,728 | 0 | 0 | 0 |
| hidden | 1,008 | 0 | 0 | 0 |
| no_rule | 648 | 0 | 0 | 0 |
| notices | 14,112 | 0 | 94 | 0 |
| ordinary | 300 | 0 | 0 | 0 |
| r27 | 4,461 | 0 | 206 | 0 |
| recitals | 3,354 | 0 | 120 | 0 |
| ruleless_name | 810 | 0 | 0 | 8 |
| stacks | 5,376 | 0 | 444 | 0 |
| two_columns | 288 | 0 | 0 | 0 |
| variants | 700 | 0 | 0 | 0 |
| workers | 6 | 0 | 0 | 0 |

Retained raw flags are the reviewer's named-party and immutable L-2 policy controls. Every remaining flagged output is identical to c2a.28 except `analysis_version`; no new or moved placement is excused. The four H-1 matrices, hidden shapes, r27 700 and all inherited families have **0 raw wrong**.

## Hold cost, lows and nits

Ordinary two-party added holds versus c2a.28 and c2a.27: **0**, including the ordinary NDA/MSA cohorts, 576 exhibit controls and all 300 exact reviewer ordinary cells. The ruleless-name stress cohort adds eight correct-to-hold transitions: a second Pat name below Fleet's Date while Fleet prints Dan and Pat has a real line in the right column. There is also one added inherited hold in the r3 inserted-person `roles` fixture. These are separately reported, not counted as ordinary hold cost. [Ordinary cost](ordinary-hold-cost.json).

**L-1 retained:** the exact 14,112-cell notice/cc/person-row matrix reproduces 180 c2a.27 → c2a.28 correct-to-hold transitions. Restoring any would create prohibited `n → p` against live c2a.28. No relaxation ships. Named-Pat policy controls remain separately visible.

**L-2 retained:** earlier misspelt-recital and table-row exhibit hold costs remain. Immutable r13 L-2 remains **20/20 placements at y=560/600 with score=4 and margin=4, plus 20/20 both-signer holds**.

**N-1:** git HEAD/status and SHA-256 checks were available. **N-2/N-3:** comments document that peers attach only to hosts on their own page and that the 60-point fallback also covers a name with no tail. Runtime peer behavior is unchanged. HTTP calls are zero in all comparisons; synthetic Mock calls are explicit in each summary and match c2a.28 for the final candidate.

## Full suite and preservation

**58,058 passed / 0 failed / 0 errors / 0 skipped.** The full Send suite completed without `-x`, retries or skip filters. Four isolated pytest processes cover every one of the 58,058 collected IDs exactly once, with independent scratch SQLite databases. The runner checks the final source hash before and after execution. All **53,690 prior test IDs** are preserved. [Complete log](full-suite-complete.txt), [JUnit](full-suite-complete.xml), [partition manifest](full-suite-manifest.json), [completion ledger](full-suite-completion.json).

Command: `PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r29/run_full_suite.py`. Each process uses the existing isolated Send environment through `run_tests.py`.

Four new Python test-tree files (one capture adapter and three regression files) add **4,368 tests**, plus exact source fixtures. Final assertions and fixtures match their failing-first hashes. **3,566/3,566 pre-existing tracked files other than placement.py are unchanged**, including every old test, fixture, evidence file and `.done` marker. Every new evidence file is below 20 MB. [Preservation audit](preservation-summary.json).

Exploratory full/replay runs were stopped when a wider family or live control showed that the candidate needed revision; their partial logs and stop records remain. Final complete runs use only `release-source.py.txt`. The first measurement harness had an indentation error, and its initial real-worker adapter lacked an oracle for the baseline's fields; both original errors remain. The final worker oracle treats any emitted field as wrong, matching the required hold. No test was skipped, weakened, deleted or retargeted to obtain the release result.

**Blockers: none.** No staging, commit, deployment, migration, configuration or project-memory change.
