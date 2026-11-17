"""Replay final regression tests against the reviewed commits, restoring edits."""
from pathlib import Path
import subprocess

send = Path('/root/worktrees/send-c1b')
board = Path('/root/worktrees/board-s1')
out = send / 'docs/implementation/c2a-r4'


def replay(root, revision, relative, runner, args, logfile):
    path = root / relative
    working = path.read_bytes()
    baseline = subprocess.check_output(['git', 'show', f'{revision}:{relative}'], cwd=root)
    try:
        path.write_bytes(baseline)
        with (out / logfile).open('w') as log:
            log.write(f'Baseline: {revision}; production file: {relative}\n')
            log.flush()
            run = subprocess.run(['bash', str(out / runner), *args], cwd=send, stdout=log, stderr=subprocess.STDOUT)
        print(f'{logfile}: exit {run.returncode}', flush=True)
    finally:
        path.write_bytes(working)
        assert path.read_bytes() == working


replay(send, 'ef62c4da', 'backend/dealroom_sign/placement.py', 'run-send-tests.sh',
       ['dealroom_sign/tests/test_placement_r4.py', 'dealroom_sign/tests/test_placement_transport_r4.py',
        'dealroom_sign/tests/test_send_r4.py',
        'dealroom_sign/tests/test_placement_r3.py::test_inserted_raw_person_vetoes_across_fixtures'],
       'baseline-send-red.txt')
replay(board, '11d1606', 'hermes_board/dealroom.py', 'run-board-tests.sh',
       ['tests/test_dealroom_c2a_r4.py', '-k', 'not expired'], 'baseline-board-red.txt')
