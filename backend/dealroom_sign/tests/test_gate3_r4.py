"""Gate 3 r2 review regressions, applied in r4."""
import json
import re
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.test import RequestFactory
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from dealroom_sign.views import can_retry_email

from dealroom.models import Activity
from dealroom_sign.client import SignError
from dealroom_sign.counterparty import observe_completion
from dealroom_sign.counterparty_mail import attempt_history, compose, drain, enqueue, enqueue_requester, send_effect
from dealroom_sign.models import CounterpartyEffect, ObservedSignEvent, Workflow
from dealroom_sign.recipient_proxy import authorize_rpc
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_counterparty_mail import completed
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope
from dealroom_sign.validation import validate_recipients
from dealroom_sign.workflows import execute, process, sweep

pytestmark = pytest.mark.django_db


def test_major2_waiting_has_no_history_or_repeated_sweep_cost(access):
    effect = enqueue(access, 'invitation', 'release')
    before = Activity.objects.count()
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)) as native, \
         patch('dealroom_sign.recipient_proxy.eligible', return_value=False), \
         patch('dealroom_sign.counterparty_mail.attempt_history', wraps=attempt_history) as history:
        for _ in range(50):
            drain(1)
    assert history.call_count == 2
    assert Activity.objects.count() == before
    assert not ObservedSignEvent.objects.filter(kind__in=['mail.attempt', 'mail.waiting']).exists()
    assert native.call_count == 1
    effect.refresh_from_db()
    assert effect.state == 'pending'
    with patch('dealroom_sign.counterparty_mail.timezone.now', return_value=effect.updated_at + timedelta(minutes=16)), \
         patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)) as recheck, \
         patch('dealroom_sign.recipient_proxy.eligible', return_value=False):
        drain(1)
    recheck.assert_called_once()
    assert Activity.objects.count() == before
    assert not ObservedSignEvent.objects.filter(kind__startswith='mail.').exists()
    effect.refresh_from_db()
    assert effect.state == 'pending' and effect.last_error == 'mail_waiting'


def test_minor11_waiting_does_not_overwrite_interrupted_worker(access):
    effect = enqueue(access, 'invitation', 'release')
    def interrupted(*args):
        CounterpartyEffect.objects.filter(pk=effect.pk).update(state='delivery_uncertain')
        return False
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.recipient_proxy.eligible', side_effect=interrupted):
        send_effect(effect.pk)
    effect.refresh_from_db()
    assert effect.state == 'delivery_uncertain'


def test_minor2_company_survives_command_validation(pdf, recipients):
    recipients[0]['company'] = 'Harbor Light'
    normalized = validate_recipients(recipients, pdf)
    assert normalized[0]['company'] == 'Harbor Light'


@pytest.mark.parametrize('role', ['SIGNER', 'CC'])
def test_minor3_requester_copy_reuses_existing_recipient(access, role):
    work = access.workflow
    work.state = 'done'; work.completed_at = timezone.now(); work.save()
    access.email = work.owner.email.upper(); access.role = role; access.save()
    observe_completion(access, work.completed_at)
    existing = enqueue(access, 'fully_signed', 'completion')
    assert enqueue_requester(work, 'completion').pk == existing.pk
    assert work.signer_accesses.count() == 1
    assert CounterpartyEffect.objects.filter(kind='fully_signed').count() == 1


def test_minor4_nda_has_no_requester_copy(access):
    work = access.workflow
    work.purpose = 'nda'; work.state = 'done'; work.completed_at = timezone.now(); work.save()
    assert enqueue_requester(work, 'completion') is None
    assert not CounterpartyEffect.objects.filter(kind='fully_signed').exists()
    assert not work.signer_accesses.filter(native_recipient_id='requester').exists()


def test_minor5_missing_key_stops_before_distribute(access, settings):
    settings.SIGN_CAPABILITY_KEY = ''
    work = access.workflow
    work.state = 'draft'; work.save()
    native = Mock(); native.get.return_value = envelope(work, 'DRAFT')
    with pytest.raises(SignError, match='capability_key_unavailable'):
        execute(work, native)
    native.distribute.assert_not_called()
    work.refresh_from_db(); assert work.state == 'draft'


def test_minor6_done_watch_expires_and_active_work_has_priority(access):
    work = access.workflow
    work.state = 'done'; work.completed_at = timezone.now()-timedelta(days=3)
    work.next_attempt_at = timezone.now()-timedelta(days=3); work.save()
    with patch('dealroom_sign.workflows.process') as run, patch('dealroom_sign.counterparty_mail.drain'), patch('dealroom_sign.storage.recover_previews'):
        sweep(1)
    run.assert_not_called()
    work.completed_at = timezone.now(); work.save()
    active = Workflow.objects.create(owner=work.owner, room=work.room, source_version=work.source_version,
        idempotency_key='active', external_id='active', state='awaiting_signature', next_attempt_at=timezone.now())
    with patch('dealroom_sign.workflows.process') as run, patch('dealroom_sign.counterparty_mail.drain'), patch('dealroom_sign.storage.recover_previews'):
        sweep(1)
    run.assert_called_once_with(active.pk)


