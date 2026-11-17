"""Visitor signing starts in place and returns through the bound room origin."""
from io import StringIO
from unittest.mock import patch

import pytest
from django.core import signing
from django.core.management import call_command
from django.test import Client, RequestFactory
from django.utils import timezone

from dealroom.tests.test_drive_onramp import room, snapshot, storage
from dealroom.tests.test_room_round3 import visitor
from dealroom.drive import import_tree, walk_tree
from dealroom.tests.test_room_round4 import source, confirm
from dealroom_sign.counterparty import COOKIE, new_session, provision, consume_handoff, observe_completion
from dealroom_sign.counterparty_mail import compose, enqueue
from dealroom_sign.client import SignError
from dealroom_sign.models import ObservedSignEvent, SignCredential, Workflow
from dealroom_sign.recipient_proxy import page
from dealroom_sign.tests.test_workflows import envelope

pytestmark = pytest.mark.django_db


@pytest.fixture
def started(room, staff, source, settings):
    settings.SITE_DOMAIN = 'https://room.test:9447'
    settings.SIGN_RECIPIENT_ORIGIN = 'https://recipient.test:9445'
    settings.SIGN_CAPABILITY_KEY = 'fictional-room-round-five-capability-key'
    confirm(staff, room, source)
    SignCredential.objects.create(owner=room.created_by, token='fictional', team_id=1)
    client, member = visitor(room, 'maya@northwind.test', 'Maya Chen')
    url = f'/api/v1/dealroom-sign/nda/{room.pk}/'
    response = client.post(url, {'return_url': 'https://elsewhere.test/view/other'}, format='json')
    assert response.status_code == 201
    work = Workflow.objects.get(room=room)
    return client, member, work, url


def ready(work, member):
    work.state = 'awaiting_signature'
    work.signing_token = 'fictional-native-token'
    work.signer_projection = [{'email': member.email, 'signingStatus': 'NOT_SIGNED'}]
    work.envelope_id = 'envelope_test'
    work.item_ids = ['item_test']
    work.save()
    env = envelope(work)
    env['recipients'][0].update(email=member.email, name=member.name, token=work.signing_token)
    return provision(work, env)[0]


def test_start_binds_room_origin_and_resume_keeps_one_workflow(started, settings):
    client, member, work, url = started
    event = ObservedSignEvent.objects.get(workflow=work, kind='room.return')
    assert event.payload == {'room_id': str(work.room_id), 'origin': 'https://room.test:9447'}
    settings.SITE_DOMAIN = 'https://gateway.test'
    assert client.post(url, {'return_url': 'https://elsewhere.test'}, format='json').status_code == 201
    event.refresh_from_db()
    assert event.payload['origin'] == 'https://room.test:9447'
    assert Workflow.objects.filter(room=work.room).count() == 1


def test_direct_entry_works_before_backup_mail_and_handoff_is_one_time(started):
    client, member, work, url = started
    access = ready(work, member)
    assert access.invite_state != 'succeeded'
    status = client.get(url).data
    assert status['email_sent'] is False
    result = client.post(url + 'enter/', {'return_url': 'https://elsewhere.test'}, format='json')
    assert result.status_code == 200
    assert result.data['signing_url'].startswith('https://recipient.test:9445/s/nda/')
    token = result.data['signing_url'].rsplit('/', 1)[1]
    consumed, session, _ = consume_handoff(token)
    assert consumed.workflow_id == work.pk and session.access_id == access.pk
    with pytest.raises(SignError):
        consume_handoff(token)


@pytest.mark.parametrize('path', ['return', 'context', 'complete'])
@pytest.mark.parametrize('state', ['awaiting_seal', 'done'])
def test_shared_gateway_terminal_uses_workflow_binding(started, settings, path, state):
    client, member, work, url = started
    access = ready(work, member)
    work.state = state
    work.signer_projection = [{'email': member.email, 'signingStatus': 'SIGNED'}]
    work.save()
    observe_completion(access, timezone.now())
    session, raw = new_session(access)
    browser = Client()
    browser.cookies[COOKIE] = raw
    settings.SITE_DOMAIN = 'https://preview.test:9443'
    route = {'return': '/s/return/' + str(work.pk), 'context': '/s/session/context',
             'complete': '/sign/' + access.native_token + '/complete'}[path]
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(work)):
        response = browser.get(route + '?return_url=https://elsewhere.test&signed=true',
            HTTP_HOST='recipient.test:9445', HTTP_X_FLEET_RECIPIENT_LISTENER='1')
    assert response.status_code == 303
    assert response['Location'] == 'https://room.test:9447/view/' + work.room.roompolicy.entry_link.slug + '?nda=complete'


