"""Run draft-test corrections against the unchanged r21 source and worker."""
from pathlib import Path
import subprocess
import tempfile

from dealroom_sign import placement

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
scratch = None


def pytest_configure(config):
    global scratch
    source = subprocess.check_output(
        ['git', 'show', 'afb9aa6e:backend/dealroom_sign/placement.py'], cwd=ROOT).decode()
    exec(compile(source, placement.__file__, 'exec'), placement.__dict__)
    scratch = tempfile.TemporaryDirectory(prefix='baseline-worker-', dir=OUT)
    package = Path(scratch.name) / 'dealroom_sign'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'placement.py').write_text(source)
    (package / 'placement_worker.py').write_bytes(
        (ROOT / 'backend/dealroom_sign/placement_worker.py').read_bytes())
    placement.WORKER_CWD = Path(scratch.name)


def pytest_unconfigure(config):
    if scratch:
        scratch.cleanup()
