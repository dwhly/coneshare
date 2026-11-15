import json
from unittest.mock import patch

import httpx
import pytest
from django.test import Client, RequestFactory

from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope

pytestmark = pytest.mark.django_db


def test_proxy_forwarding_is_an_allowlist(access, settings, tmp_path):
    from dealroom_sign.recipient_proxy import forward_headers
    key = tmp_path/'proxy-key'
    key.write_text('private-test-key\n')
    settings.FLEET_PROXY_KEY_FILE = str(key)
    req = RequestFactory().post('/api/trpc/envelope.field.sign', '{}', content_type='application/json',
        HTTP_HOST='recipient.test:9445', HTTP_ORIGIN='https://recipient.test:9445',
        HTTP_X_FLEET_RECIPIENT_LISTENER='1', HTTP_X_FORWARDED_FOR='100.64.0.4',
        HTTP_X_FORWARDED_HOST='other.test', HTTP_X_FORWARDED_PROTO='http',
        HTTP_X_FLEET_PROXY_KEY='caller-key', HTTP_X_REAL_IP='1.2.3.4', HTTP_FORWARDED='for=1.2.3.4',
        HTTP_AUTHORIZATION='Bearer caller', HTTP_COOKIE='staff=secret', HTTP_CF_CONNECTING_IP='1.2.3.4',
        HTTP_USER_AGENT='Browser fixture')
    headers = forward_headers(req)
    assert headers == {'Content-Type': 'application/json', 'User-Agent': 'Browser fixture',
        'Origin': 'https://recipient.test:9445', 'X-Forwarded-For': '100.64.0.4',
        'X-Forwarded-Host': 'recipient.test:9445', 'X-Forwarded-Proto': 'https',
        'x-fleet-proxy-key': 'private-test-key', 'Accept-Encoding': 'identity'}


def test_unsessioned_native_url_has_help_without_upstream_or_metadata(access):
    with patch('dealroom_sign.recipient_proxy.Documenso') as native:
        result = Client().get('/sign/'+access.native_token, HTTP_HOST='recipient.test:9445',
            HTTP_X_FLEET_RECIPIENT_LISTENER='1')
    assert result.status_code == 403
    assert b'Open the link in your Fleet Dealroom email' in result.content
    assert access.workflow.title.encode() not in result.content
    native.assert_not_called()


@pytest.mark.parametrize('headers', [{}, {'HTTP_HOST': 'recipient.test:9445'},
    {'HTTP_HOST': 'staff.test:9443', 'HTTP_X_FLEET_RECIPIENT_LISTENER': '1', 'HTTP_X_FORWARDED_FOR': '100.64.0.4'},
    {'HTTP_HOST': 'recipient.test:9445', 'HTTP_X_FORWARDED_HOST': 'recipient.test:9445'}])
def test_recipient_host_and_listener_are_both_required(access, headers):
    from dealroom_sign.counterparty import capability
    result = Client().get('/s/'+capability(access), **headers)
    assert result.status_code == 403
    assert access.workflow.title.encode() not in result.content


def test_scanner_get_does_not_enter_and_enter_requires_csrf_and_exact_origin(access):
    from dealroom_sign.counterparty import capability, COOKIE
    from dealroom_sign.models import SignerSession
    browser = Client(enforce_csrf_checks=True)
    base = {'HTTP_HOST': 'recipient.test:9445', 'HTTP_X_FLEET_RECIPIENT_LISTENER': '1', 'HTTP_X_FORWARDED_FOR': '100.64.0.4'}
    path = '/s/'+capability(access)
    response = browser.get(path, **base)
    assert response.status_code == 200 and not SignerSession.objects.exists()
    assert COOKIE not in response.cookies
    assert browser.post(path+'/enter', **base).status_code == 403
    csrf = browser.cookies['csrftoken'].value
    assert browser.post(path+'/enter', HTTP_X_CSRFTOKEN=csrf,
        HTTP_ORIGIN='https://recipient.test:9443', **base).status_code == 403
    response = browser.post(path+'/enter', HTTP_X_CSRFTOKEN=csrf,
        HTTP_ORIGIN='https://recipient.test:9445', **base)
    assert response.status_code == 200 and COOKIE in response.cookies
    cookie = response.cookies[COOKIE]
    assert cookie['secure'] and cookie['httponly'] and cookie['samesite'] == 'Lax' and not cookie['domain']


