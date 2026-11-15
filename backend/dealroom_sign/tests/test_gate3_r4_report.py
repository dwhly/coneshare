"""Execute the documented generator only against fictional temporary files."""
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

REPORT = Path(__file__).resolve().parents[3]/'docs/implementation/c1b-report.md'


def generator():
    return re.search(r"python3 - <<'PY'\n(.*?)\n   PY", REPORT.read_text(), re.S)[1].replace('\n   ', '\n').lstrip()


def prepare(tmp_path, text='EXISTING=fixture\n'):
    directory = tmp_path/'deploy/do1/proto'; directory.mkdir(parents=True)
    env = directory/'send.env'; env.write_text(text); env.chmod(0o644)
    return env, directory/'fleet-proxy-key'


def test_nit11_generator_sets_private_modes(tmp_path):
    env, proxy = prepare(tmp_path)
    result = subprocess.run([sys.executable, '-c', generator()], cwd=tmp_path, capture_output=True)
    assert result.returncode == 0 and result.stdout == b''
    assert env.stat().st_mode & 0o777 == 0o600
    assert proxy.stat().st_mode & 0o777 == 0o600
    assert len(re.findall('SIGN_CAPABILITY_KEY=', env.read_text())) == 1


@pytest.mark.parametrize('line', ['SIGN_CAPABILITY_KEY=fixture', 'export SIGN_CAPABILITY_KEY=fixture', 'SIGN_CAPABILITY_KEY = fixture'])
def test_nit11_generator_preserves_existing_keys(tmp_path, line):
    env, proxy = prepare(tmp_path, line+'\n')
    result = subprocess.run([sys.executable, '-c', generator()], cwd=tmp_path, capture_output=True)
    assert result.returncode != 0
    assert env.read_text() == line+'\n' and not proxy.exists()


def test_nit11_proxy_creation_failure_does_not_append_env(tmp_path):
    env, proxy = prepare(tmp_path)
    prefix = '''from pathlib import Path
original_open = Path.open
def fail_proxy(self, mode='r', *args, **kwargs):
    if self.name == 'fleet-proxy-key' and mode == 'x':
        raise PermissionError('fictional creation failure')
    return original_open(self, mode, *args, **kwargs)
Path.open = fail_proxy
'''
    result = subprocess.run([sys.executable, '-c', prefix+generator()], cwd=tmp_path, capture_output=True)
    assert result.returncode != 0
    assert env.read_text() == 'EXISTING=fixture\n' and not proxy.exists()


def test_minor7_report_discloses_network_lock_tradeoff():
    assert 'parallel tRPC calls and co-signers wait' in REPORT.read_text()


def test_minor10_report_limits_mutation_claim():
    assert 'does not prove that removing the listener route gate is detected' in REPORT.read_text()


def test_minor1_key_still_fails_closed_without_pytest_fixture():
    # Standalone Django initialization does not import pytest's autouse fixture.
    script = '''import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
import django
django.setup()
from django.conf import settings
from dealroom_sign.counterparty import keyed_hash
from dealroom_sign.client import SignError
if hasattr(settings, 'SIGN_CAPABILITY_KEY'):
    del settings.SIGN_CAPABILITY_KEY
try:
    keyed_hash('link', 'fixture')
except SignError as exc:
    assert exc.code == 'capability_key_unavailable'
else:
    raise AssertionError('Missing capability key must fail closed')
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, env={**os.environ, 'SIGN_CAPABILITY_KEY': ''})
    assert result.returncode == 0, result.stderr.decode()
