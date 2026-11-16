"""Replay the final r5 regressions on 079e2957, restoring the working code."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
relative = 'backend/dealroom_sign/placement.py'
path = root / relative
working = path.read_bytes()
baseline = subprocess.check_output(['git', 'show', f'079e2957:{relative}'], cwd=root)
try:
    path.write_bytes(baseline)
    with (out / 'baseline-send-red.txt').open('w') as log:
        log.write('Baseline: 079e2957; final r5 tests; only placement.py temporarily restored.\n')
        log.flush()
        run = subprocess.run(['bash', str(out / 'run-send-tests.sh'),
                              'dealroom_sign/tests/test_placement_r5.py',
                              'dealroom_sign/tests/test_send_r5.py'],
                             cwd=root, stdout=log, stderr=subprocess.STDOUT)
    print(f'Baseline replay exit: {run.returncode}')
finally:
    path.write_bytes(working)
    assert path.read_bytes() == working
