from datetime import timedelta
from email.utils import parseaddr
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from dealroom_sign.client import SignError
from dealroom_sign.counterparty import observe_completion, provision
from dealroom_sign.counterparty_mail import compose, drain, enqueue, send_effect
from dealroom_sign.models import CounterpartyEffect, SignatureRequest
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope

pytestmark = pytest.mark.django_db


def test_invitation_headers_content_and_brand(access):
    access.context.update(title='Mutual NDA.pdf', note='<b>Please review</b>', pages=3, signatures=1)
    access.save()
    effect = enqueue(access, 'invitation', 'release')
    message = compose(effect)
    mime = message.message()
    assert parseaddr(message.from_email) == (access.sender['name'] + ' via Fleet Sign', 'sign@fleet.test')
    assert message.reply_to == [access.sender['email']] and message.to == [access.email] and not message.cc
    assert message.subject == access.sender['name'] + ' sent you “Mutual NDA” to sign'
    assert message.attachments == []
    assert "You don't need an account" in message.body and 'Is this legit?' in message.body
    html = message.alternatives[0][0]
    assert '&lt;b&gt;Please review&lt;/b&gt;' in html and '<b>Please review</b>' not in html
    assert html.count('>Review and sign<') == 1 and 'mailto:support@fleet.test' in html
    assert 'Estimated' in html and 'Due' in html and 'display:none' in html
    for content in [mime.as_string(), html, message.body]:
        assert not any(brand in content.lower() for brand in ['amforge', 'documenso', 'sslip.io'])
    assert mime.as_bytes() == message.message().as_bytes()
    assert all(part.get_content_type() in {'multipart/alternative', 'text/plain', 'text/html'} for part in mime.walk())


def test_incoming_staff_invitation_names_requester_and_preserves_staff_identity(access):
    work = access.workflow
    row = SignatureRequest.objects.create(workflow=work, board_id='board', creator=work.owner,
        title=work.title, kind='in', state='awaiting_signature', room=work.room,
        source_context={'requester': {'name': 'Harbor Light', 'email': 'requester@harbor.test'}})
    access.delete()
    incoming = provision(work, envelope(work))[0]
    message = compose(enqueue(incoming, 'invitation', 'release'))
    assert parseaddr(message.from_email)[0] == 'Harbor Light via Fleet Sign'
    assert message.reply_to == ['requester@harbor.test']
    assert f'Harbor Light (via {incoming.sending_staff["name"]}’s Dealroom)' in message.body
    assert incoming.sender != incoming.sending_staff
    row.source_context = {}
    row.save()
    with pytest.raises(SignError, match='incoming_requester_missing'):
        provision(work, envelope(work))


def completed(access):
    observe_completion(access, timezone.now())
    access.workflow.state = 'done'
    access.workflow.save()
    return enqueue(access, 'fully_signed', 'completion')


@pytest.mark.parametrize('size,attached', [(9_999_999, True), (10_000_000, True), (10_000_001, False)])
def test_final_copy_size_threshold_and_real_filenames(access, size, attached):
    effect = completed(access)
    files = [('Mutual NDA — signed.pdf', b'%PDF-' + b'x'*(size-10)), ('Signing certificate.pdf', b'%PDF-')]
    message = compose(effect, files=files)
    assert bool(message.attachments) is attached
    assert len(message.attachments) == (2 if attached else 0)
    if attached:
        assert [a[0] for a in message.attachments] == [f[0] for f in files]
        assert all(a[2] == 'application/pdf' for a in message.attachments)
    else:
        assert 'above the attachment limit' in message.body and 'Download your copies:' in message.body
    assert '.pdf.pdf' not in message.message().as_string()


def test_final_mime_cap_falls_back_as_a_pair_and_room_expiry_holds_mail(access, settings):
    effect = completed(access)
    settings.SIGN_SMTP_SIZE = 12_000
    message = compose(effect, files=[('signed.pdf', b'%PDF-' + b'x'*10000), ('certificate.pdf', b'%PDF-')])
    assert not message.attachments and len(message.message().as_bytes()) < 12_000
    access.room_expires_at = timezone.now()-timedelta(seconds=1)
    access.save()
    with pytest.raises(SignError, match='copy_link_unavailable'):
        compose(effect, files=[('signed.pdf', b'%PDF-'), ('certificate.pdf', b'%PDF-')])


