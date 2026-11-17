"""Exercise deployment settings in fresh processes, outside pytest's settings."""
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[2]
BOARDS = {
    'fixture': {
        'owner_ids': ['owner-1'],
        'room_ids': ['room-1'],
        'team_ids': [3],
    },
    'empty': {'owner_ids': [], 'room_ids': [], 'team_ids': []},
}


@pytest.fixture(params=['backend.settings', 'dealroom_sign.runtime_settings'])
def settings_module(request):
    return request.param


def load_settings(settings_module, boards=None, proxy_key=None):
    env = os.environ.copy()
    env.update({
        'DJANGO_SETTINGS_MODULE': settings_module,
        'SECRET_KEY': 'settings-test-secret',
        'SITE_DOMAIN': 'http://send.test',
        'DATABASE_URL': 'sqlite:///:memory:',
        'SENTRY_DSN': '',
        'SIGN_WEBHOOK_SECRET': 'settings-test-webhook-secret',
    })
    if settings_module == 'dealroom_sign.runtime_settings':
        # Board-setting tests must supply the dedicated runtime's independent transport requirement.
        env['SIGN_INTERNAL_URL'] = 'http://sign.test'
    for name, value in (
        ('BOARD_SIGN_BOARDS', boards),
        ('BOARD_SIGN_PROXY_KEY', proxy_key),
    ):
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return subprocess.run(
        [sys.executable, '-c', textwrap.dedent('''
            import importlib
            import json
            import os

            import django
            from django.conf import settings

            django.setup()
            module = importlib.import_module(os.environ['DJANGO_SETTINGS_MODULE'])
            assert settings.SETTINGS_MODULE == os.environ['DJANGO_SETTINGS_MODULE']
            assert settings.BOARD_SIGN_PROXY_KEY == module.BOARD_SIGN_PROXY_KEY
            assert settings.BOARD_SIGN_BOARDS == module.BOARD_SIGN_BOARDS
            print(json.dumps({
                'proxy_key': settings.BOARD_SIGN_PROXY_KEY,
                'boards': settings.BOARD_SIGN_BOARDS,
            }))
        ''')],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize('boards', [BOARDS, {}])
def test_board_settings_read_from_env(settings_module, boards):
    result = load_settings(settings_module, json.dumps(boards), 'test-proxy-key')

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'proxy_key': 'test-proxy-key', 'boards': boards}


def test_board_settings_default_when_env_absent(settings_module):
    result = load_settings(settings_module)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'proxy_key': '', 'boards': {}}


@pytest.mark.parametrize('boards', ['{', '', '  '], ids=['invalid-json', 'empty', 'whitespace'])
def test_malformed_board_json_fails_at_startup(settings_module, boards):
    result = load_settings(settings_module, boards)

    assert result.returncode != 0
    assert 'ImproperlyConfigured: BOARD_SIGN_BOARDS' in result.stderr


@pytest.mark.parametrize('boards', [
    [], None, True, 1, 'fixture',
    {'fixture': []},
    {'fixture': None},
    {'fixture': {}},
], ids=['list', 'null', 'boolean', 'number', 'string', 'board-list', 'board-null', 'missing-lists'])
def test_invalid_board_shape_fails_at_startup(settings_module, boards):
    result = load_settings(settings_module, json.dumps(boards))

    assert result.returncode != 0
    assert 'ImproperlyConfigured: BOARD_SIGN_BOARDS' in result.stderr


@pytest.mark.parametrize('field', ['owner_ids', 'room_ids', 'team_ids'])
@pytest.mark.parametrize('invalid', ['missing', 'string', 'null', 'object'])
def test_board_scope_requires_lists(settings_module, field, invalid):
    board = dict(BOARDS['fixture'])
    if invalid == 'missing':
        del board[field]
    else:
        board[field] = {'string': 'id-1', 'null': None, 'object': {}}[invalid]
    result = load_settings(settings_module, json.dumps({'fixture': board}))

    assert result.returncode != 0
    assert 'ImproperlyConfigured: BOARD_SIGN_BOARDS' in result.stderr
    assert field in result.stderr
