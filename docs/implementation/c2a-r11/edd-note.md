# C2a r11 — Gate 3 r10 B-1 / M-1 / L-1 / N-1

Review: `counterparty-c2a-gate3-r10.md`, including B-1 (107–163), M-1
(165–187), L-1 (189–195), and N-1 (197–202), read in full. Base:
`945ad159`, branch `agent/c1b-counterparty`. No commit is authorized.

## Contract

The absorbing host is the SIGNATURE/Witness rule that subordinated the
caption. Collect `(host, text)` for every person row whose top is strictly
below that host's rule. The caption's dy and column no longer limit
collection. Before applying the veto, require the name to lie within its
own absorbing host's extent: inclusive top/bottom and strict horizontal
overlap. If that rule formed no block, retain its collected names. Every
block containing a retained name receives the uncertainty veto after
partitioning, including overlapping hosts.

`subordinating_host()` returns the matching rule or `None`;
`subordinate_caption()` remains its Boolean wrapper. The Boolean gate in
`extract()` is retained so the existing r8 forced-classification tests still
exercise the independent mixed-company check. The host is then obtained
separately for collection. In normal execution the two lookups agree; a
forced Boolean classification without a real host contributes no absorbed
names. This keeps the existing test hook without changing any r8 test.

The six unconditional contact captions remain exempt. Extents, identity
scores, worker payloads, and ordinary signature classification are unchanged.
`analysis_version` is bumped to `c2a.11`.
The [runbook](../c2a-runbook.md#identity-extent) describes the corrected rule.

## Control baseline discrepancy

The review's parenthetical that every new C12 `Signature:` control places
on 360/420 does not match unchanged `945ad159` for the new forms. Executed
real-worker baseline: **198 holds and 6 placements** across 204 controls.
C13 holds all 102; C12 places the six left-margin cases and holds the other
96. Large-font and raised names are shared by both hosts and tie their
identity scores. Indenting the caption to x150 leaves the Date at x72,
outside its companion column. These holds predate r11.

The new tests preserve these observed outcomes. The existing r10 controls
are untouched and still require C12 high placement on 360/420 and C13 holds.
[Baseline control evidence](r10-signature-controls.json) records all 204
executed cases in compact groups. This discrepancy was surfaced during work;
no placement/scoring change is included to turn those existing holds into
placements.

## Reproduction

The [summary runner](run_summary.py) uses the requested command, adding
`--tb=short` and temporary JUnit XML to collect counts. Raw output is held in
memory and discarded; the XML is removed after producing JSON.

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r11/check_evidence.py
```

The [evidence checker](check_evidence.py) uses real reportlab PDFs and the
parser subprocess, forbids external model I/O, and uses one local confirming
stub for the unusual golden. It compares all seven complete golden results
with the pre-edit r10 execution, excluding only `analysis_version`, and also
checks exact geometry, confidence, and native fields against r4/r5.

## Failing first and test scope

The finalized tests ran against byte-for-byte `945ad159` production before
restoring the unchanged r11 implementation: **1,017 failed, 239 passed,
0 errors, 0 skipped, 318.318 seconds**. The
[executed failing-first summary](failing-first-summary.json) records the
production and test hashes; [baseline source proof](baseline-source.json)
identifies the original production bytes.

| Group | Failed on r10 | Passed on r10 |
| --- | ---: | ---: |
| B-1: 17 forms × C12/C13 × six headings × five captions | 1,000 | 20 |
| M-1: four cross-host layouts × four captions | 12 | 4 |
| New Signature controls with measured r10 outcomes | 0 | 204 |
| Absorbing Witness rule without its own block | 0 | 1 |
| Retargeted boundary cases | 5 | 10 |

The 1,000 B-1 failures place instead of holding; the 12 M-1 failures hold
instead of placing. The 20 already-held B-1 cases are the merged-text
layouts described below.

The 17 forms are plain and `Name:`-prefixed names on the caption baseline
at 13/14/16/18 pt (eight), raised names at exact dy −13/−16/−19/−22/−25/−28
at x300 (six), a caption at x150 with the name at x72 at +12/+24 (two), and
a name at x20 in the left margin (one). Every B-1 test uses the real worker
and requires the specified observable hold: no fields and no model calls.

There are **1,241 new r11 tests**. The sole existing-test edit is
`test_placement_r9.py::test_caption_identity_slot_edges`: the original eight
cases remain, with the three approved expectation flips. Seven additional
rows pin strict `top > host.y`, inclusive host bottom, and strict left-edge
overlap. The monkeypatch/extract/assert structure is unchanged. All r8 and
r10 tests, including the 40 r10 H-1 cases, remain untouched.

Two new-test draft executions are retained separately. The
[initial draft](initial-test-draft-summary.json) had 1,133 failures and 122
passes; 96 failures exposed the Signature-control baseline discrepancy.
The [second draft](second-test-draft-summary.json), after preserving the
measured control outcomes, had 1,037 failures and 219 passes.

The second draft reused r9's `assert_identity_hold` helper, which additionally
requires an internal `uncertain_identity` flag. Twenty cases with dy −28 and
one of the two long headings merge the name into the heading during text-row
extraction. They hold without that flag, so this extra helper assertion was
inappropriate for the requested observable behavior. The
[first full-suite attempt](interrupted-suite-summary.json) was interrupted
when this was identified. Only the **new r11 B-1 test** was changed to the
existing `assert_stack_hold` helper, which requires `needs_sender`,
`ambiguous_identity`, no fields, and zero model calls. No existing helper or
test was altered. The finalized tests were then re-run against restored,
exact r10 bytes before restoring the unchanged r11 implementation and
restarting the full suite.

## Executed placement evidence

[Placement summary](placement-summary.json) and
[grouped outcomes](review-placements.json) record 34 real-worker B-1
representatives and all 16 M-1 cases. All B-1 representatives hold without
fields or model calls. All 12 targeted cross-host placements are restored
with the correct signer, signature/date lines, and high confidence; the four
side-above controls still place correctly.

All [204 new Signature controls](signature-controls.json) match their
executed r10 baseline exactly on status, reason, fields, geometry,
confidence, lines, and model calls. The baseline outcomes are preserved,
including the 96 C12 holds described above.

[Golden placements](placements.json) and [comparison](golden-comparison.json)
confirm **all seven complete results are identical to r10 except for
`analysis_version`**, including assignments and evidence. They also match
r4/r5 exactly on status, geometry, confidence, and native fields, and match
`expected.json`'s independent assertions. No golden block has uncertain
identity. There were zero external model calls; only the unusual golden used
one local confirming stub. No raw logs are retained.

## Full-suite verification and preservation

[Completed full suite](full-suite-summary.json): **2,910 passed, 0 failed,
0 errors, 0 skipped, 82 warnings, 879.909 seconds**. This is the original
1,662 tests plus 1,241 new r11 cases and seven additional boundary parameters
inside the approved r9 test. The test hashes match the final failing-first
run exactly; the production hash matches the successful evidence execution.

All 1,020 B-1 cases hold without fields or model calls. All 16 cross-host
probes place on the correct signer and lines. All 204 new Signature controls
preserve their measured r10 outcomes. The unchanged r10 Signature controls
still place C12 on 360/420 and hold C13. Both the original r9 and r10 H-1
matrices pass unchanged (40 each). The overlapping-host veto test, the eight
r8 Boolean-wrapper boundary cases, and all 15 r8 forced-classification cases
pass unchanged. All seven exact golden tests pass.

The [preservation audit](preservation-summary.json) verifies that only the
approved existing test function changed, all other existing tests and golden
fixtures/baselines remain intact, the report is append-only, project memory
is unchanged, HEAD is still `945ad159`, and the index is empty. Temporary
source backups, raw logs, and JUnit XML are absent. `git diff --check` passes.

Implementation, executed placement evidence, and full-suite verification are
complete. The Signature-control baseline discrepancy remains explicitly
documented above. Changes are unstaged and uncommitted.
Completion marker: [counterparty-c2a-r11.done](counterparty-c2a-r11.done).
