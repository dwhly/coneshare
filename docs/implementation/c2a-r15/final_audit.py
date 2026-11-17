"""Record suite counts and preservation checks after the required run finishes."""
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


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def main():
    tree = ET.parse(OUT / 'full-suite.xml')
    groups, outcomes = defaultdict(Counter), []
    for case in tree.iter('testcase'):
        status = next((key for key in ['failure', 'error', 'skipped'] if case.find(key) is not None), 'passed')
        groups[case.attrib['classname']][status] += 1
        outcomes.append({'class': case.attrib['classname'], 'case': case.attrib['name'], 'status': status})
    totals = sum(groups.values(), Counter())
    summary = {'totals': totals, 'groups': groups,
               'suites': [suite.attrib for suite in tree.iter('testsuite')],
               'command': 'PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test '
                          '/root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b '
                          'dealroom_sign/tests -x --junitxml=' + str(OUT / 'full-suite.xml'),
               'launcher_scratch_warning': 'mktemp' in (OUT / 'full-suite.txt').read_text()}
    write('full-suite-summary.json', summary)
    write('full-suite-cases.json', outcomes)
    summary['complete_and_green'] = totals == {'passed': 11309}
    summary['stopped_on_existing_test_failure'] = bool(totals['failure'] or totals['error'])
    write('full-suite-summary.json', summary)
    initial = json.loads((OUT / 'initial-audit.json').read_text())
    changed_tests = [path for path, sha in initial['existing_test_files'].items() if digest(ROOT / path) != sha]
    comparison = json.loads((OUT / 'counterfactual-summary.json').read_text())
    source = ROOT / 'backend/dealroom_sign/placement.py'
    report = ROOT / 'docs/implementation/c1b-report.md'
    report_before = subprocess.check_output(['git', 'show', 'HEAD:docs/implementation/c1b-report.md'], cwd=ROOT)
    check = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    cached = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).decode().splitlines()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT).decode().strip()
    checks = {'existing_test_files_checked': len(initial['existing_test_files']),
              'existing_test_changes': changed_tests,
              'new_tests_identical_to_failing_first': digest(ROOT / 'backend/dealroom_sign/tests/test_placement_r15.py') == initial['test_sha256'],
              'production_identical_to_measured_c': digest(source) == comparison['source_sha256']['c'],
              'report_append_only': report.read_bytes().startswith(report_before),
              'memory_unchanged': digest(ROOT / '.agent/memory.md') == initial['memory_sha256'],
              'head': head, 'branch': branch, 'index_changes': cached,
              'whitespace_check_rc': check.returncode, 'whitespace_check_output': check.stdout + check.stderr,
              'cache_directories': sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
                                          if p.is_dir() and p.name in {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules'}),
              'venv_configs': sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('pyvenv.cfg'))}
    write('preservation-summary.json', checks)
    assert not changed_tests and checks['new_tests_identical_to_failing_first']
    assert checks['production_identical_to_measured_c'] and checks['report_append_only']
    assert head == comparison['base'] and branch == 'agent/c1b-counterparty'
    assert not cached and check.returncode == 0
    assert not checks['cache_directories'] and not checks['venv_configs']
    print(json.dumps({'suite': totals, 'preservation': checks}, indent=2))


if __name__ == '__main__':
    main()
