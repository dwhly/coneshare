# r22 execution method

Base HEAD is `afb9aa6e71a28f3989c9896e0318912a11572891` (`c2a.21`).
The project memory and the explicitly requested Gate 3 r21 review were read
before implementation. No staging, commits, migrations, or memory edits.

`starting-hashes.json` inventories all 2,070 starting tracked files. The only
permitted modification to that inventory is `backend/dealroom_sign/placement.py`.
All new tests and outputs live in new r22 files. Earlier tests, fixtures,
evidence scripts, results, and completion markers remain untouched.

## Failing first

The initial new test file ran on the unchanged production r21 source: 414 failed,
12 passed. This includes the verbatim two-page HLA + NORTHWIND worker reproduction
for PAT and DAN+PAT (2 failures), 36 affiliate/layout controls (24 wrong-placement
failures and 12 existing holds), all 384 L-1 mapping checks, two conjunction
boundary checks, and two repeated-definition controls.

A separate 36-cell grid varies three layouts, two Recipient spellings, three
neutral placeholder patterns, and both signer sets. All 36 fail on exact HEAD
r21, loaded by `baseline_plugin.py` with an isolated r21 worker. All 36 pass
on production r22. This is additional evidence, not a replacement of the first
36-cell control family or its recorded counts.

The first candidate passed 424/426 focused tests. The two remaining failures
showed regex backtracking could put the second party into the *company capture*
even after the description was bounded. The same conjunction boundary now
bounds both captures. The final focused run passes 426/426 unchanged assertions.

## Implementation

The conflict assignment is the reviewer's measured `conf` diff verbatim.
A conflicting mapping becomes the role word, leaving the existing domain-only
ambiguity rule to hold. Later repeated HLA/NORTHWIND definitions cannot clear it.

Direct-definition precedence is scoped to the same quoted-role occurrence
(`match.span(2)`). This covers both grammars reading the same sentence while
preserving independent definitions elsewhere in that sentence or page as
potential conflicts. Both the company capture and description stop before a
conjunction followed by a capitalised word, preventing regex backtracking from
swallowing the following company.

## Replay provenance and isolation

`replay.py` imports the preserved r21 harnesses only for their existing generators,
oracles, and module-loading helpers. All output and worker scratch is redirected
to this r22 directory. It executes exact HEAD r21 and production r22, verifies
every r21 result against the corresponding archived r21 result (versionless),
and requires exactly the same case inventory in each archive. It preserves the
existing Competition and Q4 classifications, with raw flags reported separately.
No earlier test or evidence source is edited or retargeted.

The new 384-cell L-1 sweep uses the review's documented axes: two recital layouts,
four headings, three signature layouts, four affiliates, Fleet name on/off, and
two signer sets. It additionally runs r20 and the exact `conf`-only variant to
separate conflict protection from precedence recoveries. The review's stdin
scratch generator was not included with the review, so these are explicit
reconstructions, not claims of byte-identical unpublished inputs.

`stress.py` records the 2,112-cell recital reconstruction, 504 page/section
reconstructions, 36 all-failing conflict probes, and 54 THE RECIPIENT real-worker
cells. It preserves raw geometry flags, including the review's NORTHWIND ruling
and carried M-1 misspelling class. No new raw flags are allowed. M-1 is outside
the requested M-2/L-1 fix; its residual observations are reported explicitly.

All replay processes remove `OPENROUTER_API_KEY` and `PLACE_MODEL`, patch external
HTTP to raise, disable bytecode writes, and assert expected mocked model-call
counts. Golden and selected reproduction results are checked against the real
worker, not just in-process extraction. Scratch worker packages are temporary
and confined to r22.

## Commands

All commands run from the repository root with `PYTHONDONTWRITEBYTECODE=1` and
`/root/work/sign-product/send-venv/bin/python` as the interpreter (`PY` below).

```sh
PY docs/implementation/c2a-r22/run_tests.py dealroom_sign/tests/test_placement_r22.py --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r22/failing-first.xml
PYTHONPATH=/root/worktrees/send-c1b/docs/implementation/c2a-r22 PY docs/implementation/c2a-r22/run_tests.py -p baseline_plugin dealroom_sign/tests/test_placement_r22_conflict_probes.py --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r22/probes-failing-first.xml
PY docs/implementation/c2a-r22/run_tests.py dealroom_sign/tests --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r22/final-full-suite.xml
PY docs/implementation/c2a-r22/replay.py historical
PY docs/implementation/c2a-r22/replay.py review
PY docs/implementation/c2a-r22/replay.py layouts
PY docs/implementation/c2a-r22/replay.py wrapped
PY docs/implementation/c2a-r22/replay.py new
PY docs/implementation/c2a-r22/stress.py
```

The full suite means the complete `dealroom_sign/tests` scope used by r20/r21,
with no `-x`, filtering, skips, or deselections. An initial full-suite launch
(`full-suite.txt`) was interrupted early when the additional 36-probe test file
was added; it is not completion evidence. `final-full-suite.*` includes all old
and new test files in a single complete invocation.
