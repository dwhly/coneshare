"""Gate 3 regression evidence; each item names the review it protects."""
import smtplib
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

import httpx
import pytest
from django.conf import settings as django_settings
from django.core.mail import get_connection
from django.test import Client
from django.utils import timezone

from dealroom_sign.client import Documenso, SignError, NATIVE_EMAIL_OFF, NATIVE_REMINDERS_OFF, SIGNING_PERIOD
from dealroom_sign.counterparty import keyed_hash, new_session, provision, verify_code
from dealroom_sign.counterparty_mail import compose, enqueue, send_effect
from dealroom_sign.models import CounterpartyEffect, ObservedSignEvent, SignatureRequest, SignerChallenge, Workflow
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_product_reads import base
from dealroom_sign.tests.test_counterparty_mail import completed
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope, linked
from dealroom_sign.workflows import process, reconcile, sweep

pytestmark = pytest.mark.django_db


def release_transport(work, failure=None, auth=None, released_meta=None):
    distributed = False
    def handle(request):
        nonlocal distributed
        if request.url.path.endswith('/distribute'):
            distributed = True
        if request.url.path.endswith('/audit-log'):
            return httpx.Response(200, json={'data': [], 'count': 0})
        if request.url.path.endswith('/update') and failure:
            raise httpx.ConnectError('offline')
        result = envelope(work, 'PENDING' if distributed else 'DRAFT')
        result.update(teamId=3, authOptions={'globalAccessAuth': [] if auth is None else auth, 'globalActionAuth': []})
        result['documentMeta'] = {'reminderSettings': NATIVE_REMINDERS_OFF,
            'envelopeExpirationPeriod': SIGNING_PERIOD, 'distributionMethod': 'NONE', 'emailSettings': NATIVE_EMAIL_OFF}
        if request.method == 'GET' and released_meta is not None:
            result['documentMeta'] = released_meta
        return httpx.Response(200, json=result)
    return httpx.MockTransport(handle)


def test_m1_preparation_failure_remains_draft_with_backoff_and_history(access):
    work = access.workflow
    work.state = 'draft'; work.save()
    client = Documenso(work.owner.signcredential, release_transport(work, failure=True))
    with patch('dealroom_sign.workflows.Documenso', return_value=client):
        process(work.pk)
    work.refresh_from_db()
    assert work.state == 'draft'
    assert work.last_error == 'sign_transport_error'
    assert work.next_attempt_at > timezone.now()
    assert ObservedSignEvent.objects.filter(workflow=work, kind='release.error', payload__data__error='sign_transport_error').exists()
    before = work.last_error
    process(work.pk)
    work.refresh_from_db()
    assert work.last_error == before and work.attempts == 1


def test_m1_attempt_marker_is_immediately_before_native_distribute(access):
    work = access.workflow
    work.state = 'draft'; work.save()
    paths = []
    transport = release_transport(work)
    def handle(request):
        work.refresh_from_db()
        paths.append(request.url.path)
        assert work.state == ('distributing' if '/api/v2/envelope/distribute' in paths else 'draft')
        return transport.handle_request(request)
    client = Documenso(work.owner.signcredential, httpx.MockTransport(handle))
    with patch('dealroom_sign.workflows.Documenso', return_value=client):
        process(work.pk)
    assert '/api/v2/envelope/distribute' in paths


@pytest.mark.parametrize('auth', [['EMAIL'], None])
def test_minor5_release_checks_auth_readback(access, auth):
    work = access.workflow
    paths = []
    def handle(request):
        paths.append(request.url.path)
        result = envelope(work, 'DRAFT')
        result.update(teamId=3, authOptions={'globalActionAuth': []})
        if auth is not None:
            result['authOptions']['globalAccessAuth'] = auth
        result['documentMeta'] = {'reminderSettings': NATIVE_REMINDERS_OFF, 'envelopeExpirationPeriod': SIGNING_PERIOD}
        return httpx.Response(200, json=result)
    with Documenso(work.owner.signcredential, httpx.MockTransport(handle)) as client:
        with pytest.raises(SignError, match='release_settings_not_persisted'):
            client.distribute(work.envelope_id, external_id=work.external_id)
    assert not any(path.endswith('/distribute') for path in paths)


