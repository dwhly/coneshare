"""Durable workflow execution; remote calls happen outside local transactions."""
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .client import Documenso, SignError
from .models import NdaAcceptance, ObservedSignEvent, SignCredential, Workflow
from .storage import publish, source_bytes, stage, verify_seal
from .validation import digest, request_digest, validate_recipients

TERMINAL = {'done', 'cancelled', 'declined', 'failed', 'quarantined'}
AUDIT_KINDS = {
    'DOCUMENT_SENT': 'envelope.sent', 'DOCUMENT_OPENED': 'envelope.viewed',
    'DOCUMENT_VIEWED': 'envelope.viewed', 'DOCUMENT_RECIPIENT_COMPLETED': 'envelope.signed',
    'DOCUMENT_COMPLETED': 'envelope.completed', 'DOCUMENT_REJECTED': 'envelope.declined',
    'DOCUMENT_CANCELLED': 'envelope.cancelled',
}


def record_fact(workflow, kind, source_id, data=None):
    from dealroom.activity import record
    _, created = ObservedSignEvent.objects.get_or_create(workflow=workflow, source_id=str(source_id), kind=kind)
    if created:
        recipient_event = kind in {'envelope.viewed', 'envelope.signed', 'nda.signed'}
        actor = (workflow.member_id or 'sign:' + digest(str((data or {}).get('email', '')).encode())[:50]) if recipient_event else workflow.owner
        record(kind, organization=workflow.room.organization, actor=actor, actor_kind='recipient' if recipient_event else 'staff',
               room_id=workflow.room_id, target_id=workflow.envelope_id or str(workflow.pk),
               data={'workflow_id': str(workflow.pk), 'member_id': workflow.member_id, 'source': 'sign', 'source_record_id': str(source_id), **(data or {})})


def command(*, owner, room, version, recipients, idempotency_key, purpose='room_document',
            member=None, policy=None):
    if not idempotency_key or len(idempotency_key) > 200:
        raise ValidationError('An idempotency key of at most 200 characters is required.')
    pdf = source_bytes(version)
    recipients = validate_recipients(recipients, pdf)
    if purpose == 'nda':
        if not member or len(recipients) != 1 or recipients[0]['email'] != member.email.strip().lower():
            raise ValidationError('NDA signer must match the verified member.')
        if not policy or digest(pdf) != policy.source_sha256:
            raise ValidationError('NDA source revision changed.')
    data = {'room': str(room.pk), 'version': str(version.pk), 'sha256': digest(pdf),
            'recipients': recipients, 'purpose': purpose,
            'member': str(member.pk) if member else '', 'policy': str(policy.revision) if policy else ''}
    fingerprint = request_digest(data)
    command_id = uuid.uuid4()
    with transaction.atomic():
        workflow, created = Workflow.objects.get_or_create(owner=owner, idempotency_key=idempotency_key, defaults={
            'id': command_id, 'room': room, 'request_sha256': fingerprint, 'purpose': purpose,
            'member_id': str(member.pk) if member else '', 'member_email': member.email.strip().lower() if member else '',
            'policy_revision': str(policy.revision) if policy else '', 'source_version': version,
            'source_sha256': digest(pdf), 'recipients': recipients, 'title': version.document.name,
            'external_id': f'dealroom:{getattr(settings, "SIGN_DEPLOYMENT_ID", "chief")}:{command_id}',
        })
        if workflow.request_sha256 != fingerprint:
            raise ValidationError('Idempotency key already used with different inputs.')
    return workflow


def validate_envelope(workflow, envelope):
    if envelope.get('id') != workflow.envelope_id or envelope.get('externalId') != workflow.external_id:
        raise SignError('envelope_correlation_mismatch')
    expected = sorted((r['email'], r.get('role', 'SIGNER')) for r in workflow.recipients)
    actual = sorted((r.get('email', '').strip().lower(), r.get('role')) for r in envelope.get('recipients', []))
    if actual != expected:
        raise SignError('signer_identity_changed')
    items = [item['id'] for item in envelope.get('envelopeItems', [])]
    if not items or (workflow.item_ids and sorted(items) != sorted(workflow.item_ids)):
        raise SignError('envelope_items_changed')
    if envelope.get('status') not in {'DRAFT', 'PENDING', 'COMPLETED', 'REJECTED', 'CANCELLED'}:
        raise SignError('unknown_sign_status')
    return items


