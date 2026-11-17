# C2a r15 execution method

Review read in full: `counterparty-c2a-gate3-r14.md`, including B-1, L-1,
and N-1. Baseline: `d88bfb889f3863796b276a6f0aef3da57539c4c3` (`c2a.14`).
All evidence and completion markers for this run live in this directory.
The external review/brief folder is read-only and is not modified.

## Failing first

`test_placement_r15.py` adds the review's two reproductions verbatim, each
with PAT and DAN+PAT through `placement.place` and its real worker. Its
geometry matrices use the review's in-process `extract` + `prepare_blocks`
path, through `place`, with a model mock and the existing no-network fixture.

M1 has 640 cases: five headings × 16 y positions (300–450 inclusive, step 10)
× title on/off × two orientations × two signer sets. M2 has 2,592 cases:
six second rows × nine dy positions (40–120 inclusive, step 10) × four name
gaps (12/24/40/60) × three headings × two orientations × two signer sets.
The second row is 26 pt below Pat's row, exactly as in reproduction B.
The counterparty date is 100 pt below its signature; our signature/date
are y290/y390. M1 uses r14's fixed geometry with the five new headings.

The unchanged baseline produced **534 failed / 2,702 passed**, zero errors
or skips: M1 100/640 failed, M2 432/2,592 failed, real-worker reproductions
2/4 failed. All failures are PAT-only. Each M1 heading fails in 20 cases.
The tests reject any Pat field on our signature rule, regardless of field
type or confidence. A hold must have zero fields.

Command (stdout and JUnit outcomes retained):

```sh
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r15.py --tb=no --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r15/failing-first.xml
```

`failing-first-summary.json` records the test hash, HEAD, and confirmation
that `placement.py` had no diff when failures were recorded.

## Candidates

`check_evidence.py` reads the baseline with `git show` and builds all three
counterfactual modules in memory before any product edit. Temporary import
roots in this directory allow the unchanged worker to import each source;
they are removed on exit. Candidate patches and SHA-256 source hashes make
the experiment reproducible.

**(c): column ownership.** A row's horizontal interval is its extracted
`[rect[0], rect[2]]`. The block's label/rule column is
`[min(rule.x0, label.rect[0]), rule.x1]`, falling back to rule.x0 when no
label exists. The row must have positive overlap with that column expanded
by **10 pt on each side**: `row.x0 < rule.x1 + 10` and
`row.x1 > column.left - 10`. Equality at the expanded boundary does not
qualify. Vertical/page membership remains governed by the existing raw
label collection and partitioning. The tolerance preserves the existing
`Signature:` margin control: its name ends at x63.35, 8.65 pt left of the
label column at x72. It is much smaller than the reproduction's column gap.

This is a scoring restriction in `printed_names`. It retains the existing
raw evidence, ambiguity checks, absorbed-caption checks, and r14 mixed
heading veto. Consequently a row can still cause a conservative hold even
when it cannot contribute a printed-name score. No raw identity is newly
serialized or sent to a model.

**(b′): generalised veto.** Replace r14's mixed-heading-only propagation
with same-page physical-row sharing. For each block, collect the other
extents containing any of its printed-name rows. Compute every block's
per-signer score before redaction or propagation. A zero score in any peer
(including an `uncertain_identity` block) zeroes the borrowing block's score
for that signer. The comparison uses the original score snapshot, so block
iteration order cannot alter it. Temporary peer references are removed
before worker output and are not dataclass fields. This is signer-specific,
not a global veto on separately printed occurrences of the same name.

**(c)+(b′)** applies both changes. No additional candidate is introduced.

## Full table and outcome definitions

The table includes every one of the 2,699 cases yielded by the r13
`check_evidence.cases()` generator, r14 GRID (3,456), FIXED (360), its
reproduction (1), and its correct controls (2), plus all 3,236 r15 tests.
That is **9,754 unique cases per source**, with r14 and three candidates.
The 72 r14 L-1 cases are also enumerated and reported separately, yielding
9,826 table rows per source. They are a subset, not 72 additional unique
layouts. The L-1 predicate is PAT-only, HARBOR, their column lower by
60/80/100, our name absent/blank, and `dy + name_gap <= 125`; both
orientations and title settings are included.

For r14/r15 geometry families, **wrong** means a Pat field on our known
signature rule; **placed** includes wrong placements; **holds** means
`needs_sender`. Earlier required-hold families must remain holds; earlier
placed controls use the original accepted field geometry as their oracle.
Goldens are compared as full results against r13, excluding only
`analysis_version`. The `bare` golden is separately counted, not called a
hold or placement. Any new earlier-family placement or changed earlier
field geometry is flagged for investigation rather than presumed correct.

Every baseline result overlapping the r14 evidence archive is checked for
exact equality except version. Every source additionally runs the seven
goldens, r14 reproduction and correct controls, and both r15 reproductions
under both signer sets through the real worker; full results and mock-call
counts must equal their in-process results.

`OPENROUTER_API_KEY` and `PLACE_MODEL` are removed and `httpx.Client.send`
raises on any use. No external model/network call is allowed. The unusual
golden invokes its deterministic local model stub exactly once; all other
table cases invoke no model. The worker runs with its existing credential-free
environment. Bytecode caches created by that worker are cleaned after all
verification, since its fixed environment does not inherit the parent's
`PYTHONDONTWRITEBYTECODE` setting.