@pytest.mark.parametrize('meta', [{}, {'distributionMethod': 'EMAIL', 'emailSettings': NATIVE_EMAIL_OFF},
    {'distributionMethod': 'NONE', 'emailSettings': {**NATIVE_EMAIL_OFF, 'documentCompleted': True}}])
def test_minor5_post_distribution_native_mail_is_verified(access, meta):
    work = access.workflow
    with Documenso(work.owner.signcredential, release_transport(work, released_meta=meta)) as client:
        with pytest.raises(SignError, match='release_mail_settings_mismatch'):
            client.distribute(work.envelope_id, external_id=work.external_id)


def test_m4_reconcile_preserves_concurrent_lease_errors_and_retry_schedule(access):
    work = access.workflow
    lease, next_at = timezone.now()+timedelta(minutes=5), timezone.now()+timedelta(minutes=2)
    Workflow.objects.filter(pk=work.pk).update(lease_until=lease, attempts=7, last_error='real_error', next_attempt_at=next_at)
    client = Mock(); client.audit.return_value = {'data': []}
    reconcile(work, client, envelope(work))
    work.refresh_from_db()
    assert (work.lease_until, work.attempts, work.last_error, work.next_attempt_at) == (lease, 7, 'real_error', next_at)


def test_m4_completed_reconcile_never_stages_again(access):
    work = access.workflow
    work.state = 'done'; work.save()
    client = Mock(); client.audit.return_value = {'data': []}
    with patch('dealroom_sign.workflows.stage') as stage:
        reconcile(work, client, envelope(work, 'COMPLETED'))
    stage.assert_not_called()
    client.pdf.assert_not_called()


def test_minor9_sweep_observes_late_native_mail_on_done_workflow(access):
    work = access.workflow
    work.state = 'done'; work.save()
    client = Mock(); client.audit.return_value = {'data': [{'id': 'late-mail', 'type': 'EMAIL_SENT'}]}
    with patch('dealroom_sign.workflows.Documenso') as native, patch('dealroom_sign.counterparty_mail.drain'), patch('dealroom_sign.storage.recover_previews'):
        native.return_value.__enter__.return_value = client
        sweep()
    assert ObservedSignEvent.objects.filter(workflow=work, kind='native_email.alert', source_id='late-mail').count() == 1
    client.signed_item.assert_not_called()


@pytest.mark.parametrize('failure', [SignError('sign_transport_error'), ConnectionRefusedError()])
def test_m2_preparation_failure_retries_with_backoff(access, failure):
    effect = enqueue(access, 'invitation', 'release')
    with patch('dealroom_sign.recipient_proxy.reconcile_native', side_effect=failure) as prepare:
        send_effect(effect.pk)
        effect.refresh_from_db()
        assert effect.state == 'pending'
        send_effect(effect.pk)
        assert prepare.call_count == 1


@pytest.mark.parametrize('failure', [smtplib.SMTPDataError(451, b'temporary'),
    smtplib.SMTPSenderRefused(450, b'temporary', 'sender@fleet.test'), ConnectionRefusedError()])
def test_m2_definite_preacceptance_failure_retries(access, failure):
    effect = enqueue(access, 'invitation', 'release')
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', side_effect=failure):
        send_effect(effect.pk)
    effect.refresh_from_db()
    assert effect.state == 'pending'


def test_m2_six_attempts_over_about_24h_then_failed_history(access):
    effect = enqueue(access, 'invitation', 'release')
    start = timezone.now()
    with patch('dealroom_sign.recipient_proxy.reconcile_native', side_effect=SignError('sign_transport_error')) as prepare:
        for attempt, hours in enumerate([0, .75, 2.25, 5.25, 11.25, 23.25], 1):
            with patch('django.utils.timezone.now', return_value=start+timedelta(hours=hours, seconds=attempt)):
                send_effect(effect.pk)
            effect.refresh_from_db()
            assert effect.state == ('failed' if attempt == 6 else 'pending')
        assert prepare.call_count == 6
    assert ObservedSignEvent.objects.filter(workflow=access.workflow, kind='mail.failed').count() == 1


