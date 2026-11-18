"""Complete the cand3 suite in an isolated copy while preserving the narrow run."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def main():
    source = (OUT / 'cand3-source.py.txt').read_bytes().replace(
        b"VERSION = 'c2a.23'", b"VERSION = 'c2a.24'", 1)
    (OUT / 'fallback-source.py.txt').write_bytes(source)
    with TemporaryDirectory(prefix='fallback-suite-', dir=OUT) as scratch:
        root = Path(scratch)
        for entry in ROOT.iterdir():
            if entry.name != 'backend':
                (root / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        backend = root / 'backend'
        backend.mkdir()
        for entry in (ROOT / 'backend').iterdir():
            if entry.name != 'dealroom_sign':
                (backend / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        shutil.copytree(ROOT / 'backend/dealroom_sign', backend / 'dealroom_sign',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (backend / 'dealroom_sign/placement.py').write_bytes(source)
        test_hashes = {}
        for path in (ROOT / 'backend/dealroom_sign/tests').rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                relative = path.relative_to(ROOT)
                assert path.read_bytes() == (root / relative).read_bytes(), relative
                test_hashes[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                   SECRET_KEY='dummy-secret-key-for-ci-tests',
                   DATABASE_URL='sqlite:///' + scratch + '/db.sqlite3',
                   REDIS_URL='redis://127.0.0.1:16379', CELERY_TASK_ALWAYS_EAGER='True',
                   INTERNAL_API_TOKEN='dummy-internal-api-token-for-ci',
                   FIELD_ENCRYPTION_KEY='S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8=',
                   CORE_API_URL='http://127.0.0.1:18080', SIGN_INTERNAL_URL='http://sign.test',
                   TMPDIR=scratch)
        for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
            env.pop(key, None)
        proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                               'dealroom_sign/tests', '--tb=short',
                               '--junitxml=' + str(OUT / 'fallback-full-suite.xml')],
                              cwd=backend, env=env)
    (OUT / 'fallback-suite-provenance.json').write_text(json.dumps(dict(
        returncode=proc.returncode, source_sha256=hashlib.sha256(source).hexdigest(),
        test_hashes=test_hashes, scratch_removed=not root.exists()), indent=2) + '\n')
    return proc.returncode


if __name__ == '__main__':
    sys.exit(main())
