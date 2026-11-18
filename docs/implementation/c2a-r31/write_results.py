"""Write the final report and, last, the completion marker after release audit."""
from collections import Counter
import gzip
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
bars = json.loads((OUT/'release-bars.json').read_text())
assert bars['rc'] == 0 and not bars['blockers']
families = json.loads((OUT/'family-comparison.json').read_text())
preserved = json.loads((OUT/'preservation-summary.json').read_text())
extraction = json.loads((OUT/'extraction-verification.json').read_text())
with gzip.open(OUT/'every-n-to-p.json.gz', 'rt') as stream:
    recoveries = json.load(stream)
breakdown = {axis: Counter(str(r['case']['axes'][axis]) for r in recoveries)
             for axis in ('layout','signer','datefirst')}
rows = []
for family, f in families.items():
    transitions = []
    for base in ('r29','r28','r21'):
        c=f['comparisons'][base]
        transitions.append(f"{c['n_to_p']} / {c['c_to_w']} / {c['n_to_W']}")
    rows.append(f"| {family} | {f['cases']} | {f['policy_controls']} | " + ' | '.join(transitions) + ' |')
comparison = []
for base,c in bars['comparisons'].items():
    comparison.append(f"| {base} | {c['n_to_p']} | {c['c_to_w']} | {c['n_to_W']} | {c.get('c_to_n',0)} |")
