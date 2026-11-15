import base64
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch

import httpx
import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.utils import timezone

from dealroom_sign.client import SignError
from dealroom_sign.counterparty import (COOKIE, alternate_code, capability, disclosure_hash, get_session,
    issue_handoff, keyed_hash, new_session, observe_completion, material, resolve, verify_code, consume_handoff)
from dealroom_sign.models import NdaPolicy, SignerChallenge, SignerSession, SignerHandoff
from dealroom_sign.recipient_proxy import forward_headers, limit
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope
from sharelinks.models import Viewer

pytestmark = pytest.mark.django_db
BASE = {'HTTP_HOST': 'recipient.test:9445', 'HTTP_X_FLEET_RECIPIENT_LISTENER': '1',
    'HTTP_X_FORWARDED_FOR': '100.64.0.4'}
ORIGIN = 'https://recipient.test:9445'


def browser_session(access):
    browser = Client(enforce_csrf_checks=True)
    session, raw = new_session(access)
    browser.cookies[COOKIE] = raw
    browser.get('/s/access', **BASE)
    return browser, session, raw


def post(browser, path, data, **extra):
    return browser.post(path, data, content_type='application/json', HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value,
        HTTP_ORIGIN=ORIGIN, **BASE, **extra)


def test_minor13_consent_csrf_origin_rotation_and_planted_cookie(access):
    browser, session, raw = browser_session(access)
    path = '/s/session/consent'
    data = {'agree': True, 'disclosure_hash': disclosure_hash(access)}
    assert browser.post(path, data, content_type='application/json', HTTP_ORIGIN=ORIGIN, **BASE).status_code == 403
    assert browser.post(path, data, content_type='application/json', HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value,
        HTTP_ORIGIN='https://other.test', **BASE).status_code == 403
    assert post(browser, path, {**data, 'disclosure_hash': 'other'}).status_code == 403
    result = post(browser, path, data)
    assert result.status_code == 303 and result['Location'] == '/sign/'+access.native_token
    fresh = result.cookies[COOKIE].value
    assert fresh != raw and get_session(raw) is None and get_session(fresh).consented_at
    browser.cookies[COOKIE] = raw
    assert post(browser, path, data).status_code == 403
    planted = SessionStore(); planted['signer_access'] = str(access.pk); planted.create()
    browser.cookies[COOKIE] = planted.session_key
    assert post(browser, path, data).status_code == 403
    assert not SignerSession.objects.filter(session_hash=keyed_hash('session', planted.session_key)).exists()


def test_minor13_alternate_access_csrf_origin_and_previous_cookie(access):
    browser, session, raw = browser_session(access)
    assert browser.post('/s/access', {'code': alternate_code(access)}, HTTP_ORIGIN=ORIGIN, **BASE).status_code == 403
    assert browser.post('/s/access', {'code': alternate_code(access)}, HTTP_ORIGIN='https://other.test',
        HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value, **BASE).status_code == 403
    assert post(browser, '/s/access', {'code': 'INVALID'}).status_code == 403
    response = post(browser, '/s/access', {'code': alternate_code(access)})
    assert response.status_code == 303 and response['Location'] == '/s/session/context'
    assert response.cookies[COOKIE].value != raw and get_session(raw) is None


def test_minor13_code_verification_csrf_origin_wrong_session_five_attempt_lockout(access):
    access.required_auth = 'email_code'; access.save()
    browser, session, raw = browser_session(access)
    other, other_raw = new_session(access)
    challenge = SignerChallenge.objects.create(session=session, access=access, code_hash=keyed_hash('otp', '123456'),
        expires_at=timezone.now()+timedelta(minutes=5))
    path = '/s/session/code/verify'
    data = {'challenge_id': str(challenge.pk), 'code': '123456'}
    assert browser.post(path, data, content_type='application/json', HTTP_ORIGIN=ORIGIN, **BASE).status_code == 403
    assert browser.post(path, data, content_type='application/json', HTTP_ORIGIN='https://other.test',
        HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value, **BASE).status_code == 403
    browser.cookies[COOKIE] = other_raw
    assert post(browser, path, data).status_code == 403
    challenge.refresh_from_db(); assert challenge.attempts == 0
    browser.cookies[COOKIE] = raw
    for _ in range(5):
        assert post(browser, path, {**data, 'code': '000000'}).status_code == 403
    assert post(browser, path, data).status_code == 403
    challenge.refresh_from_db(); assert challenge.attempts == 5 and challenge.used_at is None
    second = SignerChallenge.objects.create(session=other, access=access, code_hash=keyed_hash('otp', '123456'),
        expires_at=timezone.now()+timedelta(minutes=5))
    browser.cookies[COOKIE] = other_raw
    response = post(browser, path, {**data, 'challenge_id': str(second.pk)})
    assert response.status_code == 200 and response.cookies[COOKIE].value != other_raw
    assert get_session(other_raw) is None and get_session(response.cookies[COOKIE].value).code_verified_at


