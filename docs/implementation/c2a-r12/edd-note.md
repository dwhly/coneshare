# C2a r12 — retain absorbed names across intervening blocks

Implemented Gate 3 r11 B-1 **fix A only** on `agent/c1b-counterparty`, based on
`0c190e9b45db25ee5c1b8d71cdc2b040cd956fab`. `VERSION` is `c2a.12`.
No commit or staging operation is part of this change.

`extract` now collects `(host, line.label, t)` for each absorbed person row.
After the block extents are built, it retains that row when its original host
extent contains it **or any block extent on the same page contains both the
absorbed caption label and the person row**. A host that formed no block still
keeps the row, failing closed. Containment uses the existing inclusive vertical
top/bottom and strict horizontal overlap boundaries. Every block containing a
retained name receives the existing veto after partitioning.

Host lookup and its iteration order are unchanged. Fix B is executed only as
an evidence counterfactual; it is not in the product. No scoring, partitioning,
extent construction, contact-caption exemption, or worker payload is changed.
The collected tuple remains local to `extract`.

## Failing first and regression scope

The new `backend/dealroom_sign/tests/test_placement_r12.py` ran against
byte-for-byte HEAD production before the edit: **256 failed, 135 passed,
0 errors, 0 skips, 97.850 seconds**. All failures were placements where the test
required `needs_sender/ambiguous_identity`, no fields, and zero model calls.
Production and test SHA-256 values are recorded in the
[summary](failing-first-summary.json); all 391 test IDs and outcomes are in
[per-case results](failing-first-summary-cases.json).

| New worker regressions | Cases | r11 failures | r11 passes |
| --- | ---: | ---: | ---: |
| Matrix 1 | 120 | 120 | 0 |
| Matrix 2, PAT only | 135 | 135 | 0 |
| Matrix 2, Dan+Pat | 135 | 0 | 135 |
| Same-band right host | 1 | 1 | 0 |

Matrix 1 is the requested Cartesian product of three second rules, five
captions, four headings, and plain/prefixed Pat names. Matrix 2 includes the
three requested stacks, five captions, both signer sets, and nine forms.
The review enumerates **eight** forms but reports 270 cases, requiring nine.
The extra form used here is a 10 pt caption-baseline name, in addition to the
explicit 13/16 pt baseline, below 12/24, raised 16/25, margin, and indented
forms. This assumption was raised for clarification and is recorded in the
test and evidence runner. The reproduced outcome totals match the review.
The source review does not give exact coordinates for every widened stack;
the generators in the new test file are the complete reproducible definition.

The additional right-host case uses `By:` rules at **the same y=290**, in
columns x=72 and x=330. The absorbed caption begins at x=260 and overlaps both
bands; the name starts at x=340, beyond the left extent. A nearest-first stable
sort still selects the left rule. Executed results: r11 and fix B place Pat
incorrectly on the right `By:`; fix A holds without fields or a model call.

## Executed counterfactual table

[check_evidence.py](check_evidence.py) loads the exact r11 source from git and
builds a separate in-memory fix B module by changing only the host-loop order.
Fix A is the working-tree product. For all three versions, `place` receives
`extract` + `prepare_blocks` through `bounded_extract`, matching the review's
counterfactual method and the worker's extraction steps. The real worker is
covered separately by pytest; all seven goldens also run through it here.

All **1,750 cases** executed. Both model configuration environment variables
are removed, model clients are local mocks, and HTTP sends raise. Every
non-golden case makes zero model calls. Only the unusual golden invokes its
local confirming stub once per execution. External model calls: **0**.

| Case | r11 placed | Fix A placed | Fix B placed | Full result differences from r11 (A / B) |
| --- | ---: | ---: | ---: | ---: |
| Matrix 1, 120 | 120 (wrong) | 0 | 0 | 120 / 120 |
| Matrix 2, 270 | 135 (wrong) | 0 | 0 | 270 / 270 |
| r11 B-1, 1,020 | 0 | 0 | 0 | 0 / 0 |
| `Signature:` controls, 204 | 6 | 6 | 6 | 0 / 0 |
| M-1 cross-host, 16 | 16 | 16 | 16 | 0 / 0 |
| r9 heading matrix, 72 | 6 | 6 | 6 | 0 / 0 |
| r9 H-1 stacks, 40 | 0 | 0 | 0 | 0 / 0 |
| Seven goldens | 6 + bare | 6 + bare | 6 + bare | 0 / 0 |
| Additional same-band right host | 1 (wrong) | 0 | 1 (wrong) | 1 / 0 |