report = f'''# C2a r31 results

**coder rc=0. `VERSION = 'c2a.31'`.** Base HEAD `{bars['head']}` remains unchanged; comparison base is live **c2a.29**, not rejected c2a.30. Final source SHA-256 `{bars['source_sha256']}`. No staging or commit.

**B-1: 0 wrong in all 18,432 cells (9,216 each direction). M-1: 686/686 recovered correctly. Full Send suite: 80,088 passed / 0 failed / 0 errors / 0 skipped.** [Release audit](release-bars.json), [tested source](shipping-source.py.txt), [source provenance](source-provenance.json).

## What changed

The 22–50 pt Date-first band is provisional until signer preparation. A name that can receive fields must match a supplied signer's full name, and the signer's explicit company or non-generic email domain must match this block's heading or recital-mapped party. A different mapped party vetoes expansion, including an affiliate that shares domain tokens. Missing or incompatible ownership restores the r29 boundary hold.

Expansion also requires no competing same-page stack for that signer. An unnamed same-company or unresolved block, a block printing the same name, an unclaimed hidden signing stack, or a ruled block that extraction could not attribute prevents expansion. A separately named person or clearly different company can account for a peer. Completed stacks, intervening signing rules, the 50 pt cap and the original column/contact/heading boundaries remain in force.

The guard runs before evidence redaction. Provisional printed names are cleared before worker serialization. Scoring, assignment, placement geometry and model eligibility are unchanged; failed ownership adds a boundary veto rather than removing competing identity evidence.

An unrequested full name remains non-signable competition: the existing full-name mismatch rule gives its block score zero for every supplied signer. It cannot receive fields using the wider band. Keeping this distinction preserves four valid company-only M-1 recoveries on the other company's separate block, without adopting the unrequested name for anyone.

## Reviewer extraction and failing first

Extracted **{extraction['commands']} Bash inputs, {extraction['heredoc_bodies']} heredoc bodies and {extraction['write_payloads']} Write payloads byte-for-byte** from the requested Gate 3 r30 JSONL into `backend/dealroom_sign/tests/fixtures/r31/`, including `band.py` and `repro.py`. Also reconstructed the ten scripts copied by the reviewer's call 10 from their frozen prior payloads and its exact revision-hash substitutions, and verified byte equality against `/tmp/r30rev/`. The inherited generator bodies are unchanged. [Extraction verification](extraction-verification.json), [copy provenance](copied-generator-provenance.json), [body equality](generator-body-verification.json).

Before modifying production code, the full new B-1 file completed on untouched c2a.30: **3,068 failed / 15,400 passed / 0 errors / 0 skipped**. These are precisely **3,040 matrix failures (1,520 per direction)** and **28 of the 36 exact real-worker cases**. Supplemental ownership controls produced 14 failures and 4 passes; unclaimed ruled-stack controls 2 failures; affiliate/recital controls 1 failure and 1 pass. Total failing first: **3,085 failed / 15,405 passed / 0 errors / 0 skipped**. [Matrix/worker evidence](failing-first.txt), [ownership](ownership-failing-first.txt), [unclaimed stack](unclaimed-failing-first.txt), [recital](recital-failing-first.txt).

All new regression assertions and fixtures remain hash-identical to their failing-first snapshots. Four new test files add 18,490 tests; one new helper captures the exact reviewer generators. No existing test or fixture was edited, skipped, weakened, deleted or retargeted.

## Variant measurements

| Variant | M-1 recoveries / 686 | M-1 wrong | B-1 result |
| --- | ---: | ---: | --- |
| Reviewer suggestion: require every expanded name to match a supplied signer and its party | 682 | 0 | plain: 0 wrong / 9,216 |
| Same check plus unclaimed-peer guard | 682 | 0 | not separately swept |
| Peer guard with unrequested names retained as non-signable competition | 686 | 0 | plain and swap: 0 wrong / 18,432 |
| Shipped: above plus unattributed-rule and conflicting-recital-party vetoes | **686** | **0** | **plain and swap: 0 wrong / 18,432** |

The literal suggestion loses only Date-gap-30, `v=none`, `fleetname=dan`, domain/explicit Pat-only cases in side and stacked layouts. Dan's unrequested printed name cannot score for Pat; Pat's correct fields are on HLA's separate unnamed ruled block. The shipped variant retains these four without relaxing ownership for any adopted signer. All 686 correct M-1 recoveries is the maximum possible. [Suggestion measurement](suggestion-date-summary.json), [shipped M-1](shipping-date-summary.json), [plain](shipping-plain-summary.json), [swap](shipping-swap-summary.json).

The shipped B-1 matrices are exactly live r29: each direction has **768 correct placements and 8,448 holds**. All 3,040 r30 wrong placements become holds. The broader r30 band's additional correct B-1 placements (760 plain / 456 swap) also return to r29 holds because they do not satisfy the ownership guard; they are outside M-1.

## Every release comparison

Every cell below is **n → p / c → w / n → W**, with n → W checked explicitly against live c2a.29 in every family. All newly placed cells are correct; no other family gains a placement. Every unchanged output equals r29 except `analysis_version`. The 686 new M-1 outputs equal the correct r28 output, including fields, assignments and evidence. [Every n → p, with case axes and output](every-n-to-p.json.gz), [family comparisons](family-comparison.json), [all inherited subgroups](group-comparison.json).

| Baseline | n → p | c → w | n → W | c → hold |
| --- | ---: | ---: | ---: | ---: |
''' + '\n'.join(comparison) + f'''

M-1 recovery breakdown: layout `{dict(breakdown['layout'])}`; signer `{dict(breakdown['signer'])}`; Date gap `{dict(breakdown['datefirst'])}`. All **2,844 M-1 cells** have 0 wrong; final outcomes are 2,211 correct placements and 633 holds.

The five H-1 matrices contain **4,482 cells**: hidden 1,008 (including conformed and two-column-row shapes), two columns 288, no rule 648, geometry 1,728, ruleless name 810. Each has 0 wrong and no new placement versus live. The exact r27 matrix remains **700 holds / 0 wrong**. The inherited r16–r30 families are covered by 27 collections, **82,450 cells with 0 raw wrong**, and the complete existing test suite. Collections overlap; totals are not deduplicated.

The **876 inherited raw-oracle flags** below are established named-party policy controls, not new wrong placements. The reviewer archives mark the stacks/r27/recitals/notices rows as retained controls; the twelve stray-name flags retain the same earlier in-column named-Pat policy. All 876 outputs are identical to r29 and r28. These are disclosed rather than silently relabeled or removed; the immutable r13 L-2 policy control still passes all 40 cases. There are **0 wrong placements after the established policy controls, 0 c → w and 0 n → W in every family**.

| Family | Cells | Unchanged policy controls | vs live r29 | vs r28 | vs r21 |
| --- | ---: | ---: | --- | --- | --- |
''' + '\n'.join(rows) + f'''

Historical baseline sources match their Git commits. Inherited baseline results come from immutable r29 archives with complete case-key coverage checked; the shipping candidate executes every generated cell. The current reviewer matrices execute fresh r29/r28/r21/r30/r31 modules. Seven goldens and their native-field conversions are exact except `analysis_version`.

All 21 exact inherited reviewer worker cases remain holds and match in-process results. The full suite passes all 36 exact B-1 worker cases and the existing ten M-1 worker recoveries. The inherited replay checks 245 candidate worker evaluations; the prior reviewer replay checks six more. External HTTP calls are zero throughout the matrix/worker evidence; mock-model counts match the baselines.

## Full suite, nits and preservation

**80,088 passed / 0 failed / 0 errors / 0 skipped**, completed without `-x`, retries, skip filters or test-selection omissions. Four isolated pytest processes use separate scratch SQLite databases; the merged JUnit IDs equal the full collection exactly. All **61,598 pre-existing test IDs** are preserved, plus **18,490 new IDs**. [Completion ledger](shipping-full-suite-completion.json), [JUnit](shipping-full-suite-complete.xml), [partition manifest](shipping-full-suite-manifest.json).

Command: `PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r31/run_full_suite_shipping.py`.

N-1: Git confirms HEAD and the exact source provenance; SHA-256 independently confirms **{preserved['unchanged']}/{preserved['inventoried']} pre-existing tracked files unchanged**, with only placement.py differing. This includes every old test, fixture, evidence file and `.done` marker. N-2: both close-spacing directions now have permanent must-not-place-wrong regressions and explicit live-r29 n → W bars. [Preservation audit](preservation-summary.json).

All new evidence files are below 20 MB. **Blockers: none.** No staging, commit, deployment, migration or configuration change. Project memory is unchanged.
'''
(OUT/'results-r31.md').write_text(report)
marker=f'''coder rc=0 head={bars['head']}
failing-first: 3085 failed, 15405 passed, 0 errors, 0 skipped; B-1 matrix 3040 failures (1520 each direction), exact workers 28 failures.
shipped: c2a.31; source sha256={bars['source_sha256']}; adopted-name company/role ownership, conflicting mapped-party veto, same-page unclaimed-stack/rule veto; unrequested names remain non-signable competition.
M-1: 686/686 correct recoveries; B-1 18432 cells 0 wrong; H-1 4482 cells 0 wrong; exact r27 700 cells 0 wrong; inherited 82450 cells 0 raw wrong; seven goldens exact except analysis_version.
vs live c2a.29: n->p=686, c->w=0, n->W=0 in every family; every n->p is a correct M-1 recovery, individually recorded. Vs c2a.28 and r21: c->w=0, n->W=0. 876 pre-existing named-party raw-oracle policy controls unchanged; r13 L-2 all 40 pass.
full suite: 80088 passed, 0 failed, 0 errors, 0 skipped; complete without -x; all 61598 prior test IDs preserved.
test changes: four new test files, one capture helper, exact r30 reviewer fixtures; 18490 added tests; no existing tests/fixtures/evidence/.done markers changed; frozen failing-first hashes verified.
preservation: {preserved['unchanged']} pre-existing tracked files hash-identical; placement.py only existing change; all new evidence below 20 MB; no staging or commit.
blockers: none. Results: docs/implementation/c2a-r31/results-r31.md.
'''
(OUT/'counterparty-c2a-r31.done').write_text(marker)
print('Wrote results-r31.md and completion marker last')