def test_nit6_each_failed_delivery_attempt_has_history(access):
    effect = enqueue(access, 'invitation', 'release')
    with patch('dealroom_sign.recipient_proxy.reconcile_native', side_effect=SignError('sign_transport_error')):
        send_effect(effect.pk)
        with patch('django.utils.timezone.now', return_value=timezone.now()+timedelta(hours=1)):
            send_effect(effect.pk)
    events = ObservedSignEvent.objects.filter(workflow=access.workflow, kind='mail.pending')
    assert events.count() == 2
    assert len(set(events.values_list('source_id', flat=True))) == 2


def test_m3_private_final_mail_and_nit5_distinct_copy(access):
    effect = completed(access)
    access.sender = {**access.sender, 'name': 'Requester'}
    access.context['timezone'] = 'America/Los_Angeles'
    access.workflow.recipients = [{'email': access.email, 'name': '', 'company': 'Harbor', 'role': 'SIGNER'},
        {'email': 'copy@example.test', 'name': 'CC Person', 'role': 'CC'}]
    access.workflow.signer_projection = [{'email': access.email, 'signedAt': '2026-11-14T23:42:00Z'},
        {'email': 'copy@example.test', 'role': 'CC', 'signedAt': None}]
    message = compose(effect, files=[('signed.pdf', b'%PDF-a'), ('certificate.pdf', b'%PDF-b')])
    for text in [message.subject, message.body, message.alternatives[0][0]]:
        assert access.email not in text and 'copy@example.test' not in text and 'CC Person' not in text
        assert 'Requester' in text
    for text in [message.body, message.alternatives[0][0]]:
        assert 'Harbor' in text and '14 Nov 2026, 3:42 PM PST' in text
        assert 'This invitation uses' not in text and 'Estimated' not in text
        assert 'fully signed' in text


def test_minor2_final_date_is_stable_completion_time(access):
    effect = completed(access)
    access.workflow.completed_at = datetime(2026, 11, 14, 23, 42, tzinfo=dt_timezone.utc)
    message = compose(effect, files=[])
    assert message.message()['Date'] == 'Sat, 14 Nov 2026 23:42:00 +0000'
    assert message.message().as_bytes() == compose(effect, files=[]).message().as_bytes()


def test_minor3_plain_text_is_not_html_escaped(access):
    access.context['note'] = "O'Brien & Harbor <review>"
    message = compose(enqueue(access, 'invitation', 'release'))
    assert "O'Brien & Harbor <review>" in message.body
    assert 'O&#x27;Brien &amp; Harbor &lt;review&gt;' in message.alternatives[0][0]


def test_minor4_smtp_timeout_is_bounded():
    assert 0 < django_settings.EMAIL_TIMEOUT <= 60
    assert get_connection('django.core.mail.backends.smtp.EmailBackend').timeout == django_settings.EMAIL_TIMEOUT


@pytest.mark.parametrize('missing', ['', '   ', None])
def test_minor6_capability_key_has_no_secret_key_fallback(settings, missing):
    settings.SIGN_CAPABILITY_KEY = missing
    with pytest.raises(SignError, match='capability_key_unavailable'):
        keyed_hash('link', 'value')


def test_minor7_cc_deadline_is_publication_plus_year(access):
    work = access.workflow
    work.completed_at = timezone.now(); work.state = 'done'; work.save()
    env = envelope(work, 'COMPLETED')
    env['recipients'][0]['role'] = 'CC'
    cc = provision(work, env)[0]
    assert cc.completed_at == work.completed_at
    assert cc.room_expires_at == work.completed_at.replace(year=work.completed_at.year+1)


