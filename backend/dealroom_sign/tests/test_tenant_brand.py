"""Deployment branding stays outside the product and defaults to Fleet."""
import base64
import os
from email.utils import parseaddr
from pathlib import Path

import pytest
from django.test import RequestFactory

from dealroom_sign import tenant_brand
from dealroom_sign.counterparty_mail import compose, enqueue
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_counterparty_mail import completed
from dealroom_sign.tests.test_recipient_shell_c4a import _render
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=')


@pytest.fixture(autouse=True)
def clean_brand(monkeypatch):
    for key in list(os.environ):
        if key.startswith('FLEET_TENANT_'):
            monkeypatch.delenv(key)


@pytest.fixture
def logo(tmp_path):
    path = tmp_path / 'logo.png'
    path.write_bytes(PNG)
    return path


def test_defaults_and_env_configuration(logo, monkeypatch):
    from dealroom_sign.tenant_brand import get_tenant_brand, parse_tenant_brand
    brand = parse_tenant_brand({})
    assert (brand.name, brand.logo_url, brand.logo_baseline, brand.chrome, brand.chrome_rule, brand.surface, brand.powered_by) == ('Fleet', '', .8, '', '', '', False)
    monkeypatch.setenv('FLEET_TENANT_NAME', 'Acme Test Co')
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    monkeypatch.setenv('FLEET_TENANT_LOGO_BASELINE', '0.75')
    monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    monkeypatch.setenv('FLEET_TENANT_CHROME_RULE', '#abc')
    monkeypatch.setenv('FLEET_TENANT_SURFACE', 'warm')
    monkeypatch.setenv('FLEET_TENANT_POWERED_BY', '1')
    brand = get_tenant_brand()
    assert brand.name == 'Acme Test Co' and brand.logo_baseline == .75
    assert brand.logo_url.startswith('/chief/tenant-logo?v=') and str(logo) not in brand.logo_url
    assert brand.chrome_hsl == '210 65.3846% 20.3922%'
    assert brand.chrome_rule == '#abc' and brand.surface == 'warm' and brand.powered_by


@pytest.mark.parametrize('key,value,field,default', [
    ('NAME', '\r\nInjected', 'name', 'Fleet'), ('NAME', '  ', 'name', 'Fleet'),
    ('LOGO_BASELINE', 'NaN', 'logo_baseline', .8), ('LOGO_BASELINE', '1.01', 'logo_baseline', .8),
    ('LOGO_BASELINE', '-.1', 'logo_baseline', .8), ('LOGO_BASELINE', '1px', 'logo_baseline', .8),
    ('CHROME', 'red', 'chrome', ''), ('CHROME', '#123456;display:none', 'chrome', ''),
    ('CHROME_RULE', '#12345678', 'chrome_rule', ''), ('SURFACE', 'cold', 'surface', ''),
    ('POWERED_BY', 'true', 'powered_by', False), ('LOGO', '/missing.png', 'logo_url', ''),
])
def test_invalid_fields_fall_back_independently(key, value, field, default):
    from dealroom_sign.tenant_brand import parse_tenant_brand
    brand = parse_tenant_brand({'FLEET_TENANT_' + key: value})
    assert getattr(brand, field) == default


def test_invalid_settings_log_only_once(monkeypatch, caplog):
    from dealroom_sign import tenant_brand
    tenant_brand._warned.clear()
    tenant_brand.get_tenant_brand.cache_clear()
    monkeypatch.setenv('FLEET_TENANT_CHROME', 'invalid')
    for _ in range(3):
        tenant_brand.get_tenant_brand()
    assert sum('FLEET_TENANT_CHROME' in r.message for r in caplog.records) == 1


