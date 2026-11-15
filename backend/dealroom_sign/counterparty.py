"""Personal capabilities and rotating Django sessions (EDD §4.2)."""
import base64
import calendar
import hashlib
import hmac
import secrets
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.db import transaction
from django.utils import timezone

from sharelinks.models import Viewer

from .client import SignError
from .evidence import instant
from .models import (NdaPolicy, SignatureRequest, SignerAccess, SignerChallenge,
                     SignerHandoff, SignerSession, Workflow)

COOKIE = '__Host-fleet_signer'
DISCLOSURE = 'Fleet | Dealroom electronic signature consent v1'


def keyed_hash(purpose, value):
    root = getattr(settings, 'SIGN_CAPABILITY_KEY', '') or settings.SECRET_KEY
    key = hmac.digest(root.encode(), ('fleet-sign/' + purpose).encode(), 'sha256')
    return hmac.new(key, value if isinstance(value, bytes) else value.encode(), hashlib.sha256).hexdigest()


def material(access):
    return access.pk.bytes + access.generation.to_bytes(8, 'big')


def capability(access):
    return base64.urlsafe_b64encode(bytes.fromhex(keyed_hash('link', material(access)))).decode().rstrip('=')


def alternate_code(access):
    raw = base64.b32encode(bytes.fromhex(keyed_hash('alternate', material(access)))[:10]).decode()
    return '-'.join(raw[i:i+4] for i in range(0, 16, 4))


def set_lookups(access):
    access.capability_hash = keyed_hash('lookup-link', capability(access))
    access.alternate_hash = keyed_hash('lookup-alternate', alternate_code(access).replace('-', ''))


def revision(workflow):
    row = SignatureRequest.objects.filter(workflow=workflow).first()
    return str(row.revision) if row else workflow.policy_revision or '1'


def access_state(access):
    now, work = timezone.now(), access.workflow
    if access.revoked_at or work.state == 'cancelled' or work.source_status == 'CANCELLED':
        return 'withdrawn'
    if access.revision != revision(work):
        return 'unavailable'
    if access.completed_at or access.role == 'CC':
        if access.room_expires_at and access.room_expires_at > now:
            return 'signed'
        return 'expired' if access.room_expires_at else 'waiting'
    if work.state == 'declined' or work.source_status == 'REJECTED':
        return 'declined'
    if access.signing_expires_at <= now:
        return 'expired'
    if work.state in {'failed', 'quarantined'}:
        return 'unavailable'
    return 'welcome'


def resolve(value, *, alternate=False):
    if not isinstance(value, str) or len(value) > 80:
        return None
    if alternate:
        value = value.upper().replace('-', '').replace(' ', '')
    name = 'alternate_hash' if alternate else 'capability_hash'
    expected = keyed_hash('lookup-alternate' if alternate else 'lookup-link', value)
    access = SignerAccess.objects.select_related('workflow').filter(**{name: expected}).first()
    if not access or not hmac.compare_digest(getattr(access, name), expected) or access.revoked_at:
        return None
    return access


def observe_completion(access, completed):
    if access.completed_at:
        return
    end = completed.replace(year=completed.year+1,
        day=min(completed.day, calendar.monthrange(completed.year+1, completed.month)[1]))
    SignerAccess.objects.filter(pk=access.pk, completed_at__isnull=True).update(completed_at=completed, room_expires_at=end)
    access.completed_at, access.room_expires_at = completed, end


def sender_snapshot(workflow):
    row = SignatureRequest.objects.filter(workflow=workflow).first()
    staff = {'name': workflow.owner.get_full_name() or workflow.owner.email,
             'email': workflow.owner.email, 'company': workflow.room.organization.name}
    sender = staff
    context = row.source_context if row else {}
    if row and row.kind == 'in':
        sender = context.get('requester')
        if not isinstance(sender, dict) or not sender.get('name') or not sender.get('email'):
            raise SignError('incoming_requester_missing')
    return row, staff, sender, context


