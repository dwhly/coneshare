# C2a r15 candidate results

**STOP: the chosen candidate failed an existing r10 control in the required
full suite (802 passed, 1 failed). This is a completed comparison, not a
successful delivery. See [STOP.md](STOP.md). No further fix was attempted.**

Selected **(c), column ownership**, with `VERSION = c2a.15`. All three candidates achieve zero wrong placements in every family and exact goldens except `analysis_version`. Candidate (c) is the smallest source change (four added lines in `printed_names`, plus version), preserves every correct placement, and restores 1,352 correct placements from r14 holds. No generalised veto is needed.

See [method](method.md), [executable comparison](check_evidence.py), [summary](counterfactual-summary.json), [all case outcomes](counterfactual-cases.json), [all differences](counterfactual-differences.json), [worker results](counterfactual-workers.json), and [field geometry audit](geometry-audit.json).

Each cell is **wrong / placed / holds**. Wrong is included in placed. The seven goldens also include one `bare` result for every source. L-1 is a separately displayed subset of GRID, not additional unique layouts.

| Family | Cases | r14 | (c) | (b′) | (c)+(b′) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Matrix 1 | 120 | 0 / 0 / 120 | 0 / 0 / 120 | 0 / 0 / 120 | 0 / 0 / 120 |
| Matrix 2 | 270 | 0 / 0 / 270 | 0 / 0 / 270 | 0 / 0 / 270 | 0 / 0 / 270 |
| r11 B-1 | 1020 | 0 / 0 / 1020 | 0 / 0 / 1020 | 0 / 0 / 1020 | 0 / 0 / 1020 |
| Signature controls | 204 | 0 / 6 / 198 | 0 / 6 / 198 | 0 / 6 / 198 | 0 / 6 / 198 |
| M-1 | 16 | 0 / 16 / 0 | 0 / 16 / 0 | 0 / 16 / 0 | 0 / 16 / 0 |
| r9 heading matrix | 72 | 0 / 6 / 66 | 0 / 6 / 66 | 0 / 6 / 66 | 0 / 6 / 66 |
| r9 H-1 | 40 | 0 / 0 / 40 | 0 / 0 / 40 | 0 / 0 / 40 | 0 / 0 / 40 |
| Seven goldens | 7 | 0 / 6 / 0 | 0 / 6 / 0 | 0 / 6 / 0 | 0 / 6 / 0 |
| Same-band right host | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| r12 B-1 reproduction | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| r13 same-band grid | 42 | 0 / 0 / 42 | 0 / 0 / 42 | 0 / 0 / 42 | 0 / 0 / 42 |
| r12 B-1 sweep | 864 | 0 / 0 / 864 | 0 / 0 / 864 | 0 / 0 / 864 | 0 / 0 / 864 |
| L-1 short-rule controls | 2 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 |
| L-2 own-company controls | 40 | 0 / 20 / 20 | 0 / 20 / 20 | 0 / 20 / 20 | 0 / 20 / 20 |
| r14 reproduction | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| r14 grid | 3456 | 0 / 1200 / 2256 | 0 / 2436 / 1020 | 0 / 1176 / 2280 | 0 / 1176 / 2280 |
| r14 fixed sweep | 360 | 0 / 128 / 232 | 0 / 244 / 116 | 0 / 128 / 232 | 0 / 128 / 232 |
| r14 correct controls | 2 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 0 / 2 |
| r14 L-1 (grid subset) | 72 | 0 / 0 / 72 | 0 / 0 / 72 | 0 / 0 / 72 | 0 / 0 / 72 |
| r15 M1 reproduction | 2 | 1 / 1 / 1 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| r15 M2 reproduction | 2 | 1 / 1 / 1 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| r15 M1 | 640 | 100 / 100 / 540 | 0 / 0 / 640 | 0 / 0 / 640 | 0 / 0 / 640 |
| r15 M2 | 2592 | 432 / 432 / 2160 | 0 / 0 / 2592 | 0 / 0 / 2592 | 0 / 0 / 2592 |

9,754 unique cases × four sources = **39,016 unique source/case evaluations**. Including the separately enumerated L-1 subset: 39,304. Additionally, 56 real-worker evaluations (14 cases × four sources) exactly match their in-process outcomes. External HTTP/model calls: **0**. Only the `unusual` golden uses one local deterministic stub call per evaluation.

## Placement costs and realistic layouts

Relative to r14, candidate (c) loses **zero correct placements in every family**. It turns 534 wrong placements into holds: M1 100, M2 432, and one PAT-only case in each reproduction. All are ordinary two-column layouts: suffix-less company headings and a second person/initials row are realistic. Counting parameter/signers cases, that is 534 realistic wrong-to-hold cases; the two reproductions duplicate matrix geometry, leaving 532 distinct matrix cases. It restores 1,236 correct GRID placements and 116 correct FIXED placements. All 7,992 emitted fields in its 2,680 placed GRID/FIXED cases were checked against each signer’s expected signature/date/name column and rule.

Candidate (b′) also removes the same 534 wrong placements, but loses **24 correct GRID placements**. These are realistic though uncommon staggered columns: PAT-only, Dan typed on our lower side, `RECIPIENT:` or no counterparty heading, dy/gap pairs (80,60), (100,40), (100,60), both orientations and title settings. The other block’s conflicting Dan row zeroes Pat and propagates a veto despite Pat owning the counterparty column. All 24 are realistic layouts. No other family loses correct placements under (b′).

The combination loses the same 24 GRID placements and **two r14 correct controls**, for **26 realistic correct-to-hold cases**. The two controls are staggered blocks with an unambiguous HARBOR/Pat column and an unheaded other column. Column ownership makes the other block score Pat zero, which the generalised veto then propagates back to the correct block. No other family loses correct placements under the combination.

**Review L-1:** all three candidates retain the exact 72 r14 holds. None restores them. They are the same 72 realistic, uncommon layouts identified by the reviewer; this selection was independently compared against the archived r13-correct → r14-hold case set and matched exactly. Candidate (c) retains r14’s mixed-heading veto, so merely narrowing positive printed-name evidence does not remove that conservative hold. The earlier two L-1 short-rule controls remain placed with exact results.

## Result preservation details

The selected candidate preserves all earlier-family field/status outcomes. Full results are byte-equivalent except version for **2,511 / 2,699** earlier cases. The 188 differences are `Signature controls` holds: the status, reason, empty fields, and zero model-call count remain unchanged, while assignment diagnostics stop crediting non-overlapping names. All six placed `Signature controls` remain exact. Candidate (b′) preserves that entire 204-case family exactly; the combination has the same 188 hold-diagnostic changes as (c). These differences are disclosed rather than described as full-result preservation.

The r14 correct controls retain exact field geometry; their assignment margins change when an unowned competing name no longer scores. The seven goldens are exact in full except `analysis_version`, including native field projections. The r14 reproduction remains held. Both new reproductions hold for both signer sets with no fields and no model calls.

## Verification status

The required full suite is recorded separately in `full-suite.txt`, `full-suite.xml`, and `full-suite-summary.json` when complete. It runs through the exact supplied launcher, with `-x` to stop on any failure and JUnit output added for count evidence. The launcher prints a read-only `/root/.hermes/cache/scratch/sendlocal.XXXX` mktemp warning in this sandbox; pytest still starts. The final test outcome is reported explicitly rather than treating this warning as a successful scratch-directory creation. No launcher or existing test is changed.