Full-result comparisons omit only `analysis_version`. Matrix 2's Dan+Pat
cases already held, but now Pat's assignment score is zero and confidence is
low; the explanation includes Pat among the unresolved signers. Thus all 270
full results change even though only 135 statuses change. This is the expected
identity veto, with no fields or model calls in either Dan+Pat outcome.

[Counterfactual summary](counterfactual-summary.json) records counts and source
hashes. [Per-case evidence](counterfactual-cases.json) maps every case to all
three full results using SHA-256 keys, deduplicating repeated outcomes without
discarding result fields or case IDs.

## Goldens and review Low / Nit

All **seven complete real-worker results equal r4 and r5 exactly except
`analysis_version`**, including evidence, assignments, model metadata, and
geometry. They also equal r11 under the same comparison. Native conversions
match for every signer. Six satisfy `assert_golden`; `bare` remains `bare` with
no fields. No golden block has `uncertain_identity`.
[Results](placements.json) · [Comparison](golden-comparison.json).

**L-1:** The 204 `Signature:` controls retain their measured baseline:
198 holds and six correct C12 margin placements on signature 360/date 420,
all with zero model calls. The review corrected its earlier parenthetical;
no product or test change is needed for it. The full-result comparison against
r11 has zero differences. C12 has 96 holds and six placements; C13 has 102 holds.

**N-1:** The Boolean `subordinate_caption()` gate and its subsequent
`subordinating_host()` lookup are intentionally retained. Existing r8 tests
force the Boolean hook, so replacing that call with only the host lookup would
change their target. Both calls still use the same unchanged host helper;
the actual returned host is the one recorded in the tuple. Fix A changes the
retention decision after extents exist and therefore needs no alternate
host-selection implementation. The harmless duplicate loop remains explicit.

## Reproduction and full-suite verification

```bash
# Run before the product edit to reproduce failing first.
python3 docs/implementation/c2a-r12/run_summary.py failing-first-summary dealroom_sign/tests/test_placement_r12.py

# Complete signing suite; maxfail stops immediately if an existing test fails.
python3 docs/implementation/c2a-r12/run_summary.py full-suite-summary dealroom_sign/tests --maxfail=1

# Executed counterfactuals and exact real-worker goldens.
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r12/check_evidence.py

# Audit unchanged tests, edit scope, and execution hashes.
python3 docs/implementation/c2a-r12/check_preservation.py
```

The summary runner invokes the requested command with stop/reporting arguments:

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests --maxfail=1 --tb=short --junitxml=<temporary-report>
```

**Full suite: 3,301 passed, 0 failures, 0 errors, 0 skips, 82 warnings,
961.055 seconds.** This is all 2,910 existing cases plus 391 new r12 cases.
No existing-test failure occurred. [Summary](full-suite-summary.json) ·
[Every test result](full-suite-summary-cases.json).

[Preservation audit](preservation-summary.json) checks all 50 existing test and
fixture files byte-for-byte against HEAD, verifies that only `extract` changed
among product functions, and confirms matching production/test hashes across
failing-first, final-suite, and counterfactual execution. Historical evidence
and project memory are unchanged; the report is append-only, the index is
empty, and HEAD remains `0c190e9b`. `git diff --check` passes. Existing tests
were not weakened, skipped, deleted, edited, or re-targeted.

## Completion-marker delivery

The local [completion marker](counterparty-c2a-r12.done) was written after the
successful suite and preservation audit. It contains the requested first line
and five-line summary, with the unchanged HEAD SHA.

The subsequent copy to
`/root/worktrees/dealroom-sign-edd/docs/edd/briefs/counterparty-c2a-r12.done`
failed with exit code 1: **Read-only file system**. That destination is outside
this session's writable roots, and approval escalation is unavailable. The
external brief marker was therefore not written. The ready-to-copy local
marker contains the complete requested payload; this delivery is the only
unfinished action.
