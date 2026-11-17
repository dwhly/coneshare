"""Hash-preserve the baseline and record every pytest outcome."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRODUCT = 'backend/dealroom_sign/placement.py'
N1 = 'backend/dealroom_sign/tests/test_placement_r16.py'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(stem, data):
    (OUT / (stem + '.json')).write_text(json.dumps(data, indent=2) + '\n')


def suite(stem):
    tree = ET.parse(OUT / (stem + '.xml'))
    groups, cases = defaultdict(Counter), []
    counts = Counter(dict(passed=0, failed=0, errors=0, skipped=0))
    for case in tree.iter('testcase'):
        tag = next((s for s in ['failure', 'error', 'skipped'] if case.find(s) is not None), None)
        status = {'failure': 'failed', 'error': 'errors', 'skipped': 'skipped', None: 'passed'}[tag]
        counts[status] += 1
        groups[case.attrib['name'].split('[')[0]][status] += 1
        record = dict(classname=case.attrib['classname'], case=case.attrib['name'], status=status)
        if tag:
            record['details'] = case.find(tag).text
        cases.append(record)
    summary = dict(counts=counts, total=sum(counts.values()), groups=groups,
                   failures=[c for c in cases if c['status'] != 'passed'],
                   suites=[s.attrib for s in tree.iter('testsuite')])
    write(stem + '-summary', summary)
    if stem == 'full-suite':
        write('full-suite-cases', cases)
    return summary


def main():
    initial = json.loads((OUT / 'initial-hashes.json').read_text())
    changed = [p for p, sha in initial.items() if not (ROOT / p).is_file() or digest(ROOT / p) != sha]
    original_n1 = subprocess.check_output(['git', 'show', '75837b04:' + N1], cwd=ROOT).decode()
    n1_only = (ROOT / N1).read_text() == original_n1.replace('assert party.scores == [6]', 'assert party.scores == [0]')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    index = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).decode().splitlines()
    check = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    comparison = json.loads((OUT / 'counterfactual-summary.json').read_text())
    audit = dict(tracked_files_hash_checked=len(initial), changed_tracked_files=changed,
                 only_permitted_test_assertion_changed=n1_only,
                 all_other_tracked_tests_fixtures_and_evidence_hash_exact=set(changed) == {PRODUCT, N1},
                 memory_unchanged=digest(ROOT / '.agent/memory.md') == initial['.agent/memory.md'],
                 head=head, index_changes=index, whitespace_check_rc=check.returncode,
                 source_matches_comparison=digest(ROOT / PRODUCT) == comparison['source_sha256']['r17'])
    write('preservation-summary', audit)
    summaries = {stem: suite(stem)['counts'] for stem in [
        'failing-first', 'failing-first-heading', 'targeted-green', 'targeted-retained-witness',
        'r11-preserved', 'targeted-final', 'retained-witness-candidate/full-suite', 'full-suite']}
    write('test-runs-summary', summaries)
    previous = json.loads((OUT.parent / 'c2a-r16/full-suite-cases.json').read_text())
    current = json.loads((OUT / 'full-suite-cases.json').read_text())
    before = Counter((c['classname'], c['case']) for c in previous)
    after = Counter((c['classname'], c['case']) for c in current)
    missing = list((before - after).elements())
    write('test-inventory-summary', dict(previous_cases=len(previous), current_cases=len(current),
                                       missing_existing_test_cases=missing,
                                       new_cases=sum((after - before).values())))
    assert not missing, missing
    assert set(changed) == {PRODUCT, N1} and n1_only and not index and check.returncode == 0
    assert audit['source_matches_comparison'] and audit['memory_unchanged']
    assert head == comparison['base'] == '75837b04da05c3b736d6f48648536627bd062ca0'
    assert summaries['full-suite']['failed'] == summaries['full-suite']['errors'] == summaries['full-suite']['skipped'] == 0
    assert all(comparison['bars'].values()), comparison['bars']
    print(json.dumps(dict(test_runs=summaries, preservation=audit), indent=2))


if __name__ == '__main__':
    main()
