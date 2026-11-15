"""Regressions from the C1b iPhone recipient acceptance walk."""
import re
from datetime import timedelta
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

from dealroom.models import RoomPolicy
from dealroom_sign.client import SignError
from dealroom_sign.counterparty import (COOKIE, alternate_code, capability, disclosure_hash,
    get_session, issue_handoff, keyed_hash, new_session, observe_completion, provision, sender_snapshot)
from dealroom_sign.counterparty_mail import compose, enqueue
from dealroom_sign.models import SignatureRequest, SignerChallenge
from dealroom_sign.recipient_proxy import page
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_gate3_routes import BASE, ORIGIN, nda
from dealroom_sign.tests.test_product_reads import base
from dealroom_sign.tests.test_workflows import envelope, fixture, pdf, recipients
from sharelinks.models import ShareLink

pytestmark = pytest.mark.django_db
REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def local_runtime(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    settings.SIGN_RECIPIENT_ORIGIN = ORIGIN


class FormPage(HTMLParser):
    """Read the actual form controls and document policy, including meta overrides."""
    def __init__(self, response, path):
        super().__init__()
        self.path = path
        self.policy = response['Referrer-Policy']
        self.forms = {}
        self.action = None
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name') == 'referrer':
            self.policy = attrs['content']
        if tag == 'form':
            self.action = attrs.get('action', self.path)
            self.forms[self.action] = {}
        if tag == 'input' and self.action and attrs.get('type') == 'hidden':
            self.forms[self.action][attrs['name']] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.action = None

    def headers(self, *, fetch=False):
        # Fetch retains Origin; a navigation form under no-referrer has an opaque
        # Origin in Chromium/WebKit. Referrer never goes to a different origin.
        headers = dict(BASE, HTTP_ORIGIN=ORIGIN if fetch or self.policy == 'same-origin' else 'null')
        if self.policy == 'same-origin':
            headers['HTTP_REFERER'] = ORIGIN + self.path
        return headers

    def submit(self, browser, action, **values):
        return browser.post(action, {**self.forms[action], **values}, **self.headers())


@pytest.mark.parametrize('path', ['/s/access', '/articles/signature-disclosure', 'entry', 'context', 'return'])
def test_html_header_and_meta_allow_only_same_origin_referrers(access, path):
    browser = Client(enforce_csrf_checks=True)
    _, raw = new_session(access)
    browser.cookies[COOKIE] = raw
    path = {'entry': '/s/' + capability(access), 'context': '/s/session/context',
            'return': '/s/return/' + str(access.workflow_id)}.get(path, path)
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)):
        response = browser.get(path, **BASE)
    assert response.status_code == 200
    assert response['Referrer-Policy'] == 'same-origin'
    assert FormPage(response, path).policy == 'same-origin'


def test_browser_policy_drives_real_entry_consent_and_download_forms(access, pdf):
    cache.clear()
    browser = Client(enforce_csrf_checks=True)
    path = '/s/' + capability(access)
    document = FormPage(browser.get(path, **BASE), path)
    # Entry's real script uses FormData fetch with the hidden CSRF token.
    entry = browser.post(path + '/enter', document.forms[path + '/enter'], **document.headers(fetch=True))
    assert entry.status_code == 200
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)):
        context = browser.get(entry.json()['url'], **BASE)
    document = FormPage(context, entry.json()['url'])
    consent = document.submit(browser, '/s/session/consent', agree='on')
    assert consent.status_code == 303
    assert consent['Location'] == '/sign/' + access.native_token
    assert get_session(browser.cookies[COOKIE].value).consented_at
    with patch('dealroom_sign.recipient_proxy.source_bytes', return_value=pdf):
        original = browser.get('/s/session/original', **BASE)
    assert original.status_code == 200 and original['Referrer-Policy'] == 'no-referrer'
    observe_completion(access, timezone.now())
    access.workflow.state = 'done'; access.workflow.save()
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow, 'COMPLETED')):
        document = FormPage(browser.get('/s/session/context', **BASE), '/s/session/context')
    with patch('dealroom_sign.counterparty_mail.final_files', return_value=[('signed.pdf', pdf), ('certificate.pdf', pdf)]):
        for kind in ('final', 'certificate'):
            result = document.submit(browser, '/s/session/download', kind=kind)
            assert result.status_code == 200 and result.content == pdf
            assert result['Referrer-Policy'] == 'no-referrer'


