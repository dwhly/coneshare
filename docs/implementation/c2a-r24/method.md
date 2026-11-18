# r24 execution method

Base HEAD: `e2bbb7587f7ef100e1fb82fea825000ba6eac705`; live r21:
`afb9aa6e`. No staging, commits, migration commands, or memory writes.

The requested r23 review was read from its explicitly supplied path. Its scratch
harness was deleted according to the review. Historical generators, oracles,
fixtures, reports and markers remain unchanged. `starting-hashes.json` covers
all 2,245 initially tracked files. The final audit permits only `placement.py`
and the exact authorised `b1_three` expectation substitution.

## Inputs and failing first

`placement_r24_review_cases.py` adds the five B-1 descriptions and four B-2 names
through the existing `placement_r23_review_cases.matrix`. Each recital has 240
cells. The B-1 and B-2 cohorts reproduce exactly 120 and 42 r23 wrong cells.
Twelve attack recitals plus the seven unchanged r23 supplements total 4,560
cells. Ten boundary recitals add 2,400. The two boundary fixture artefacts named
by the reviewer are retained, with their raw geometry flags visible.

H-1 is an explicit reconstruction: four existing recital forms × five own-block
forms × two affiliate-page positions × three affiliate names × three captions ×
two extra-row forms × three signer sets = 2,160 cells. The alias-veto reconstruction
has three recitals × two Discloser headings × five own-block forms × seven repeated
block placements × two extra-row forms × three signer sets = 1,260 cells.
These are not represented as byte-identical copies of the deleted reviewer harness.
The H-1 reconstruction measures 90 r21 wrong / 54 r23 wrong, rather than the review's
96 / 60; both reproduce the 36-cell alias-veto improvement and the 228-cell cand3
hold cost. The veto reconstruction also has different aggregate hold counts.

The two B-1/B-2 worker reproductions use the literal review rows, each with PAT and
DAN+PAT. The literal H-1 worker reproduction is retained too. It holds on the
unchanged source because its `GUARANTOR:` caption is unaccounted. A separate
uncaptioned affiliate worker case reproduces the reported wrong-page mechanism.
No existing input was changed to obtain the latter result.

Three failing-first runs precede production changes: the initial 7,445 checks,
the additional 1,260 alias-veto checks, and the separate uncaptioned H-1 worker.
Together they record 239 failed / 8,467 passed on unchanged r23. The initial
recital failures include 162 blocking cells and 18 boundary fixture flags.
Source equality is recorded in `baseline-source.json` and
`failing-first-summary.json`.

## Candidates and comparison

`candidate_sources.py` extracts r21's entire ROLE_DESCRIPTION assignment using
its AST source span, changing only the variable name to ROLE_DESCRIPTION_WIDE.
Both description grammars contribute to the unchanged M-2 conflict guard.
The five measured sources are r21, r23, exact reviewer cand, cand3 (the page
filter removed), and cand with the conditional cross-page competitor (r24).
All five source snapshots and SHA-256 hashes are retained.

The conditional guard applies only to company/domain-only scores. Matching
headings on other pages compete when any block's raw labels contain a party role
that `accounted_label` cannot account for. Printed-name scoring retains its path.
The existing article-prefixed alias veto remains in place.

`measure.py` imports the earlier generators without edits and validates every
r21/r23 result and the complete case inventory against the r23 archives. It also
runs Q2, supplements, the added recitals, H-1, veto and worker cases. All candidate
variants parse and score actual generated PDFs. To avoid repeating identical PDF
parsing, cand/cand3/r24 share a cached pristine extraction (their extraction code
and grammars are identical); each scorer receives its own deep copy. Independent
worker subprocesses always parse independently and must equal in-process output.

Every result has its own digest, case identifier, PDF hash, raw wrong flag and
historical classified wrong flag. The runner records all five-state transitions,
including holds that become any placement, correct placements that become wrong,
and additional holds relative to cand. It records raw flags separately from the
immutable historical Competition and Q4 classifications; none is silently erased.
The stress collection uses raw geometry throughout, including NORTHWIND and M-1.

Seven r13 goldens are checked exactly except analysis_version, with native fields
and real-worker equality. HTTP is patched to raise, OPENROUTER_API_KEY and
PLACE_MODEL are removed, and bytecode writes are disabled. Only existing expected
mock-model calls in old controls are allowed; new cases require zero model calls.
Temporary workers and test databases are confined to this r24 directory and removed
on normal process completion.

## Commands

Interpreter: `/root/work/sign-product/send-venv/bin/python` (`PY` below), with
`PYTHONDONTWRITEBYTECODE=1`. Commands run from the repository root.

