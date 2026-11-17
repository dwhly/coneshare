# C2a r10 — Gate 3 r9 B-1 / M-1 / L-1 / N-1

Review: `counterparty-c2a-gate3-r9.md`, Blocking B-1 (94–138), M-1
(140–146), L-1 (148–153), N-1 (155–159), read in full. Base:
`4db6335403216f467d3a285e9d85f987724ac571`, branch `agent/c1b-counterparty`.

## Contract

The absorbed-identity veto covers **a typed name at or below a subordinated
rule, within the absorbing host's extent**. It uses the review's exact
collection predicate:

```python
t['rect'][1] - line.y >= -12 and t['rect'][2] > column - 5 and person_text(t['text'])
```

Only structural subordination collects names. The six unconditional contact
captions (Email, E-mail, Address, Phone, Tel, Company) remain exempt. The
existing host-extent containment after partitioning still bounds the veto
vertically and horizontally; no extent, scoring or worker payload change is
part of this revision. `analysis_version` becomes `c2a.10`.

The B-1 matrix covers all four requested forms: Title then Name at +24, Name
then a tab gap to x150, Name indented to x110, and the name on the caption
baseline at x300, right of the rule. Both C12/C13, all six unrecognised
headings, and all five captions are included. The dy sweep covers +22, +24,
+26, +28, +30 and +34 in both layouts with every caption. Signature controls
retain C12's high placement on 360/420 and C13's hold.

M-1 applies the same hold to all four forms under Fax, Mobile, Contact,
Attention, Notice Address, Initials and Sign, for Lee/LEE and Pat/PAT.
L-1 explicitly accepts the single-signer hold when the name is printed under
a Fax-style contact line. The [runbook](../c2a-runbook.md#identity-extent)
documents this cost next to the existing second-company L-1 sentence.

## Test preservation

The sole existing-test edit is
`test_placement_r9.py::test_caption_identity_slot_edges`: eight cases, same
monkeypatch/extract/assert structure, retargeted to inclusive `dy = -12` and
strict `x1 > column - 5`. `dx` now positions the row's right edge. The dy
cases sit right of the rule to isolate collection from the intervening-name
check in `subordinate_caption`. No other existing test was changed.

The new `test_placement_r10.py` has 499 cases. The original 40 H-1 controls in
`test_placement_r9.py` remain unchanged. The new H-1 extensions assert a hold
and zero model calls for all four out-of-slot forms. The initial test draft also
required the internal `uncertain_identity` flag on r9's already-held H-1
blocks; that extra requirement was removed from the **new** tests before any
production edit, and the original stack's Date row at 395 was restored (the
draft used 420, outside the 290 host's companion range).
[Initial draft execution](initial-test-draft-summary.json)
is retained separately from the final failing-first run.

## Failing first on unchanged `4db63354`

The [final failing-first run](failing-first-summary.json) executed all 499 new
tests and the eight approved boundary cases before the production edit:
**391 failed, 116 passed, zero errors/skips, 127.882 seconds**.

| Group | Failed | Passed |
| --- | ---: | ---: |
| B-1: four forms × C12/C13 × six headings × five captions | 240 | 0 |
| B-1: six dy values × C12/C13 × five captions | 60 | 0 |
| Signature controls | 0 | 48 |
| Additional out-of-slot H-1 stacks | 30 | 10 |
| M-1: four forms × seven contacts × two matching signers | 56 | 0 |
| Six exempt contacts × four forms × two matching signers | 0 | 48 |
| Seven exact goldens | 0 | 7 |
| Retargeted boundary cases | 5 | 3 |

The 356 B-1/M-1 failures were placements instead of holds, with high confidence
in the representative assertions. The additional H-1 forms with tabs, indents
or right-side names also placed on r9 with the original Date at 395; only the
Title-before-Name form already held. These are extensions to the original
40-case H-1 matrix, not changed expectations in that matrix. This fixture
detail differs from the review's broader statement that all out-of-slot
H-1 variants already held. The prescribed predicate covers them too.

The recorded production SHA-256 is
`e4f2dc4d23a022bcce9eef41bdf52f77b0db85a80644a61ccf8009c4c22bc005`,
identical to `git show 4db63354:backend/dealroom_sign/placement.py`.
Test hashes are recorded so the final run can verify the same test definitions.

## Full-suite result

[Executed full-suite summary](full-suite-summary.json): **1,662 passed,
0 failures, 0 errors, 0 skipped, 82 warnings, 560.649 seconds**. This is the
original 1,163 tests plus 499 r10 cases. The final test-file hashes exactly
match the failing-first run. All original H-1 stacks hold; all new B-1/M-1 and
out-of-slot H-1 cases hold; Signature and exempt-contact outcomes are unchanged.
All seven goldens match r4/r5 exactly on status, geometry, confidence and
native fields.

## Reproduction

`run_summary.py` invokes the requested runner with
`SIGN_INTERNAL_URL=http://sign.test`, adding only `--tb=short` and temporary
JUnit XML for counts. Output is captured in memory, reduced to JSON, and the
XML is removed. Raw logs are not retained.

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r10/check_evidence.py
```

The evidence checker runs real reportlab PDFs through `placement.place` and
the parser subprocess. It stores each common result once with the full list
of executed case IDs. Golden comparisons reuse the r9 checker with output
redirected only to this r10 directory. All model I/O is stubbed or forbidden;
the unusual golden uses one local confirming stub.

## Executed placement evidence and completion

[Placement summary](placement-summary.json) and
[grouped case outcomes](review-placements.json) cover **532 executed cases**:
240 B-1, 60 dy-sweep holds, 48 Signature controls, 40 new H-1 extensions,
40 original H-1 stacks, 56 M-1 holds and 48 exempt-contact placements. Every
hold has no fields and no model calls. B-1, dy-sweep and M-1 cases additionally
verify `uncertain_identity` and a zero identity score. All external model
calls are forbidden; the unusual golden uses a single local stub.

[Golden placements](placements.json) and [exact comparison](golden-comparison.json)
confirm all seven fixtures against both r4 and r5. None subordinates a rule.
The [preservation audit](preservation-summary.json) records the exact production
diff, unchanged existing tests outside the permitted function, unchanged
fixtures/baselines, append-only report, matching failing-first/final test
hashes, empty index and unchanged project memory.

Implementation and verification are complete. HEAD remains `4db63354`.
Changes are unstaged and uncommitted. Raw logs and temporary XML are absent.
Completion marker: [counterparty-c2a-r10.done](counterparty-c2a-r10.done).
