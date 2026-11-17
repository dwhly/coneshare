# C2a r14 — staggered columns and shared printed names

Base: `2ff90be102b4a4a3f65cee15a3f8258fcb445685`, branch
`agent/c1b-counterparty`. Read the complete `counterparty-c2a-gate3-r13.md`
review, including Blocking B-1, Low L-1, and Nit N-1.

## Failing first — recorded before any product edit

On byte-for-byte r13 product source, the new test file completed with
**105 failed, 3,718 passed, 0 errors, 0 skipped, 47.370 seconds**.
The failures were the real-worker reproduction (1), the two-column grid
(**84/3,456**), and the fixed-geometry sweep (**20/360**).
The two correct-placement, two L-1, and two independently printed name controls passed.
[Summary and source hashes](failing-first-summary.json) ·
[Every test outcome](failing-first-summary-cases.json).

After adding the two separate-name locality controls, the final unchanged test
file was rerun on r13 before the product edit; these are that complete run’s
counts. The initial 3,821-test run had the same 105 failures.

The new file has 3,823 tests. Reproduction and six controls call `place`
through the real subprocess worker. The geometry matrices use `place` with
`bounded_extract` replaced by `extract` + `prepare_blocks`, the review's
in-process method. All tests disable provider configuration and forbid HTTP;
all use model mocks and require zero model calls. No existing test is edited.

The grid explicitly enumerates our column left/right, lower column ours/theirs,
dy 0/20/40/60/80/100, name offset 12/24/40/60, our name absent/blank rule/Dan,
counterparty heading HARBOR/RECIPIENT:/absent, title absent/present, and
PAT-only/DAN+PAT. Name offsets apply to both columns; dates are 100 pt below
their respective rules. Its 84 wrong placements reproduce the review count.
The reviewer did not supply its generator, so the checked-in generator and
complete parameter IDs are the reproducible definition, not a claim that
unpublished case bytes are identical.

The fixed sweep uses the reproduction's name/date positions and both column
orientations, our By at every 10 pt from y300 through y440, three headings,
title absent/present, and both signer sets (360 cases). This is denser than the
review's described sample; the per-case evidence records all 20 wrong cases,
including the reported y350/y370 placements. A field counts as wrong only
when Pat is confidently assigned a SIGNATURE on our independently generated
rule coordinates. Holds have no fields.

## Counterfactuals queued before selection

Both candidates are generated from the exact committed r13 source in memory;
no candidate has yet been applied to production. Candidate (a) removes the
vertical same-band condition from column bounds, keeping the other column's
rule-end/label-edge bounds. Candidate (b) collects the physical printed-name
rows from mixed-company-vetoed blocks and vetoes every extent containing
those same rows on the same page, after all conflicts have been collected.

The runner evaluates the complete 2,699-case r13 table plus the new B-1
families. The original 1,750 preserved cases are included, as are all 864
r12 B-1 sweep cases and the remaining r13 additions. This resolves the brief's
count mismatch by running every enumerated family rather than dropping any.
Reproduction, correct controls, and all goldens also execute with the
unchanged real worker in temporary import roots for each counterfactual.

## Low and Nit

L-1's two short-caption controls continue to require the existing high Pat
placement when the printed name is in our column. This task does not blanket
veto company/name disagreement. The complete earlier table also includes
these controls and L-2.

N-1 is a marker naming issue, without product behavior to test. This run uses
`counterparty-c2a-r14.done` locally and in the requested external briefs path;
previous r12/r13 markers are left intact.

## Executed counterfactuals — before production selection

Both candidates completed all **6,518 cases** (19,554 in-process results)
and **30 real-worker checks**: reproduction, two correct controls, seven
goldens, for r13/a/b. Every old r13 result was also checked against the saved
r13 evidence: **2,699 exact**. Full comparisons remove only `analysis_version`.
No external HTTP calls; only each `unusual` golden calls its local stub once.

### (a) Column-gutter bound

