# r23 execution method

Base: `e2d7ba11e138da4f67fbb5562507985f19bde7f5` (`c2a.22`).
Read the explicitly requested Gate 3 r22 review and project memory first.
No staging, commits, migrations or memory writes.

## Preserved inputs

`starting-hashes.json` records every one of the 2,140 starting tracked files.
Only `backend/dealroom_sign/placement.py` may change. The final audit verifies
all remaining hashes, including every earlier test, fixture, implementation
report and completion marker. New regression inputs are repository files;
nothing imports from `/tmp`.

The review's stdin Q2 generator was not preserved. The new test helper explicitly
reconstructs its 22 recitals and 5,280-cell axes: 3 layouts × 4 headings ×
5 affiliate/caption states × 2 extras × 2 signer sets per recital. There are
four affiliate/caption combinations plus one no-affiliate state, avoiding duplicate
caption-on/off cells for an absent block. Names containing conjunctions have
matching signer domains and affiliated company names. The two inline real-worker
reproductions are copied verbatim and expanded to 72 worker cases.

An initial supplemental-fixture draft accidentally retained Harbor Light identity
for the Johnson/Procter recitals. The final new fixtures correct this construction
error; `supplement-failing-first.*` executes all 1,680 final supplemental inputs
on unchanged r22. Original repository tests and fixtures are untouched. The draft
log is retained, and the report uses final-input counts for this supplement.

## Failing first and production changes

`q2-baseline-discovery.*` records exactly 42 B-1 and 24 B-2 wrong cells on unchanged
r22. `baseline-placement.py.txt` and `baseline-source.json` attest the tested
production source. `failing-first.*` records the Q2 tests, real-worker regressions,
role mapping assertions and draft supplement. The final supplement's separate
baseline has 12 failures and 1,668 passes. Combining final-input families gives
126 failed and 6,912 passed (66 Q2, 42 worker, six mapping, 12 supplement
failures), before any production edit.

`apply_candidate.py` applied the review's measured completed-designation boundary
to both name and description groups, removed direct ROLE_DEF span suppression,
and bumped the version. M-2's conflict assignment is unchanged.

The exact candidate left six failing worker tests: explicit-company Pat with
THE RECIPIENT, across both signer sets and all three layouts. `focused.*` records
those failures. Extraction retains THE RECIPIENT in local raw labels while the
block heading is empty. The final additional veto consults those local labels:
an unresolved article-prefixed role whose recital company matches the signer
prevents company-only confidence on another block. This applies across pages,
including explicit-company signers, and does not grant confidence or change
printed-name assignment. `focused-alias.*` records an insufficient heading-only
attempt; `focused-final.*` passes all 80 selected worker/mapping checks.

An early candidate replay was interrupted after these six failures were found.
Its logs/source snapshots are retained with `candidate-` names and are not final
release evidence. `candidate-scratch-cleanup.json` records removed temporary
packages. The final full suite starts only after the additional veto is fixed.

## Family replay and isolation

`replay.py` reuses the unchanged r21/r22 generators and geometry oracles. It loads
exact r21 (`git show afb9aa6e`), exact r22 (`git show e2d7ba11`), and final r23 in
independent modules and temporary worker packages confined to this evidence
directory. Every baseline result and full case inventory must match the archived
r21/r22 evidence. The candidate's new veto is therefore tested against the same
family inventory as the parser changes.

The replay includes historical, review, literal-layout, wrapped-layout, r22
conflict/description, and supplemental stress families. Competition and Q4 keep
the prior review classifications; raw flags are separately retained. Q2,
supplements and worker tests use the unchanged raw page/column/By–Date oracle
without exceptions. M-1's misspelling family and the reviewer-approved NORTHWIND
shapes remain explicitly visible in the stress measurements.

The test runner and final replay processes clear OPENROUTER_API_KEY and
PLACE_MODEL, disable bytecode output, and patch external HTTP to raise. The
initial Q2 discovery also disables bytecode and blocks HTTP, while supplying an
explicit mock model client. Each model-call count must match the existing
expected mocked calls. Q2 and new worker cases require zero model calls. Seven
goldens are compared with r13 except analysis_version, including native fields
and real-worker equality.

## Commands

Run from the repository root. `PY` below denotes
`/root/work/sign-product/send-venv/bin/python`; set `PYTHONDONTWRITEBYTECODE=1`.

```sh
PY docs/implementation/c2a-r23/measure_q2_baseline.py
PY docs/implementation/c2a-r23/run_tests.py dealroom_sign/tests/test_placement_r23.py --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r23/failing-first.xml
PY docs/implementation/c2a-r23/run_tests.py dealroom_sign/tests/test_placement_r23.py -k additional --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r23/supplement-failing-first.xml
PY docs/implementation/c2a-r23/run_tests.py dealroom_sign/tests --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r23/full-suite.xml
PY docs/implementation/c2a-r23/run_replays.py
PY docs/implementation/c2a-r23/audit_report.py
```

The complete suite is all `dealroom_sign/tests`, matching the established r22
scope. It runs without `-x`, selection, deselection or skip additions. The runner
creates a temporary scratch database using the existing Send test environment.
Three independent replay processes run alongside the full suite; each output and
return code is retained. Final report and completion marker are written only
after completed-suite, family and preservation audits.
