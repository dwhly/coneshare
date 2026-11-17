"""Signers must receive Sign's TrueType/OpenType fonts (typed signature styles, PDF field fonts)."""
from unittest.mock import patch

import httpx
import pytest
from django.test import RequestFactory

from dealroom_sign.client import SignError
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope

pytestmark = pytest.mark.django_db


def _forward(access, settings, tmp_path, path, content_type, content=b'\x00\x01\x00\x00font'):
    from dealroom_sign.counterparty import new_session, COOKIE, consent, disclosure_hash
    from dealroom_sign.recipient_proxy import forward
    session, raw = new_session(access)
    session, raw = consent(session, raw, disclosure_hash(access), True)
    key = tmp_path/'key'; key.write_text('private-key')
    settings.FLEET_PROXY_KEY_FILE = str(key)
    req = RequestFactory().get(path, HTTP_HOST='recipient.test:9445',
        HTTP_X_FLEET_RECIPIENT_LISTENER='1', HTTP_X_FORWARDED_FOR='100.64.0.4')
    req.COOKIES[COOKIE] = raw
    transport = httpx.MockTransport(lambda r: httpx.Response(200, headers={'content-type': content_type},
        stream=httpx.ByteStream(content)))
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.recipient_proxy.httpx.Client', return_value=httpx.Client(transport=transport)):
        return forward(req, session)


@pytest.mark.parametrize('path,content_type', [
    ('/fonts/caveat-variablefont_wght.ttf', 'font/ttf'),
    ('/fonts/noto-sans.ttf', 'font/ttf'),
    ('/chief/signature-fonts/Allura-Regular.ttf', 'font/ttf'),
    ('/fonts/example.otf', 'font/otf'),
])
def test_signer_receives_sign_truetype_and_opentype_fonts(access, settings, tmp_path, path, content_type):
    result = _forward(access, settings, tmp_path, path, content_type)
    assert result.status_code == 200
    assert b''.join(result.streaming_content) == b'\x00\x01\x00\x00font'
    assert result['Content-Type'] == content_type
    result.close()


def test_other_binary_types_stay_denied(access, settings, tmp_path):
    with pytest.raises(SignError, match='native_content_denied'):
        _forward(access, settings, tmp_path, '/fonts/evil.ttf', 'application/x-msdownload')