def test_alternate_form_and_code_fetch_use_document_policy(access):
    cache.clear()
    browser = Client(enforce_csrf_checks=True)
    document = FormPage(browser.get('/s/access', **BASE), '/s/access')
    result = document.submit(browser, '/s/access', code=alternate_code(access))
    assert result.status_code == 303 and result['Location'] == '/s/session/context'
    access.required_auth = 'email_code'; access.save()
    session = get_session(browser.cookies[COOKIE].value)
    challenge = SignerChallenge.objects.create(session=session, access=access, code_hash=keyed_hash('otp', '123456'),
        expires_at=timezone.now() + timedelta(minutes=5))
    result = browser.post('/s/session/code/verify', {'challenge_id': str(challenge.pk), 'code': '123456'},
        content_type='application/json', HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value,
        **document.headers(fetch=True))
    assert result.status_code == 200 and get_session(browser.cookies[COOKIE].value).code_verified_at


def test_nda_handoff_lands_on_same_origin_consent_and_return(access, fixture):
    viewer = nda(access, fixture)
    browser = Client(enforce_csrf_checks=True)
    handoff = browser.get('/s/nda/' + issue_handoff(access, viewer), **BASE)
    assert handoff.status_code == 303
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)):
        document = FormPage(browser.get(handoff['Location'], **BASE), handoff['Location'])
        result = document.submit(browser, '/s/session/consent', agree='on')
        assert result.status_code == 303
        returned = browser.get('/s/return/' + str(access.workflow_id), **BASE)
        assert returned.status_code == 200 and returned['Referrer-Policy'] == 'same-origin'


@pytest.mark.parametrize('origin', ['null', 'https://other.test', None])
@pytest.mark.parametrize('path', ['/s/access', '/s/session/consent', '/s/session/code/verify',
    '/s/session/download', '/s/session/sign', '/api/trpc/envelope.field.sign', 'enter'])
def test_all_recipient_posts_still_reject_noncanonical_origin(access, origin, path):
    browser = Client(enforce_csrf_checks=True)
    browser.get('/s/access', **BASE)
    _, raw = new_session(access); browser.cookies[COOKIE] = raw
    headers = dict(BASE, HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value)
    if origin is not None:
        headers['HTTP_ORIGIN'] = origin
    path = '/s/' + capability(access) + '/enter' if path == 'enter' else path
    with patch('dealroom_sign.recipient_proxy.httpx.Client') as upstream:
        assert browser.post(path, {}, content_type='application/json', **headers).status_code == 403
    upstream.assert_not_called()


@pytest.mark.parametrize('layout', ['repo-public', 'repo-dist', 'image-copy', 'preview-copy', 'configured'])
@pytest.mark.parametrize('asset', ['fds/tokens.css', 'fds/theme-boot.js', 'fds/marks/fleet.svg', 'dealroom/shell.css', 'dealroom/shell.js'])
def test_assets_in_repository_and_actual_docker_copy_layout(access, settings, tmp_path, layout, asset):
    settings.BASE_DIR = tmp_path / 'backend'
    settings.SIGN_RECIPIENT_ASSET_ROOTS = None
    if layout in {'image-copy', 'preview-copy'}:
        # Derive both destinations from the deployed image's real COPY chain.
        deployment = 'sign-product-preview' if layout == 'preview-copy' else 'chief-glue-v1'
        backend_copy = (REPO / 'deploy' / deployment / 'Dockerfile').read_text()
        frontend_copy = (REPO / 'deploy/chief-send-proto/Dockerfile').read_text()
        backend_dest = re.search(r'^COPY .*backend/ (\S+)', backend_copy, re.M)[1]
        frontend_dest = re.search(r'^COPY .* \. (\S+)', frontend_copy, re.M)[1]
        settings.BASE_DIR = tmp_path / backend_dest.lstrip('/')
        root = tmp_path / frontend_dest.lstrip('/')
    elif layout == 'configured':
        root = tmp_path / 'mounted-assets'
        settings.SIGN_RECIPIENT_ASSET_ROOTS = [root]
    else:
        root = tmp_path / 'frontend' / layout.removeprefix('repo-')
    target = root / asset
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((REPO / 'frontend/public' / asset).read_bytes())
    result = Client().get('/s/assets/' + asset, **BASE)
    assert result.status_code == 200
    assert b''.join(result.streaming_content) == target.read_bytes()
    result.close()


def test_asset_roots_fail_closed_for_missing_paths_extensions_and_symlinks(access, settings, tmp_path):
    settings.SIGN_RECIPIENT_ASSET_ROOTS = [tmp_path / 'assets']
    (tmp_path / 'assets/fds').mkdir(parents=True)
    (tmp_path / 'outside.css').write_text('private')
    (tmp_path / 'assets/fds/private.css').symlink_to(tmp_path / 'outside.css')
    for path in ['fds/missing.css', 'fds/private.css', 'fds/private.py', 'fds/../outside.css', '../outside.css']:
        assert Client().get('/s/assets/' + path, **BASE).status_code == 403
    settings.SIGN_RECIPIENT_ASSET_ROOTS = []
    assert Client().get('/s/assets/fds/tokens.css', **BASE).status_code == 403


