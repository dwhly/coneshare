from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory
from django.utils import timezone

from dealroom_sign.client import SignError
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, linked, envelope

pytestmark = pytest.mark.django_db


@pytest.fixture
def access(fixture, settings):
    from dealroom_sign.counterparty import provision
    settings.SIGN_RECIPIENT_ORIGIN = 'https://recipient.test:9445'
    settings.SIGN_CAPABILITY_KEY = 'test-purpose-key-not-a-proxy-key'
    work = linked(fixture)
    env = envelope(work)
    env['recipients'][0].update(sentAt=timezone.now().isoformat(), signingOrder=1)
    return provision(work, env)[0]


def test_capabilities_are_stable_opaque_and_rotated(access):
    from dealroom_sign.counterparty import capability, alternate_code, resolve, revoke
    link, code = capability(access), alternate_code(access)
    assert len(link) == 43 and len(code.replace('-', '')) == 16
    assert capability(access) == link and alternate_code(access) == code
    assert resolve(link).pk == access.pk and resolve(code, alternate=True).pk == access.pk
    assert access.native_token not in link and access.email not in link
    revoke(access, 'Sender revoked room')
    assert resolve(link) is None and resolve(code, alternate=True) is None
    access.refresh_from_db()
    assert capability(access) != link


def test_enter_and_consent_rotate_sessions_and_invalidate_previous(access):
    from dealroom_sign.counterparty import new_session, get_session, consent, disclosure_hash
    first, raw = new_session(access)
    second, raw2 = new_session(access, previous=raw)
    assert raw != raw2 and get_session(raw) is None
    assert get_session(raw2).pk == second.pk
    third, raw3 = consent(second, raw2, disclosure_hash(access), True)
    assert raw3 != raw2 and get_session(raw2) is None
    assert third.consented_at and third.disclosure_hash == disclosure_hash(access)
    assert SessionStore(session_key=raw2).load() == {}
    assert SessionStore(session_key=raw3).load()['signer_access'] == str(access.pk)


def test_code_verification_rotates_only_validated_scoped_state(access):
    from dealroom_sign.counterparty import new_session, get_session, verify_code
    from dealroom_sign.models import SignerChallenge
    from dealroom_sign.counterparty import keyed_hash
    access.required_auth = 'email_code'
    access.save()
    session, raw = new_session(access)
    challenge = SignerChallenge.objects.create(access=access, session=session,
        code_hash=keyed_hash('otp', '123456'), expires_at=timezone.now()+timedelta(minutes=5))
    with pytest.raises(SignError):
        verify_code(session, raw, str(challenge.pk), '000000')
    challenge.refresh_from_db()
    assert challenge.attempts == 1
    verified, fresh = verify_code(session, raw, str(challenge.pk), '123456')
    assert fresh != raw and get_session(raw) is None and verified.code_verified_at
    assert verified.consented_at is None
    with pytest.raises(SignError):
        verify_code(verified, fresh, str(challenge.pk), '123456')


def test_signing_and_room_deadlines_are_independent(access):
    from dealroom_sign.counterparty import access_state, observe_completion
    assert access.signing_expires_at == access.released_at + timedelta(days=30)
    completed = timezone.now() - timedelta(days=35)
    observe_completion(access, completed)
    access.refresh_from_db()
    original = access.room_expires_at
    assert original.year == completed.year+1 and original.month == completed.month
    access.signing_expires_at = timezone.now()-timedelta(days=5)
    access.save()
    assert access_state(access) == 'signed'
    observe_completion(access, timezone.now())
    access.refresh_from_db()
    assert access.room_expires_at == original
    access.room_expires_at = timezone.now()-timedelta(seconds=1)
    access.save()
    assert access_state(access) == 'expired'


def test_void_and_generation_invalidate_sessions(access):
    from dealroom_sign.counterparty import new_session, get_session, revoke
    session, raw = new_session(access)
    revoke(access, 'Void')
    assert get_session(raw) is None
    access.revoked_at = None
    access.save()
    session, raw = new_session(access)
    access.workflow.state = 'cancelled'
    access.workflow.save()
    assert get_session(raw) is None