| Family | Cases | r13 placed | Candidate placed | Candidate holds | Wrong placements | Full differences from r13 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Matrix 1 | 120 | 0 | 0 | 120 | — | 0 |
| Matrix 2 | 270 | 0 | 0 | 270 | — | 0 |
| r11 B-1 | 1020 | 0 | 0 | 1020 | — | 0 |
| Signature controls | 204 | 6 | 6 | 198 | — | 0 |
| M-1 | 16 | 16 | 16 | 0 | — | 0 |
| r9 heading matrix | 72 | 6 | 6 | 66 | — | 0 |
| r9 H-1 | 40 | 0 | 0 | 40 | — | 0 |
| Seven goldens | 7 | 6 | 6 | 0 | — | 0 |
| Same-band right host | 1 | 0 | 0 | 1 | — | 0 |
| r12 B-1 reproduction | 1 | 0 | 0 | 1 | — | 0 |
| r13 same-band grid | 42 | 0 | 0 | 42 | — | 0 |
| r12 B-1 sweep | 864 | 0 | 0 | 864 | — | 0 |
| L-1 short-rule controls | 2 | 2 | 2 | 0 | — | 0 |
| L-2 own-company controls | 40 | 20 | 20 | 20 | — | 0 |
| r14 reproduction | 1 | 1 | 1 | 0 | 0 | 1 |
| r14 grid | 3456 | 1356 | 3312 | 144 | 0 | 2304 |
| r14 fixed sweep | 360 | 148 | 360 | 0 | 0 | 312 |
| r14 correct controls | 2 | 2 | 2 | 0 | 0 | 2 |

Seven goldens include six placed results and one `bare`; `bare` is not a hold.

### (b) Shared-name veto

| Family | Cases | r13 placed | Candidate placed | Candidate holds | Wrong placements | Full differences from r13 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Matrix 1 | 120 | 0 | 0 | 120 | — | 0 |
| Matrix 2 | 270 | 0 | 0 | 270 | — | 0 |
| r11 B-1 | 1020 | 0 | 0 | 1020 | — | 0 |
| Signature controls | 204 | 6 | 6 | 198 | — | 0 |
| M-1 | 16 | 16 | 16 | 0 | — | 0 |
| r9 heading matrix | 72 | 6 | 6 | 66 | — | 0 |
| r9 H-1 | 40 | 0 | 0 | 40 | — | 0 |
| Seven goldens | 7 | 6 | 6 | 0 | — | 0 |
| Same-band right host | 1 | 0 | 0 | 1 | — | 0 |
| r12 B-1 reproduction | 1 | 0 | 0 | 1 | — | 0 |
| r13 same-band grid | 42 | 0 | 0 | 42 | — | 0 |
| r12 B-1 sweep | 864 | 0 | 0 | 864 | — | 0 |
| L-1 short-rule controls | 2 | 2 | 2 | 0 | — | 0 |
| L-2 own-company controls | 40 | 20 | 20 | 20 | — | 0 |
| r14 reproduction | 1 | 1 | 0 | 1 | 0 | 1 |
| r14 grid | 3456 | 1356 | 1200 | 2256 | 0 | 336 |
| r14 fixed sweep | 360 | 148 | 128 | 232 | 0 | 40 |
| r14 correct controls | 2 | 2 | 2 | 0 | 0 | 0 |

Seven goldens include six placed results and one `bare`; `bare` is not a hold.

### Choice: (b), as executed

Both candidates meet zero-wrong-placement, exact-preservation, and exact-golden
checks. **(a) fails the additional explicit reproduction requirement:** its
real-worker reproduction places Pat correctly on the HARBOR rule at y290,
instead of holding. The review says either candidate must hold this case,
and the requested regression test requires `needs_sender/ambiguous_identity`,
zero fields, and zero model calls. Therefore (a) is not an eligible passing
candidate, despite its zero wrong placements. Its 2,304 full grid changes also
include many newly permitted placements; these are recorded, not shipped.

**(b) passes the required hold and all three bars.** All 2,489 holds in the
new reproduction/grid/fixed families are `ambiguous_identity`, with zero
fields and model calls; none are parser failures or timeouts. It adds only vetoes, after
partitioning, using the same physical name row on the same page. Separate
printings of the same name remain eligible. There are no scoring changes,
new fields in the worker payload, or altered column/host geometry.
The production source will be exactly the executed candidate-b source with
`VERSION = 'c2a.14'`; both candidate patches and source hashes are retained.

