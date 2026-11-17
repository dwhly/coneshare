# r21 method

Base HEAD is `e0ed35e70be90f983fbe4701e758ad812e97e936`. The r20 review was
read first, alongside project memory. The initial SHA-256 inventory covers
all 1,905 tracked files. No starting test, fixture, evidence, completion marker,
memory file, HEAD, or index entry is changed.

New regression tests cover the two cross-page layouts × three recitals × ten
unnamed headings × two signer sets × two placeholder settings (240), the full
5,280 layout matrix, 12 exact B-2 worker/printed-name cases, 52 singular/plural
role cases, four combined roles, four real-person controls, two role-definition
checks and two L-1 checks. The inline PDF rows are kept in the new support module.

The initial run was on unchanged c2a.20. Two newly authored test details were
corrected during drafting: the role-definition test initially passed a positional
signer argument to `extract`, and the L-1 two-signer control initially expected
the whole document to place even though Dan retains his separate veto. The
final L-1 assertion requires Pat's high score in both configurations and retains
the whole-document hold with Dan. Both final L-1 tests and both corrected
role-definition tests also fail against the exact r20 source, via the isolated
baseline plugin. All original runs and draft source are retained. No starting
test or assertion was edited.

An initial B-2 candidate also made pure roles public identity labels. Historical
replay rejected 32 output differences: geometry was unchanged, but `RECIPIENT`
replaced `[redacted]` in accepted fields. The final candidate keeps output
redaction unchanged and excludes pure roles from `person_text` and the fallback
`unresolved_person` predicate. A role-only heading is tested before recital
alias expansion in the unnamed-party guard. This also holds the alias-conflict
case where an own-block role resolves to the other company's name. Initial
candidate source snapshots and replay outputs remain available; final evidence
has the `release-` prefix.

Each replay runs five cumulative variants: r20, exact fix3, fix3+B-2,
fix3+B-2+ROLE_DEF, and final r21 with L-1. ROLE_DEF and L-1 use the exact r20
candidate transformations. Every original r20 family is regenerated, and every
r20 result is checked against its archived full result apart from version.
The old coordinate oracles and the reviewer-permitted competition/Q4 exceptions
are reused unchanged; raw flags remain in the JSON evidence.

The literal inline-row matrix and the reviewer-style recital matrix are separate
runs. The latter applies the 95-character wrap from `/tmp/rev19/q1real.py` to
the review's recital text. The 1,800 cross-page cases are the guarantor and split
subsets with an unnamed heading and an affiliate. Every new matrix field must
be inside its own signer's page, column and By/Date span; NAME fields are included.

HTTP is patched to fail and model credentials/configuration are removed. Existing
deterministic model mocks remain in historical tests; the unusual golden retains
its one mocked call. Seven goldens run through both in-process extraction and
isolated real workers, and native fields are compared too. B-2 exact worker
cases also require equality to in-process results. Temporary databases and
worker packages are confined to this evidence directory and removed on exit.

The full suite is the same complete Send backend suite as r20:
`dealroom_sign/tests`, with no `-x`, skips or deselections. Test IDs are compared
to all 18,376 r20 IDs. The final preservation audit checks every starting file,
HEAD and index, and checks that every release replay measured the shipped source.

Commands from the repository root use
`/root/work/sign-product/send-venv/bin/python` and `PYTHONDONTWRITEBYTECODE=1`:

```sh
python docs/implementation/c2a-r21/run_tests.py dealroom_sign/tests/test_placement_r21.py --tb=short --junitxml=.../failing-first.xml
python docs/implementation/c2a-r21/run_tests.py dealroom_sign/tests/test_placement_r21.py dealroom_sign/tests/test_placement_r21_l1.py --tb=short --junitxml=.../targeted.xml
python docs/implementation/c2a-r21/run_tests.py dealroom_sign/tests --junitxml=.../full-suite.xml
R21_RUN_PREFIX=release- python docs/implementation/c2a-r21/check_evidence.py historical
R21_RUN_PREFIX=release- python docs/implementation/c2a-r21/check_evidence.py review
R21_RUN_PREFIX=release- python docs/implementation/c2a-r21/check_layouts.py
R21_RUN_PREFIX=reviewer- python docs/implementation/c2a-r21/check_reviewer_matrix.py
python docs/implementation/c2a-r21/audit.py
```