def test_unsigned_callback_cannot_claim_completion_or_select_another_workflow(started):
    _, member, work, _ = started
    access = ready(work, member)
    _, raw = new_session(access)
    browser = Client()
    browser.cookies[COOKIE] = raw
    headers = {'HTTP_HOST': 'recipient.test:9445', 'HTTP_X_FLEET_RECIPIENT_LISTENER': '1'}
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(work)):
        response = browser.get('/s/return/' + str(work.pk) + '?signed=true&return_url=https://elsewhere.test', **headers)
        assert response.status_code == 200 and 'Location' not in response
        assert browser.get('/s/return/00000000-0000-0000-0000-000000000001', **headers).status_code == 403


def test_nda_mail_and_invitation_use_owner_display_name(started):
    client, member, work, url = started
    work.owner.name = 'Dan Whaley'
    work.owner.save(update_fields=['name'])
    access = ready(work, member)
    assert access.sender['name'] == 'Dan Whaley'
    message = compose(enqueue(access, 'invitation', 'fictional'))
    assert message.subject.startswith('Dan Whaley sent you')
    assert 'Dan Whaley via ' in message.from_email and 'Dealroom' in message.from_email
    assert message.reply_to == [work.owner.email]
    assert 'Dan Whaley' in message.body
    # Existing personal links can carry an old display name; the live owner wins.
    token = signing.dumps({
        'room': str(work.room_id), 'grant': str(work.room.roompolicy.entry_link.access_grants.get(email=member.email).pk),
        'email': member.email, 'sender_name': 'Fleet Admin'}, salt='room-personal')
    response = client.get(f'/api/v1/dealroom/recipient/{work.room.roompolicy.entry_link.slug}/challenge/', HTTP_X_ROOM_INVITATION=token)
    assert response.data['sender_name'] == 'Dan Whaley'


@pytest.mark.parametrize('name,expected', [('', 'Dan Whaley'), ('Fleet Admin', 'Dan Whaley'), ('Morgan Lee', 'Morgan Lee')])
def test_seed_sets_only_placeholder_owner_names(snapshot, owner, storage, name, expected):
    owner.name = name
    owner.save(update_fields=['name'])
    call_command('seed_room_onramp', owner=owner.email, stdout=StringIO())
    owner.refresh_from_db()
    assert owner.name == expected


def test_room_invitation_email_names_owner_using_brand_from(staff, owner, room, source, django_capture_on_commit_callbacks):
    owner.name = 'Dan Whaley'
    owner.save(update_fields=['name'])
    confirm(staff, room, source)
    with patch('dealroom.onramp.send_mail') as send, django_capture_on_commit_callbacks(execute=True):
        response = staff.post(f'/api/v1/dealroom/rooms/{room.pk}/invite/',
            {'emails': ['maya@northwind.test']}, format='json')
    assert response.status_code == 201
    subject, body, sender, recipients = send.call_args.args
    assert 'Dan Whaley invited you' in body
    assert sender.startswith('Dan Whaley via ')
    assert recipients == ['maya@northwind.test']


def test_backup_email_acknowledges_delivery_on_status_and_gateway(started):
    client, member, work, url = started
    access = ready(work, member)
    request = RequestFactory().get('/sign/fictional')
    assert 'emailed you this link' not in page(request, 'welcome', access=access).content.decode()
    access.invite_state = 'succeeded'
    access.save(update_fields=['invite_state'])
    assert client.get(url).data['email_sent'] is True
    assert 'We’ve also emailed you this link.' in page(request, 'welcome', access=access).content.decode()


def test_room_exposes_sheet_count_only_after_spreadsheet_render(room, snapshot, storage):
    import_tree(room, room.created_by, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'))
    client, _ = visitor(room, 'maya@northwind.test', 'Maya Chen')
    item = room.documents.get(document__name='Customer list - top 10.xlsx')
    version = item.document.versions.get(is_primary=True)
    url = f'/api/v1/dealroom/recipient/{room.roompolicy.entry_link.slug}/room/'
    assert next(f for f in client.get(url).data['files'] if f['id'] == str(item.pk))['sheet_count'] is None
    version.type, version.render_status, version.num_pages = 'spreadsheet', 'ready', 3
    version.save(update_fields=['type', 'render_status', 'num_pages'])
    assert next(f for f in client.get(url).data['files'] if f['id'] == str(item.pk))['sheet_count'] == 3