def test_minor8_default_due_time_is_in_sender_timezone(access):
    work = access.workflow
    SignatureRequest.objects.create(workflow=work, board_id='test', creator=work.owner, title=work.title,
        kind='out', state=work.state, room=work.room, source_context={'timezone': 'America/Los_Angeles'})
    access.delete()
    fresh = provision(work, envelope(work), released_at=datetime(2026, 11, 7, 23, 42, tzinfo=dt_timezone.utc))[0]
    assert fresh.context['due_at'] == '14 Nov 2026, 3:42 PM PST'


def test_minor11_code_history_survives_rotation(access):
    session, raw = new_session(access)
    challenge = SignerChallenge.objects.create(access=access, session=session, code_hash=keyed_hash('otp', '123456'),
        expires_at=timezone.now()+timedelta(minutes=5))
    with pytest.raises(SignError):
        verify_code(session, raw, str(challenge.pk), '000000')
    verify_code(session, raw, str(challenge.pk), '123456')
    challenge.refresh_from_db()
    assert challenge.attempts == 2 and challenge.used_at


@pytest.mark.parametrize('response', [smtplib.SMTPSenderRefused(552, b'SIZE exceeded', 'sender@fleet.test'),
    smtplib.SMTPDataError(552, b'SIZE exceeded')])
def test_minor1_relay_size_rejection_recomposes_pair_once(access, response):
    effect = completed(access)
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow, 'COMPLETED')), \
         patch('dealroom_sign.counterparty_mail.final_files', return_value=[('signed.pdf', b'%PDF-a'), ('cert.pdf', b'%PDF-b')]), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', side_effect=[response, 1]) as send:
        send_effect(effect.pk)
    effect.refresh_from_db()
    assert effect.state == 'succeeded' and send.call_count == 2


def test_minor1_cap_uses_actual_smtp_crlf_bytes(access, settings):
    effect = completed(access)
    files = [('signed.pdf', b'%PDF-'+b'x'*3000), ('cert.pdf', b'%PDF-b')]
    message = compose(effect, files=files)
    settings.SIGN_MAIL_MAX_BYTES = len(message.message().as_bytes())
    assert len(message.message().as_bytes(linesep='\r\n')) > settings.SIGN_MAIL_MAX_BYTES
    assert not compose(effect, files=files).attachments


@pytest.mark.parametrize('incoming', [False, True])
def test_minor10_requester_gets_separate_copy_without_other_capability(access, incoming):
    from dealroom_sign import counterparty_mail
    work = access.workflow
    if incoming:
        SignatureRequest.objects.create(workflow=work, board_id='fixture', creator=work.owner, title=work.title,
            kind='in', state='done', room=work.room, source_context={'requester': {'name': 'Requester', 'email': 'requester@harbor.test'}})
    work.state = 'done'; work.completed_at = timezone.now(); work.save()
    recipient_effect = completed(access)
    effect = counterparty_mail.enqueue_requester(work, 'completion')
    assert effect.pk != recipient_effect.pk
    assert counterparty_mail.enqueue_requester(work, 'completion').pk == effect.pk
    expected = 'requester@harbor.test' if incoming else work.owner.email
    files = [('signed.pdf', b'%PDF-a'), ('certificate.pdf', b'%PDF-b')]
    message = compose(effect, files=files)
    from dealroom_sign.counterparty import capability
    assert message.to == [expected] and not message.cc and not message.bcc
    assert capability(access) not in message.body
    assert len(message.attachments) == 2
    assert effect.access.native_token == '' and effect.access.role == 'CC'