def provision(workflow, envelope, *, released_at=None):
    row, staff, sender, context = sender_snapshot(workflow)
    result = []
    for person in envelope['recipients']:
        recipient_id = str(person['id'])
        access = SignerAccess.objects.select_for_update().filter(workflow=workflow,
            revision=revision(workflow), native_recipient_id=recipient_id).first()
        if not access:
            expires = instant(person.get('expiresAt'))
            released = released_at or instant(envelope.get('sentAt')) or (expires - timedelta(days=30) if expires else None) or instant(person.get('sentAt')) or timezone.now()
            access = SignerAccess(workflow=workflow, request=row, revision=revision(workflow),
                native_recipient_id=recipient_id, native_token=person.get('token', ''),
                email=person['email'].lower(), name=person.get('name') or next((p['name'] for p in workflow.recipients
                    if p['email'] == person['email'].lower()), ''), role=person.get('role', 'SIGNER'),
                sender=sender, sending_staff=staff, released_at=released, signing_expires_at=released+timedelta(days=30),
                context={'title': workflow.title, 'note': context.get('note', ''),
                    'pages': workflow.source_version.num_pages, 'signatures': sum(f['type'] in {'SIGNATURE', 'FREE_SIGNATURE'}
                        for p in workflow.recipients if p['email'] == person['email'].lower() for f in p.get('fields', [])),
                    'due_at': context.get('due_at') or (released+timedelta(days=7)).isoformat(),
                    'timezone': context.get('timezone', 'UTC'), 'incoming': bool(row and row.kind == 'in')})
            set_lookups(access)
            access.save()
        if access.email != person['email'].lower() or access.native_token != person.get('token', ''):
            raise SignError('signer_identity_changed')
        expires = instant(person.get('expiresAt'))
        if expires and expires < access.signing_expires_at:
            from .workflows import record_fact
            record_fact(workflow, 'signing_deadline.alert', recipient_id + ':' + expires.isoformat(),
                {'recipient_id': recipient_id, 'expires_at': expires.isoformat()})
            access.signing_expires_at = expires
            access.save(update_fields=['signing_expires_at'])
        completed = instant(person.get('signedAt'))
        if not completed and envelope['status'] == 'COMPLETED':
            completed = instant(envelope.get('completedAt'))
        if person.get('signingStatus') == 'SIGNED' and completed:
            observe_completion(access, completed)
        if person.get('role') == 'CC' and envelope['status'] == 'COMPLETED':
            observe_completion(access, instant(envelope.get('completedAt')) or timezone.now())
        result.append(access)
    return result


def revoke(access, reason):
    from .workflows import record_fact
    with transaction.atomic():
        access = SignerAccess.objects.select_for_update().get(pk=access.pk)
        access.generation += 1
        access.revoked_at, access.revocation_reason = timezone.now(), reason[:500]
        set_lookups(access)
        access.save()
        access.sessions.all().delete()
        record_fact(access.workflow, 'signer.revoked', f'{access.pk}:{access.generation}', {'reason': reason[:500]})


def disclosure_hash(access):
    return hashlib.sha256((DISCLOSURE + ':' + access.workflow.source_sha256 + ':' + access.revision).encode()).hexdigest()


def get_session(raw):
    if not raw or len(raw) > 128:
        return None
    session = SignerSession.objects.select_related('access__workflow').filter(session_hash=keyed_hash('session', raw)).first()
    if not session:
        return None
    access, now = session.access, timezone.now()
    if (session.generation != access.generation or session.expires_at <= now or
            (access.required_auth == 'email_code' and session.idle_expires_at <= now) or
            access_state(access) in {'withdrawn', 'expired', 'unavailable'} or
            SessionStore(session_key=raw).get('signer_access') != str(access.pk)):
        return None
    SignerSession.objects.filter(pk=session.pk).update(idle_expires_at=min(session.expires_at, now+timedelta(minutes=30)))
    return session


def new_session(access, *, previous=None, validated=None):
    with transaction.atomic():
        access = SignerAccess.objects.select_for_update().select_related('workflow').get(pk=access.pk)
        if access_state(access) in {'withdrawn', 'expired', 'unavailable'}:
            raise SignError('recipient_unavailable')
        if validated and (validated.access_id != access.pk or validated.generation != access.generation):
            raise SignError('session_scope_mismatch')
        if previous:
            SignerSession.objects.filter(session_hash=keyed_hash('session', previous)).delete()
            SessionStore(session_key=previous).delete()
        now = timezone.now()
        deadline = access.room_expires_at if access.completed_at else access.signing_expires_at
        expiry = min(now+timedelta(hours=8), deadline or now+timedelta(hours=8))
        transport = SessionStore()
        transport['signer_access'] = str(access.pk)
        transport.set_expiry(expiry)
        transport.create()
        session = SignerSession.objects.create(session_hash=keyed_hash('session', transport.session_key), access=access,
            generation=access.generation, issued_at=now, expires_at=expiry,
            idle_expires_at=min(expiry, now+timedelta(minutes=30)),
            code_verified_at=validated.code_verified_at if validated else None,
            disclosure_hash=validated.disclosure_hash if validated else '',
            consented_at=validated.consented_at if validated else None)
        return session, transport.session_key


