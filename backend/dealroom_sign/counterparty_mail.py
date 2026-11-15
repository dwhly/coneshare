"""Request-scoped mail, immutable copy bytes and durable SMTP outcomes."""
import hashlib
import re
import smtplib
import uuid
from datetime import timedelta
from email.utils import formataddr, format_datetime
from urllib.parse import urlsplit

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.validators import validate_email
from django.db import transaction
from django.template import Context
from django.template.loader import get_template, render_to_string
from django.utils import timezone

from .client import SignError, pdf_filename
from .counterparty import (access_state, alternate_code, capability, display_time, observe_completion,
    revision, sender_snapshot, set_lookups)
from .models import CounterpartyEffect, ObservedSignEvent, SignerAccess
from .storage import source_bytes


class StableMessage(EmailMultiAlternatives):
    def message(self):
        message = super().message()
        seed = hashlib.sha256(self.extra_headers['Message-ID'].encode()).hexdigest()
        for index, part in enumerate(message.walk()):
            if part.is_multipart():
                part.set_boundary('fleet-' + seed + '-' + str(index))
        return message


def clean_title(title):
    value = pdf_filename(title)[:-4]
    value = re.sub(r'(?:[ _-]+\d{10,13}|[ _-]+\d{4}-\d{2}-\d{2}(?:[T _-]\d{2}[:_-]\d{2}(?::\d{2})?)?)$', '', value)
    return value or 'Document'


def header(value):
    if not isinstance(value, str) or '\r' in value or '\n' in value:
        raise SignError('invalid_mail_header')
    return value


def address(value):
    validate_email(header(value))
    return value


def personal_url(access):
    from .recipient_proxy import origin
    return origin() + '/s/' + capability(access)


def final_files(access):
    if access.workflow.state != 'done':
        raise SignError('copy_not_ready')
    artifacts = list(access.workflow.artifacts.filter(kind__in=['sealed_pdf', 'certificate']).select_related('version'))
    if sorted(a.kind for a in artifacts) != ['certificate', 'sealed_pdf']:
        raise SignError('copy_not_ready')
    result = {}
    for artifact in artifacts:
        content = source_bytes(artifact.version)
        if len(content) != artifact.size or hashlib.sha256(content).hexdigest() != artifact.sha256:
            raise SignError('copy_hash_mismatch')
        result[artifact.kind] = content
    return [(clean_title(access.context['title']) + ' — signed.pdf', result['sealed_pdf']),
            ('Signing certificate.pdf', result['certificate'])]


