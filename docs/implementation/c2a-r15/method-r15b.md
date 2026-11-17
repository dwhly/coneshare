# C2a r15b verification method

Baseline: `d88bfb889f3863796b276a6f0aef3da57539c4c3` (`c2a.14`).
The inherited r15 candidate and STOP evidence are retained. All new evidence
is in this directory with the `-r15b` suffix; no brief is edited.

## Rule

The column starts at `min(rule.x0, label.rect[0])`, using `rule.x0` when
there is no label. Rules on the same page with the same column start are
one column, extending to their maximum `rule.x1`. This preserves stacked
rules of different lengths, as in the offer golden. A different page never
competes. No vertical-distance cutoff is added to column ownership.

For a printed row `[row.x0, row.x1]` and column `[left, right]`, distance is
`max(left - row.x1, row.x0 - right, 0)`. A row can count only when every
other column's distance is **strictly more than 2 pt greater**. Overlap is
distance zero; equality at 2 pt fails closed. One column can own an
outdented row without a fixed distance limit. Existing raw extents and
stacked-row partitioning still determine vertical membership.

The complete page's blocks are passed to `printed_names` during extraction
and scoring. Raw evidence, ambiguous-identity checks, absorbed captions,
company-only restrictions, the r14 mixed-heading veto, redaction and field
geometry remain unchanged in the nearest-only candidate. It introduces one
wrong r3 witness placement, so the permitted combination with (b′) is also
measured. That combination replaces r14's mixed-heading propagation with the
prior generalised same-page, physical-row veto: snapshot every block's signer
scores, then zero a borrowing block's score if any peer extent containing its
name row has zero score. Peer references are removed before worker output.
The exact prior patch is adapted only to pass the new column-context argument.
The version remains `c2a.15` in both candidates.

## Failing first and unchanged tests

The inherited fixed 10 pt rule produces **24 failures / 51 passes** in the
75-case focused check: 18 new ownership cases and all six C12
`caption_row_right` heading variants fail. The initial nearest-interval
implementation passes those 75 checks, but treating differently sized
aligned rules as separate columns fails the offer golden. Four additional
aligned-column cases fail first against that implementation. Its already
started full suite is allowed to finish without `-x`; all failures are
retained separately, before installing the refined candidate.

New tests cover distances beyond the old cutoff, exact and near 2 pt ties,
overlapping rows, reversed block order, the label's part of a column,
unlabelled rules, distinct pages, and aligned stacked rules of equal and
unequal lengths. No pre-existing test or fixture is edited. The original
r15 M1/M2 tests also remain byte-for-byte unchanged.

## Expanded table and oracles

[The generator](check_evidence-r15b.py) reuses all 9,754 original cases and
the separately displayed 72-case L-1 subset. It additionally executes the
omitted fixture-free PDF control families from r2–r11 and r14, including
all four r10 signature variants and the six exempt-contact caption family.
Every original parametrization is expanded. A function making multiple
placement calls contributes a separately identified case for each call.

The unchanged original test functions run against r14, so their assertions
validate each added oracle. The same captured PDF, signer set and local
deterministic model replies are then evaluated against r14 and the new
candidate. The per-test inventory and results list every added family.
Helper-only unit checks, fixture-based synthetic extraction/transport/logging
tests and application/API tests remain covered by the full pytest suite;
they are not represented as PDF comparison cases. Already-enumerated
families and duplicate seven-golden tests are not re-added.

As in r15, wrong placements in M1/M2 and r14 geometry families include any
Pat field on our signature rule. Earlier controls use accepted field
geometry: a new placement from a required hold, or any changed fields in a
placed control, is flagged as wrong. Holds have zero fields. Transitions
and full-result differences are retained, including assignment diagnostics.
The seven goldens must match the archived r13 full results except
`analysis_version`; native fields are also compared. The 72-case L-1 subset
is excluded from the overall total, and controls can repeat geometry used
elsewhere, so the expanded total counts identified cases, not distinct PDFs.

Goldens, r14/r15 reproductions, r14 correct controls and the complete r10
`caption_row_right` family additionally use the real extraction worker;
their full results must match the in-process extraction/scoring path.
`OPENROUTER_API_KEY` and `PLACE_MODEL` are unset, HTTP sends raise, and all
model replies are local deterministic stubs. No external model is called.

## Required full suite

```sh
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r15/full-suite-r15b.xml
```

There is no `-x`, selection filter or maximum-failures override. The supplied
launcher itself disables pytest's cache. Its read-only scratch-directory
warning is retained in the log; the launcher and environment are unchanged.
Worker-created bytecode caches are removed after verification. Source and
test hashes, every suite outcome, failures, HEAD, index, memory, whitespace,
and cache/venv checks are recorded in the final audit.
