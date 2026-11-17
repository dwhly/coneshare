"""Audit complete pytest outcomes, immutable tests, and the measured candidate."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')


def suite(stem):
    tree = ET.parse(OUT / (stem + '.xml'))
    groups, cases = defaultdict(Counter), []
    counts = Counter(dict(passed=0, failed=0, errors=0, skipped=0))
    for case in tree.iter('testcase'):
        tag = next((s for s in ['failure', 'error', 'skipped'] if case.find(s) is not None), None)
        status = {'failure': 'failed', 'error': 'errors', 'skipped': 'skipped', None: 'passed'}[tag]
        counts[status] += 1
        groups[case.attrib['classname']][status] += 1
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
    initial = json.loads((OUT / 'initial-audit.json').read_text())
    full = suite('full-suite')
    failing = {stem: suite(stem)['counts'] for stem in [
        'failing-first-existing', 'failing-first-new', 'failing-first-crossing']}
    write('failing-first-summary', failing)
    comparison = json.loads((OUT / 'counterfactual-summary.json').read_text())
    special = {'.agent/memory.md', 'backend/dealroom_sign/placement.py',
               'docs/implementation/c1b-report.md'}
    tests = {p: sha for p, sha in initial['sha256'].items() if p not in special}
    changed = [p for p, sha in tests.items() if not (ROOT / p).is_file() or digest(ROOT / p) != sha]
    check = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    index = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).decode().splitlines()
    tracked = subprocess.check_output(['git', 'diff', '--name-only', '--',
                                      'backend/dealroom_sign/tests'], cwd=ROOT).decode().splitlines()
    new_test = 'backend/dealroom_sign/tests/test_placement_r16.py'
    audit = dict(existing_test_and_fixture_files_checked=len(tests), changed_existing_tests=changed,
                 tracked_test_changes=tracked, new_test=new_test, new_test_sha256=digest(ROOT / new_test),
                 source_sha256=digest(ROOT / 'backend/dealroom_sign/placement.py'),
                 source_matches_comparison=digest(ROOT / 'backend/dealroom_sign/placement.py') ==
                 comparison['source_sha256']['chosen'],
                 memory_unchanged=digest(ROOT / '.agent/memory.md') == initial['sha256']['.agent/memory.md'],
                 inherited_report_unchanged=digest(ROOT / 'docs/implementation/c1b-report.md') ==
                 initial['sha256']['docs/implementation/c1b-report.md'],
                 head=head, index_changes=index, whitespace_check_rc=check.returncode,
                 whitespace_output=check.stdout + check.stderr)
    write('preservation-summary', audit)

    data = json.loads((OUT / 'counterfactual-cases.json').read_text())
    changed_geometry, checked = [], 0
    for row in data['cases']:
        result = data['outcomes'][row['results']['chosen']]
        nearest = data['outcomes'][row['results']['nearest']]
        if result['status'] == 'placed':
            checked += len(result['fields'])
            if result['fields'] != nearest['fields']:
                changed_geometry.append({'group': row['group'], 'case': row['case']})
    write('geometry-audit', dict(placed_fields_checked=checked,
                               changed_fields_against_nearest=changed_geometry))
    assert not changed and not tracked and not index and check.returncode == 0
    assert audit['source_matches_comparison'] and audit['memory_unchanged'] and audit['inherited_report_unchanged']
    assert head == initial['head'] == comparison['base']
    assert not changed_geometry
    print(json.dumps(dict(full_suite=full['counts'], preservation=audit), indent=2))


if __name__ == '__main__':
    main()
