"""Gate 3 regression coverage for the deployed tenant presentation boundary."""
import ast
import hashlib
import os
import re
import subprocess
import sys
import zlib
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from PIL import Image
from django.test import Client, RequestFactory
from django.utils import translation

from dealroom_sign import tenant_brand
from dealroom_sign.counterparty import COOKIE, new_session
from dealroom_sign.counterparty_mail import compose, enqueue
from dealroom_sign.tests.tenant_scan import scan
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_recipient_shell_c4a import _render
from dealroom_sign.tests.test_tenant_brand import PNG, clean_brand, logo
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.django_db
def test_h1_logo_uses_already_proxied_prefix_on_staff_and_recipient(client, logo, monkeypatch, settings):
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    settings.SIGN_RECIPIENT_ORIGIN = 'https://recipient.test'
    brand = tenant_brand.get_tenant_brand()
    assert brand.logo_url.startswith('/signing/tenant-logo?v=')
    for url in [brand.logo_url, brand.logo_url.replace('/signing/', '/chief/')]:
        for headers in [{}, {'HTTP_HOST': 'recipient.test', 'HTTP_X_FLEET_RECIPIENT_LISTENER': '1'}]:
            response = client.get(url, **headers)
            assert response.status_code == 200 and response.content == PNG
            assert response['Content-Type'] == 'image/png'
            assert not response.cookies and 'immutable' in response['Cache-Control']
    for config in (ROOT / 'deploy').rglob('*nginx.conf'):
        source = config.read_text()
        assert 'location = /chief/tenant-logo' in source, config
        assert 'location /signing/' in source, config


@pytest.mark.parametrize('colour', ['#fff', '#abcdef', '#777777'])
def test_m2_white_text_requires_aa_contrast_and_warns_once(colour, caplog):
    tenant_brand._warned.clear()
    for _ in range(3):
        brand = tenant_brand.parse_tenant_brand({'FLEET_TENANT_CHROME': colour})
        assert not brand.chrome and not brand.chrome_hsl
    assert sum('FLEET_TENANT_CHROME' in r.message for r in caplog.records) == 1
    assert tenant_brand.parse_tenant_brand({'FLEET_TENANT_CHROME': '#767676'}).chrome == '#767676'


@pytest.mark.django_db
def test_m4_logo_requires_valid_chrome_on_page_and_mail(access, logo, monkeypatch, caplog):
    monkeypatch.setenv('FLEET_TENANT_NAME', 'Acme Test Co')
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    tenant_brand._warned.clear()
    for chrome in ['', '#fff', 'invalid']:
        monkeypatch.setenv('FLEET_TENANT_CHROME', chrome)
        brand = tenant_brand.get_tenant_brand()
        assert not brand.logo_url and not brand.logo_bytes
        assert 'class="fleet-tenant-logo"' not in _render('welcome')
        message = compose(enqueue(access, 'invitation', 'no-chrome-' + chrome))
        assert not any(p.get_content_type() == 'image/png' for p in message.message().walk())
        assert 'Acme Test Co' in message.alternatives[0][0]
    assert sum('FLEET_TENANT_LOGO' in r.message for r in caplog.records) == 1


def test_l1_internal_url_is_required_in_both_settings_modules():
    for relative in ['backend/settings.py', 'dealroom_sign/runtime_settings.py']:
        module = ast.parse((ROOT / 'backend' / relative).read_text())
        assignment = next(n.value for n in module.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'SIGN_INTERNAL_URL' for t in n.targets))
        with pytest.raises(KeyError, match='SIGN_INTERNAL_URL'):
            exec(compile(ast.Expression(assignment), relative, 'eval'), {'os': type('Env', (), {'environ': {}})})


def test_l2_fifo_never_blocks_and_configuration_is_warmed_at_boot(tmp_path):
    fifo = tmp_path / 'logo.png'
    os.mkfifo(fifo)
    # A child timeout also catches the stat/open race regression without hanging pytest.
    code = "from dealroom_sign.tenant_brand import _logo; import sys\ntry: _logo(sys.argv[1])\nexcept ValueError: pass\nelse: raise AssertionError('FIFO accepted')"
    result = subprocess.run([sys.executable, '-c', code, str(fifo)], timeout=3, capture_output=True)
    assert result.returncode == 0, result.stderr
    source = (ROOT / 'backend/dealroom_sign/tenant_brand.py').read_text()
    assert 'os.O_NONBLOCK' in source
    assert 'get_tenant_brand()' in (ROOT / 'backend/dealroom_sign/apps.py').read_text()


@pytest.mark.parametrize('width,height,length', [(2001, 1, 13), (1, 601, 13), (30000, 30000, 13), (1, 1, 14)])
def test_l3_logo_dimensions_and_ihdr_length_are_bounded(tmp_path, width, height, length):
    payload = width.to_bytes(4, 'big') + height.to_bytes(4, 'big') + PNG[24:29] + b'\0' * (length - 13)
    chunk = b'IHDR' + payload
    data = PNG[:8] + length.to_bytes(4, 'big') + chunk + zlib.crc32(chunk).to_bytes(4, 'big') + PNG[33:]
    file = tmp_path / 'logo.png'
    file.write_bytes(data)
    assert not tenant_brand.parse_tenant_brand({'FLEET_TENANT_LOGO': str(file), 'FLEET_TENANT_CHROME': '#123456'}).logo_url