@pytest.mark.parametrize('filename,content', [
    ('mark.svg', b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M0 0h20v20z"/></svg>'),
    ('mark.png', b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M0 0h20v20z"/></svg>'),
    ('mark.png', b'not an image'), ('mark.jpg', PNG),
    ('mark.png', PNG + b' ' * 204800),
    ('mark.svg', b'<svg><script>alert(1)</script></svg>'),
    ('mark.svg', b'<svg><image href="https://example.test/logo.png"/></svg>'),
])
def test_invalid_logo_warns_once_and_falls_back_to_tenant_name(tmp_path, filename, content, monkeypatch, caplog):
    path = tmp_path / filename
    path.write_bytes(content)
    tenant_brand._warned.clear()
    tenant_brand.get_tenant_brand.cache_clear()
    monkeypatch.setenv('FLEET_TENANT_NAME', 'Acme Test Co')
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(path))
    for _ in range(3):
        brand = tenant_brand.parse_tenant_brand(os.environ)
        assert not brand.logo_url and not brand.logo_bytes
        assert brand.name == 'Acme Test Co'
    html = _render('welcome')
    assert '>Acme Test Co</span>' in html and 'aria-label="Acme Test Co Sign"' in html
    assert 'class="fleet-tenant-logo"' not in html
    assert tenant_brand.tenant_logo(RequestFactory().get('/chief/tenant-logo')).status_code == 404
    assert [r.message for r in caplog.records if 'FLEET_TENANT_LOGO' in r.message] == [
        'Invalid FLEET_TENANT_LOGO; using default',
    ]


def test_header_defaults_name_logo_and_product_rule(logo, monkeypatch):
    assert 'aria-label="Fleet Sign"' in _render('welcome')
    assert 'aria-label="Fleet Dealroom"' in _render('signed')
    monkeypatch.setenv('FLEET_TENANT_NAME', 'Acme Test Co')
    monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    monkeypatch.setenv('FLEET_TENANT_CHROME_RULE', '#abcdef')
    monkeypatch.setenv('FLEET_TENANT_SURFACE', 'warm')
    monkeypatch.setenv('FLEET_TENANT_POWERED_BY', '1')
    html = _render('welcome')
    assert 'aria-label="Acme Test Co Sign"' in html and '>Acme Test Co</span>' in html
    assert 'Acme Test Co Dealroom · Every copy' in html
    assert 'data-chrome="dark"' in html and 'data-chrome-rule' in html and 'data-surface="warm"' in html
    assert '--chrome-base:210 65.3846% 20.3922%' in html and 'Powered by Fleet' in html
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    html = _render('signed')
    assert 'class="fleet-tenant-logo"' in html and 'alt="Acme Test Co"' in html
    assert 'class="fds-lockup__mark"' not in html and 'class="fds-lockup__family"' not in html
    assert 'aria-label="Acme Test Co Dealroom"' in html


def test_fixed_logo_route_hash_and_cache(logo, monkeypatch):
    from dealroom_sign.tenant_brand import get_tenant_brand, tenant_logo
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    brand = get_tenant_brand()
    response = tenant_logo(RequestFactory().get(brand.logo_url))
    assert response.status_code == 200 and response.content == PNG
    assert response['Content-Type'] == 'image/png' and response['X-Content-Type-Options'] == 'nosniff'
    assert 'immutable' in response['Cache-Control']
    assert tenant_logo(RequestFactory().get('/chief/tenant-logo?v=old')).status_code == 404
    monkeypatch.delenv('FLEET_TENANT_LOGO')
    assert tenant_logo(RequestFactory().get(brand.logo_url)).status_code == 404


@pytest.mark.django_db
def test_email_cid_band_and_plain_text(access, logo, monkeypatch):
    effect = enqueue(access, 'invitation', 'tenant')
    original = compose(effect).body
    monkeypatch.setenv('FLEET_TENANT_NAME', 'Acme Test Co')
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    monkeypatch.setenv('FLEET_TENANT_CHROME', '#123456')
    monkeypatch.setenv('FLEET_TENANT_CHROME_RULE', '#abcdef')
    monkeypatch.setenv('FLEET_TENANT_POWERED_BY', '1')
    message = compose(effect)
    assert parseaddr(message.from_email)[0] == access.sender['name'] + ' via Acme Test Co Sign'
    assert message.body == original.replace('Fleet | Dealroom', 'Acme Test Co | Dealroom')
    html = message.alternatives[0][0]
    assert 'background:#123456' in html and 'border-bottom:2px solid #abcdef' in html
    assert 'src="cid:' in html and 'Powered by Fleet' in html and str(logo) not in html
    mime = message.message()
    related = next(p for p in mime.walk() if p.get_content_type() == 'multipart/related')
    image = next(p for p in related.walk() if p.get_content_type() == 'image/png')
    assert image.get_payload(decode=True) == PNG and image['Content-Disposition'].startswith('inline')
    assert f'cid:{image["Content-ID"][1:-1]}' in html
    assert [p.get_content_type() for p in related.get_payload()] == ['text/html', 'image/png']
    assert mime.as_bytes() == message.message().as_bytes()
    final = compose(completed(access), files=[('signed.pdf', b'%PDF-final'), ('certificate.pdf', b'%PDF-cert')])
    assert parseaddr(final.from_email)[0].endswith(' via Acme Test Co Dealroom')
    assert len(final.attachments) == 2
    assert len([p for p in final.message().walk() if p.get_content_type() == 'application/pdf']) == 2


def test_no_tenant_names_in_product_tree():
    names = ['Acme Test Co', *filter(None, os.environ.get('FLEET_TEST_TENANT_NAMES', '').split(','))]
    root = Path(__file__).resolve().parents[1]
    hits = []
    for path in root.rglob('*'):
        if not path.is_file() or any(p in {'tests', 'e2e', '__pycache__', 'management'} for p in path.relative_to(root).parts):
            continue
        if path.suffix in {'.py', '.html', '.txt', '.js', '.css'}:
            for name in names:
                if name.casefold() in path.read_text().casefold():
                    hits.append(str(path.relative_to(root)))
    assert not hits


@pytest.mark.parametrize('filename,content', [
    ('logo.png', PNG[:45] + b'changed' + PNG[52:]),
    ('logo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><path></svg>'),
    ('logo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><image xmlns:x="http://www.w3.org/1999/xlink" x:href="https://example.test/image.png"/></svg>'),
])
def test_malformed_image_is_rejected(tmp_path, filename, content):
    from dealroom_sign.tenant_brand import parse_tenant_brand
    path = tmp_path / filename
    path.write_bytes(content)
    assert not parse_tenant_brand({'FLEET_TENANT_LOGO': str(path)}).logo_url


@pytest.mark.django_db
def test_logo_is_available_on_visitor_origin_without_a_signer_session(client, logo, monkeypatch, settings):
    from dealroom_sign.tenant_brand import get_tenant_brand
    from urllib.parse import urlsplit
    settings.SIGN_RECIPIENT_ORIGIN = 'https://recipient.test:9445'
    monkeypatch.setenv('FLEET_TENANT_LOGO', str(logo))
    response = client.get(get_tenant_brand().logo_url, HTTP_HOST=urlsplit(settings.SIGN_RECIPIENT_ORIGIN).netloc,
        HTTP_X_FLEET_RECIPIENT_LISTENER='1')
    assert response.status_code == 200 and response.content == PNG
    assert not response.cookies and 'immutable' in response['Cache-Control']
    page = client.get('/s/access', HTTP_HOST=urlsplit(settings.SIGN_RECIPIENT_ORIGIN).netloc,
        HTTP_X_FLEET_RECIPIENT_LISTENER='1')
    assert "default-src 'self'" in page['Content-Security-Policy']