def test_batch_scope_rejects_wrong_tokens_fields_items_and_unknown_members(access):
    from dealroom_sign.recipient_proxy import authorize_rpc
    from dealroom_sign.client import SignError
    env = envelope(access.workflow)
    env['fields'] = [{'id': 5, 'recipientId': 1, 'envelopeItemId': 'item_test'}]
    for name, data in [('envelope.field.sign', {'token': 'other', 'fieldId': 5}),
        ('envelope.field.sign', {'token': access.native_token, 'fieldId': 6}),
        ('envelope.item.getManyByToken', {'envelopeId': 'other', 'access': {'type': 'recipient', 'token': access.native_token}}),
        ('envelope.field.sign,envelope.create', {}), ('future.recipient', {})]:
        req = RequestFactory().post('/api/trpc/'+name+'?batch=1', json.dumps({'0': {'json': data}}), content_type='application/json')
        with pytest.raises(SignError):
            authorize_rpc(req, access, env)


def test_return_does_not_trust_browser_completion_or_other_request(access):
    from dealroom_sign.counterparty import new_session, COOKIE
    session, raw = new_session(access)
    browser = Client()
    browser.cookies[COOKIE] = raw
    base = {'HTTP_HOST': 'recipient.test:9445', 'HTTP_X_FLEET_RECIPIENT_LISTENER': '1', 'HTTP_X_FORWARDED_FOR': '100.64.0.4'}
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)):
        response = browser.get('/s/return/'+str(access.workflow_id)+'?signed=true', **base)
        assert b'Checking your signature' in response.content and b'Signed \xe2\x80\x94' not in response.content
        response = browser.get('/s/return/00000000-0000-0000-0000-000000000001', **base)
        assert response.status_code == 403


def test_native_completion_uses_pinned_secondary_document_id_and_no_override(access):
    from dealroom_sign.recipient_proxy import authorize_rpc
    from dealroom_sign.client import SignError
    env = envelope(access.workflow)
    env['secondaryId'] = 'document_42'
    data = {'token': access.native_token, 'documentId': 42}
    def req(value):
        return RequestFactory().post('/api/trpc/recipient.completeDocumentWithToken?batch=1',
            json.dumps({'0': {'json': value}}), content_type='application/json')
    assert authorize_rpc(req(data), access, env) == ['recipient.completeDocumentWithToken']
    for value in [{**data, 'documentId': 43}, {**data, 'nextSigner': {'email': 'other@test.test'}},
                  {**data, 'recipientOverride': {'name': 'Other'}}]:
        with pytest.raises(SignError):
            authorize_rpc(req(value), access, env)