def nda(access, fixture):
    viewer = Viewer.objects.create(organization=fixture.org, email=access.email, name='Member', verified_at=timezone.now())
    policy = NdaPolicy.objects.create(room=fixture.room, source_version=fixture.version, source_sha256=fixture.work.source_sha256)
    work = access.workflow
    work.purpose, work.member_id, work.member_email, work.policy_revision = 'nda', str(viewer.pk), viewer.email, str(policy.revision)
    work.signing_token = access.native_token; work.save()
    access.revision = str(policy.revision); access.save()
    return viewer


def test_minor13_nda_handoff_http_cookie_redirect_and_replay(access, fixture):
    viewer = nda(access, fixture)
    browser, session, old = browser_session(access)
    handoff = issue_handoff(access, viewer)
    response = browser.get('/s/nda/'+handoff, **BASE)
    assert response.status_code == 303 and response['Location'] == '/sign/'+access.native_token
    cookie = response.cookies[COOKIE]
    assert cookie.value != old and get_session(old) is None
    assert cookie['secure'] and cookie['httponly'] and cookie['samesite'] == 'Lax' and not cookie['domain']
    assert browser.get('/s/nda/'+handoff, **BASE).status_code == 403


def test_m7_nda_return_only_redirects_after_verified_publication(access, fixture, settings):
    nda(access, fixture)
    settings.SITE_DOMAIN = 'https://staff.test:9443'
    browser, session, raw = browser_session(access)
    path = '/s/return/'+str(access.workflow_id)
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)):
        response = browser.get(path+'?signed=true', **BASE)
        assert response.status_code == 200 and b'Checking your signature' in response.content
    observe_completion(access, timezone.now())
    access.workflow.state = 'awaiting_seal'; access.workflow.save()
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow, 'COMPLETED')):
        assert browser.get(path, **BASE).status_code == 200
        access.workflow.state = 'done'; access.workflow.save()
        response = browser.get(path, **BASE)
    assert response.status_code == 303
    assert response['Location'] == 'https://staff.test:9443/signing/nda/'+str(access.workflow.room_id)


def test_minor13_forwarding_requires_single_ip_and_key(access, settings, tmp_path):
    key = tmp_path/'key'; key.write_text('private-test-key'); settings.FLEET_PROXY_KEY_FILE = str(key)
    for ip in ['100.64.0.4, 1.2.3.4', '', 'unknown']:
        request = RequestFactory().get('/', **{**BASE, 'HTTP_X_FORWARDED_FOR': ip})
        with pytest.raises(SignError, match='recipient_hop_unavailable'):
            forward_headers(request)
    request = RequestFactory().get('/', **BASE)
    key.unlink()
    with pytest.raises(SignError, match='recipient_proxy_unavailable'):
        forward_headers(request)


def test_minor13_hmac_purposes_are_disjoint(access):
    purposes = ['link', 'alternate', 'lookup-link', 'lookup-alternate', 'session', 'otp', 'handoff', 'rate']
    values = [keyed_hash(p, 'same material') for p in purposes]
    assert len(set(values)) == len(purposes)
    assert values == [keyed_hash(p, 'same material') for p in purposes]