def adopt(workflow, client, envelope_id):
    workflow.envelope_id = envelope_id
    envelope = client.get(envelope_id)
    items = validate_envelope(workflow, envelope)
    if len(items) != 1:
        raise SignError('unexpected_source_item_count')
    original = client.pdf(f'envelope/item/{items[0]}/download', params={'version': 'original'})
    if digest(original) != workflow.source_sha256:
        raise SignError('source_hash_changed')
    workflow.item_ids = items
    workflow.state = 'draft'
    workflow.save(update_fields=['envelope_id', 'item_ids', 'state'])
    return envelope


def execute(workflow, client):
    if not workflow.envelope_id:
        if workflow.state in {'creating', 'uncertain'}:
            matches = client.find(workflow.external_id)
            if len(matches) > 1:
                raise SignError('duplicate_external_id')
            if not matches:
                raise SignError('create_outcome_uncertain', uncertain=True)
            adopt(workflow, client, matches[0]['id'])
        elif workflow.state == 'queued':
            pdf = source_bytes(workflow.source_version)
            if digest(pdf) != workflow.source_sha256:
                raise SignError('source_hash_changed')
            workflow.state = 'creating'
            workflow.save(update_fields=['state'])
            envelope_id = client.create(workflow, pdf)
            # Persist response before any second remote request; ambiguous create is never replayed.
            workflow.envelope_id = envelope_id
            workflow.save(update_fields=['envelope_id'])
            adopt(workflow, client, envelope_id)
    envelope = client.get(workflow.envelope_id)
    if not workflow.item_ids:
        envelope = adopt(workflow, client, workflow.envelope_id)
    validate_envelope(workflow, envelope)
    if workflow.state == 'draft' and envelope['status'] == 'DRAFT':
        workflow.state = 'distributing'
        workflow.save(update_fields=['state'])
        redirect = f'{settings.SITE_DOMAIN}/signing/nda/{workflow.room_id}' if workflow.purpose == 'nda' else ''
        client.distribute(workflow.envelope_id, nda=workflow.purpose == 'nda', redirect_url=redirect)
        envelope = client.get(workflow.envelope_id)
        validate_envelope(workflow, envelope)
    if envelope['status'] == 'DRAFT':
        raise SignError('distribution_outcome_uncertain', uncertain=True)
    return reconcile(workflow, client, envelope)


