"""Record the completed suite, unchanged existing tests, and measured source."""
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


def write(stem, value):
    (OUT / (stem + '-r15b.json')).write_text(json.dumps(value, indent=2) + '\n')


def main():
    tree = ET.parse(OUT / 'full-suite-r15b.xml')
    groups, outcomes, failures = defaultdict(Counter), [], []
    for case in tree.iter('testcase'):
        status = next((key for key in ['failure', 'error', 'skipped'] if case.find(key) is not None), 'passed')
        groups[case.attrib['classname']][status] += 1
        record = {'class': case.attrib['classname'], 'case': case.attrib['name'], 'status': status}
        outcomes.append(record)
        if status != 'passed':
            failures.append(dict(record, details=case.find(status).text))
    totals = sum(groups.values(), Counter())
    summary = {'totals': totals, 'groups': groups, 'failures': failures,
               'suites': [suite.attrib for suite in tree.iter('testsuite')],
               'command': 'PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test '
                          '/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b '
                          'dealroom_sign/tests --junitxml=' + str(OUT / 'full-suite-r15b.xml'),
               'complete_and_green': totals == {'passed': 11340},
               'launcher_scratch_warning': 'mktemp' in (OUT / 'full-suite-r15b.txt').read_text()}
    write('full-suite-summary', summary)
    write('full-suite-cases', outcomes)
    initial = json.loads((OUT / 'initial-audit-r15b.json').read_text())
    test_paths = [path for path in initial['sha256'] if path.startswith('backend/dealroom_sign/tests/')]
    changed_tests = [path for path in test_paths if digest(ROOT / path) != initial['sha256'][path]]
    comparison = json.loads((OUT / 'counterfactual-summary-combined-r15b.json').read_text())
    source = ROOT / 'backend/dealroom_sign/placement.py'
    report = ROOT / 'docs/implementation/c1b-report.md'
    report_before = subprocess.check_output(['git', 'show', 'HEAD:docs/implementation/c1b-report.md'], cwd=ROOT)
    check = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    cached = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).decode().splitlines()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    tracked_changes = subprocess.check_output(['git', 'diff', '--name-only', '--', 'backend/dealroom_sign/tests'], cwd=ROOT).decode().splitlines()
    checks = {'test_and_fixture_files_checked': len(test_paths), 'changed_test_files': changed_tests,
              'tracked_existing_test_changes': tracked_changes,
              'production_identical_to_measured_combined': digest(source) == comparison['source_sha256']['combined'],
              'report_append_only': report.read_bytes().startswith(report_before),
              'inherited_r15_report_preserved': hashlib.sha256(
                  report.read_bytes().split(b'\n## C2a r15b', 1)[0]).hexdigest()
                  == initial['sha256']['docs/implementation/c1b-report.md'],
              'memory_unchanged': digest(ROOT / '.agent/memory.md') == initial['sha256']['.agent/memory.md'],
              'head': head, 'index_changes': cached,
              'whitespace_check_rc': check.returncode, 'whitespace_check_output': check.stdout + check.stderr,
              'cache_directories': sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
                                          if p.is_dir() and p.name in {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules'}),
              'venv_configs': sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('pyvenv.cfg'))}
    aligned = json.loads((OUT / 'aligned-failing-first-summary-r15b.json').read_text())
    checks['aligned_tests_identical_to_failing_first'] = digest(
        ROOT / 'backend/dealroom_sign/tests/test_placement_r15b_columns.py') == aligned['test_sha256']
    write('preservation-summary', checks)
    assert not changed_tests and not tracked_changes
    assert checks['aligned_tests_identical_to_failing_first']
    assert checks['production_identical_to_measured_combined'] and checks['report_append_only']
    assert checks['inherited_r15_report_preserved']
    assert checks['memory_unchanged'] and head == comparison['base'] == initial['head']
    assert not cached and check.returncode == 0
    assert not checks['cache_directories'] and not checks['venv_configs']
    print(json.dumps({'suite': totals, 'preservation': checks}, indent=2))


if __name__ == '__main__':
    main()