@pytest.mark.parametrize('failure', [SignError('sign_transport_error'), RuntimeError('offline')])
def test_minor6_done_outage_adds_no_history(access, failure):
    work = access.workflow
    work.state = 'done'; work.completed_at = timezone.now(); work.save()
    native = Mock(); native.audit.side_effect = failure
    before = Activity.objects.count()
    with patch('dealroom_sign.workflows.Documenso') as client:
        client.return_value.__enter__.return_value = native
        process(work.pk)
    assert Activity.objects.count() == before
    work.refresh_from_db(); assert work.next_attempt_at >= timezone.now()+timedelta(minutes=14)


@pytest.mark.parametrize('name,value', [('envelope.signingStatus', {'token': ''}),
    ('envelope.attachment.find', {'token': '', 'envelopeId': 'envelope_test'}),
    ('envelope.item.getManyByToken', {'envelopeId': 'envelope_test', 'access': {'type': 'recipient', 'token': ''}})])
def test_nit4_empty_native_token_denied(access, name, value):
    access.native_token = ''
    request = RequestFactory().get('/api/trpc/'+name, {'input': json.dumps({'json': value})})
    with pytest.raises(SignError, match='recipient_scope_mismatch'):
        authorize_rpc(request, access, envelope(access.workflow))


def test_nit6_final_footer_refers_to_link(access):
    message = compose(completed(access), files=[])
    for body in [message.body, message.alternatives[0][0]]:
        assert "If the button doesn't work" not in body
        assert "If the link doesn't work" in body


def test_nit12_release_mismatch_is_held_once(access):
    work = access.workflow
    work.state = 'distributing'; work.save()
    native = Mock(); native.get.return_value = envelope(work)
    native.verify_release.side_effect = SignError('release_mail_settings_mismatch', uncertain=True)
    with patch('dealroom_sign.workflows.Documenso') as client:
        client.return_value.__enter__.return_value = native
        for _ in range(3):
            Workflow.objects.filter(pk=work.pk).update(next_attempt_at=timezone.now())
            process(work.pk)
    work.refresh_from_db()
    assert work.state == 'quarantined'
    assert ObservedSignEvent.objects.filter(kind='release.error').count() == 1
    native.verify_release.assert_called_once()


def test_major3_multiple_signers_have_neutral_rows_and_no_addresses(access):
    effect = completed(access)
    access.workflow.recipients = [
        {'email': access.email, 'name': 'First Signer', 'role': 'SIGNER'},
        {'email': 'second@example.test', 'name': '', 'role': 'SIGNER'},
        {'email': 'copy@example.test', 'name': 'Copy Person', 'role': 'CC'},
    ]
    access.workflow.signer_projection = [{'email': p['email'], 'signedAt': '2026-11-14T23:42:00Z'} for p in access.workflow.recipients]
    message = compose(effect, files=[])
    for body in [message.subject, message.body, message.alternatives[0][0]]:
        assert 'First Signer' in body and 'Signer 2' in body
        assert 'Copy Person' not in body
        assert '@' not in body
    assert access.sender['name'] + ':' not in message.body
    for part in message.message().walk():
        for name, value in part.items():
            if name.lower() == 'message-id':
                assert re.fullmatch(r'<[0-9a-f]{64}@fleet\.test>', str(value))
            elif name.lower() not in {'to', 'from', 'reply-to'}:
                assert '@' not in str(value), name


def test_major2_waiting_does_not_consume_limit_and_reconcile_wakes_it(access):
    waiting = enqueue(access, 'invitation', 'waiting')
    sending = enqueue(access, 'invitation', 'eligible')
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.recipient_proxy.eligible', side_effect=[False, True]), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', return_value=1):
        drain(1)
    sending.refresh_from_db(); waiting.refresh_from_db()
    assert sending.state == 'succeeded' and waiting.last_error == 'mail_waiting'
    enqueue(access, 'invitation', 'waiting')
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', return_value=1):
        drain(1)
    waiting.refresh_from_db(); assert waiting.state == 'succeeded'


def test_nit5_retry_requires_explicit_board_binding(access):
    request = RequestFactory().post('/')
    request.user = access.workflow.owner
    request.user.is_staff = True
    request.auth = None
    request.successful_authenticator = JWTAuthentication()
    row = Mock(workflow=access.workflow)
    assert can_retry_email(request, row) is False


def test_major3_address_valued_display_labels_stay_private(access):
    effect = completed(access)
    access.sender['name'] = 'sender@example.test'
    access.workflow.recipients = [
        {'email': access.email, 'name': access.email, 'company': 'other@example.test', 'role': 'SIGNER'},
        {'email': 'second@example.test', 'name': 'Second', 'role': 'SIGNER'},
    ]
    message = compose(effect, files=[])
    for body in [message.subject, message.body, message.alternatives[0][0]]:
        assert '@' not in body
        assert 'Signer 1' in body
