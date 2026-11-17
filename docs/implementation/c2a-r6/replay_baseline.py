"""Replay final r6 tests on 1efaca25 and always restore the working production file."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
relative = 'backend/dealroom_sign/placement.py'
path = root / relative
working = path.read_bytes()
baseline = subprocess.check_output(['git', 'show', f'1efaca25:{relative}'], cwd=root)
try:
    path.write_bytes(baseline)
    with (out / 'baseline-send-red.txt').open('w') as log:
        log.write('Baseline: 1efaca25; final r6 tests; only placement.py temporarily restored.\n')
        log.flush()
        run = subprocess.run(['bash', str(out / 'run-send-tests.sh'),
                              'dealroom_sign/tests/test_placement_r6.py',
                              'dealroom_sign/tests/test_send_r6.py'],
                             cwd=root, stdout=log, stderr=subprocess.STDOUT)
    print(f'Baseline replay exit: {run.returncode}')
finally:
    path.write_bytes(working)
    assert path.read_bytes() == working