def test_final_bytes_are_verified_against_stored_manifest(access, fixture, pdf):
    from dealroom_sign.counterparty_mail import final_files
    from dealroom_sign.models import ExecutedArtifact
    from documents.models import DocumentVersion
    from dealroom_sign.validation import digest
    completed(access)
    cert = DocumentVersion.objects.create(document=fixture.version.document, version_number=2,
        content_type='application/pdf', original_storage_key='certificate.pdf')
    for kind, version in [('sealed_pdf', fixture.version), ('certificate', cert)]:
        ExecutedArtifact.objects.create(workflow=access.workflow, item_id=kind, kind=kind, version=version,
            size=len(pdf), sha256=digest(pdf))
    with patch('dealroom_sign.counterparty_mail.source_bytes', return_value=pdf):
        files = final_files(access)
    assert files == [('Source — signed.pdf', pdf), ('Signing certificate.pdf', pdf)]
    with patch('dealroom_sign.counterparty_mail.source_bytes', return_value=pdf+b'changed'):
        with pytest.raises(SignError, match='copy_hash_mismatch'):
            final_files(access)


def test_mail_effect_deduplicates_and_timeout_is_not_retried(access):
    effect = enqueue(access, 'invitation', 'release')
    assert enqueue(access, 'invitation', 'release').pk == effect.pk
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', side_effect=TimeoutError) as send:
        send_effect(effect.pk)
        send_effect(effect.pk)
    effect.refresh_from_db()
    assert effect.state == 'delivery_uncertain' and send.call_count == 1 and effect.payload_hash
    other = enqueue(access, 'invitation', 'different-release')
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)):
        send_effect(other.pk)
    other.refresh_from_db()
    assert other.state == 'succeeded' and len(mail.outbox) == 1


def test_interrupted_effect_is_uncertain_and_waiting_signer_is_not_invited(access):
    effect = enqueue(access, 'invitation', 'release')
    CounterpartyEffect.objects.filter(pk=effect.pk).update(state='running', updated_at=timezone.now()-timedelta(minutes=6))
    drain()
    effect.refresh_from_db()
    assert effect.state == 'delivery_uncertain'
    other = enqueue(access, 'invitation', 'second')
    env = envelope(access.workflow)
    env['documentMeta'] = {'signingOrder': 'SEQUENTIAL'}
    env['recipients'][0]['signingOrder'] = 2
    env['recipients'].append({'id': 2, 'email': 'first@test.test', 'role': 'SIGNER', 'signingStatus': 'NOT_SIGNED', 'signingOrder': 1})
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=env):
        send_effect(other.pk)
    other.refresh_from_db()
    assert other.state == 'pending' and not getattr(mail, 'outbox', [])


def test_mime_hash_matches_the_message_actually_sent_and_size_rejection_uses_link(access):
    import hashlib
    import smtplib
    effect = completed(access)
    files = [('Source — signed.pdf', b'%PDF-final'), ('Signing certificate.pdf', b'%PDF-certificate')]
    messages = []
    def deliver(message, **kwargs):
        messages.append(message)
        if len(messages) == 1:
            raise smtplib.SMTPDataError(552, b'SIZE exceeded')
        return 1
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.counterparty_mail.final_files', return_value=files), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', autospec=True, side_effect=deliver):
        send_effect(effect.pk)
    effect.refresh_from_db()
    assert effect.state == 'succeeded' and len(messages) == 2
    assert len(messages[0].attachments) == 2 and messages[1].attachments == []
    assert messages[0].extra_headers['Message-ID'] == messages[1].extra_headers['Message-ID']
    assert effect.payload_hash == hashlib.sha256(messages[1].message().as_bytes(linesep='\r\n')).hexdigest()


def test_incoming_requester_must_be_bound_before_native_release(access):
    from unittest.mock import Mock
    from dealroom_sign.workflows import execute
    work = access.workflow
    work.state = 'draft'; work.save()
    SignatureRequest.objects.create(workflow=work, board_id='board', creator=work.owner,
        title=work.title, kind='in', state='draft', room=work.room, source_context={})
    native = Mock()
    native.get.return_value = envelope(work, 'DRAFT')
    with pytest.raises(SignError, match='incoming_requester_missing'):
        execute(work, native)
    native.distribute.assert_not_called()


def test_sender_name_follows_the_app_sign_for_invitations_dealroom_for_copies(access):
    # Owner, 15 Nov 2026: the app is "Sign" while signing and "Dealroom" once signed, so the From name matches the
    # email's own header ("Fleet | Sign" on the invitation, "Fleet | Dealroom" on the fully-signed copy).
    invitation = compose(enqueue(access, 'invitation', 'release'))
    assert parseaddr(invitation.from_email) == (access.sender['name'] + ' via Fleet Sign', 'sign@fleet.test')
    final = compose(completed(access), files=[('signed.pdf', b'%PDF-'), ('certificate.pdf', b'%PDF-')])
    assert parseaddr(final.from_email)[0].endswith(' via Fleet Dealroom')
