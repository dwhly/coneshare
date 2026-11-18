# C2a r25 results

**Structural guard implemented as `c2a.25`; no commit.** **coder rc=1** solely because the exact review Q3 matrices are unavailable; all executed release checks below pass. The broader reconstructed measurements must not be described as the exact 6,318 review cells.

Base HEAD `9a91a4b99d0df4d913780914379bf7e0fa374e1d`; shipped source SHA-256 `8988fe1a399c903aeb0c9794c810d2dcb66995beb663ddb89a690e71c179d7a5`.

## What shipped

Before redaction, `prepare_blocks` records whether another page contains a non-witness signing block that no provided signer scores positively. Only after the original assignment and validation succeed, a company/domain-only assignment (score 4) landing across that unresolved page boundary becomes a hold. Printed-name assignments keep their path. Every provided signer, including a supplied sender, participates in accounting for blocks. If the sender is omitted, its identity cannot be distinguished from another unclaimed party without extra input, so separated pages conservatively hold; that cost is measured below. Existing r24 scoring/role guards remain in force. The new guard adds no vocabulary.

Scores and assignment margins are unchanged. Applying the guard only to an otherwise valid placement makes it a hold-only change by construction. A discarded candidate zeroed company scores before assignment and produced eight hold → correct-placement transitions in Q3a. It was rejected; all eight remain holds under the shipped implementation. Its partial suite and replay logs are retained, and are not release evidence. [Tie check](final-tie-preservation.json), [discarded Q3a](v1/q3a-summary.json).

## Failing first and tests

**422 failed / 7,047 passed on unchanged c2a.24** across the final new tests: 248 Q3a failures, 166 in the broader Q3b matrix, seven worker failures, and one cross-page ownership boundary. The first draft of the new boundary fixture accidentally overprinted a Name placeholder; its original log is retained separately, and the corrected new fixture was rerun on c2a.24 before the fix. No pre-existing test or fixture was edited. [Initial matrix run](failing-first.txt), [final boundary baseline](failing-first-boundaries-final.txt).

**Full Send suite: 47,655 passed, 0 failed, 0 errors, 0 skipped**, completed without `-x` or test selection. All 40,186 existing test IDs remain; 7,469 new IDs come from two added test-tree files. All 40 r19 identity-before-veto score cells pass, including the 20 cross-page cells. [Full log](final-full-suite.txt), [JUnit](final-full-suite.xml), [command/hashes](run-provenance.json).

## Candidate and final comparison

Columns count raw wrong placements. The only remaining raw flags belong to the explicitly accepted historical classes, and each remaining output equals r21 except analysis_version. Of the original 258 accepted flags (48 M-1 plus 210 historical), 104 now hold; 154 remain: 16 M-1 and 138 historical flags. Both r21 and r24 are freshly executed and match their archived complete outputs in every retained family. All new cases use zero model calls; historical golden/control stubs retain their expected calls. External HTTP calls are zero. Real workers parse independently and match in-process results.

| Collection | Cells | r21 wrong | r24 wrong | cand4 wrong | r25 wrong | r24 correct → hold | r21 correct → hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| historical | 17,204 | 0 | 0 | 0 | 0 | 0 | 0 |
| review | 12,760 | 102 | 102 | 102 | 102 | 0 | 0 |
| layouts | 5,680 | 0 | 0 | 0 | 0 | 37 | 102 |
| wrapped | 5,280 | 0 | 0 | 0 | 0 | 35 | 85 |
| new | 420 | 24 | 0 | 0 | 0 | 0 | 0 |
| stress | 2,706 | 288 | 156 | 156 | 52 | 32 | 90 |
| q2 | 5,280 | 48 | 0 | 0 | 0 | 350 | 514 |
| extra | 1,680 | 0 | 0 | 0 | 0 | 130 | 162 |
| workers | 72 | 6 | 0 | 0 | 0 | 4 | 16 |
| attack | 2,880 | 0 | 0 | 0 | 0 | 116 | 262 |
| boundary | 2,400 | 24 | 0 | 0 | 0 | 54 | 74 |
| h1_review | 2,160 | 96 | 0 | 0 | 0 | 396 | 624 |
| veto | 1,260 | 0 | 0 | 0 | 0 | 52 | 118 |
| workers24 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| workers_h1_uncaptioned | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| h1 | 2,160 | 90 | 0 | 0 | 0 | 396 | 624 |
| q3a | 4,536 | 292 | 248 | 152 | 0 | 354 | 374 |
| q3b | 2,916 | 178 | 166 | 128 | 0 | 298 | 482 |
| workers25 | 8 | 7 | 7 | 5 | 0 | 0 | 0 |
| q3b_aligned | 2,430 | 104 | 96 | 70 | 0 | 292 | 478 |
| ordinary_ndas | 216 | 0 | 0 | 0 | 0 | 28 | 28 |