@pytest.mark.parametrize('role,status', [('manager', 200), ('writer', 200), ('reader', 403)])
def test_m2_audited_sender_retry_of_failed_effect(base, role, status, settings):
    from dealroom_sign.tests.test_product_reads import product, headers, PREFIX
    from rest_framework.test import APIClient
    import json
    settings.SIGN_CAPABILITY_KEY = 'test-capability-key'
    row, binding = product(base)
    binding.role = role; binding.save()
    env = {'status': 'PENDING', 'recipients': [{'id': 12, 'email': 'signer@example.test', 'name': 'Signer', 'token': 't'}]}
    effect = enqueue(provision(base.work, env)[0], 'invitation', 'release')
    effect.state = 'failed'; effect.save()
    path = PREFIX+f'/requests/{row.pk}/emails/{effect.pk}/retry'
    raw = json.dumps({}).encode()
    result = APIClient().generic('POST', path, raw, content_type='application/json', **headers('POST', path, raw))
    assert result.status_code == status
    effect.refresh_from_db()
    assert effect.state == ('pending' if status == 200 else 'failed')
    if status == 200:
        assert ObservedSignEvent.objects.filter(workflow=base.work, kind='mail.retry').count() == 1
        effect.state = 'delivery_uncertain'; effect.save()
        assert APIClient().generic('POST', path, raw, content_type='application/json', **headers('POST', path, raw)).status_code == 400
        effect.refresh_from_db()
        assert effect.state == 'delivery_uncertain'



def test_minor5_retry_after_uncertain_distribution_rechecks_mail_settings(access):
    work = access.workflow
    work.state = 'distributing'; work.save()
    native = Mock()
    native.get.return_value = envelope(work)
    native.verify_release.side_effect = SignError('release_mail_settings_mismatch', uncertain=True)
    with patch('dealroom_sign.workflows.reconcile') as publish:
        from dealroom_sign.workflows import execute
        with pytest.raises(SignError, match='release_mail_settings_mismatch'):
            execute(work, native)
    publish.assert_not_called()
    native.distribute.assert_not_called()


def test_m2_link_recompose_failure_is_known_preacceptance(access):
    effect = completed(access)
    real_compose = compose
    def build(effect, **kwargs):
        if kwargs.get('force_link'):
            raise SignError('copy_not_ready')
        return real_compose(effect, files=[('signed.pdf', b'%PDF-a'), ('cert.pdf', b'%PDF-b')], **kwargs)
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.counterparty_mail.compose', side_effect=build), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', side_effect=smtplib.SMTPSenderRefused(552, b'SIZE', 'sender@fleet.test')):
        send_effect(effect.pk)
    effect.refresh_from_db()
    assert effect.state == 'pending'
    assert effect.last_error == 'copy_not_ready'


def test_m2_retry_visibility_matches_readonly_role(base, settings):
    from dealroom_sign.tests.test_product_reads import product, get, PREFIX
    settings.SIGN_CAPABILITY_KEY = 'test-capability-key'
    row, binding = product(base)
    binding.role = 'reader'; binding.save()
    env = {'status': 'PENDING', 'recipients': [{'id': 12, 'email': 'signer@example.test', 'name': 'Signer', 'token': 't'}]}
    effect = enqueue(provision(base.work, env)[0], 'invitation', 'release')
    effect.state = 'failed'; effect.save()
    response = get(PREFIX+f'/requests/{row.pk}')
    assert response.status_code == 200
    assert response.data['email_effects'][0]['can_retry'] is False


def test_m2_nonowner_writer_retry_records_actual_actor(base, settings):
    from core.models import User
    from dealroom.models import Activity
    from dealroom_sign.tests.test_product_reads import product, headers, PREFIX
    from rest_framework.test import APIClient
    settings.SIGN_CAPABILITY_KEY = 'test-capability-key'
    row, binding = product(base)
    writer = User.objects.create_user(username='writer@fleet.test', email='writer@fleet.test', organization=base.org, is_staff=True)
    binding.send_user, binding.login, binding.role = writer, writer.email, 'writer'; binding.save()
    env = {'status': 'PENDING', 'recipients': [{'id': 12, 'email': 'signer@example.test', 'name': 'Signer', 'token': 't'}]}
    effect = enqueue(provision(base.work, env)[0], 'invitation', 'release')
    effect.state = 'failed'; effect.save()
    path = PREFIX+f'/requests/{row.pk}/emails/{effect.pk}/retry'
    raw = b'{}'
    response = APIClient().generic('POST', path, raw, content_type='application/json', **headers('POST', path, raw, login=writer.email))
    assert response.status_code == 200
    assert Activity.objects.get(event_type='mail.retry').actor_id == str(writer.pk)
