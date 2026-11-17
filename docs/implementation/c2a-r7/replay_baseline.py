"""Replay new r7 tests on be30d623 and restore the working production file."""
import os
from pathlib import Path
import re
import subprocess
import json

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
relative = 'backend/dealroom_sign/placement.py'
path = root / relative
working = path.read_bytes()
baseline = subprocess.check_output(['git', 'show', f'be30d623:{relative}'], cwd=root)
try:
    path.write_bytes(baseline)
    with (out / 'baseline-send-red.txt').open('w') as log:
        log.write('Baseline: be30d623; final r7 tests; only placement.py temporarily restored.\n')
        log.flush()
        run = subprocess.run(['/root/work/sign-product/run-send-local.sh', str(root),
                              'dealroom_sign/tests/test_placement_r7.py',
                              'dealroom_sign/tests/test_send_r7.py'], cwd=root,
                             env={**os.environ, 'SIGN_INTERNAL_URL': 'http://sign.test'},
                             stdout=log, stderr=subprocess.STDOUT)
    log_text = (out / 'baseline-send-red.txt').read_text()
    failures = re.findall(r'^FAILED (.+?)(?: - |$)', log_text, re.M)
    summary = {'baseline': 'be30d623', 'exit_code': run.returncode, 'failures': failures}
    (out / 'baseline-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'Baseline replay exit: {run.returncode}; failures: {len(failures)}')
finally:
    path.write_bytes(working)
    assert path.read_bytes() == working
