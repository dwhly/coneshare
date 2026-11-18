"""Audit fresh r26b evidence without rewriting earlier tests or evidence."""
from collections import Counter
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
OLD = OUT.parent
ROOT = OLD.parents[2]
sys.path.insert(0, str(OLD))
import audit26 as prior

PRODUCT = 'backend/dealroom_sign/placement.py'
REPORT = 'docs/implementation/c2a-r26/results-r26.md'
BASES = ('r25', 'r24', 'r21')


def read(path):
    return json.loads(path.read_text())


def write(name, data):
    with (OUT / name).open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')


def state(data, row, version):
    return ('w' if row['raw_wrong'][version] else
            {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[
                data['outcomes'][row['results'][version]]['status']])


def main():
    prior.OUT = OUT
    sha = prior.sha
    source = ROOT / PRODUCT
    source_hash = sha(source)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == '701f6aeeabfc47bf5b997b1187705b039aea4f40'
    assert source.read_bytes() == (OUT / 'r26b-source.py.txt').read_bytes()
    assert b"VERSION = 'c2a.26'" in source.read_bytes()
    provenance = read(OUT / 'source-provenance.json')
    assert source_hash == provenance['source_sha256']
    for path, digest in provenance['new_tests'].items():
        assert sha(ROOT / path) == digest
    old_ast = ast.parse((OLD / 'r26-source.py.txt').read_bytes())
    new_ast = ast.parse(source.read_bytes())
    old_functions = {n.name: ast.dump(n) for n in old_ast.body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: ast.dump(n) for n in new_ast.body if isinstance(n, ast.FunctionDef)}
    changed_functions = [n for n in old_functions if old_functions[n] != new_functions[n]]
    assert changed_functions == ['prepare_blocks'], changed_functions

    counts, ids, families = prior.tests(OUT / 'full-suite.xml')
    assert counts == dict(passed=50498, failed=0, errors=0, skipped=0), counts
    old_counts, old_ids, _ = prior.tests(OLD / 'full-suite.xml')
    assert not old_ids - ids and sum((ids - old_ids).values()) == 24
    live_counts, live_ids, _ = prior.tests(OLD.parent / 'c2a-r25/final-full-suite.xml')
    assert not live_ids - ids and sum(live_ids.values()) == 47655
    l2 = ('dealroom_sign.tests.test_placement_r13',
          'test_l2_separate_own_company_line_preserves_scoring', 'passed')
    assert families[l2] == 40
    assert sum(n for (cls, name), n in ids.items()
               if cls == l2[0] and name.startswith(l2[1] + '[False-')) == 20
    assert families[('dealroom_sign.tests.test_placement_r19',
                     'test_company_competition_uses_identity_before_vetoes', 'passed')] == 40
    assert prior.tests(OUT / 'failing-first.xml')[0] == dict(passed=20, failed=20, errors=0, skipped=0)
    assert prior.tests(OUT / 'new-failing-first.xml')[0] == dict(passed=18, failed=6, errors=0, skipped=0)
    assert prior.tests(OUT / 'targeted.xml')[0] == dict(passed=2883, failed=0, errors=0, skipped=0)
    pilot = read(OUT / 'candidate-measurement-v2.json')
    assert pilot['external_http_calls'] == pilot['model_calls'] == 0
    for row in pilot['rows']:
        if row['group'] == 'L-2':
            current = row['results']['name_count']
            live = row['results']['r25']
            assert row['states']['name_count'] == row['states']['r25'] == 'c'
            assert row['states']['cand5'] == row['states']['recital'] == 'n'
            assert {k: v for k, v in current.items() if k != 'analysis_version'} == {
                k: v for k, v in live.items() if k != 'analysis_version'}
    returns = read(OUT / 'final/returncodes.json')
    assert len(returns) == 27 and not any(returns.values()), returns
    summaries, cand5_cost, flags = {}, {}, {}
    comparisons = {b: Counter() for b in BASES}
    restored = []
    for part in returns:
        summary = prior.raw_summary(part, read(OUT / 'final' / (part + '-summary.json')))
        summaries[part] = summary
        assert summary['source_sha256']['r26'] == source_hash
        assert summary['external_http_calls'] == 0
        current = read(OUT / 'final' / (part + '-cases.json'))
        cand5 = read(OLD / 'final' / (part + '-cases.json'))
        old_rows = {(r['group'], r['case']): r for r in cand5['cases']}
        assert len(old_rows) == len(current['cases'])
        cost = Counter(cases=len(current['cases']))
        for row in current['cases']:
            old_row = old_rows[(row['group'], row['case'])]
            for b in BASES:
                assert current['outcomes'][row['results'][b]] == cand5['outcomes'][old_row['results'][b]]
            before, after = state(cand5, old_row, 'r26'), state(current, row, 'r26')
            cost[before + '_to_' + after] += 1
            result = current['outcomes'][row['results']['r26']]
            previous = cand5['outcomes'][old_row['results']['r26']]
            if before == after:
                assert result == previous, (part, row['case'], 'same-state output changed')
            else:
                assert before == 'n' and after == 'c', (part, row['case'], before, after)
                live = current['outcomes'][row['results']['r25']]
                assert {k: v for k, v in result.items() if k != 'analysis_version'} == {
                    k: v for k, v in live.items() if k != 'analysis_version'}
                restored.append(dict(part=part, group=row['group'], case=row['case'], result=result))
        cand5_cost[part] = cost
        for name, group in summary['groups'].items():
            for base in BASES:
                for key in ('n_to_p', 'c_to_w', 'c_to_n', 'w_to_n'):
                    value = group.get(base + '_to_r26_' + key, 0)
                    comparisons[base][key] += value
                    if key in {'n_to_p', 'c_to_w'}:
                        assert value == 0, (part, name, base, key, value)
            if group.get('r26_raw_wrong', 0):
                flags[part + ': ' + name] = group['r26_raw_wrong']
        assert not flags, flags
    for part, size in [('exact_q3a', 4536), ('exact_q3b', 2430), ('exact_q3c', 2808),
                       ('h1', 2160), ('h1_review', 2160), ('workers26', 10),
                       ('exhibits', 576), ('three_party', 36)]:
        assert summaries[part]['cases'] == size
    same = summaries['exact_q3c']['groups']['exact_q3c same_page3']
    assert same['cases'] == 468 and same['r25_raw_wrong'] == 55
    assert same['r25_to_r26_c_to_n'] == 10
    m1 = summaries['stress']['groups']['Recitals misspelled_M1']
    assert m1['cases'] == 192 and m1['r26_raw_wrong'] == 0
    golden = summaries['historical']['groups']['Seven goldens']
    assert golden['cases'] == 7 and golden['r26_golden_diffs'] == golden['r26_native_diffs'] == 0
    cells = sum(s['cases'] for s in summaries.values())
    workers = sum(s['worker_evaluations'] for s in summaries.values())
    assert cells == 82450 and workers == 980
    initial = read(OUT / 'starting-hashes.json')
    changed = [p for p, digest in initial.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    preservation = dict(head=head, inventoried_files=len(initial),
                        unchanged=len(initial)-1, changed=changed,
                        existing_tests_fixtures_evidence_markers_unchanged=True,
                        r26_test_ids_preserved=sum(old_ids.values()),
                        live_test_ids_preserved=sum(live_ids.values()), new_test_ids=24,
                        new_tests_unchanged_since_failing_first=True,
                        report_update='Only append an r26b section after this audit.')
    total_cost = sum(cand5_cost.values(), Counter())
    write('family-comparison.json', summaries)
    write('vs-live.json', dict(cells=cells, worker_evaluations=workers, comparisons=comparisons))
    write('hold-cost-vs-cand5.json', dict(total=total_cost, families=cand5_cost, restored=restored,
          l2_included_in_historical=dict(cases=20, cand5_hold=20, r26b_correct=20)))
    write('preservation-summary.json', preservation)
    write('full-suite-summary.json', counts)
    write('remaining-flags.json', flags)
    write('release-bars.json', dict(rc=0, head=head, source_sha256=source_hash, version='c2a.26',
          full_suite=counts, measured_cells=cells, comparisons=comparisons,
          goldens_exact_except_analysis_version=True, raw_wrong=0,
          changed_functions_vs_cand5=changed_functions, preservation_passed=True,
          l2_positive_placed=20, l2_both_signers_held=20, blockers=[]))
    print(json.dumps(dict(cells=cells, comparisons=comparisons, full_suite=counts,
                         cand5_cost=total_cost, preserved_files=len(initial)-1), indent=2))


if __name__ == '__main__':
    main()