def compose(effect, *, files=None, force_link=False, smtp_size=0):
    access = effect.access
    title = clean_title(access.context['title'])
    sender = header(access.sender['name'])
    sender_email = address(access.sender['email'])
    to = address(access.email)
    url = personal_url(access)
    public = urlsplit(url)
    report = address(getattr(settings, 'SIGN_REPORT_EMAIL', 'support@fleet.test'))
    from_email = formataddr((sender + ' via Fleet Dealroom', address(settings.SIGN_FROM_EMAIL)))
    invitation = effect.kind == 'invitation'
    subject = f'{sender} sent you “{title}” to sign' if invitation else f'“{title}” fully signed'
    projection = {p.get('email', '').lower(): p for p in access.workflow.signer_projection}
    parties = []
    for person in access.workflow.recipients:
        if person.get('role') == 'CC':
            continue
        signed = projection.get(person['email'].lower(), {}).get('signedAt')
        parties.append({'name': person.get('name') or sender, 'company': person.get('company', ''),
            'signed_at': display_time(signed, access.context['timezone']) if signed else 'Not recorded'})
    if not invitation:
        subject += ' — ' + ' and '.join(p['name'] for p in parties)
    data = {'access': access, 'title': title, 'sender': sender, 'url': url,
        'origin': public.scheme + '://' + public.netloc, 'report': report,
        'alternate': alternate_code(access), 'invitation': invitation,
        'estimated_minutes': max(1, (access.context.get('pages') or 1) // 3 + access.context.get('signatures', 1)),
        'parties': parties, 'files': [], 'link_only': False}
    if not invitation:
        if access_state(access) != 'signed':
            raise SignError('copy_link_unavailable')
        files = files if files is not None else final_files(access)
        data['files'] = [{'name': name, 'size': len(content)} for name, content in files]
    def build(attach):
        data['link_only'] = not invitation and not attach
        text = get_template('dealroom_sign/emails/mail.txt').template.render(Context(data, autoescape=False))
        html = render_to_string('dealroom_sign/emails/mail.html', data)
        if len(html.encode()) >= 102*1024:
            raise SignError('mail_html_too_large')
        message = StableMessage(header(subject), text, from_email, [to], reply_to=[sender_email],
            headers={'Message-ID': effect.message_id, 'Date': format_datetime(access.released_at if invitation else (access.workflow.completed_at or access.completed_at))})
        message.attach_alternative(html, 'text/html')
        if attach:
            for name, content in files:
                message.attach(name, content, 'application/pdf')
        return message
    attach = not invitation and not force_link and sum(len(b) for _, b in files) <= 10_000_000
    message = build(attach)
    cap = min([settings.SIGN_MAIL_MAX_BYTES, *[v for v in (smtp_size, getattr(settings, 'SIGN_SMTP_SIZE', 0)) if v > 0]])
    if len(message.message().as_bytes(linesep='\r\n')) > cap:
        if not attach:
            raise SignError('mail_size_exceeded')
        message = build(False)
        if len(message.message().as_bytes(linesep='\r\n')) > cap:
            raise SignError('mail_size_exceeded')
    return message


def enqueue(access, kind, source_id):
    source_id = str(source_id)
    key = hashlib.sha256(f'{access.pk}:{kind}:{source_id}'.encode()).hexdigest()
    return CounterpartyEffect.objects.get_or_create(access=access, kind=kind, source_id=source_id,
        defaults={'message_id': f'<{key}@{settings.SIGN_MESSAGE_DOMAIN}>'})[0]


def enqueue_requester(workflow, source_id):
    """A separate copy capability has no native token or signing authority."""
    row, staff, sender, _ = sender_snapshot(workflow)
    template = workflow.signer_accesses.exclude(native_recipient_id='requester').first()
    if not template or not workflow.completed_at:
        raise SignError('copy_not_ready')
    with transaction.atomic():
        access = SignerAccess.objects.select_for_update().filter(workflow=workflow,
            revision=revision(workflow), native_recipient_id='requester').first()
        if access is None:
            access = SignerAccess(workflow=workflow, request=row, revision=revision(workflow),
                native_recipient_id='requester', native_token='', role='CC', email=sender['email'].lower(),
                name=sender['name'], sender=sender, sending_staff=staff, context=template.context,
                released_at=template.released_at, signing_expires_at=template.signing_expires_at)
            set_lookups(access)
            access.save()
        observe_completion(access, workflow.completed_at)
        return enqueue(access, 'fully_signed', source_id)


def attempt_history(effect):
    events = ObservedSignEvent.objects.filter(workflow=effect.access.workflow,
        payload__data__effect_id=str(effect.pk))
    reset = events.filter(kind='mail.retry').order_by('-occurred_at').first()
    attempts = events.filter(kind='mail.attempt')
    if reset:
        attempts = attempts.filter(pk__gt=reset.pk)
    return attempts.count()


def ready_at(effect, attempts):
    return effect.updated_at + timedelta(minutes=45 * 2 ** (min(attempts, 6)-1)) if attempts else effect.updated_at


def retry_email(effect, actor):
    from .workflows import record_fact
    with transaction.atomic():
        effect = CounterpartyEffect.objects.select_for_update().get(pk=effect.pk)
        if effect.state != 'failed':
            raise SignError('mail_retry_requires_failed')
        record_fact(effect.access.workflow, 'mail.retry', uuid.uuid4(),
            {'effect_id': str(effect.pk), 'actor_id': str(actor.pk), 'kind': effect.kind}, actor=actor)
        effect.state, effect.last_error = 'pending', ''
        effect.save(update_fields=['state', 'last_error', 'updated_at'])
        if effect.kind == 'invitation':
            effect.access.invite_state = 'pending'
            effect.access.save(update_fields=['invite_state'])
    return effect


def send_effect(effect_id):
    from .recipient_proxy import eligible, reconcile_native
    from .workflows import record_fact
    with transaction.atomic():
        effect = CounterpartyEffect.objects.select_for_update().select_related('access__workflow').get(pk=effect_id)
        attempts = attempt_history(effect)
        if effect.state != 'pending' or ready_at(effect, attempts) > timezone.now():
            return
        attempt_id = uuid.uuid4()
        attempts += 1
        record_fact(effect.access.workflow, 'mail.attempt', attempt_id,
            {'effect_id': str(effect.pk), 'attempt': attempts, 'kind': effect.kind})
        effect.state = 'running'
        effect.save(update_fields=['state', 'updated_at'])
    connection = None
    try:
        access = effect.access
        envelope = reconcile_native(access)
        if effect.kind == 'invitation' and not eligible(access, envelope):
            effect.state = 'pending' if access_state(access) == 'welcome' else 'cancelled'
            # Waiting for a preceding signer is not a delivery attempt.
            ObservedSignEvent.objects.filter(workflow=access.workflow, source_id=str(attempt_id), kind='mail.attempt').update(kind='mail.waiting')
            effect.save(update_fields=['state', 'updated_at'])
            return
        connection = get_connection(fail_silently=False)
        connection.open()
        smtp = getattr(connection, 'connection', None)
        if smtp:
            smtp.ehlo_or_helo_if_needed()
        advertised = (getattr(smtp, 'esmtp_features', {}) or {}).get('size', '')
        smtp_size = int(advertised) if str(advertised).isdigit() else 0
        message = compose(effect, smtp_size=smtp_size)
        message.connection = connection
        effect.payload_hash = hashlib.sha256(message.message().as_bytes(linesep='\r\n')).hexdigest()
        effect.save(update_fields=['payload_hash', 'updated_at'])
        access.refresh_from_db()
        if access_state(access) not in {'welcome', 'signed'}:
            raise SignError('recipient_unavailable')
    except Exception as exc:
        effect.state = 'pending' if attempts < 6 else 'failed'
        effect.last_error = exc.code if isinstance(exc, SignError) else 'mail_preparation_' + type(exc).__name__[:60]
    else:
        try:
            try:
                accepted = message.send(fail_silently=False)
            except (smtplib.SMTPDataError, smtplib.SMTPSenderRefused) as exc:
                if exc.smtp_code != 552 or not message.attachments:
                    raise
                message = compose(effect, force_link=True, smtp_size=smtp_size)
                message.connection = connection
                effect.payload_hash = hashlib.sha256(message.message().as_bytes(linesep='\r\n')).hexdigest()
                effect.save(update_fields=['payload_hash', 'updated_at'])
                accepted = message.send(fail_silently=False)
            if accepted != 1:
                raise smtplib.SMTPRecipientsRefused({access.email: (550, b'rejected')})
            effect.state, effect.last_error = 'succeeded', ''
        except SignError as exc:
            effect.state = 'pending' if attempts < 6 else 'failed'
            effect.last_error = exc.code
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError, ConnectionRefusedError) as exc:
            codes = [value[0] for value in exc.recipients.values()] if isinstance(exc, smtplib.SMTPRecipientsRefused) else [getattr(exc, 'smtp_code', 450)]
            temporary = all(400 <= code < 500 for code in codes)
            effect.state = 'pending' if temporary and attempts < 6 else 'failed'
            effect.last_error = 'mail_rejected'
        except Exception:
            effect.state, effect.last_error = 'delivery_uncertain', 'mail_acceptance_unknown'
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass
    with transaction.atomic():
        # A timed-out lease is held even if an old worker later returns.
        current = CounterpartyEffect.objects.select_for_update().get(pk=effect.pk)
        if current.state != 'running':
            return
        effect.save(update_fields=['state', 'last_error', 'updated_at'])
        if effect.kind == 'invitation':
            effect.access.invite_state = effect.state
            effect.access.save(update_fields=['invite_state'])
        record_fact(effect.access.workflow, 'mail.' + effect.state, uuid.uuid4(),
            {'effect_id': str(effect.pk), 'kind': effect.kind, 'recipient_id': effect.access.native_recipient_id,
             'attempt': attempts, 'error': effect.last_error,
             'next_attempt_at': ready_at(effect, attempts).isoformat() if effect.state == 'pending' else None})


def drain(limit=20):
    from .workflows import record_fact
    stale = CounterpartyEffect.objects.filter(state='running', updated_at__lt=timezone.now()-timedelta(minutes=5))
    for effect in stale:
        if CounterpartyEffect.objects.filter(pk=effect.pk, state='running').update(state='delivery_uncertain', last_error='worker_interrupted'):
            record_fact(effect.access.workflow, 'mail.delivery_uncertain', uuid.uuid4(),
                {'effect_id': str(effect.pk), 'kind': effect.kind, 'error': 'worker_interrupted'})
    sent = 0
    for effect in CounterpartyEffect.objects.filter(state='pending').select_related('access__workflow').order_by('updated_at').iterator():
        if ready_at(effect, attempt_history(effect)) <= timezone.now():
            send_effect(effect.pk)
            sent += 1
            if sent >= limit:
                break
