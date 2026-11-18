"""Require every release bar before producing r28's completion evidence."""
from collections import Counter, defaultdict
import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
BASES = ('r21', 'r26', 'r27')


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as stream:
            return json.load(stream)
    return json.loads(path.read_text())


def write(name, data):
    with (OUT / name).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tests(path):
    counts = Counter(dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0))
    ids, families = Counter(), Counter()
    for case in ET.parse(path).getroot().iter('testcase'):
        state = ('failed' if case.find('failure') is not None else
                 'errors' if case.find('error') is not None else
                 'skipped' if case.find('skipped') is not None else 'passed')
        counts[state] += 1
        ids[(case.attrib['classname'], case.attrib['name'])] += 1
        families[(case.attrib['classname'], case.attrib['name'].split('[')[0], state)] += 1
    return counts, ids, families


def transitions(counts, before, after):
    for key, condition in (
        ('n_to_p', before == 'n' and after in {'c', 'w'}),
        ('c_to_w', before == 'c' and after == 'w'),
        ('c_to_n', before == 'c' and after == 'n'),
        ('w_to_n', before == 'w' and after == 'n'),
    ):
        counts[key] += condition


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == '1c425e1bfc7b508cc977eb5e5e3fffefb1eba0b7'
    source_hash = sha(ROOT / PRODUCT)
    assert source_hash == sha(OUT / 'r28-source.py.txt')
    assert b"VERSION = 'c2a.28'" in (ROOT / PRODUCT).read_bytes()
    counts, ids, families = tests(OUT / 'full-suite.xml')
    prior_counts, prior_ids, _ = tests(OUT.parent / 'c2a-r27/full-suite.xml')
    assert prior_counts['passed'] == 52424
    assert not prior_ids - ids
    assert counts == dict(passed=53690, failed=0, errors=0, skipped=0), counts
    assert sum((ids - prior_ids).values()) == 1266
    assert tests(OUT / 'failing-first-final.xml')[0] == dict(passed=820, failed=446, errors=0, skipped=0)
    targeted = tests(OUT / 'targeted.xml')[0]
    assert targeted['failed'] == targeted['errors'] == targeted['skipped'] == 0
    for path, digest in read(OUT / 'new-tests-failing-first-hashes.json').items():
        assert sha(ROOT / path) == digest, path
    assert families[('dealroom_sign.tests.test_placement_r13',
                     'test_l2_separate_own_company_line_preserves_scoring', 'passed')] == 40
    inherited_codes = read(OUT / 'effective-inherited-returncodes.json')
    assert len(inherited_codes) == 26 and not any(inherited_codes.values()), inherited_codes
    assert not any(read(OUT / 'new-returncodes.json').values())
    inherited, comparisons, ordinary = {}, {b: Counter() for b in BASES}, {}
    total, workers = 0, 0
    for part in ('historical', *inherited_codes):
        summary = read(OUT / 'final' / (part + '-summary.json'))
        data = read(OUT / 'final' / (part + '-cases.json.gz'))
        assert summary['source_sha256']['r28'] == source_hash
        assert summary['external_http_calls'] == 0 and summary['archive_results_exact']
        groups = defaultdict(Counter)
        for row in data['cases']:
            states = {v: 'w' if row['raw_wrong'][v] else
                      {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[
                          data['outcomes'][row['results'][v]]['status']]
                      for v in (*BASES, 'r28')}
            assert states['r28'] != 'w', (part, row['case'])
            group = groups[row['group']]
            group['cases'] += 1
            for v, state in states.items():
                group[v + '_' + state] += 1
            for base in BASES:
                transitions(comparisons[base], states[base], states['r28'])
                local = Counter()
                transitions(local, states[base], states['r28'])
                group.update({base + '_' + k: value for k, value in local.items()})
        summary['raw_groups'] = dict(groups)
        inherited[part] = summary
        total += len(data['cases'])
        workers += summary['worker_evaluations']
        if part in {'ordinary_ndas', 'exhibits'}:
            ordinary[part] = dict(cases=len(data['cases']),
                added_holds={b: sum(g[b + '_c_to_n'] for g in groups.values()) for b in BASES})
            assert ordinary[part]['added_holds']['r27'] == ordinary[part]['added_holds']['r26'] == 0
        if part in {'q3b', 'q3b_aligned'}:
            ordinary[part] = {name: dict(g) for name, g in groups.items() if 'ordinary' in name.lower()}
            assert all(g['r27_c_to_n'] == g['r26_c_to_n'] == 0 for g in ordinary[part].values())
    assert total == 82450 and workers == 980, (total, workers)
    assert all(c['n_to_p'] == c['c_to_w'] == 0 for c in comparisons.values())
    golden = inherited['historical']['groups']['Seven goldens']
    assert golden['cases'] == 7 and golden['r28_golden_diffs'] == golden['r28_native_diffs'] == 0
    new, new_comparisons = {}, {b: Counter() for b in BASES}
    policies = defaultdict(Counter)
    for part in ('variants', 'workers', 'ordinary', 'stacks', 'recitals', 'r27', 'extended'):
        folder = OUT / ('measured-' + part)
        summary, rows = read(folder / 'summary.json'), read(folder / 'cases.json.gz')
        assert summary['source_sha256']['r28'] == source_hash and summary['external_http_calls'] == 0
        assert summary['model_calls']['r28'] == summary['model_calls']['r27'] == summary['model_calls']['r26']
        for row in rows:
            assert row['states']['r28'] != 'w', (part, row['axes'])
            for base in BASES:
                transitions(new_comparisons[base], row['raw_states'][base], row['raw_states']['r28'])
            if row['raw_states']['r28'] == 'w':
                assert row['retained_policy_control'] and row['raw_states']['r27'] == 'w'
                old, current = row['results']['r27'], row['results']['r28']
                assert {k: v for k, v in old.items() if k != 'analysis_version'} == {
                    k: v for k, v in current.items() if k != 'analysis_version'}
                policies[part]['unchanged_raw_flags'] += 1
        new[part] = summary
    assert all(c['n_to_p'] == c['c_to_w'] == 0 for c in new_comparisons.values())
    variants = new['variants']['groups']['variants']
    assert variants['cases'] == 700 and variants['r27_raw_wrong'] == 220
    assert variants['cand27_raw_wrong'] == 90 and variants['r28_raw_wrong'] == 0
    assert variants['r27_to_cand27_w_to_n'] == 130 and variants['r27_to_r28_w_to_n'] == 220
    stacks = new['stacks']['groups']
    table = stacks['stacks table_exhibit']
    assert table['r26_to_r27_c_to_n'] == 44 and table['r26_to_r27_w_to_n'] == 24
    assert all(g['r27_to_r28_n_to_p'] == g['r27_to_r28_c_to_w'] == 0 for g in stacks.values())
    for group in new['ordinary']['groups'].values():
        assert group['r27_to_r28_c_to_n'] == group['r26_to_r28_c_to_n'] == 0
    ordinary['reviewer_call38'] = new['ordinary']
    initial = read(OUT / 'starting-hashes.json')
    changed = [p for p, digest in initial.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    oversized = [str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file() and p.stat().st_size >= 20_000_000]
    assert not oversized, oversized
    # Product changes are restricted to the version and the veto-only helper.
    def components(path):
        return {getattr(node, 'name', str(i)): ast.dump(node) for i, node in enumerate(ast.parse(path.read_text()).body)}
    before, after = components(OUT / 'r27-source.py.txt'), components(ROOT / PRODUCT)
    changes = [name for name in before if before[name] != after.get(name)]
    assert len(changes) == 2 and 'unclaimed_signing_peers' in changes, changes
    write('family-comparison.json', inherited)
    write('new-family-comparison.json', new)
    write('ordinary-hold-cost.json', ordinary)
    write('vs-live.json', dict(inherited_cells=total, inherited=comparisons,
          new_cells=sum(s['cases'] for s in new.values()), new=new_comparisons))
    write('preservation-summary.json', dict(base_head=head, inventoried_files=len(initial),
          unchanged=len(initial)-1, changed=changed, prior_test_ids_preserved=52424,
          new_test_ids=1266, new_tests_frozen_since_failing_first=True, oversized_evidence=oversized))
    write('full-suite-summary.json', counts)
    write('release-bars.json', dict(rc=0, base_head=head, working_tree_version='c2a.28',
          source_sha256=source_hash, full_suite=counts, targeted=targeted,
          inherited_cells=total, inherited_comparisons=comparisons, new_comparisons=new_comparisons,
          worker_evaluations=workers+20, seven_goldens_exact_except_analysis_version=True,
          inherited_raw_wrong=0, new_blocking_scope_raw_wrong=0, retained_policy_controls=policies,
          table_row_exhibit_cost=table, preservation_passed=True, blockers=[]))
    print(json.dumps(dict(cells=total, comparisons=comparisons, new_comparisons=new_comparisons,
                         full_suite=counts, preservation=len(initial)-1), indent=2))


if __name__ == '__main__':
    main()
