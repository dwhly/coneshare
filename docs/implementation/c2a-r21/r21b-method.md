# r21b method

Base HEAD remains `e0ed35e70be90f983fbe4701e758ad812e97e936` and
`VERSION = 'c2a.21'`. The incoming r21 candidate and its evidence were inventoried
in `r21b-starting-state.json` before implementation edits. The r20 Gate 3 review
and the existing r21 notes were read. No staging, commits, or memory edits.

## Manager authorization

The manager explicitly authorized changing only the `different_page` control's
expectation in `test_placement_r20_boundaries.py` from 4 to the document-wide hold
score 0. The other controls retain their original expectation expression exactly.
The NORTHWIND mapped-role parameter and its expectation of 4 remain byte-identical.
The audit reconstructs the entire allowed test file from HEAD and requires exact
equality, in addition to hashing every other incoming file.

## Production correction and failing-first evidence

The initial 14-test boundary run reproduced both r21 failures. Classifying the
resolved heading instead of the literal role fixes the NORTHWIND control. A
complete targeted run of the prior r21 additions and r20 boundaries then found
one remaining failure: the `discloser-False-` role-vocabulary case. Its recital
maps the role to Fleet, but a separate Fleet block also exists. Two unnamed
signatures claim the same role's named company, so that role assignment remains
ambiguous. A unique NORTHWIND mapping has no such conflict.

The final correction keeps the resolved heading named and separately holds
domain-only placement when another block claims its company without independent
printed-person evidence. This check applies across pages. Explicit company and
printed-name paths retain their existing behavior. Eight new regressions cover
two role spellings, two page arrangements, and printed/unprinted peer controls;
the four unprinted cases fail before this refinement, while the four printed
controls pass. All eight pass after it. No existing test other than the authorized
assertion changed. Forty-two additional score controls cover missing, empty,
role-word and named-company mappings.

The first simple-narrowing suite and four replay runs were interrupted after
the targeted test exposed this failure. Their partial logs and source snapshots
are retained as `r21b-*` draft evidence. They are not completion evidence.
Final full-suite and replay evidence uses `r21b-final-*` filenames.

## Final execution

All commands run from the repository root with `PYTHONDONTWRITEBYTECODE=1` and
`/root/work/sign-product/send-venv/bin/python` as the interpreter (`PY` below).

```sh
PY docs/implementation/c2a-r21/run_tests.py dealroom_sign/tests --tb=short --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r21/r21b-final-full-suite.xml
PY docs/implementation/c2a-r21/r21b_replay.py historical
PY docs/implementation/c2a-r21/r21b_replay.py review
PY docs/implementation/c2a-r21/r21b_replay.py layouts
PY docs/implementation/c2a-r21/r21b_replay.py reviewer
PY docs/implementation/c2a-r21/r21b_audit.py
```

The full suite uses the same complete `dealroom_sign/tests` scope as r20/r21,
without `-x`, filtering or deselections. The focused alias run's 5,520 deselections
are only its explicit `-k` filter; the final full suite includes those tests.

`r21b_replay.py` loads the preserved r21 generators and oracles unchanged. It
applies the two production refinements only to the B-2 and subsequent cumulative
variants, checks byte equality to production, and selects fresh output prefixes.
Each replay evaluates r20, fix3, B-2, ROLE_DEF and final r21. Network/model
isolation, real-worker comparisons, the seven exact goldens and native-field
comparisons remain in the original harnesses. Reviewer-approved Competition and
Q4 classifications remain unchanged, with raw flags retained.

The final audit checks the 1,905-file r20 inventory and the 1,999-file incoming
r21 inventory, all previous test IDs, the exact authorized test diff, production
source equality, all family results and golden invariance. `results-r21.md` is
the only existing evidence document authorized for update. Every other original
test, fixture, evidence file and completion marker must retain its SHA-256.
