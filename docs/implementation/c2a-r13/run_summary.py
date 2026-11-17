"""Run the supplied signing test runner, retaining only compact count evidence."""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from xml.etree import ElementTree


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def main():
    name, *targets = sys.argv[1:]
    report = OUT / (name + '.xml')
    command = ['/root/work/sign-product/run-send-local.sh', str(ROOT), *targets]
    env = dict(os.environ, SIGN_INTERNAL_URL='http://sign.test', PYTHONDONTWRITEBYTECODE='1',
               PYTHONUNBUFFERED='1')
    executed_command = command + ['--tb=short', '--junitxml=' + str(report)]
    process = subprocess.Popen(executed_command, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    output = []
    for line in process.stdout:
        output.append(line)
        if re.match(r'^[.FEsx]+\s+\[', line):
            print(line.rstrip(), flush=True)
    result = subprocess.CompletedProcess(executed_command, process.wait(), ''.join(output), '')
    if not report.exists():
        print(result.stdout[-4000:] + result.stderr[-4000:])
        raise SystemExit(result.returncode or 1)
    suite = ElementTree.parse(report).getroot().find('testsuite')
    groups = defaultdict(lambda: defaultdict(int))
    failures = {}
    cases = []
    for test in suite.findall('testcase'):
        state = next((s for s in ('failure', 'error', 'skipped') if test.find(s) is not None), 'passed')
        cases.append({'test': test.get('classname') + '.' + test.get('name'), 'outcome': state})
        group = test.get('name').split('[')[0]
        groups[group][state] += 1
        if state in {'failure', 'error'}:
            failures.setdefault(group, {'example_test': test.get('classname') + '.' + test.get('name'),
                                        'message': test.find(state).get('message', '')[:400]})
    summary = {'command': 'SIGN_INTERNAL_URL=http://sign.test ' + shlex.join(command),
               'reporting_arguments': ['--tb=short', '--junitxml=' + str(report)],
               'base': '4ad9f7e20822ca15e8c5a5196f8b61c8cb59a312', 'exit_code': result.returncode,
               **{k: int(suite.get(k, 0)) for k in ('tests', 'failures', 'errors', 'skipped')},
               'seconds': float(suite.get('time')), 'groups': dict(groups),
               'raw_suite_logs_retained': False}
    summary['source_sha256'] = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in (
            'backend/dealroom_sign/placement.py',
            'backend/dealroom_sign/tests/test_placement_r13.py',
            'backend/dealroom_sign/tests/test_placement_r12.py',
            'backend/dealroom_sign/tests/test_placement_r11.py',
            'backend/dealroom_sign/tests/test_placement_r10.py',
            'backend/dealroom_sign/tests/test_placement_r9.py',
        )
    }
    summary['passed'] = summary['tests'] - sum(summary[k] for k in ('failures', 'errors', 'skipped'))
    warnings = re.findall(r'(\d+) warnings?', result.stdout)
    if warnings:
        summary['warnings'] = int(warnings[-1])
    if failures:
        summary['failure_inventory'] = failures
    (OUT / (name + '.json')).write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / (name + '-cases.json')).write_text(json.dumps(cases, indent=2) + '\n')
    report.unlink()
    print(json.dumps({k: v for k, v in summary.items() if k not in {'groups', 'failure_inventory'}}, indent=2))
    if failures:
        print(json.dumps(dict(groups), indent=2))
        print(json.dumps(failures, indent=2))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
