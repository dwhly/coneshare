"""Verify unchanged starting files, test inventory, source and release bars."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from variants import variants

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def write(name, data):
    target = OUT / (name + '.json')
    assert not target.exists(), target
    target.write_text(json.dumps(data, indent=2) + '\n')


def run_counts(name):
    counts = Counter({'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0})
    by_test, inventory = defaultdict(Counter), []
    for test in ET.parse(OUT / (name + '.xml')).iter('testcase'):
        status = ('failed' if test.find('failure') is not None else
                  'errors' if test.find('error') is not None else
                  'skipped' if test.find('skipped') is not None else 'passed')
        counts[status] += 1
        by_test[test.attrib['name'].split('[')[0]][status] += 1
        inventory.append(test.attrib['classname'] + '::' + test.attrib['name'])
    return {'counts': counts, 'by_test': by_test}, inventory


def main():
    before = json.loads((OUT / 'starting-hashes.json').read_text())
    start = json.loads((OUT / 'starting-state.json').read_text())
    changed, missing = [], []
    for name, digest in before.items():
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            changed.append(name)
    preservation = {
        'starting_files': len(before), 'changed': changed, 'missing': missing,
        'head_unchanged': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == start['head'],
        'index_unchanged': subprocess.check_output(['git', 'ls-files', '-s'], cwd=ROOT).decode() == start['index'],
    }
    write('preservation-summary', preservation)
    assert changed == ['backend/dealroom_sign/placement.py'] and not missing
    assert preservation['head_unchanged'] and preservation['index_unchanged']

    baseline = subprocess.check_output(['git', 'show', start['head'] + ':backend/dealroom_sign/placement.py'], cwd=ROOT).decode()
    source = (ROOT / 'backend/dealroom_sign/placement.py').read_text()
    assert variants(baseline)['r21'] == source
    digest = hashlib.sha256(source.encode()).hexdigest()
    for filename in ['release-historical-summary', 'release-review-summary',
                     'release-layouts-summary', 'reviewer-layouts-summary']:
        summary = json.loads((OUT / (filename + '.json')).read_text())
        assert summary['source_sha256']['r21'] == digest, filename
        assert summary['external_http_calls'] == 0, filename
        assert all(group.get('r21_wrong', 0) == 0 for group in summary['groups'].values()), filename
    write('source-equivalence', {'release_equals_measured_source': True, 'sha256': digest})

    runs = {}
    for name in ['failing-first', 'failing-first-options', 'baseline-final-options',
                 'targeted', 'targeted-refinement', 'fix3-existing-boundaries', 'full-suite']:
        runs[name], _ = run_counts(name)
    write('test-runs-summary', runs)
    full, actual = run_counts('full-suite')
    qualified = full['counts']['failed'] == full['counts']['errors'] == full['counts']['skipped'] == 0
    previous = [t.attrib['classname'] + '::' + t.attrib['name']
                for t in ET.parse(OUT.parent / 'c2a-r20/full-suite.xml').iter('testcase')]
    removed = list((Counter(previous) - Counter(actual)).elements())
    added = list((Counter(actual) - Counter(previous)).elements())
    write('test-inventory-summary', {'previous': len(previous), 'current': len(actual),
                                     'added': len(added), 'removed': removed})
    assert not removed and len(added) == 5596

    historical = json.loads((OUT / 'release-historical-summary.json').read_text())
    golden = historical['groups']['Seven goldens']
    assert golden['r21_golden_diffs'] == golden['r21_native_diffs'] == 0
    failures = [test.attrib['classname'] + '::' + test.attrib['name']
                for test in ET.parse(OUT / 'full-suite.xml').iter('testcase')
                if test.find('failure') is not None or test.find('error') is not None]
    write('release-bars', {'qualified': qualified, 'wrong': 0, 'golden_diffs': 0, 'native_golden_diffs': 0,
                           'full_suite': full['counts'], 'starting_files_preserved': len(before) - 1})
    print(json.dumps({'preservation': preservation, 'full_suite': full['counts'],
                      'added_tests': len(added), 'source_sha256': digest,
                      'qualified': qualified, 'failures': failures}, indent=2))
    sys.exit(0 if qualified else 1)


if __name__ == '__main__':
    main()