@pytest.mark.parametrize('first,last,expected', [('None', 'None', 'Requester'), (' ', '\t', 'Requester'),
    ('None', 'Whaley', 'Whaley'), (' Drew ', 'None', 'Drew'), ('', '', 'Requester')])
def test_missing_staff_names_never_render_none(access, first, last, expected):
    work = access.workflow
    work.owner.first_name, work.owner.last_name = first, last
    work.owner.save()
    access.delete()
    fresh = provision(work, envelope(work))[0]
    message = compose(enqueue(fresh, 'invitation', 'release'))
    assert parseaddr(message.from_email)[0] == expected + ' via Fleet Sign'
    assert message.reply_to == [work.owner.email]
    html = page(RequestFactory().get('/'), 'welcome', access=fresh).content.decode()
    for text in [message.subject, message.body, message.alternatives[0][0], html]:
        assert 'None' not in text and expected in text


def test_outgoing_requester_overrides_owner_for_mail_and_context(access):
    work = access.workflow
    requester = {'name': 'Drew Whaley', 'email': 'dwhaley@amforge.com'}
    SignatureRequest.objects.create(workflow=work, board_id='board', creator=work.owner,
        title=work.title, kind='out', state=work.state, room=work.room, source_context={'requester': requester})
    access.delete()
    fresh = provision(work, envelope(work))[0]
    message = compose(enqueue(fresh, 'invitation', 'release'))
    assert message.reply_to == [requester['email']]
    assert parseaddr(message.from_email)[0] == 'Drew Whaley via Fleet Sign'
    assert fresh.sending_staff['email'] == work.owner.email
    assert 'Drew Whaley' in page(RequestFactory().get('/'), 'welcome', access=fresh).content.decode()


@pytest.mark.parametrize('kind', ['in', 'out'])
@pytest.mark.parametrize('requester', [{'name': 'Drew', 'email': 'bad'}, {'name': 'Drew\nBcc: Extra', 'email': 'drew@example.test'},
    {'name': 'Drew', 'email': 'drew@example.test\r\nBcc: extra@example.test'}, {}, None])
def test_incoming_and_outgoing_requesters_share_validation(access, kind, requester):
    work = access.workflow
    SignatureRequest.objects.create(workflow=work, board_id='board', creator=work.owner,
        title=work.title, kind=kind, state=work.state, room=work.room, source_context={'requester': requester})
    with pytest.raises(SignError):
        sender_snapshot(work)


def board_body(base):
    return {'room_id': str(base.room.pk), 'version_id': str(base.version.pk),
        'recipients': base.work.recipients, 'idempotency_key': 'r6-board-send', 'board_id': 'fixture',
        'title': 'Harbor Light Mutual NDA', 'requester': {'name': 'Drew Whaley', 'email': 'dwhaley@amforge.com'}}


def test_board_send_persists_requester_and_clean_display_title_with_replay_binding(base):
    client = APIClient(); client.force_authenticate(base.user)
    base.version.document.name = 'Harbor Light Mutual NDA (Nov 15 1511).pdf'; base.version.document.save()
    body = board_body(base)
    with patch('dealroom_sign.workflows.source_bytes', return_value=base.pdf):
        response = client.post('/api/v1/dealroom-sign/envelopes/', body, format='json')
        assert response.status_code == 201, response.data
        row = SignatureRequest.objects.get(workflow_id=response.data['id'])
        assert row.kind == 'out' and row.title == row.workflow.title == body['title']
        assert row.source_context['requester'] == body['requester']
        assert row.creator == base.user and row.workflow.owner == base.user
        assert client.post('/api/v1/dealroom-sign/envelopes/', body, format='json').data['id'] == response.data['id']
        for change in [{'title': 'Another agreement'}, {'requester': {'name': 'Another', 'email': 'another@example.test'}}]:
            assert client.post('/api/v1/dealroom-sign/envelopes/', {**body, **change}, format='json').status_code == 400
    native = envelope(row.workflow)
    native['recipients'][0]['email'] = base.work.recipients[0]['email']
    fresh = provision(row.workflow, native)[0]
    assert fresh.context['title'] == body['title'] and fresh.sender == body['requester']
    message = compose(enqueue(fresh, 'invitation', 'release'))
    assert message.reply_to == [body['requester']['email']]
    for text in [message.subject, message.body, message.alternatives[0][0], page(RequestFactory().get('/'), 'welcome', access=fresh).content.decode()]:
        assert body['title'] in text and 'Nov 15 1511' not in text and '.pdf' not in text