def test_native_post_requires_origin_json_consent_and_source_hash(access, settings, tmp_path, pdf):
    from dealroom_sign.counterparty import new_session, COOKIE, consent, disclosure_hash
    from dealroom_sign.validation import digest
    session, raw = new_session(access)
    browser = Client()
    browser.cookies[COOKIE] = raw
    headers = {'HTTP_HOST': 'recipient.test:9445', 'HTTP_X_FLEET_RECIPIENT_LISTENER': '1',
        'HTTP_ORIGIN': 'https://recipient.test:9445', 'HTTP_X_FORWARDED_FOR': '100.64.0.4'}
    data = {'0': {'json': {'token': access.native_token, 'fieldId': 5, 'fieldValue': {'type': 'SIGNATURE', 'value': 'Member'}}}}
    env = envelope(access.workflow)
    env['fields'] = [{'id': 5, 'recipientId': 1, 'envelopeItemId': 'item_test'}]
    path = '/api/trpc/envelope.field.sign?batch=1'
    key = tmp_path/'key'; key.write_text('fixture-private-key'); settings.FLEET_PROXY_KEY_FILE = str(key)
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=env), \
         patch('dealroom_sign.recipient_proxy.Documenso') as engine, \
         patch('dealroom_sign.recipient_proxy.httpx.Client') as upstream:
        engine.return_value.__enter__.return_value.item_pdf.return_value = pdf
        assert browser.post(path, data, content_type='application/json', **headers).status_code == 403
        upstream.assert_not_called()
    session, raw = consent(session, raw, disclosure_hash(access), True)
    browser.cookies[COOKIE] = raw
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=env), \
         patch('dealroom_sign.recipient_proxy.Documenso') as engine, \
         patch('dealroom_sign.recipient_proxy.httpx.Client') as upstream:
        engine.return_value.__enter__.return_value.item_pdf.return_value = b'%PDF-changed'
        assert browser.post(path, data, content_type='application/json', **headers).status_code == 403
        upstream.assert_not_called()

    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=env), \
         patch('dealroom_sign.recipient_proxy.Documenso') as engine, \
         patch('dealroom_sign.recipient_proxy.httpx.Client') as upstream:
        engine.return_value.__enter__.return_value.item_pdf.return_value = pdf
        assert browser.post(path, data, content_type='application/json', **{**headers, 'HTTP_ORIGIN': 'https://other.test'}).status_code == 403
        assert browser.post(path, json.dumps(data), content_type='text/plain', **headers).status_code == 403
        upstream.assert_not_called()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, headers={'content-type': 'application/json'},
        stream=httpx.ByteStream(b'{"result":"signed"}')))
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=env), \
         patch('dealroom_sign.recipient_proxy.Documenso') as engine, \
         patch('dealroom_sign.recipient_proxy.httpx.Client', return_value=httpx.Client(transport=transport)):
        engine.return_value.__enter__.return_value.item_pdf.return_value = pdf
        result = browser.post(path, data, content_type='application/json', **headers)
        assert result.status_code == 200
        assert b''.join(result.streaming_content) == b'{"result":"signed"}'
        result.close()


def test_live_native_read_returns_exact_bytes_strips_cookies_and_rejects_external_redirect(access, settings, tmp_path):
    from dealroom_sign.counterparty import new_session, COOKIE, consent, disclosure_hash
    from dealroom_sign.recipient_proxy import forward
    session, raw = new_session(access)
    session, raw = consent(session, raw, disclosure_hash(access), True)
    key = tmp_path/'key'; key.write_text('private-key')
    settings.FLEET_PROXY_KEY_FILE = str(key)
    req = RequestFactory().get('/sign/'+access.native_token, HTTP_HOST='recipient.test:9445',
        HTTP_X_FLEET_RECIPIENT_LISTENER='1', HTTP_X_FORWARDED_FOR='100.64.0.4')
    req.COOKIES[COOKIE] = raw
    for status, headers, content in [(200, {'content-type': 'text/html', 'set-cookie': 'staff=x',
        'Content-Security-Policy': "script-src 'nonce-abc'"}, b'<html>canonical</html>'),
        (303, {'location': 'https://elsewhere.test'}, b'')]:
        transport = httpx.MockTransport(lambda r: httpx.Response(status, headers=headers, stream=httpx.ByteStream(content)))
        client = httpx.Client(transport=transport)
        with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
             patch('dealroom_sign.recipient_proxy.httpx.Client', return_value=client):
            if status == 303:
                from dealroom_sign.client import SignError
                with pytest.raises(SignError, match='native_redirect_denied'):
                    forward(req, session)
            else:
                result = forward(req, session)
                assert b''.join(result.streaming_content) == content
                assert not result.cookies and result['Content-Security-Policy'] == "script-src 'nonce-abc'"
                result.close()


def test_superjson_undefined_optional_values_are_checked_without_allowing_identity_changes(access):
    from dealroom_sign.recipient_proxy import authorize_rpc
    env = envelope(access.workflow)
    env['secondaryId'] = 'document_42'
    data = {'0': {'json': {'token': access.native_token, 'documentId': 42, 'recipientOverride': None},
        'meta': {'values': {'recipientOverride': ['undefined']}, 'v': 1}}}
    req = RequestFactory().post('/api/trpc/recipient.completeDocumentWithToken?batch=1',
        json.dumps(data), content_type='application/json')
    assert authorize_rpc(req, access, env) == ['recipient.completeDocumentWithToken']
    data['0']['meta']['values']['token'] = ['undefined']
    req = RequestFactory().post('/api/trpc/recipient.completeDocumentWithToken?batch=1',
        json.dumps(data), content_type='application/json')
    from dealroom_sign.client import SignError
    with pytest.raises(SignError):
        authorize_rpc(req, access, env)