def reconcile(workflow, client, envelope=None):
    envelope = envelope or client.get(workflow.envelope_id)
    validate_envelope(workflow, envelope)
    recipients = envelope['recipients']
    projection = [{k: r.get(k) for k in ('id', 'email', 'role', 'signingStatus', 'signedAt', 'readStatus')} for r in recipients]
    status = envelope['status']
    if workflow.purpose == 'nda':
        if len(recipients) != 1 or recipients[0]['email'].strip().lower() != workflow.member_email:
            raise SignError('nda_identity_mismatch')
        workflow.signing_token = recipients[0].get('token', '')
    audit = client.audit(workflow.envelope_id)
    audit_rows = audit if isinstance(audit, list) else audit.get('data', audit.get('logs', []))
    completion_id = next((f['id'] for f in audit_rows if f.get('type') == 'DOCUMENT_COMPLETED' and f.get('id')), None)
    staged = []
    seal = None
    if status == 'COMPLETED':
        for item_id in workflow.item_ids:
            original = client.pdf(f'envelope/item/{item_id}/download', params={'version': 'original'})
            if digest(original) != workflow.source_sha256:
                raise SignError('source_hash_changed')
        if not envelope.get('completedAt') or any(r.get('signingStatus') != 'SIGNED' for r in recipients):
            raise SignError('completion_evidence_incomplete')
        if not completion_id:
            raise SignError('completion_audit_pending')
        for item_id in workflow.item_ids:
            pdf = client.signed_item(item_id)
            seal = verify_seal(pdf)
            staged.append(stage(workflow, item_id, 'sealed_pdf', pdf))
        staged.append(stage(workflow, workflow.envelope_id, 'certificate', client.certificate(workflow.envelope_id)))
        staged.append(stage(workflow, workflow.envelope_id, 'audit', client.audit_pdf(workflow.envelope_id)))
    with transaction.atomic():
        locked = Workflow.objects.select_for_update().get(pk=workflow.pk)
        if locked.state == 'done':
            return locked
        workflow.source_status = status
        workflow.signer_projection = projection
        workflow.reconciled_at = timezone.now()
        workflow.state = {'COMPLETED': 'done', 'REJECTED': 'declined', 'CANCELLED': 'cancelled'}.get(status, 'awaiting_signature')
        if status == 'PENDING' and all(r.get('signingStatus') == 'SIGNED' for r in recipients):
            workflow.state = 'awaiting_seal'
        for fact in audit_rows:
            kind = AUDIT_KINDS.get(fact.get('type', fact.get('event')))
            if kind and fact.get('id'):
                record_fact(workflow, kind, fact['id'], {'email': fact.get('email', ''), 'name': fact.get('name', ''), 'occurred_at': fact.get('createdAt')})
        if staged:
            publish(workflow, staged)
            workflow.completed_at = timezone.now()
            if workflow.purpose == 'nda':
                NdaAcceptance.objects.get_or_create(room=workflow.room, member_id=workflow.member_id,
                    policy_revision=workflow.policy_revision, defaults={'member_email': workflow.member_email, 'workflow': workflow})
                record_fact(workflow, 'nda.signed', completion_id, {'email': workflow.member_email})
            record_fact(workflow, 'fileback.completed', completion_id, seal)
        elif status == 'PENDING':
            record_fact(workflow, 'nda.sent' if workflow.purpose == 'nda' else 'envelope.sent', f'sent:{workflow.pk}')
        workflow.last_error = ''
        workflow.next_attempt_at = timezone.now() + timedelta(seconds=15)
        workflow.save()
    return workflow


def process(workflow_id):
    now = timezone.now()
    # Long enough for bounded remote calls; CAS prevents concurrent webhook/poll runners.
    claimed = Workflow.objects.filter(pk=workflow_id).exclude(state__in=TERMINAL).filter(
        Q(lease_until__isnull=True) | Q(lease_until__lt=now)).update(lease_until=now + timedelta(minutes=5))
    if not claimed:
        return
    workflow = Workflow.objects.select_related('owner', 'room__organization', 'source_version__document').get(pk=workflow_id)
    try:
        credential = SignCredential.objects.get(owner=workflow.owner, enabled=True)
        with Documenso(credential) as client:
            execute(workflow, client)
    except SignError as exc:
        workflow.refresh_from_db()
        if exc.code in {'sealed_bytes_conflict', 'duplicate_external_id', 'signer_identity_changed', 'source_hash_changed', 'envelope_items_changed', 'envelope_correlation_mismatch', 'nda_identity_mismatch', 'sign_team_mismatch'}:
            workflow.state = 'quarantined'
        elif not workflow.envelope_id and workflow.state == 'creating':
            workflow.state = 'uncertain' if exc.uncertain else 'failed'
        workflow.last_error = exc.code
        workflow.attempts += 1
        workflow.next_attempt_at = timezone.now() + timedelta(seconds=min(300, 15 * 2 ** min(workflow.attempts, 4)))
        workflow.save(update_fields=['state', 'last_error', 'attempts', 'next_attempt_at'])
    except Exception as exc:
        # Do not log exceptions containing remote credential or recipient tokens.
        Workflow.objects.filter(pk=workflow.pk).update(last_error='integration_' + type(exc).__name__[:60], next_attempt_at=timezone.now() + timedelta(seconds=15))
    finally:
        Workflow.objects.filter(pk=workflow.pk).update(lease_until=None)


def sweep(limit=20):
    ids = Workflow.objects.exclude(state__in=TERMINAL).filter(next_attempt_at__lte=timezone.now()).order_by('next_attempt_at').values_list('pk', flat=True)[:limit]
    for workflow_id in list(ids):
        process(workflow_id)