def require_auth(session):
    if session.access.required_auth == 'email_code' and not session.code_verified_at:
        raise SignError('code_required')


def consent(session, raw, digest, agree):
    require_auth(session)
    if agree is not True or not hmac.compare_digest(digest, disclosure_hash(session.access)):
        raise SignError('consent_required')
    from .workflows import record_fact
    with transaction.atomic():
        if not get_session(raw):
            raise SignError('session_expired')
        fresh, cookie = new_session(session.access, previous=raw, validated=session)
        fresh.consented_at, fresh.disclosure_hash = timezone.now(), digest
        fresh.save(update_fields=['consented_at', 'disclosure_hash'])
        record_fact(session.access.workflow, 'signer.consent', fresh.pk,
            {'recipient_id': session.access.native_recipient_id, 'disclosure_hash': digest,
             'source_sha256': session.access.workflow.source_sha256})
        return fresh, cookie


def verify_code(session, raw, challenge_id, code):
    if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
        raise SignError('code_invalid')
    error = False
    with transaction.atomic():
        try:
            challenge = SignerChallenge.objects.select_for_update().get(pk=challenge_id, session=session, access=session.access)
        except (SignerChallenge.DoesNotExist, ValueError):
            raise SignError('code_invalid') from None
        if challenge.used_at or challenge.expires_at <= timezone.now() or challenge.attempts >= 5 or not get_session(raw):
            raise SignError('code_invalid')
        challenge.attempts += 1
        error = not hmac.compare_digest(challenge.code_hash, keyed_hash('otp', code))
        if not error:
            challenge.used_at = timezone.now()
        challenge.save(update_fields=['attempts', 'used_at'])
        if not error:
            session.code_verified_at = timezone.now()
            session.disclosure_hash, session.consented_at = '', None
            return new_session(session.access, previous=raw, validated=session)
    raise SignError('code_invalid')


def issue_handoff(access, viewer):
    if not viewer.verified_at or access.email != viewer.email.lower():
        raise SignError('handoff_unavailable')
    raw = secrets.token_urlsafe(32)
    SignerHandoff.objects.create(token_hash=keyed_hash('handoff', raw), access=access,
        generation=access.generation, viewer_id=str(viewer.pk), workflow=access.workflow,
        revision=access.revision, native_recipient_id=access.native_recipient_id,
        expires_at=timezone.now()+timedelta(seconds=60))
    return raw


def consume_handoff(raw, previous=None):
    with transaction.atomic():
        handoff = SignerHandoff.objects.select_for_update().select_related('access__workflow').filter(token_hash=keyed_hash('handoff', raw)).first()
        if not handoff or handoff.used_at or handoff.expires_at <= timezone.now():
            raise SignError('handoff_unavailable')
        access, work = handoff.access, handoff.access.workflow
        viewer = Viewer.objects.filter(pk=handoff.viewer_id, verified_at__isnull=False).first()
        policy = NdaPolicy.objects.filter(room=work.room, enabled=True).first()
        latest = Workflow.objects.filter(room=work.room, purpose='nda', member_id=work.member_id,
            policy_revision=work.policy_revision).order_by('-created_at').first()
        if (not viewer or not policy or not latest or latest.pk != work.pk or work.purpose != 'nda' or
            work.state != 'awaiting_signature' or handoff.workflow_id != work.pk or
            handoff.viewer_id != work.member_id or viewer.email.lower() != work.member_email or
            viewer.email.lower() != access.email or handoff.revision != work.policy_revision or
            handoff.revision != str(policy.revision) or handoff.revision != access.revision or
            handoff.native_recipient_id != access.native_recipient_id or handoff.generation != access.generation or
            work.signing_token != access.native_token):
            raise SignError('handoff_unavailable')
        handoff.used_at = timezone.now()
        handoff.save(update_fields=['used_at'])
        session, cookie = new_session(access, previous=previous)
        return access, session, cookie
