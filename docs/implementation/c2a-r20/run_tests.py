"""Run the existing local Send test environment with scratch confined to this repo."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

with TemporaryDirectory(prefix='test-runtime-', dir=OUT) as scratch:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               SECRET_KEY='dummy-secret-key-for-ci-tests',
               DATABASE_URL='sqlite:///' + scratch + '/db.sqlite3',
               REDIS_URL='redis://127.0.0.1:16379', CELERY_TASK_ALWAYS_EAGER='True',
               INTERNAL_API_TOKEN='dummy-internal-api-token-for-ci',
               FIELD_ENCRYPTION_KEY='S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8=',
               CORE_API_URL='http://127.0.0.1:18080', SIGN_INTERNAL_URL='http://sign.test',
               TMPDIR=scratch)
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        env.pop(key, None)
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                             *sys.argv[1:]], cwd=ROOT / 'backend', env=env)
    sys.exit(result.returncode)
