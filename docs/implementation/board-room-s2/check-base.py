"""Replay new S2 acceptance cases against the named base in a disposable archive."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
root=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='dealroom-s2-base-') as directory:
    base=Path(directory)
    archive=subprocess.check_output(['git','archive','bed45588'],cwd=root)
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        files.extractall(base,filter='data')
    for rel in ['backend/tests/dealroom/test_room_commands_s2.py','backend/tests/s2_postgres/test_room_concurrency.py',
                'docs/implementation/board-room-s2/run-isolated-postgres.sh',
                'docs/implementation/board-room-s2/run-postgres-tests.sh','docs/implementation/board-room-s2/s2_postgres_settings.py']:
        target=base/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/rel,target)
    with (root/'docs/implementation/board-room-s2/extended-base-red.txt').open('w') as log:
        result=subprocess.run(['bash',str(base/'docs/implementation/board-room-s2/run-isolated-postgres.sh')],stdout=log,stderr=subprocess.STDOUT)
    print('Base replay exit:',result.returncode)