def test_native_read_batch_is_scoped_and_contains_no_external_attachment_or_other_token(access):
    from urllib.parse import urlencode
    from dealroom_sign.counterparty import new_session, COOKIE
    from dealroom_sign.recipient_proxy import forward
    session, raw = new_session(access)
    inputs = {'0': {'json': {'envelopeId': access.workflow.envelope_id,
        'access': {'type': 'recipient', 'token': access.native_token}}},
        '1': {'json': {'envelopeId': access.workflow.envelope_id, 'token': access.native_token}}}
    req = RequestFactory().get('/api/trpc/envelope.item.getManyByToken,envelope.attachment.find?' +
        urlencode({'batch': '1', 'input': json.dumps(inputs)}))
    req.COOKIES[COOKIE] = raw
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)):
        response = forward(req, session)
    data = json.loads(response.content)
    assert data[0]['result']['data']['json']['data'][0]['id'] == 'item_test'
    assert data[1]['result']['data']['json'] == {'data': []}
    assert access.native_token.encode() not in response.content


def test_recipient_csp_retains_native_nonce_and_disables_frames(access):
    from django.http import HttpResponse
    from dealroom_sign.recipient_proxy import RecipientBoundaryMiddleware
    request = RequestFactory().get('/sign/'+access.native_token, HTTP_X_FLEET_RECIPIENT_LISTENER='1')
    native = HttpResponse('<html>unchanged</html>')
    native['Content-Security-Policy'] = "script-src 'nonce-native'; frame-ancestors *; connect-src 'self'"
    with patch('dealroom_sign.recipient_proxy.handle', return_value=native):
        response = RecipientBoundaryMiddleware(lambda _: None)(request)
    assert response.content == b'<html>unchanged</html>'
    assert response['Content-Security-Policy'] == "script-src 'nonce-native'; connect-src 'self'; frame-ancestors 'none'"


def test_status_batch_distinguishes_waiting_cosigner_from_sealing(access):
    from urllib.parse import urlencode
    from django.utils import timezone
    from dealroom_sign.counterparty import new_session, observe_completion, COOKIE
    from dealroom_sign.recipient_proxy import forward
    observe_completion(access, timezone.now())
    session, raw = new_session(access)
    data = {'0': {'json': {'token': access.native_token}}}
    request = RequestFactory().get('/api/trpc/envelope.signingStatus?' + urlencode({'batch':'1', 'input':json.dumps(data)}))
    request.COOKIES[COOKIE] = raw
    env = envelope(access.workflow)
    env['recipients'][0]['signingStatus'] = 'SIGNED'
    env['recipients'].append({'id': 2, 'role':'SIGNER', 'signingStatus':'NOT_SIGNED'})
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=env):
        result = forward(request, session)
        assert json.loads(result.content)[0]['result']['data']['json']['status'] == 'PENDING'
        env['recipients'][1]['signingStatus'] = 'SIGNED'
        result = forward(request, session)
        assert json.loads(result.content)[0]['result']['data']['json']['status'] == 'PROCESSING'


def test_expired_personal_link_renders_closed_window_without_metadata_or_session(access):
    from datetime import timedelta
    from django.utils import timezone
    from dealroom_sign.counterparty import capability
    from dealroom_sign.models import SignerSession
    access.signing_expires_at = timezone.now()-timedelta(seconds=1)
    access.save()
    base = {'HTTP_HOST':'recipient.test:9445', 'HTTP_X_FLEET_RECIPIENT_LISTENER':'1', 'HTTP_X_FORWARDED_FOR': '100.64.0.4'}
    with patch('dealroom_sign.recipient_proxy.Documenso') as native:
        response = Client().get('/s/'+capability(access), **base)
    assert response.status_code == 410 and b'This signing window has closed' in response.content
    assert access.workflow.title.encode() not in response.content
    assert not SignerSession.objects.exists()
    native.assert_not_called()
