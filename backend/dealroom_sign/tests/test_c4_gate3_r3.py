"""Gate 3 r2 regressions: optional integration, ingress and tenant scan boundaries."""
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client

from dealroom_sign.client import Documenso
from dealroom_sign.counterparty import COOKIE, new_session
from dealroom_sign.tests.tenant_scan import scan
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_tenant_brand import PNG
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('module,expected', [('backend.settings', ''), ('dealroom_sign.test_settings', 'http://sign.test')])
def test_h_new_1_settings_import_without_sign(module, expected):
    environment = dict(os.environ)
    environment.pop('SIGN_INTERNAL_URL', None)
    environment['DJANGO_SETTINGS_MODULE'] = module
    code = (f'import {module} as settings; assert settings.SIGN_INTERNAL_URL == {expected!r}; '
            'import django; django.setup(); import backend.wsgi, backend.asgi, backend.celery')
    result = subprocess.run([sys.executable, '-c', code], env=environment, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize('url', ['', '  '])
def test_h_new_1_sign_client_fails_clearly_before_transport(settings, url):
    settings.SIGN_INTERNAL_URL = url
    with patch('dealroom_sign.client.httpx.Client') as transport:
        with pytest.raises(ImproperlyConfigured, match='SIGN_INTERNAL_URL is required for Dealroom Sign'):
            Documenso(SimpleNamespace(enabled=True, team_id=1, token='test-token'))
        transport.assert_not_called()


def test_l_new_1_send_v1_exposes_only_exact_logo_routes():
    source = (ROOT / 'deploy/chief-send-v1/nginx.conf').read_text()
    assert 'location /signing/' not in source
    for url in ['/signing/tenant-logo', '/chief/tenant-logo']:
        block = source.split('location = ' + url + ' {')[1].split('}')[0]
        assert 'try_files $uri @proxy_to_app;' in block
        assert 'include /home/coneshare/runtime/nginx/security-headers.conf;' in block


@pytest.mark.parametrize('value', [
    '210 39.5349% 16.8627%', '210 40% 17%', 'hsl(210, 39.5349%, 16.8627%)',
    'rgb(26, 43, 60)', 'RGB(26,43,60)', 'rgb(26 43 60)',
])
def test_l_new_3_colour_representations(tmp_path, value):
    relative = 'frontend/public/dealroom/shell.css'
    file = tmp_path / relative
    file.parent.mkdir(parents=True)
    file.write_text(':root { --chrome-base: ' + value + '; }')
    assert scan(tmp_path, {'FLEET_TEST_TENANT_COLOURS': '#1a2b3c'}) == [relative]


def test_l_new_3_only_exact_vendored_comment_is_exempt(tmp_path):
    relative = 'frontend/public/fds/tokens.css'
    file = tmp_path / relative
    file.parent.mkdir(parents=True)
    original = (ROOT / relative).read_text()
    fixtures = {'FLEET_TEST_TENANT_COLOURS': '#0b1f4d'}
    file.write_text(original)
    assert scan(tmp_path, fixtures) == []
    for source in [original + '\n/* changed */', original + '\n:root { color: #0b1f4d; }', original + '\n/* Acme Test Co */']:
        file.write_text(source)
        assert scan(tmp_path, fixtures) == [relative]
    file.unlink()
    (file.parent / 'other.css').write_text(original)
    assert scan(tmp_path, fixtures) == ['frontend/public/fds/other.css']


@pytest.mark.django_db
@pytest.mark.parametrize('path,status,content_type,authenticated,cacheable', [
    ('/chief/sign-tenant-logo?v=hash', 200, 'image/png', True, True),
    ('/chief/sign-tenant-logo?v=hash', 404, 'image/png', True, False),
    ('/chief/sign-tenant-logo?v=hash', 200, 'text/html', True, False),
    ('/chief/sign-tenant-logo?v=hash', 200, 'image/png', False, False),
    ('/chief/other.png', 200, 'image/png', True, False),
])
def test_n_new_1_cache_is_exact_successful_authenticated_sign_logo(access, settings, tmp_path, path, status, content_type, authenticated, cacheable):
    settings.SIGN_RECIPIENT_ORIGIN = 'https://recipient.test'
    settings.SIGN_RECIPIENT_INTERNAL_URL = 'http://sign-internal.test'
    key = tmp_path / 'proxy-key'
    key.write_text('test-proxy-key')
    settings.FLEET_PROXY_KEY_FILE = str(key)
    browser = Client()
    if authenticated:
        _, raw = new_session(access)
        browser.cookies[COOKIE] = raw
    transport = httpx.MockTransport(lambda request: httpx.Response(status, headers={
        'content-type': content_type, 'cache-control': 'public, max-age=31536000, immutable',
        'x-not-forwarded': 'private-value',
    }, stream=httpx.ByteStream(PNG)))
    with patch('dealroom_sign.recipient_proxy.httpx.Client', return_value=httpx.Client(transport=transport)):
        result = browser.get(path, HTTP_HOST='recipient.test', HTTP_X_FLEET_RECIPIENT_LISTENER='1', HTTP_X_FORWARDED_FOR='192.0.2.1')
        assert result['Cache-Control'] == ('public, max-age=31536000, immutable' if cacheable else 'private, no-store')
        assert 'X-Not-Forwarded' not in result
        assert result['X-Content-Type-Options'] == 'nosniff'
        if cacheable:
            assert b''.join(result.streaming_content) == PNG
            assert not result.cookies
        if not authenticated:
            assert result.status_code == 403
        result.close()