@pytest.mark.django_db
def test_l4_cid_image_has_no_attachment_filename(access, logo, monkeypatch):
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    message = compose(enqueue(access, 'invitation', 'inline'))
    image = next(p for p in message.message().walk() if p.get_content_type() == 'image/png')
    assert image['Content-Disposition'] == 'inline'
    assert image.get_filename() is None
    assert image['Content-ID']


@pytest.mark.parametrize('state,wstate,product', [('welcome', 'sent', 'Sign'), ('signed', 'sent', 'Sign'), ('signed', 'done', 'Dealroom')])
def test_l6_n2_title_and_lockup_use_same_product(state, wstate, product, monkeypatch):
    monkeypatch.setenv('FLEET_TENANT_NAME', 'Acme Test Co')
    html = _render(state, wstate=wstate)
    assert re.search(r'<title>[^<]+ · Acme Test Co ' + product + '</title>', html)
    assert 'aria-label="Acme Test Co ' + product + '"' in html


def test_low_baseline_is_not_localized(logo, monkeypatch):
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    with translation.override('de'):
        assert '--tenant-logo-baseline:0.8' in _render('welcome')


def test_m3_l5_theme_tooltip_live_status_and_forced_colours():
    css = (ROOT / 'frontend/public/dealroom/shell.css').read_text()
    js = (ROOT / 'frontend/public/dealroom/shell.js').read_text()
    assert 'forced-colors: active' in css and 'background: ButtonText' in css
    assert 'forced-color-adjust: none' in css
    assert 'setAttribute("title", label)' in js
    assert 'aria-live' in js and 'polite' in js


def test_n5_logo_does_not_advertise_an_unimplemented_validator(logo, monkeypatch):
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    response = tenant_brand.tenant_logo(RequestFactory().get(tenant_brand.get_tenant_brand().logo_url))
    assert 'ETag' not in response


@pytest.mark.parametrize('relative', [
    'backend/backend/settings.py', 'backend/backend/urls.py',
    'backend/dealroom_sign/templates/mail.html', 'frontend/public/dealroom/shell.js',
    'frontend/public/dealroom/icons/logo.svg', 'frontend/public/fds/tokens.css',
    'frontend/public/fds/config.json', 'frontend/public/dealroom/module.mjs',
])
@pytest.mark.parametrize('value,env', [
    ('aCmE tEsT cO', {}), ('#1a2b3c', {'FLEET_TEST_TENANT_COLOURS': '#1A2B3C'}),
    ('#aabbcc', {'FLEET_TEST_TENANT_COLOURS': '#ABC'}), ('#ABC', {'FLEET_TEST_TENANT_COLOURS': '#aabbcc'}),
    ('TENANT.EXAMPLE.TEST', {'FLEET_TEST_TENANT_DOMAINS': 'tenant.example.test'}),
])
def test_m5_scanner_covers_served_trees_and_all_fixture_kinds(tmp_path, relative, value, env):
    file = tmp_path / relative
    file.parent.mkdir(parents=True)
    file.write_text(value)
    assert scan(tmp_path, env) == [relative]


@pytest.mark.django_db
@pytest.mark.parametrize('send_configured', [False, True])
def test_m1_sign_logo_is_forwarded_without_comparing_sends_hash(access, logo, monkeypatch, settings, tmp_path, send_configured):
    settings.SIGN_RECIPIENT_ORIGIN = 'https://recipient.test'
    settings.SIGN_RECIPIENT_INTERNAL_URL = 'http://sign-internal.test'
    key = tmp_path / 'proxy-key'
    key.write_text('test-proxy-key')
    settings.FLEET_PROXY_KEY_FILE = str(key)
    if send_configured:
        monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
        monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    # A second valid logo, with different compressed pixels, belongs only to Sign.
    data = BytesIO()
    Image.new('RGB', (2, 1), (10, 20, 30)).save(data, format='PNG')
    sign_png = data.getvalue()
    digest = hashlib.sha256(sign_png).hexdigest()
    assert digest != tenant_brand.get_tenant_brand().logo_hash
    expected = '/chief/sign-tenant-logo?v=' + digest
    session, raw = new_session(access)
    browser = Client()
    browser.cookies[COOKIE] = raw

    def upstream(request):
        assert str(request.url) == settings.SIGN_RECIPIENT_INTERNAL_URL + expected
        return httpx.Response(200, headers={'content-type': 'image/png'}, stream=httpx.ByteStream(sign_png))

    with patch('dealroom_sign.recipient_proxy.httpx.Client', return_value=httpx.Client(transport=httpx.MockTransport(upstream))):
        result = browser.get(expected, HTTP_HOST='recipient.test', HTTP_X_FLEET_RECIPIENT_LISTENER='1', HTTP_X_FORWARDED_FOR='192.0.2.1')
        assert result.status_code == 200
        assert result['Content-Type'] == 'image/png'
        assert b''.join(result.streaming_content) == sign_png
        assert not result.cookies
        result.close()