All **2,699 earlier cases remain fully exact**, covering the original 1,750,
the 864-case sweep, and every later r13 control. Earlier wrong-to-hold
exceptions: **none**; no preservation exception is needed.

In the new grid, (b) changes 156 placements to holds: all 84 wrong placements
plus **72 previously correct placements** in mixed-heading geometry. Holds
are allowed by the brief; the required unambiguous-placement controls stay
placed and fully exact. Another 180 existing holds change assignments but
remain holds, making 336 full grid differences. The fixed sweep has 20
wrong-to-hold changes and 20 hold-to-hold changes. The reproduction adds one
wrong-to-hold change. All 377 changes, with full before/after results, are
recorded in the differences file. No new placement is introduced by (b) in the executed families.

[Counterfactual summary](counterfactual-summary.json) ·
[Every full result and case](counterfactual-cases.json) ·
[All differences](counterfactual-differences.json) ·
[Real-worker checks](counterfactual-workers.json) ·
[Candidate a](candidate-a.patch) · [Candidate b](candidate-b.patch).

## Reproduction commands

```bash
# Failing first, before the production change (r13 product source):
python3 docs/implementation/c2a-r14/run_summary.py failing-first-summary dealroom_sign/tests/test_placement_r14.py

# Both candidate sources are rebuilt from committed r13; no product edit:
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r14/check_evidence.py

# Full requested suite on selected production source:
python3 docs/implementation/c2a-r14/run_summary.py full-suite-summary dealroom_sign/tests

# Final goldens, unchanged tests, source hashes, scope, and index audit:
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r14/check_preservation.py
```

The summary runner invokes the requested command exactly, with reporting-only
`--tb=short` and `--junitxml` arguments added:

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```

It retains compact counts, source hashes, and per-case outcomes; temporary
JUnit XML is removed after parsing. No selection/skip/stop option is added.

The fixed sweep's 20 baseline wrong placements are four each at
**y350, y360, y370, y380, y390**, all HARBOR-headed/PAT-only. The review named
y350 and y370; the denser sweep exposes the intervening and nearby values.
The selected grid's signer split is **672 placed/1,056 held PAT-only** and
**528 placed/1,200 held DAN+PAT**. Both have zero wrong Pat placements.
[Geometry breakdown](grid-breakdown.json) ·
[Selected transitions](chosen-transitions.json).

## Final production validation

The requested full signing suite completed with **8,073 passed, 0 failures,
0 errors, 0 skipped, 82 warnings, 1,339.898 seconds**: all 4,250 existing
cases plus 3,823 new cases. No test selection, weakening, or skip was used.
[Full-suite summary](full-suite-summary.json) ·
[Every test outcome](full-suite-summary-cases.json).

On the final production source, all **seven real-worker goldens are exactly
r13 except `analysis_version`**, including native field conversions. Six
place and pass `assert_golden`; bare stays bare with no fields. Only unusual
uses its one local stub call. External HTTP calls: zero.
[Placements](placements.json) · [Golden comparison](golden-comparison.json).

The [preservation audit](preservation-summary.json) passes. All **52 existing
test and fixture files** remain byte-for-byte unchanged. The new test source
matches the final failing-first run, and the product source matches the
executed candidate (b) and full-suite source hash. Only `extract` and
`VERSION` change in product code. The report is append-only, memory is
unchanged, the index is empty, and `git diff --check` passes.

HEAD remains `2ff90be102b4a4a3f65cee15a3f8258fcb445685` on
`agent/c1b-counterparty`. No staging or commit was performed.

## Completion-marker delivery

The local [completion marker](counterparty-c2a-r14.done) was written first.
The subsequent write to
`/root/worktrees/dealroom-sign-edd/docs/edd/briefs/counterparty-c2a-r14.done`
failed: **Read-only file system**. This destination is outside the writable
roots; approval escalation is unavailable. The local marker records the
blocker and is ready to copy. Previous markers were not changed.
Implementation, tests, and evidence are complete and uncommitted; the
external marker is the only blocked delivery.
