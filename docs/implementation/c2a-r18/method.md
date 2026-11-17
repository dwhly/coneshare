# Method and commands

Baseline HEAD: `465e5afa408a219caa4288b762f0c71ce54f16bf`, after r17
`1084b075` and the manager's restoration of the r16 `.done` marker.
The user-specified Gate 3 r17 review was read first. Before edits, SHA-256
hashes were saved for all 1,698 tracked files, together with HEAD and the index.
The only permitted existing-test edit is the r17 docstring's
`Gate 3 r16:` → `Gate 3 r16 findings:`. No existing test, fixture,
or evidence file is otherwise edited or retargeted.

The 1,536-case affiliate generator reconstructs every stated review axis,
including the verbatim real-worker reproduction. Its independent field oracle
allows only each signer's original signature/date rules, never the affiliate.
Production still equaled r17 during the initial 1,538-case pytest run, the
20-case identity run, and the complete matrix baseline recording. That baseline
matches the review's 320 wrong / 96 correct / 1,120 holds, including 80 wrong
for each of four affiliate headings, all PAT-only, and 64 ordinary-length
Harbor headings. All initial failures are preserved.

B-1 is tested independently before considering optional L-1. Focused score
checks cover direct, role-mapped, behalf-prefixed, and combined normalization,
both crossing directions, authoritative printed names, and a different-company
crossing heading. All 1,558 B-1 tests pass. The B-1 production source and the
optional L-1 source are archived separately. L-1 is first measured on F and
both F-gap families: 1,152 cases, no full-result changes, zero wrong.
After both candidates passed the full replay, 88 new L-1 boundary/PDF tests
ran against B-1 alone (20 failed / 68 passed). The final two geometry comparisons
were then applied, making production byte-identical to the evaluated L-1
candidate. See `l1-decision.md` for the measured recovery and exact axes.

The replay runner imports the untouched r17 evidence generators and oracles;
their `main()` functions are never called, so they do not rewrite old evidence.
Historical r17 is reconstructed from `git show 1084b075:...`. Every archived
r17 result and per-family count is checked before evaluating the candidates.
The new affiliate matrix and verbatim reproduction are added as separate
families. All sources run in process; selected reproductions and all seven
goldens also run in isolated real worker packages containing the corresponding
source. Temporary packages live under this new evidence directory and are
removed automatically. No existing fixture or test target is replaced.

All seven goldens are compared with `c2a-r13/placements.json`, ignoring only
`analysis_version`; native field conversion is checked exactly. Results,
source hashes, model-call counts, wrong flags, transitions, and worker results
are retained. `OPENROUTER_API_KEY` and `PLACE_MODEL` are removed, and
`httpx.Client.send` raises. All model responses are deterministic local mocks.

Commands are run from the repository root with the supplied interpreter and
unchanged launcher:

```sh
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r18.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r18/failing-first.xml > docs/implementation/c2a-r18/failing-first.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r18.py -k normalizes --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r18/failing-first-identity.xml > docs/implementation/c2a-r18/failing-first-identity.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r18.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r18/targeted-b1.xml > docs/implementation/c2a-r18/targeted-b1.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r18/check_evidence.py --preflight > docs/implementation/c2a-r18/l1-preflight.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r18/check_evidence.py > docs/implementation/c2a-r18/counterfactual-run.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r18.py -k l1 --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r18/failing-first-l1.xml > docs/implementation/c2a-r18/failing-first-l1.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests/test_placement_r18.py --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r18/targeted-final.xml > docs/implementation/c2a-r18/targeted-final.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r18/full-suite.xml > docs/implementation/c2a-r18/full-suite.txt 2>&1
python3 docs/implementation/c2a-r18/finalize.py
```

The full suite uses no `-x`, maximum-failures override, selection filter, skip,
or retargeted fixture. JUnit is parsed for all outcomes, including errors and
skips, and all original 15,498 node identities must remain. The launcher's
existing scratch-directory warning is retained in the logs. Finalization
requires exact protected-file hashes, the sole permitted docstring edit,
unchanged HEAD/index/memory, clean whitespace, a source hash matching the
evaluated candidate, zero wrong, exact goldens/native fields, and a fully
passing suite. It writes `results-r18.md` and then the new `.done` marker last.
