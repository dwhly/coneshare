"""Audit preservation and completed tests, then write the r18 handoff last."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRODUCT = 'backend/dealroom_sign/placement.py'
N1 = 'backend/dealroom_sign/tests/test_placement_r17.py'


def write(stem, value):
    (OUT / (stem + '.json')).write_text(json.dumps(value, indent=2) + '\n')


def read(stem):
    return json.loads((OUT / (stem + '.json')).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def suite(path):
    tree = ET.parse(path)
    counts = Counter(passed=0, failed=0, errors=0, skipped=0)
    cases = []
    for case in tree.iter('testcase'):
        tag = next((t for t in ['failure', 'error', 'skipped'] if case.find(t) is not None), None)
        status = {'failure': 'failed', 'error': 'errors', 'skipped': 'skipped', None: 'passed'}[tag]
        counts[status] += 1
        cases.append({'classname': case.attrib['classname'], 'case': case.attrib['name'], 'status': status})
    return {'counts': counts, 'total': sum(counts.values()),
            'suites': [s.attrib for s in tree.iter('testsuite')]}, cases


def main():
    baseline = read('baseline')
    initial = read('baseline-hashes')
    changed = [p for p, sha in initial.items() if not (ROOT / p).is_file() or digest(ROOT / p) != sha]
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    index = subprocess.check_output(['git', 'ls-files', '--stage'], cwd=ROOT).decode()
    original = subprocess.check_output(['git', 'show', head + ':' + N1], cwd=ROOT).decode()
    n1_only = (ROOT / N1).read_text() == original.replace('Gate 3 r16:', 'Gate 3 r16 findings:', 1)
    whitespace = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    comparison = read('counterfactual-summary')
    chosen = next(name for name in ['b1', 'l1'] if digest(ROOT / PRODUCT) == comparison['source_sha256'][name])
    preservation = {'tracked_files_hash_checked': len(initial), 'changed_tracked_files': changed,
                    'only_permitted_docstring_changed': n1_only,
                    'all_other_existing_tests_fixtures_evidence_hash_exact': set(changed) == {PRODUCT, N1},
                    'memory_unchanged': digest(ROOT / '.agent/memory.md') == initial['.agent/memory.md'],
                    'head': head, 'head_unchanged': head == baseline['head'],
                    'index_unchanged': index == baseline['index'], 'whitespace_check_rc': whitespace.returncode,
                    'selected_candidate': chosen, 'source_matches_comparison': True}
    write('preservation-summary', preservation)
    summaries = {}
    for path in sorted(OUT.glob('*.xml')):
        summary, cases = suite(path)
        summaries[path.stem] = summary['counts']
        write(path.stem + '-summary', summary)
        if path.stem == 'full-suite':
            write('full-suite-cases', cases)
    write('test-runs-summary', summaries)
    previous = json.loads((OUT.parent / 'c2a-r17/full-suite-cases.json').read_text())
    current = read('full-suite-cases')
    before = Counter((c['classname'], c['case']) for c in previous)
    after = Counter((c['classname'], c['case']) for c in current)
    missing = list((before - after).elements())
    inventory = {'previous_cases': len(previous), 'current_cases': len(current),
                 'missing_existing_test_cases': missing, 'new_cases': sum((after - before).values())}
    write('test-inventory-summary', inventory)
    assert not missing
    assert inventory['previous_cases'] == 15498 and inventory['new_cases'] == 1646
    assert inventory['current_cases'] == 17144
    assert set(changed) == {PRODUCT, N1} and n1_only
    assert preservation['head_unchanged'] and preservation['index_unchanged'] and preservation['memory_unchanged']
    assert whitespace.returncode == 0
    assert read('affiliate-failing-first')['summary']['source_sha256'] == initial[PRODUCT]
    assert summaries['full-suite']['failed'] == summaries['full-suite']['errors'] == summaries['full-suite']['skipped'] == 0
    assert comparison['bars'][chosen + '_zero_wrong_every_family']
    assert comparison['bars'][chosen + '_goldens_exact'] and comparison['bars'][chosen + '_native_fields_exact']
    assert comparison['bars']['r17_replay_exact'] and comparison['bars']['b1_preserves_every_r17_full_result']

    archived = read('counterfactual-cases')
    affiliates = [r for r in archived['cases'] if r['group'] == 'Affiliate matrix']
    assert len(affiliates) == 1536
    affiliate_counts = Counter()
    for row in affiliates:
        old_result = archived['outcomes'][row['results']['r17']]
        b1_result = archived['outcomes'][row['results']['b1']]
        chosen_result = archived['outcomes'][row['results'][chosen]]
        if row['wrong']['r17']:
            assert (b1_result['status'], b1_result['fields']) == ('needs_sender', [])
            assert (chosen_result['status'], chosen_result['fields']) == ('needs_sender', [])
            affiliate_counts['wrong_to_hold'] += 1
        elif old_result['status'] == 'placed':
            assert {k: v for k, v in old_result.items() if k != 'analysis_version'} == {
                k: v for k, v in b1_result.items() if k != 'analysis_version'}
            assert {k: v for k, v in old_result.items() if k != 'analysis_version'} == {
                k: v for k, v in chosen_result.items() if k != 'analysis_version'}
            affiliate_counts['correct_full_results_unchanged'] += 1
    assert affiliate_counts == {'wrong_to_hold': 320, 'correct_full_results_unchanged': 96}
    assert all(r['model_calls']['b1'] == r['model_calls']['r17'] for r in archived['cases'])
    assert all(r['model_calls'][chosen] == r['model_calls']['r17'] for r in archived['cases'])
    assert all(g[chosen + '_full_diffs'] == 0 for name, g in comparison['groups'].items()
               if name not in {'Affiliate matrix', 'r18 B1 reproduction'})
    write('affiliate-preservation', affiliate_counts)
    write('placements', {r['case']: archived['outcomes'][r['results'][chosen]]
                         for r in archived['cases'] if r['group'] == 'Seven goldens'})
    totals = {name: Counter() for name in ['r17', chosen]}
    for group, counts in comparison['groups'].items():
        for name in totals:
            for key in ['wrong', 'placed', 'holds', 'bare']:
                totals[name][key] += counts[name + '_' + key]
    full = summaries['full-suite']
    lines = [
        '# C2a r18 results', '',
        f'Base HEAD: `{head}`; production `VERSION = \'c2a.18\'`. No commit or index changes.', '',
        '**B-1 closed.** Crossing headings cannot grant company credit, but their role-mapped, '
        'behalf-stripped company identity still prevents another block from winning on company alone. '
        'A matching printed name remains independent evidence. N-1 changes only the r17 test docstring.', '',
        f'Full Send backend suite: **{full["passed"]:,} passed, 0 failed, 0 errors, 0 skipped**, '
        'run to completion without `-x`. All 15,498 prior test cases remain. '
        f'{inventory["new_cases"]:,} new cases were added.', '',
        'New tests live exclusively in '
        '[test_placement_r18.py](../../../backend/dealroom_sign/tests/test_placement_r18.py): '
        '1,536 affiliate cases, 2 real-worker reproductions, 20 identity checks, '
        '80 L-1 boundary checks, and 8 L-1 PDF checks. The only existing-test change '
        'is the authorized N-1 docstring.', '',
        f'Full replay: {comparison["cases"]:,} evaluations across {len(comparison["groups"])} families, '
        f'**0 wrong** for r18. Seven goldens match exactly except `analysis_version`; native fields are exact. '
        f'{comparison["worker_evaluations"]} worker results equal their in-process counterparts; external HTTP calls: 0.', '',
        '## Failing first and affiliate matrix', '',
        'Production was unchanged for both initial pytest runs and the matrix baseline. '
        'The first run had 321 failed / 1,217 passed: 320 affiliate matrix failures and the PAT-only '
        'real-worker reproduction. Identity normalization checks had 8 failed / 12 passed. '
        'All subsequent B-1 targeted tests passed (1,558).', '',
        'The matrix is 6 affiliate headings × widths {150,180,200,218} × vertical gaps '
        '{130,160,200,240} × affiliate column {40,280} × Pat heading {ordinary,international} '
        '× PAT/DAN+PAT × Fleet heading off/on = **1,536 cases**. Pat and Fleet columns start at 40 and 280; '
        'signature rules are at y=290, dates at y=350, and affiliate rules are shifted by the selected gap. '
        'The oracle checks every signature and date against its own signer’s rule.', '',
        'r17: **320 wrong / 96 correct / 1,120 holds**. B-1 alone: '
        '**0 wrong / 96 correct / 1,440 holds**. All 320 wrong placements become holds, '
        'and the 96 correct full results are unchanged. The four triggering headings '
        '(GROUP, VENTURES, ANALYTICS UK, and repeated ANALYTICS) each account for 80 wrong placements; '
        'HOLDINGS and HARBOR LIGHT, LLC each retain 48 correct placements.', '',
        '## Optional L-1', '',
        (OUT / 'l1-decision.md').read_text().strip(), '',
        '## Per-family comparison', '',
        'Cells are **wrong / placed / holds / bare**; placed includes wrong placements in r17. '
        'The 72-case r14 L-1 subset overlaps its parent grid and is retained as in the prior evidence. '
        'B-1 alone preserves every complete result across all 15,526 archived r17 evaluations '
        'except `analysis_version`.', '',
        '| Family | Cases | r17 | B-1 alone | r18 (B-1 + L-1) |',
        '| --- | ---: | --- | --- | --- |',
    ]
    for group, counts in comparison['groups'].items():
        cell = lambda name: ' / '.join(str(counts[name + '_' + key]) for key in ['wrong', 'placed', 'holds', 'bare'])
        lines.append(f'| {group} | {counts["cases"]} | {cell("r17")} | {cell("b1")} | {cell(chosen)} |')
    lines += ['', '## Evidence and preservation', '',
              f'SHA-256 verification covers all {len(initial):,} starting tracked files. Only `placement.py` '
              'and the exact N-1 docstring differ. Every other existing test, fixture, evidence file, '
              'and `.done` marker—including the restored r16 marker—is byte-for-byte unchanged. '
              'Memory, HEAD, and index are unchanged.', '',
              '- [Replay runner](check_evidence.py), [family counts](counterfactual-summary.json), '
              '[all outcomes](counterfactual-cases.json), [worker checks](counterfactual-workers.json).',
              '- [Failing-first matrix](affiliate-failing-first.json), [initial pytest log](failing-first.txt), '
              '[identity checks](failing-first-identity.txt), [test-run counts](test-runs-summary.json).',
              '- [Full suite log](full-suite.txt), [JUnit](full-suite.xml), '
              '[inventory audit](test-inventory-summary.json), [hash audit](preservation-summary.json).',
              '- [Goldens](placements.json), [method and commands](method.md).', '', '**Blockers:** none.', '']
    (OUT / 'results-r18.md').write_text('\n'.join(lines))
    marker = [f'coder rc=0 head={head}',
              'Failing first: affiliate matrix 320 wrong / 96 correct / 1120 holds; pytest 321 failed / 1217 passed; identity checks 8 failed / 12 passed.',
              'Changed: crossing headings retain role-mapped, behalf-stripped company competition; printed-name evidence remains authoritative; VERSION=c2a.18; N-1 docstring corrected.',
              f'L-1 retained: heading must enter the neighbour column; 20 additional correct affiliate placements; zero wrong. Selected candidate={chosen}.',
              'L-1 failing first: 20 failed / 68 passed against B-1 alone; all 88 new boundary/PDF checks retained.',
              f'Full suite: {full["passed"]} passed, 0 failed, 0 errors, 0 skipped; completed without -x.',
              f'Replay: {comparison["cases"]} evaluations, 0 wrong for r18; seven goldens exact except analysis_version; native fields exact; HTTP calls=0.',
              f'Test changes: {inventory["new_cases"]} new cases in test_placement_r18.py; all 15498 existing cases retained; only existing edit is authorized N-1 docstring.',
              f'Preservation: {len(initial)} baseline tracked files hash-verified; all other tests, fixtures, evidence and .done markers unchanged; HEAD/index/memory unchanged; no commit.',
              'Blockers: none.', '']
    (OUT / 'counterparty-c2a-r18.done').write_text('\n'.join(marker))
    print(json.dumps({'suite': full, 'preservation': preservation, 'inventory': inventory}, indent=2))


if __name__ == '__main__':
    main()