```sh
PY docs/implementation/c2a-r24/run_tests.py dealroom_sign/tests/test_placement_r24.py --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r24/failing-first.xml
PY docs/implementation/c2a-r24/run_tests.py dealroom_sign/tests/test_placement_r24.py -k alias_veto --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r24/veto-failing-first.xml
PY docs/implementation/c2a-r24/run_tests.py dealroom_sign/tests/test_placement_r24.py -k uncaptioned_cross_page --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r24/h1-worker-failing-first.xml
PY docs/implementation/c2a-r24/measure.py h1
PY docs/implementation/c2a-r24/run_measures.py
PY docs/implementation/c2a-r24/measure.py workers_h1_uncaptioned
PY docs/implementation/c2a-r24/run_tests.py dealroom_sign/tests --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r24/full-suite.xml
```

The complete suite is all `dealroom_sign/tests`, the established Send suite from
r23. It has no `-x`, selection filters, skipped tests or deselection options.
An initial evidence-run module-name collision is retained in `h1-replay.txt`;
the successful retry is `h1-replay-retry.txt`. It affected no product or test input.

## Primary H-1 reconstruction and final fallback

The initial H-1 matrix above is retained unchanged as diagnostic evidence. A
separate `review_h1.py` reconstruction uses title-case `Recipient` above HLA as
the fifth own-block form. This explains the six-cell gap: that block's company
heading makes it a named competitor even when the role is unresolved. The new
2,160-cell set reproduces all reviewer totals: r21 96 wrong; r23 60 wrong,
1,398 correct, 702 holds; cand3 and narrow each zero wrong, with 228 additional
holds. `h1_review-*.json` is the primary H-1 evidence. Its frozen r23 execution
also reproduces the six title-case failures missing from the initial pytest
matrix. Nothing changes or retargets that initial test matrix or its evidence.

Both candidates retain 210 pre-existing raw-coordinate flags beyond M-1:
96 Competition, six Q4, and 108 NORTHWIND stress flags. The earlier harness
permits or separately discloses those cases. The task's literal M-1-only bar
does not grant those additional exceptions. Consequently the narrow candidate
cannot be certified as zero wrong everywhere under that reading, and the
requested cand3 fallback is selected. It also retains the old flags, so the
completion marker must be nonzero. Both sets of measurements remain available.

`run_fallback_suite.py` copies the entire Send package and every test/fixture into
a temporary repository-shaped directory under r24. Other repository entries
are linked for reads. Test/fixture copies are hash-checked before execution.
The only copied production change is exact cand3 with VERSION c2a.24. The full
suite runs independently, without `-x` or filters, using its own temporary
database. Its provenance records the tested source hash, all copied test hashes,
return code and removal of the scratch directory. The earlier narrow suite is
also allowed to finish; production is switched only after it completes, avoiding
mixed worker sources during a test run.

Original measurements use `r24` as the narrow-candidate key and `cand3` for the
fallback. Those per-cell JSON files and source snapshots are never overwritten.
The final report and `family-comparison.json` map final r24 to cand3 explicitly,
retaining the narrow results under `narrow`. `final-source-mapping.json` proves
that measured cand3 and final production differ only in VERSION.

Additional commands:

```sh
PY docs/implementation/c2a-r24/measure.py h1_review
PY docs/implementation/c2a-r24/run_fallback_suite.py
PY docs/implementation/c2a-r24/audit_report.py
```

## Full-suite conflict discovered at completion

The narrow suite completed with 39,802 passed / 384 failed / zero errors / zero
skips. All 8,706 new tests pass. Every failure is an unchanged r22
`test_recital_precedence_matrix` parameter, which requires the Recipient role
value to contain HLA. The exact requested cand supplies both HLA (bounded) and
Fleet (r21 wide) for that recital, so the unchanged M-2 guard must return the
role word `Recipient`. `immutable-test-conflict.json` records the exact grammar
matches and failing assertion. The authorised r23 `b1_three` exception does not
cover this r22 assertion. The fallback suite is also allowed to finish; its
final counts, including this incompatible assertion, are reported without skips
or test changes.

The broad fallback also conflicts with the 20 cross-page r19 controls that
explicitly require score 4; removing the page filter correctly returns 0 there.
`check_page_assertions.py` executes the original test function and its original
40 parameter combinations against each measured source, without changing its
assertion or inputs. r21/r23/cand/narrow pass all 40; cand3 passes 20 and fails
the 20 cross-page controls. `fallback-test-conflict.json` preserves those results.
