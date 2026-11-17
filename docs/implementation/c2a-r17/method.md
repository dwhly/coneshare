# Method and commands

Base HEAD: `75837b04da05c3b736d6f48648536627bd062ca0` (c2a.16).
The review was read from the user-specified
`/root/worktrees/dealroom-sign-edd/docs/edd/reviews/counterparty-c2a-gate3-r16.md`.

Before edits, SHA-256 hashes were recorded for all 1,636 tracked files.
Production source was unchanged for both failing-first runs. The sole permitted
existing-test edit is N-1's party score, from 6 to 0; its witness-zero assertion
remains unchanged. New tests live only in `test_placement_r17.py`.

The first candidate implements the review's one-line B-1 direction and the
company-heading gutter guard. Its source is preserved in
`first-candidate-placement.py.txt`. All four direct heading checks and A2 pass,
but 112 wider-sweep cases still place Pat incorrectly because extraction drops
witness rules lacking a heading and a name within 22 pt. Those same tests pass
when extraction retains explicit witness/attestation rules as zero-score blocks.
The initial failed targeted run is preserved as `targeted-green.*`; retention
then passed the 4,158 targeted cases in `targeted-retained-witness.*`. The first
complete suite found one existing r11 structural assertion failure (1 failed,
15,497 passed). That completed run and source are archived under
`retained-witness-candidate/`. Retention was narrowed to preserve the existing
absorbed-name veto path, without editing the r11 test. `r11-preserved.*` and
`targeted-final.*` verify the final candidate before the final full suite.

The comparison imports the unmodified r16 evidence generator and its earlier
oracles. It reconstructs r16 from `git show 75837b04:...`, independently replays
every archived result (ignoring only analysis_version), and verifies every
family count. A B-1-only module proves the measured one-line change preserves
every r16 family's counts. The final module is read from the working tree.
A separate optional L-1 module is built in memory, with its exact source archived.
It is rejected after six direct extracted-block ownership checks produce wrong
placements; see `l1-decision.md` and `check_l1_witness.py`.
No existing fixture, test oracle, or prior evidence file is edited.

All new family axes and expected signer-rule geometry are explicit in
`test_placement_r17.py` and `l1_candidate.py`. Both signature and date fields
must lie on their own signer's rules. A witness family must hold because Pat's
name is under a witness/attestation rule. The F family permits correct placement
or a hold and rejects any third-party signature/date field.

All seven complete goldens are compared with `c2a-r13/placements.json`, ignoring
only `analysis_version`; native fields are also exact. Selected reproductions,
controls, and goldens use real workers as well as in-process extraction. Each
historical worker runs its own isolated source package, rather than accidentally
launching the working-tree implementation. Temporary packages are removed.
External model keys are removed, HTTP sends raise, and all model callbacks are
local deterministic mocks. Full results, source hashes, model-call counts,
wrong flags, and transitions are retained.

Commands run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r17.py dealroom_sign/tests/test_placement_r16.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r17/failing-first.xml > docs/implementation/c2a-r17/failing-first.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r17.py -k crossing_heading --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r17/failing-first-heading.xml > docs/implementation/c2a-r17/failing-first-heading.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r17.py dealroom_sign/tests/test_placement_r16.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r17/targeted-retained-witness.xml > docs/implementation/c2a-r17/targeted-retained-witness.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r17.py dealroom_sign/tests/test_placement_r16.py dealroom_sign/tests/test_placement_r11.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r17/targeted-final.xml > docs/implementation/c2a-r17/targeted-final.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r17/check_evidence.py > docs/implementation/c2a-r17/counterfactual-run.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r17/full-suite.xml > docs/implementation/c2a-r17/full-suite.txt 2>&1
python3 docs/implementation/c2a-r17/final_audit.py
python3 docs/implementation/c2a-r17/write_results.py
```

The full suite has no `-x`, maximum-failures override, deselection, skip, or
retargeted fixture. It uses the unchanged supplied launcher, whose known
scratch-directory warning remains in the log. JUnit is parsed to count every
passed/failed/error/skipped outcome. Final audit also verifies source identity,
HEAD, index, memory, all original hashes, and whitespace.