def test_session_deadlines_idle_and_absolute(access):
    from dealroom_sign.counterparty import new_session, get_session
    access.required_auth = 'email_code'
    access.save()
    session, raw = new_session(access)
    assert session.expires_at <= session.issued_at+timedelta(hours=8)
    session.idle_expires_at = timezone.now()-timedelta(seconds=1)
    session.save()
    assert get_session(raw) is None


def test_nda_handoff_single_use_expiry_and_binding(access, fixture):
    from dealroom_sign.counterparty import issue_handoff, consume_handoff
    from dealroom_sign.models import NdaPolicy, SignerHandoff
    from sharelinks.models import Viewer
    viewer = Viewer.objects.create(organization=fixture.org, email=access.email, name='Member', verified_at=timezone.now())
    policy = NdaPolicy.objects.create(room=fixture.room, source_version=fixture.version, source_sha256=fixture.work.source_sha256)
    work = access.workflow
    work.purpose, work.member_id, work.member_email, work.policy_revision = 'nda', str(viewer.pk), viewer.email, str(policy.revision)
    work.signing_token = access.native_token
    work.save()
    access.revision = str(policy.revision)
    access.save()
    raw = issue_handoff(access, viewer)
    stored = SignerHandoff.objects.get()
    assert stored.token_hash != raw and stored.expires_at <= timezone.now()+timedelta(seconds=60)
    bound, session, cookie = consume_handoff(raw)
    assert bound.pk == access.pk and cookie
    with pytest.raises(SignError):
        consume_handoff(raw)
    raw = issue_handoff(access, viewer)
    SignerHandoff.objects.filter(used_at=None).update(expires_at=timezone.now()-timedelta(seconds=1))
    with pytest.raises(SignError):
        consume_handoff(raw)
    for field, value in [('member_id', 'other'), ('policy_revision', 'other'), ('signing_token', 'other')]:
        raw = issue_handoff(access, viewer)
        original = getattr(work, field)
        setattr(work, field, value)
        work.save()
        with pytest.raises(SignError):
            consume_handoff(raw)
        setattr(work, field, original)
        work.save()


def test_native_email_audit_alert_is_deduplicated(fixture):
    from dealroom_sign.workflows import reconcile
    from dealroom_sign.models import ObservedSignEvent
    work = linked(fixture)
    client = Mock()
    client.audit.return_value = {'data': [{'id': 'mail-1', 'type': 'EMAIL_SENT'}]}
    reconcile(work, client, envelope(work))
    reconcile(work, client, envelope(work))
    assert ObservedSignEvent.objects.filter(workflow=work, kind='native_email.alert').count() == 1


def test_deadline_uses_native_release_even_when_first_reconcile_is_delayed(access):
    from dealroom_sign.counterparty import provision
    work = access.workflow
    access.delete()
    env = envelope(work)
    released = timezone.now()-timedelta(days=8)
    env['recipients'][0]['expiresAt'] = (released+timedelta(days=30)).isoformat()
    restored = provision(work, env, released_at=released)[0]
    assert restored.released_at == released
    assert restored.signing_expires_at == released+timedelta(days=30)


def test_capability_request_logging_does_not_include_bearer_or_request(access):
    import logging
    from dealroom_sign.recipient_logging import RecipientLogFilter
    from dealroom_sign.counterparty import capability
    record = logging.LogRecord('django.request', logging.WARNING, '', 1, 'Forbidden: %s', ('/s/'+capability(access),), None)
    record.request = RequestFactory().get('/s/'+capability(access))
    assert RecipientLogFilter().filter(record)
    assert capability(access) not in record.getMessage() and not hasattr(record, 'request')


def test_native_email_alert_survives_history_projection(fixture):
    from dealroom_sign.models import SignatureRequest
    from dealroom_sign.requests import activity
    from dealroom_sign.workflows import reconcile
    work = linked(fixture)
    row = SignatureRequest.objects.create(workflow=work, board_id='fixture', creator=work.owner,
        title=work.title, kind='out', state=work.state, room=work.room)
    client = Mock()
    client.audit.return_value = {'data': [{'id': 'mail-1', 'type': 'EMAIL_SENT', 'createdAt': timezone.now().isoformat()}]}
    reconcile(work, client, envelope(work))
    history = activity(row)
    assert len([e for e in history if e['kind'] == 'native_email.alert']) == 1
    assert next(e for e in history if e['kind'] == 'native_email.alert')['at'] is not None
