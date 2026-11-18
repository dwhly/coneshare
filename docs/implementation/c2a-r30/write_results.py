"""Write the requested report and completion marker only after all bars pass."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
bars=json.loads((OUT/'release-bars.json').read_text())
assert bars['rc']==0
families=json.loads((OUT/'family-comparison.json').read_text())
vs=json.loads((OUT/'vs-live.json').read_text())
preservation=json.loads((OUT/'preservation-summary.json').read_text())
extraction=json.loads((OUT/'extraction-verification.json').read_text())
rows=[]
for family,data in families.items():
    counts=data['counts']; comp=data['comparisons']
    cells=data['cases']; wrong=counts.get('r30_w',0)
    values=[family,str(cells),str(wrong)]
    for base in ('r29','r28','r21'):
        c=comp[base];values.append(f"{c.get('n_to_p',0)} / {c.get('c_to_w',0)} / {c.get('n_to_W',0)}")
    rows.append('| '+' | '.join(values)+' |')
measure=[]
for family in ('date','hidden','two_columns','no_rule','geometry','ruleless_name'):
    d=json.loads((OUT/f'suggestions-{family}-summary.json').read_text())['counts']
    b=json.loads((OUT/f'bounded-{family}-summary.json').read_text())['counts']
    r=families['review/'+family]['counts']
    if family=='date':
        values=['M-1 correct recoveries',str(d.get('r29_to_heading_or_rule_nc',0)),str(d.get('r29_to_row_pitch_nc',0)),str(b.get('r29_to_bounded_pitch_nc',0)),'686']
    else:
        values=[family+' raw wrong',str(d.get('heading_or_rule_w',0)),str(d.get('row_pitch_w',0)),str(b.get('bounded_pitch_w',0)),str(r.get('r30_w',0))]
    measure.append('| '+' | '.join(values)+' |')
summary=[]
for base in ('r29','r28','r21'):
    c=vs['totals'][base]
    summary.append(f"| {base} | {c.get('n_to_p',0)} | {c.get('c_to_w',0)} | {c.get('n_to_W',0)} | {c.get('c_to_n',0)} |")
report=f'''# C2a r30 results

**coder rc=0.** `VERSION = 'c2a.30'`. Base HEAD `{bars['head']}`. Release source SHA-256 `{bars['source_sha256']}`. No staging or commit. [Release checks](release-bars.json), [tested source](shipping-source.py.txt), [baseline provenance](source-provenance.json).

## Shipped

**M-1: all 686/686 regressions recovered, with 0 wrong in all 2,844 Date-first cells.** The final matrix has 2,211 correct placements and 633 holds, exactly matching c2a.28 and r21 except `analysis_version`. Every recovered output, including fields, assignments and evidence, matches its correct c2a.28 result.

Only the Date-boundary predicate and version changed. A Date-first block without an intervening signing rule uses two By/Date row pitches, with the existing 22-point floor and a 50-point cap. This accommodates the blank row and the reviewer's largest offset while retaining a finite boundary before detached ruleless names. Text between By and Date marks an already populated stack, which retains 22 points. The column, party-heading and contact checks are unchanged, as are scoring, assignment, geometry, model eligibility, validation and the page-wide hold.

The predicate can only remove an r29 hold: every examined Date must first satisfy the original 22-point crossing condition, and its new band is never smaller. Every existing r29 placement is byte-equivalent except `analysis_version`; only the 686 correct M-1 holds become placements in the measured corpus. [Structural proof](structural-proof.json).

## Reviewer sources and failing first

Extracted **{extraction['bash_commands']} Bash command inputs, {extraction['heredoc_bodies']} heredoc bodies and {extraction['write_payloads']} Write payloads byte-for-byte** from the requested Gate 3 r29 JSONL into `backend/dealroom_sign/tests/fixtures/r30/`. This includes the exact `q3new.py`, `stray.py`, `datefirst.py`, worker generators and review text. Capture adapters execute the original generator bodies without changing cases, coordinates or oracle rules. [Extraction verification](extraction-verification.json).

The untouched c2a.29 baseline reproduces exactly **686 c2a.28 correct-placement → hold transitions**. The full new Date-first test file initially produced **6 failed / 2,848 passed / 0 errors / 0 skipped**; all six failures were real-worker gaps 22, 24 and 30 in both layouts. A separate test file freezes all 686 correct c2a.28 outputs and initially produced **686 failed / 0 passed / 0 errors / 0 skipped**. All new assertions and fixtures remain hash-identical to failing first. [Baseline matrix](baseline-date-summary.json), [worker/matrix failing first](failing-first.txt), [686 recovery failures](recoveries-failing-first.txt).

## Both suggested approaches measured

| Measure | Heading or another rule | Unbounded two-row pitch | 44-point bounded trial | Shipped scoped 50-point band |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(measure)}

Both broad suggestions recover all 686 but reopen wrong H-1 placements, so neither ships as proposed. The 44-point trial preserves H-1 but leaves 34 `dy30` / Date-gap-30 cells held: their Name text begins about 48 points below Date. The shipped cap recovers these while maintaining zero H-1 wrong; it also restricts the expansion to Date-first stacks without another signing rule.

The `hidden` family includes 144 conformed cells and 144 `two_col_rows` cells; each has 0 wrong in the shipped source. [Per-shape measurements](hidden-shape-comparison.json). All **4,482 H-1 cells** have 0 wrong: hidden 1,008, two-column 288, no-rule 648, geometry 1,728 and ruleless-name **810**. The exact r27 matrix has **700/700 holds and 0 wrong**. No case was removed or retargeted.

## Required families and baseline comparisons

All **82,450 inherited cells in 27 collections have 0 raw wrong**, covering the r16–r29 families and seven goldens. Historical sources match their Git commits. The candidate executes every cell; inherited baselines come from immutable r29 archives, with baseline source hashes and complete case-key coverage verified. New reviewer matrices freshly execute r29, r28, r21 and r30. Prior reviewer families use their immutable r29 result archives with source hashes and exact case axes checked. Collections overlap; totals are not deduplicated.

Seven goldens and their native-field conversions are exact except `analysis_version`. The 21 exact r29 worker cases all hold and match in-process results, with zero model/HTTP calls. The inherited replay checks 245 candidate worker evaluations, and the earlier six reviewer worker cases also agree. The full suite exercises the ten new Date-first workers. External HTTP calls are zero throughout the matrix replays; mock-model counts match r29.

| Baseline | n → p | c → w | n → W | c → hold |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(summary)}

Every `n → p` is a correct M-1 recovery that r28 placed correctly; **no other family gains a placement**. [All transitions](vs-live.json), [per-family data](family-comparison.json), [every inherited subfamily](group-comparison.json).

Each comparison cell below is **n → p / c → w / n → W**. Raw flags retained under the established named-party policy are explicit; they are unchanged from r29 and r28, never new or moved placements.

| Family | Cells | r30 raw flags | vs r29 | vs r28 | vs r21 |
| --- | ---: | ---: | --- | --- | --- |
{chr(10).join(rows)}

## Lows and nits

**L-1:** all 2,916 stray-person cells are unchanged from r29, including the eight intended company-only holds and the twelve pre-existing in-column named-Pat policy flags. No relaxation or new placement ships for this low. The 792 ordinary offset/wrapped/aligned-name cells remain 627 correct placements and 165 holds, with 0 wrong and no added holds.

**L-2:** the carried notice/cc and recital/exhibit hold costs remain unchanged. Releasing them would add non-M-1 `n → p`, so they remain holds. The immutable r13 L-2 control passes all **40 cases**: 20 placements on its own company line and 20 both-signer holds.

**N-1:** Git and SHA-256 verification confirm HEAD `0aa3cbbb` exactly matches the starting c2a.29 source. **N-2:** the report retains the corrected 810 ruleless-name cells, 288 r28 no-rule wrong placements and 60 `two_col_rows` wrong placements. **N-3:** all r29 test files, the goldens and the full suite are included in completed validation.

## Full suite and preservation

**61,598 passed / 0 failed / 0 errors / 0 skipped.** The full Send suite completed without `-x`, retries or skip filters. Four isolated pytest processes cover every collected test ID exactly once, using independent scratch SQLite databases. All **58,058 previous IDs** are preserved; the two new regression files add **3,540 tests**. [Complete runner log](shipping-full-suite-run.txt), [JUnit](shipping-full-suite-complete.xml), [partition manifest](shipping-full-suite-manifest.json), [completion ledger](shipping-full-suite-completion.json).

Command: `PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r30/run_full_suite_shipping.py`.

**{preservation['unchanged']:,}/{preservation['unchanged']:,} pre-existing tracked files other than placement.py are hash-identical**, including every existing test, fixture, evidence file and `.done` marker. No test was weakened, skipped, deleted or retargeted. New fixtures and tests match their failing-first hashes. Every new evidence file is below 20 MB. [Preservation audit](preservation-summary.json).

Exploratory runs on the 44-point and unscoped 50-point trials were stopped before completion when the implementation was refined; their partial logs and stop records are preserved. The release run above completed on the final source hash. The first capture attempt had a paired-output indexing error; the corrected capture was frozen before failing first. Two archived review families initially failed a harness equality check because Python tuples deserialize as JSON lists; canonical JSON comparison fixes representation only, and both complete reruns preserve their original axes, PDFs and oracles. These harness/trial records are not counted as release test passes.

**Blockers: none.** No staging, commit, deployment, migration or configuration change. Project memory is unchanged.
'''
with (OUT/'results-r30.md').open('x') as stream: stream.write(report)
# This is deliberately the final deliverable write, after the report and bars.
marker=f'''coder rc=0 head={bars['head']}
failing-first: date matrix/workers 2848 passed, 6 failed, 0 errors, 0 skipped; frozen recovery outputs 0 passed, 686 failed, 0 errors, 0 skipped; r29 reproduces 686/2844 over-holds.
shipped: VERSION c2a.30; Date-first companion band scales to two By/Date pitches, floor 22/cap 50; populated stacks and intervening signing rules retain 22. All 686 M-1 recoveries correct; 0 wrong in M-1, all 4482 H-1 cells, r27 700 and all 82450 inherited cells. Lows retained; nits verified.
vs-live c2a.29: n->p=686, all correct M-1 recoveries; c->w=0, n->W=0. Vs c2a.28 and r21: n->p=0, c->w=0, n->W=0 in every measured family. Seven goldens exact except analysis_version.
full-suite: 61598 passed, 0 failed, 0 errors, 0 skipped; completed without -x; every collected ID exactly once.
test changes: only new files; 2 regression files, 1 capture adapter, exact reviewer fixtures and frozen correct baseline outputs; 3540 new test IDs. All 58058 old IDs and {preservation['unchanged']} existing tracked files other than placement.py preserved by hashes. No existing tests, fixtures, evidence or done markers changed.
blockers: none. No commit. See results-r30.md and release-bars.json. Retained historical named-party raw flags are unchanged and enumerated by family.
'''
with (OUT/'counterparty-c2a-r30.done').open('x') as stream: stream.write(marker)
print('Wrote results-r30.md and counterparty-c2a-r30.done')
