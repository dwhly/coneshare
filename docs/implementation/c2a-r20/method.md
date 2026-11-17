# r20 method

The r19 Gate 3 review was read before investigation. Starting HEAD was
`ddfcc595041f5db88e59024670ac37aa0b9349a6`, with a clean worktree. The initial
SHA-256 inventory covers all 1,846 tracked files and records the index inventory.
No existing test, fixture, evidence file, or completion marker is edited.

The exact reviewer `q1worker.py`, `q1real.py`, and `run.py comp` were executed
against unchanged production c2a.19 before any production edit. Their outputs
and input script bytes are retained here. Both worker signer configurations
place Pat on Group before fix2. The exact competition generator reports 240 raw
oracle flags; the review identifies 144 as blocking and permits the other 96
only when Chris Jones is printed in the unnamed block. The original oracle and
allowed coordinates remain unchanged. The new assertions narrow the permitted
exception to those printed-name cases and retain both raw and adjudicated counts.

The exact realistic script reproduces 34 wrong out of 48 here (address 12,
hereinafter 12, parsed 4, no recital 6), rather than the review prose's 38. The
copied matrix produces the same 34 failures. No cases were removed or adjusted
to obtain the review's stated count. All 48 must hold in r20.

The new tests ran failing-first against unchanged c2a.19: the 530 PDF/worker
cases had 180 failures and 350 passes; 14 scope controls then had 5 failures and
9 passes. Their JUnit reports precede the production edit. All 544 pass after
the fix. The new case support module copies the realistic input generator,
worker rows and Q4 inputs into the repository; it imports nothing from `/tmp`.
The exact 480-case competition generator was already copied verbatim in r19
and is reused unchanged.

Production ships the reviewer's fix2 plus two explanatory comments and the
version bump. `audit.py` reconstructs fix2 from the preserved review sources
without importing their harness, and compares the complete production AST,
ignoring only the version value and comments.

`check_evidence.py` imports earlier generators without executing their `main`
functions. It runs r19, r20, and three optional proposals from isolated source
copies. Every archived r19 result is checked against a fresh evaluation, ignoring
only `analysis_version`. All generated worker packages live in this directory
and are removed by `TemporaryDirectory`. HTTP is blocked and credentials/model
configuration are removed. Historical deterministic model mocks are retained,
including the unusual-label golden; no live model service is used.

Each optional proposal starts from B-1-only r20 and is measured independently:

- `role_def`: an additional bounded recital grammar allows descriptive text
  after a legal suffix and optional `hereinafter` wording.
- `l1`: unambiguous printed-name evidence bypasses only the shared-heading page
  flag. Earlier geometric, mixed-company and raw-identity vetoes remain active;
  scoring still requires the exact signer's printed name.
- `m1`: using scores before redaction, remove domain-only credit on 3+ party
  pages when another named, non-matching party is identified by no supplied
  signer. The source preserves original scores while evaluating the guard so
  traversal order cannot cause further holds.

Hold costs and recoveries are relative to B-1-only r20; B-1's own costs are
relative to r19. The six Q4 named-company ambiguity cases are reported with
their raw oracle flags separately, consistent with the review's M-1
classification. They are not silently treated as correct coordinate matches.

The full Send backend suite runs with the same environment as the prior local
runner, with temporary databases confined to this repository. It selects
`dealroom_sign/tests`, as in the r19 full-suite evidence, without `-x`, skips,
deselections, or test modifications. The final audit compares every test ID
with the r19 full suite, in addition to hashing the old files.

Commands from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r20/run_tests.py dealroom_sign/tests/test_placement_r20.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r20/failing-first.xml > docs/implementation/c2a-r20/failing-first.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r20/run_tests.py dealroom_sign/tests/test_placement_r20_boundaries.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r20/failing-first-boundaries.xml > docs/implementation/c2a-r20/failing-first-boundaries.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r20/run_tests.py dealroom_sign/tests/test_placement_r20.py dealroom_sign/tests/test_placement_r20_boundaries.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r20/targeted.xml > docs/implementation/c2a-r20/targeted.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r20/run_tests.py dealroom_sign/tests --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r20/full-suite.xml > docs/implementation/c2a-r20/full-suite.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r20/check_evidence.py historical > docs/implementation/c2a-r20/historical-replay.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r20/check_evidence.py review > docs/implementation/c2a-r20/review-replay.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r20/audit.py > docs/implementation/c2a-r20/audit.txt 2>&1
```
