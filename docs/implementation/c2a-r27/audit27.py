"""Verify the completed release against immutable evidence before reporting it."""
from collections import Counter, defaultdict
import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
BASES = ('r26', 'r25', 'r21')
VERSIONS = ('r21', 'r25', 'r26', 'r27')


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as stream:
            return json.load(stream)
    return json.loads(path.read_text())


def write(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2)
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


def versionless(result):
    return {k: v for k, v in result.items() if k != 'analysis_version'}


def main():
    base_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert base_head == 'f450fdaea1ba4ddabdac216c891555b00ba8ce58'
    source_hash = sha(ROOT / PRODUCT)
    assert source_hash == sha(OUT / 'r27-source.py.txt') == read(OUT / 'run-provenance.json')['source_sha256']
    assert b"VERSION = 'c2a.27'" in (ROOT / PRODUCT).read_bytes()
    counts, ids, families = tests(OUT / 'full-suite.xml')
    assert counts == dict(passed=52424, failed=0, errors=0, skipped=0), counts
    prior_counts, prior_ids, _ = tests(OUT.parent / 'c2a-r26/r26b/full-suite.xml')
    assert not prior_ids - ids and sum(prior_ids.values()) == 50498
    assert sum((ids - prior_ids).values()) == 1926
    l2 = ('dealroom_sign.tests.test_placement_r13', 'test_l2_separate_own_company_line_preserves_scoring', 'passed')
    assert families[l2] == 40
    assert tests(OUT / 'failing-first-final.xml')[0] == dict(passed=1822, failed=104, errors=0, skipped=0)
    assert tests(OUT / 'targeted-final.xml')[0] == dict(passed=1990, failed=0, errors=0, skipped=0)
    for path, digest in read(OUT / 'new-tests-release-hashes.json').items():
        assert sha(ROOT / path) == digest
    codes = read(OUT / 'final/returncodes.json')
    assert len(codes) == 27 and codes['historical'] == 1
    assert not any(code for part, code in codes.items() if part != 'historical'), codes
    assert read(OUT / 'execution-returncodes.json')['historical_retry'] == 0
    effective_codes = dict(codes, historical=0)
    comparisons = {b: Counter() for b in BASES}
    summaries, ordinary = {}, {}
    cells = workers = 0
    for part in codes:
        folder = OUT / ('historical-retry' if part == 'historical' else 'final')
        summary = read(folder / (part + '-summary.json'))
        data = read(folder / (part + '-cases.json.gz'))
        assert summary['source_sha256']['r27'] == source_hash
        assert summary['external_http_calls'] == 0 and summary['archive_results_exact']
        groups = defaultdict(Counter)
        for row in data['cases']:
            states = {v: 'w' if row['raw_wrong'][v] else
                      {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[data['outcomes'][row['results'][v]]['status']]
                      for v in VERSIONS}
            assert states['r27'] != 'w', (part, row['case'])
            g = groups[row['group']]
            g['cases'] += 1
            for v, state in states.items():
                g[v + '_' + state] += 1
            for base in BASES:
                transitions(comparisons[base], states[base], states['r27'])
                local = Counter()
                transitions(local, states[base], states['r27'])
                g.update({base + '_' + k: value for k, value in local.items()})
        summary['raw_groups'] = dict(groups)
        summaries[part] = summary
        cells += len(data['cases'])
        workers += summary['worker_evaluations']
        if part in {'ordinary_ndas', 'exhibits'}:
            ordinary[part] = dict(cases=len(data['cases']),
                added_holds={b: sum(g[b + '_c_to_n'] for g in groups.values()) for b in BASES})
            assert ordinary[part]['added_holds']['r26'] == ordinary[part]['added_holds']['r25'] == 0
        if part in {'q3b', 'q3b_aligned'}:
            ordinary[part] = {name: dict(g) for name, g in groups.items() if 'ordinary' in name.lower()}
            assert all(g['r26_c_to_n'] == g['r25_c_to_n'] == 0 for g in ordinary[part].values())
    assert cells == 82450 and workers == 980, (cells, workers)
    for base, c in comparisons.items():
        assert c['n_to_p'] == c['c_to_w'] == 0, (base, c)
    for part, size in [('exact_q3a', 4536), ('exact_q3b', 2430), ('exact_q3c', 2808), ('h1', 2160), ('h1_review', 2160)]:
        assert summaries[part]['cases'] == size
    assert summaries['exact_q3c']['groups']['exact_q3c same_page3']['cases'] == 468
    golden = summaries['historical']['groups']['Seven goldens']
    assert golden['cases'] == 7 and golden['r27_golden_diffs'] == golden['r27_native_diffs'] == 0
    # Candidate differs from the release only in a comment; compare ASTs.
    assert ast.dump(ast.parse((OUT / 'structural-source.py.txt').read_text())) == ast.dump(ast.parse((ROOT / PRODUCT).read_text()))
    baseline = read(OUT / 'baseline-v2/cases.json.gz')
    candidate = read(OUT / 'candidate/cases.json.gz')
    assert len(baseline) == len(candidate) == 4461
    new_comparisons = {b: Counter() for b in BASES}
    new_groups, policy_groups = defaultdict(Counter), defaultdict(Counter)
    attack_e = Counter()
    no_recital_diffs = Counter()
    for old, row in zip(baseline, candidate):
        assert (old['index'], old['axes']) == (row['index'], row['axes'])
        for b in ('r25', 'r26', 'r26c'):
            assert old['results'][b] == row['results'][b]
        axes = row['axes']
        scoped = (axes['recital'] != 'none' and (
            axes['group'] == 'A' or axes['group'] == 'B' and axes['signers'] == 2
            or axes['group'] == 'E' and axes['aff'] == 'HARBOR LIGHT GROUP, INC.'))
        for b in BASES:
            transitions(new_comparisons[b], row['raw_states'][b], row['raw_states']['structural'])
        group = (new_groups if scoped else policy_groups)[row['group']]
        group['cases'] += 1
        group['raw_wrong'] += row['raw_states']['structural'] == 'w'
        group['scoped_wrong'] += row['states']['structural'] == 'w'
        if scoped:
            assert row['raw_states']['structural'] != 'w', row['axes']
        if axes['recital'] == 'none':
            no_recital_diffs[axes['group']] += versionless(row['results']['structural']) != versionless(row['results']['r26'])
        if axes['group'] == 'E' and axes['aff'] == 'HARBOR LIGHT GROUP, INC.':
            if all(old['raw_states'][b] == 'w' for b in ('r25', 'r26', 'cand5')):
                attack_e['baseline_WWW'] += 1
                attack_e['recital_WWW'] += axes['recital'] != 'none'
                if axes['recital'] != 'none':
                    assert row['states']['structural'] == 'n'
                    attack_e['recital_WWW_held'] += 1
    assert attack_e == dict(baseline_WWW=50, recital_WWW=30, recital_WWW_held=30), attack_e
    assert all(c['n_to_p'] == c['c_to_w'] == 0 for c in new_comparisons.values())
    assert not any(no_recital_diffs.values()), no_recital_diffs
    controls = read(OUT / 'measured-controls-summary.json')
    assert controls['groups']['L2 single']['r27_expected'] == controls['groups']['L2 both']['r27_expected'] == 20
    vocabulary_controls = read(OUT / 'vocabulary-names-controls-summary.json')
    assert vocabulary_controls['groups']['L2 single']['vocabulary_names_expected'] == 20
    assert vocabulary_controls['groups']['L2 both']['vocabulary_names_expected'] == 20
    assert vocabulary_controls['groups']['captions']['vocabulary_names_w'] == 4
    vocabulary = read(OUT / 'vocabulary-names/summary.json')
    assert vocabulary['cases'] == 4461
    assert sum(g.get('vocabulary_names_w', 0) for g in vocabulary['groups'].values()) == 0
    assert vocabulary['comparisons']['r26_to_vocabulary_names']['n_to_p'] == 0
    low = read(OUT / 'low-exemption-measurement.json')
    assert sum(g.get('explicit_exemption_w', 0) for g in low['groups'].values()) == 0
    assert all(sum(g.get(b + '_to_candidate_n_to_p', 0) for g in low['groups'].values()) == 28 for b in ('r25', 'r26', 'r27'))
    initial = read(OUT / 'starting-hashes.json')
    changed = [p for p, digest in initial.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    oversized = [str(p.relative_to(OUT)) for p in OUT.rglob('*.json') if p.stat().st_size >= 20_000_000]
    assert not oversized, oversized
    write('family-comparison.json', summaries)
    write('effective-replay-returncodes.json', effective_codes)
    write('ordinary-hold-cost.json', ordinary)
    write('vs-live.json', dict(cells=cells, comparisons=comparisons, new_cells=len(candidate), new_comparisons=new_comparisons))
    write('new-family-audit.json', dict(scoped_groups=new_groups, retained_policy_controls=policy_groups,
          attack_e=attack_e, no_recital_output_differences=no_recital_diffs))
    write('preservation-summary.json', dict(base_head=base_head, inventoried_files=len(initial),
          unchanged=len(initial)-1, changed=changed, existing_tests_fixtures_evidence_markers_unchanged=True,
          prior_test_ids_preserved=50498, new_test_ids=1926, new_tests_frozen_since_final_failing_first=True))
    write('full-suite-summary.json', counts)
    write('release-bars.json', dict(rc=0, base_head=base_head, working_tree_version='c2a.27',
          source_sha256=source_hash, full_suite=counts, inherited_cells=cells, new_review_cells=len(candidate),
          worker_evaluations=workers+controls['worker_evaluations']+vocabulary_controls['worker_evaluations']+36,
          comparisons=comparisons,
          new_comparisons=new_comparisons, seven_goldens_exact_except_analysis_version=True,
          inherited_raw_wrong=0, new_blocking_scope_raw_wrong=0, preservation_passed=True, blockers=[]))
    print(json.dumps(dict(cells=cells, comparisons=comparisons, new_comparisons=new_comparisons,
                         full_suite=counts, attack_e=attack_e, preservation=len(initial)-1), indent=2))


if __name__ == '__main__':
    main()