**72,054 measured cells; 940 real-worker evaluations.** `n → p = 0` and `c → w = 0` against both c2a.24 and r21 in every measured family. Seven goldens and native fields are exact except analysis_version, in-process and on workers. [Per-family counts](family-comparison.json), [comparisons](vs-live.json).

## Ordinary two-party NDA hold cost

The Q3b reconstruction uses five affiliate layouts: one without an affiliate and before/after for each of two affiliate captions. The separate ordinary-NDA measurement also tests split and reversed signature pages; no affiliate is present.

| Ordinary subset | Cells | r24 correct | r24 holds | r25 correct | r25 holds | New holds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q3b reconstructed, same page | 486 | 311 | 175 | 311 | 175 | 0 |
| Ordinary NDA same domain | 24 | 19 | 5 | 19 | 5 | 0 |
| Ordinary NDA split domain | 24 | 19 | 5 | 12 | 12 | 7 |
| Ordinary NDA reverse domain | 24 | 19 | 5 | 12 | 12 | 7 |
| Ordinary NDA same explicit | 24 | 19 | 5 | 19 | 5 | 0 |
| Ordinary NDA split explicit | 24 | 19 | 5 | 12 | 12 | 7 |
| Ordinary NDA reverse explicit | 24 | 19 | 5 | 12 | 12 | 7 |
| Ordinary NDA same both | 24 | 14 | 10 | 14 | 10 | 0 |
| Ordinary NDA split both | 24 | 14 | 10 | 14 | 10 | 0 |
| Ordinary NDA reverse both | 24 | 14 | 10 | 14 | 10 | 0 |

The review itself reports 322 correct / 164 holds among its 486 ordinary cells. That exact split is not asserted for the reconstructed role-pair list. [Ordinary inputs](ordinary_ndas.py), [Q3b reconstruction](review_q3b.py).

## Preservation and remaining limitation

**2,441/2,441 other originally tracked files are SHA-256 identical** to the session-start inventory. This includes every earlier test, fixture, evidence file and `.done` marker. Only `backend/dealroom_sign/placement.py` changed among pre-existing files. No staging, commits, migration/config changes or project-memory writes. [Audit](preservation-summary.json).

The exact review Q3a/Q3b stdin generators were not supplied. Every stated Q3a shape is covered (4,536 cells; r24 248 wrong and cand4 152, matching the review), but its reported 3,888-cell selection is unspecified. Q3b's nine role pairs are not enumerated; the explicit 2,430-cell reconstruction is independently measured, not certified as the exact review input set.

The review prose describes 12 role headings with/without a company, four named headings with/without `RECIPIENT:`, and five captions with/without a company: 42 × 108 = 4,536 Q3a cells. The complete written axes reproduce its 248 r24 wrong / 152 cand4 wrong cells; r25 is zero. The Q3b role pairs are explicit in the new generator, and its 2,430-cell aligned reconstruction and 2,916-cell broader test matrix both have zero r25 wrong placements. The exact generator was requested during work; absent that input, the literal exact-matrix certification remains blocked. [Release bars](release-bars.json).

Reproduce the full suite with the command in `run-provenance.json`. Replay all retained families using `replay25.py all <fresh-output-directory> structural-source.py.txt`; existing evidence is opened exclusively and is never overwritten.