def test_nit2_rate_keys_use_only_validated_canonical_ip(access, settings):
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    cache.clear()
    with pytest.raises(SignError, match='recipient_hop_unavailable'):
        limit(RequestFactory().get('/', **{**BASE, 'HTTP_X_FORWARDED_FOR': '1.2.3.4, 5.6.7.8'}))
    limit(RequestFactory().get('/', **{**BASE, 'HTTP_X_FORWARDED_FOR': '2001:0db8:0:0:0:0:0:1'}), maximum=1)
    with pytest.raises(SignError, match='rate_limited'):
        limit(RequestFactory().get('/', **{**BASE, 'HTTP_X_FORWARDED_FOR': '2001:db8::1'}), maximum=1)


def test_minor10_requester_link_downloads_same_copy_but_never_forwards_native_write(access):
    from dealroom_sign.counterparty_mail import enqueue_requester
    work = access.workflow
    work.state = 'done'; work.completed_at = timezone.now(); work.save()
    requester = enqueue_requester(work, 'completion').access
    browser, session, raw = browser_session(requester)
    files = [('signed.pdf', b'%PDF-final'), ('certificate.pdf', b'%PDF-certificate')]
    with patch('dealroom_sign.counterparty_mail.final_files', return_value=files):
        response = browser.post('/s/session/download', {'kind': 'final'}, HTTP_ORIGIN=ORIGIN,
            HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value, **BASE)
    assert response.status_code == 200 and response.content == files[0][1]
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(work, 'COMPLETED')), \
         patch('dealroom_sign.recipient_proxy.httpx.Client') as native:
        response = browser.post('/api/trpc/envelope.field.sign', {'json': {'token': access.native_token, 'fieldId': 1}},
            content_type='application/json', HTTP_ORIGIN=ORIGIN, **BASE)
    assert response.status_code == 200 and b'Signed' in response.content
    native.assert_not_called()


@pytest.mark.parametrize('purpose', ['link', 'alternate', 'lookup-link', 'lookup-alternate', 'session', 'otp', 'handoff', 'rate'])
def test_r4_nit8_hmac_call_sites(access, fixture, settings, purpose):
    def expected(label, value):
        key = hmac.digest(settings.SIGN_CAPABILITY_KEY.encode(), ('fleet-sign/'+label).encode(), 'sha256')
        return hmac.new(key, value if isinstance(value, bytes) else value.encode(), hashlib.sha256).hexdigest()
    if purpose == 'link':
        assert capability(access) == base64.urlsafe_b64encode(bytes.fromhex(expected(purpose, material(access)))).decode().rstrip('=')
    elif purpose == 'alternate':
        assert alternate_code(access).replace('-', '') == base64.b32encode(bytes.fromhex(expected(purpose, material(access)))[:10]).decode()
    elif purpose == 'lookup-link':
        assert access.capability_hash == expected(purpose, capability(access))
        assert resolve(capability(access)).pk == access.pk
    elif purpose == 'lookup-alternate':
        assert access.alternate_hash == expected(purpose, alternate_code(access).replace('-', ''))
        assert resolve(alternate_code(access), alternate=True).pk == access.pk
    elif purpose == 'session':
        session, raw = new_session(access)
        assert session.session_hash == expected(purpose, raw)
        assert get_session(raw).pk == session.pk
    elif purpose == 'otp':
        session, raw = new_session(access)
        challenge = SignerChallenge.objects.create(session=session, access=access, code_hash=expected(purpose, '123456'),
            expires_at=timezone.now()+timedelta(minutes=5))
        fresh, cookie = verify_code(session, raw, str(challenge.pk), '123456')
        assert fresh.code_verified_at and get_session(cookie).pk == fresh.pk
    elif purpose == 'handoff':
        viewer = nda(access, fixture)
        raw = issue_handoff(access, viewer)
        assert SignerHandoff.objects.get(access=access).token_hash == expected(purpose, raw)
        consumed, session, cookie = consume_handoff(raw)
        assert consumed.pk == access.pk and get_session(cookie).pk == session.pk
    else:
        settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
        cache.clear()
        limit(RequestFactory().get('/', **BASE))
        assert cache.get('sign-rate:'+expected(purpose, 'entry:100.64.0.4')) == 1
