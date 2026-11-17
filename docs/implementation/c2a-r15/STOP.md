# STOP: existing r10 control fails

The required full suite stopped with **1 failed, 802 passed, 43 warnings**
in **329.29 seconds**. Pytest exit code: **1**. No test was changed,
weakened, skipped, deleted, or retargeted. The remaining tests were not run
after the first failure (`-x`), as required by the stop rule.

Failing existing test:

```text
dealroom_sign/tests/test_placement_r10.py::test_signature_out_of_slot_controls_unchanged[caption_row_right-C12-HARBOR LIGHT ANALYTICS, INC., a Delaware corporation]
```

It expects a high-confidence signature at y360 and date at y420. Candidate
(c) returns `needs_sender` with no fields. The fixture puts Pat's name at
x300, immediately beyond the rule's x290 endpoint. The selected overlap
condition is strict (`row.x0 < rule.x1 + 10`), so that row at the exact
10-point boundary does not count. This diagnosis follows directly from
the failure and existing fixture source; no follow-up test or alternative
fix was run after the failure.

The requested 9,754-case comparison table is complete. All three candidates
have zero wrong placements on that table and exact seven goldens except
version. However, the r13 generator's `Signature controls` family enumerates
r11 `FORMS`; it does not include this r10 `caption_row_right` control. The
full suite therefore found a preservation failure outside that generator.
The claimed zero correct-placement loss applies to the measured table,
not the full test suite. This newly observed loss is a realistic layout.

**No approved implementation is delivered.** Candidate (c) and version
`c2a.15` remain as an uncommitted working-tree change for inspection. The
new r15 test file and all measured evidence are retained. No further
product/test changes or candidate trials were attempted after the failure.
The completion marker reports `coder rc=1`, because writing `rc=0` would
incorrectly claim success. HEAD remains the baseline commit.

The earlier optional memory draft has not been saved and should not be
treated as a validated resolution. Project memory remains unchanged.

Evidence: [full pytest output](full-suite.txt), [JUnit outcomes](full-suite.xml),
[machine-readable suite summary](full-suite-summary.json),
[candidate table](results.md), [preservation audit](preservation-summary.json).