@pytest.mark.parametrize('count', [0, 1, 2])
def test_invitation_and_context_pluralize_counts(access, count):
    access.context.update(pages=1, signatures=count)
    message = compose(enqueue(access, 'invitation', 'release'))
    suffix = '' if count == 1 else 's'
    for text in [message.body, message.alternatives[0][0]]:
        assert f'{count} signature{suffix} needed' in text
        assert f'Estimated {max(1, count)} minute' + ('' if count <= 1 else 's') in text
        assert '1 signatures' not in text and '1 minutes' not in text and '1 pages' not in text
    html = page(RequestFactory().get('/'), 'welcome', access=access).content.decode()
    assert f'{count} signature{suffix}.' in html
    assert 'signature(s)' not in html and '1 pages' not in html


@pytest.mark.parametrize('zone,display', [('UTC', '22 Nov 2026, 3:11 PM UTC'), ('America/Los_Angeles', '22 Nov 2026, 3:11 PM PST')])
def test_due_zone_is_shown_once(access, zone, display):
    access.context.update(timezone=zone, due_at=display)
    message = compose(enqueue(access, 'invitation', 'release'))
    for text in [message.body, message.alternatives[0][0], page(RequestFactory().get('/'), 'welcome', access=access).content.decode()]:
        assert 'Due ' + display in text
        assert '(' + zone + ')' not in text


def test_existing_context_cleans_extension_and_board_filename_suffix(access):
    access.context['title'] = 'Harbor Light Mutual NDA (Nov 15 1511).pdf'
    message = compose(enqueue(access, 'invitation', 'release'))
    html = page(RequestFactory().get('/'), 'welcome', access=access).content.decode()
    assert '<h1>Harbor Light Mutual NDA</h1>' in html
    for text in [html, message.subject, message.body, message.alternatives[0][0]]:
        assert 'Nov 15 1511' not in text and '.pdf' not in text


def test_nda_room_page_header_and_meta_match_same_origin_policy(fixture):
    link = ShareLink.objects.create(dataroom=fixture.room, created_by=fixture.user)
    RoomPolicy.objects.create(room=fixture.room, entry_link=link)
    for path in ['/signing/nda/' + str(fixture.room.pk), '/signing/room/' + link.slug]:
        response = Client().get(path)
        assert response.status_code == 200
        assert response['Referrer-Policy'] == 'same-origin'
        assert FormPage(response, path).policy == 'same-origin'


@pytest.mark.parametrize('change', [
    {'requester': {'name': 'Drew', 'email': 'invalid'}},
    {'requester': {'name': 'Drew\r\nExtra', 'email': 'drew@example.test'}},
    {'requester': {'name': 'Drew', 'email': 'drew@example.test', 'reply_to': 'extra@example.test'}},
    {'requester': None}, {'title': '\r\n'},
])
def test_invalid_sender_metadata_is_rejected_before_workflow_creation(base, change):
    client = APIClient(); client.force_authenticate(base.user)
    body = {**board_body(base), **change}
    with patch('dealroom_sign.workflows.source_bytes') as storage:
        response = client.post('/api/v1/dealroom-sign/envelopes/', body, format='json')
    assert response.status_code == 400
    storage.assert_not_called()
    assert not SignatureRequest.objects.exists()


def test_signer_cannot_set_requester_via_staff_send_endpoint(base):
    response = APIClient().post('/api/v1/dealroom-sign/envelopes/', board_body(base), format='json')
    assert response.status_code in {401, 403}
    assert not SignatureRequest.objects.exists()


@pytest.mark.parametrize('deployment', ['chief-glue-v1', 'chief-send-v1'])
def test_deployment_html_does_not_override_referrer_policy(deployment):
    config = (REPO / 'deploy' / deployment / 'nginx.conf').read_text().replace('"', '')
    assert 'add_header Referrer-Policy no-referrer' not in config
    assert 'add_header Referrer-Policy same-origin always;' in config


@pytest.mark.parametrize('kind', ['in', 'out'])
@pytest.mark.parametrize('name', ['', '   ', 'None', 'None None'])
def test_requester_missing_display_name_has_same_safe_fallback(access, kind, name):
    work = access.workflow
    SignatureRequest.objects.create(workflow=work, board_id='board', creator=work.owner,
        title=work.title, kind=kind, state=work.state, room=work.room,
        source_context={'requester': {'name': name, 'email': 'human@example.test'}})
    _, _, sender, _ = sender_snapshot(work)
    assert sender == {'name': 'Requester', 'email': 'human@example.test'}
