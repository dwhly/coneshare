"""Check completion and preservation, then append the r32b report and done marker."""
from collections import Counter
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
EVIDENCE = OUT.parent
ROOT = EVIDENCE.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
TEST = 'backend/dealroom_sign/tests/test_placement_r30_recoveries.py'
REPORT = 'docs/implementation/c2a-r32/results-r32.md'


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def junit(path):
    counts = Counter(dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0))
    ids = Counter()
    for case in ET.parse(path).getroot().iter('testcase'):
        state = ('failed' if case.find('failure') is not None else 'errors' if case.find('error') is not None
                 else 'skipped' if case.find('skipped') is not None else 'passed')
        counts[state] += 1
        ids[(case.get('classname'), case.get('name'))] += 1
    return counts, ids


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == '8dd65f82ae560c8563d29f16a0b3d4fad936d9e2'
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    source_hash = sha(ROOT / PRODUCT)
    assert source_hash == sha(EVIDENCE / 'shipping-source.py.txt')
    outcome = read(OUT / 'outcome-audit.json')
    assert outcome['source_sha256'] == source_hash
    assert outcome['strict_wrong_on_every_changed_outcome'] == 0
    assert outcome['fresh_changed_cells'] == 2166 and outcome['fresh_goldens'] == 7
    recovery = read(OUT / 'recovery-audit.json')
    assert recovery['held'] == 200 and recovery['retained_exact'] == 486 and not recovery['strict_wrong']
    families = read(OUT / 'family-comparison.json')
    assert all(c['c_to_w'] == c['n_to_W'] == 0 for c in families.values())

    counts, ids = junit(OUT / 'shipping-full-suite-complete.xml')
    _, r32_ids = junit(EVIDENCE / 'shipping-full-suite-complete.xml')
    _, r31_ids = junit(EVIDENCE.parent / 'c2a-r31/shipping-full-suite-complete.xml')
    completion = read(OUT / 'shipping-full-suite-completion.json')
    manifest = read(OUT / 'shipping-full-suite-manifest.json')
    assert counts == completion['counts'] == dict(passed=94688, failed=0, errors=0, skipped=0)
    assert ids == r32_ids and not r31_ids - ids
    assert completion['collected_ids_exact'] and not any(completion['returncodes'].values())
    assert not manifest['fail_fast'] and not manifest['skip_filters']
    assert manifest['collected'] == sum(ids.values()) == 94688
    assert completion['source_sha256'] == manifest['source_sha256'] == source_hash
    write('suite-audit.json', dict(counts=counts, prior_r32_ids_exact=True,
          pre_r32_ids_preserved=sum(r31_ids.values()), new_r32_ids=sum((ids - r31_ids).values()),
          source_sha256=source_hash, collected_ids_exact=True, fail_fast=False, skipped_filters=False))

    original_test = subprocess.check_output(['git', 'show', 'HEAD:' + TEST], cwd=ROOT, text=True)
    original_ast, current_ast = ast.parse(original_test), ast.parse((ROOT / TEST).read_text())
    function = next(n for n in current_ast.body if isinstance(n, ast.FunctionDef))
    branch = next(n for n in function.body if isinstance(n, ast.If))
    assert len(branch.body) == 2 and len(branch.orelse) == 1
    pos = function.body.index(branch)
    function.body[pos:pos + 1] = branch.orelse
    assert ast.dump(original_ast, include_attributes=False) == ast.dump(current_ast, include_attributes=False)
    test_diff = subprocess.check_output(['git', 'diff', '--', TEST], cwd=ROOT, text=True)
    assert test_diff == (OUT / 'authorised-test.diff').read_text()
    assert subprocess.check_output(['git', 'diff', '--numstat', '--', TEST], cwd=ROOT, text=True).startswith('6\t2\t')

    baseline = read(EVIDENCE / 'starting-hashes.json')
    baseline_changes = [p for p, digest in baseline.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert set(baseline_changes) == {PRODUCT, TEST}, baseline_changes
    start = read(OUT / 'starting-hashes.json')
    changes = [p for p, digest in start.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert changes == [TEST], changes
    before = (OUT / 'results-r32-before.md').read_bytes()
    assert (ROOT / REPORT).read_bytes() == before
    frozen = read(EVIDENCE / 'frozen-tests-hashes.json')
    for name in ('failing-first-hashes.json', 'ownership-failing-first-hashes.json', 'rules-failing-first-hashes.json'):
        frozen.update(read(EVIDENCE / name))
    for path, digest in frozen.items():
        assert sha(ROOT / path) == digest, path
    preservation = dict(head=head, tracked_baseline_files=len(baseline),
                        tracked_unchanged=len(baseline) - 2, tracked_changes=baseline_changes,
                        session_start_files=len(start), session_unchanged_before_report=len(start) - 1,
                        session_changes_before_report=changes, production_unchanged_since_r32=True,
                        all_other_tests_fixtures_evidence_done_markers_unchanged=True,
                        frozen_new_files_unchanged=len(frozen), authorised_test_added_lines=6,
                        authorised_test_deleted_lines=2, old_test_lines_changed=[24, 25],
                        new_test_lines=[24, 25, 26, 27, 28, 29], original_assertions_preserved=True,
                        results_append_only=True, staged=False, committed=False)
    write('preservation-audit.json', preservation)

    totals = outcome['release']
    measurements = outcome['measurement_only']
    table = ['| Family | Cells | Wrong live / r32 | Changed | n → p correct | c → w | n → W |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name, c in families.items():
        table.append(f"| {name} | {c['cells']:,} | {c['r29_wrong']} / {c['r32_wrong']} | {c['changed_output']} | {c['n_to_p']} | {c['c_to_w']} | {c['n_to_W']} |")
    table_text = '\n'.join(table)
    command = 'PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r32/r32b/run_full_suite.py'
    append = f'''

## r32b — authorised recovery correction and completed release bar

**coder rc=0. `VERSION = 'c2a.32'`.** HEAD remains `{head}`; live baseline is c2a.29 (`0aa3cbbb1331b9416649bfcbdef14ed788cf7684`). The manager's r32b rulings resolve both blockers recorded above. No commit or staging. Production source is unchanged from the r32 handoff, SHA-256 `{source_hash}`.

The only test change is in `backend/dealroom_sign/tests/test_placement_r30_recoveries.py`: old lines **24–25** become new lines **24–29** (**6 added / 2 removed**, net +4). The selector is exactly `recital == 'none'` and `signer in {{'domain', 'both'}}`: **120 domain-only + 80 two-signer cells = 200**. Those cells require `needs_sender` and `fields == []`, so no placement can pass that branch. The other **486** keep their original complete-result equality assertion, excluding only `analysis_version`. The original wrong-fields oracle and no-model-call assertion still run for all 686 cells. An AST comparison confirms that removing this single hold branch restores the original test exactly. The selector matches precisely the 200 failures in the r32 full-suite record. [Exact diff](r32b/authorised-test.diff), [recovery audit](r32b/recovery-audit.json).

```diff
{test_diff.rstrip()}
```

**Full suite completed without `-x`: 94,688 passed / 0 failed / 0 errors / 0 skipped.** Command: `{command}`. Four isolated pytest processes ran all collected Send test IDs with separate scratch SQLite databases. No retries, skip filters, or omitted IDs. The merged JUnit IDs equal the prior r32 collection exactly; all **80,088** pre-r32 IDs and **14,600** new r32 IDs remain. [Completion](r32b/shipping-full-suite-completion.json), [manifest](r32b/shipping-full-suite-manifest.json), [JUnit](r32b/shipping-full-suite-complete.xml), [suite audit](r32b/suite-audit.json).

**Vs live c2a.29: c → w = 0 and n → W = 0 in every family.** Across **{totals['cells']:,} release inventory cells**, **2,166** outcomes differ from live, all oracle-correct new placements; c → hold = 0. The strict-oracle check covers every changed result, not only newly placed results. All 2,166 changed cells were freshly executed on both live c2a.29 and the worktree c2a.32, matched the preserved r32 outputs, and passed the unadjusted oracle. The additional 200 authorised holds were also freshly executed on both versions. All 486 retained recoveries remain placed and exactly equal their original expected result. All **seven goldens** were freshly executed on both versions and match live and the historical golden outputs exactly except `analysis_version`; native fields also match. Model-call counts match live; external HTTP calls are zero. [Outcome audit](r32b/outcome-audit.json), [fresh per-cell results](r32b/fresh-outcomes.json.gz), [goldens](r32b/goldens.json).

The first fresh-outcome audit stopped on a tuple/list mismatch between generated axes and their JSON representation. JSON-normalizing that evidence comparison corrected the audit runner; the [initial log](r32b/outcome-audit-run.txt) and [completed log](r32b/outcome-audit-complete.txt) are retained. This did not change production, tests, fixtures, or the single full-suite run.

The complete 53-family r32 matrix evidence was re-audited against the identical production-source hash; inherited c2a.29 outputs were checked against their immutable live archives. The 876 unchanged release raw-oracle flags remain out of scope under the manager ruling: `review/stray` 12, `prior/notices` 94, `prior/r27` 206, `prior/recitals` 120, `prior/stacks` 444. They remain explicitly reported and were not reclassified or fixed. Separately, the unchanged 16–20 pt measurement inventories contain **{measurements['cells']:,} cells / {measurements['r32_wrong']:,} raw flags** (72 / 90 worker-subset cells and 1,692 / 5,832 matrix cells). All measurement outputs equal live except `analysis_version`. Inventories overlap and are not deduplicated. [Per-family comparisons](r32b/family-comparison.json), [unchanged flags](r32b/unchanged-raw-flags.json).

{table_text}

**Preservation:** SHA-256 confirms **5,248 / 5,250** files in the original r32 baseline are unchanged; the only exceptions are production `placement.py` and the single authorised recovery test. Of **{len(start):,}** files present at r32b startup, only that test and this append-only report change; production, every other existing test/fixture, all prior evidence, and all prior `.done` markers remain byte-identical. New evidence is isolated under `r32b/`; the new completion marker is `counterparty-c2a-r32b.done`. All evidence files remain under 20,000,000 bytes. [Preservation audit](r32b/preservation-audit.json), [size audit](r32b/evidence-size-audit.json).

**Blockers: none.** This addendum supersedes the earlier rc=1 release assessment under the two explicit r32b manager rulings; the original report and old completion marker remain preserved.
'''
    with (ROOT / REPORT).open('ab') as stream:
        stream.write(append.encode())
    assert (ROOT / REPORT).read_bytes().startswith(before)
    after_changes = [p for p, digest in start.items() if sha(ROOT / p) != digest]
    assert set(after_changes) == {TEST, REPORT}, after_changes
    sizes = {str(p.relative_to(ROOT)): p.stat().st_size for p in EVIDENCE.rglob('*') if p.is_file()}
    assert all(size < 20_000_000 for size in sizes.values())
    write('evidence-size-audit.json', dict(limit_bytes=20_000_000,
          largest=sorted(sizes.items(), key=lambda item: item[1], reverse=True)[:10]))
    marker = EVIDENCE / 'counterparty-c2a-r32b.done'
    with marker.open('x') as stream:
        stream.write(f'''coder rc=0 head={head}
VERSION=c2a.32 source_sha256={source_hash}; no staging or commit.
Test diff: backend/dealroom_sign/tests/test_placement_r30_recoveries.py only; old lines 24–25 -> new lines 24–29; 6 added / 2 removed.
200 no-recital cells (120 domain, 80 both) require needs_sender with empty fields; all other 486 retain the original exact placement assertion. Wrong-fields and no-model assertions unchanged.
{test_diff}
Vs-live c2a.29: 170935 release cells; 2166 changed outcomes, all strict-oracle correct; c->w=0, n->W=0, c->hold=0 in every family. All 2166 changed cells and 200 authorised holds freshly executed on both versions. 486 recoveries placed and exact. Seven goldens exact except analysis_version; native fields exact. 876 pre-existing release raw flags unchanged and out of scope. Measurement-only: 5922 cells, 1764 unchanged raw flags, zero changed outcomes. Model calls equal live; HTTP calls=0.
{table_text}

Full suite without -x: passed=94688 failed=0 errors=0 skipped=0; all collected IDs exact; 80088 pre-r32 IDs + 14600 r32 additions. Four process returncodes=0. No retries, skips, filters or omitted IDs.
Preservation: 5248/5250 original baseline files hash-identical; only placement.py and the authorised test differ. All pre-r32b artifacts preserved except the authorised test and append-only results-r32.md. Source unchanged since r32. No other existing tests changed.
Evidence: results-r32.md r32b addendum; r32b/authorised-test.diff; r32b/outcome-audit.json; r32b/family-comparison.json; r32b/shipping-full-suite-completion.json; r32b/preservation-audit.json.
Blockers: none.
''')
    assert marker.stat().st_size < 20_000_000
    print(json.dumps(dict(coder_rc=0, head=head, full_suite=counts, blockers=[]), indent=2))


if __name__ == '__main__':
    main()
