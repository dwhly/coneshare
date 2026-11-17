"""Durable leased execution and serialized reconciliation/publication."""
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from . import room_return
from .nda_template import recipient_fields
from .client import Documenso, SignError
from .evidence import ingest, snapshot_fields, instant
from .legacy import legacy_request
from .models import NdaAcceptance, ObservedSignEvent, SignCredential, SignatureRequest, Workflow
from .placement import place, to_native_fields, validate_result
from .presentation import clean_title, requester_snapshot
from .storage import publish, source_bytes, stage, verify_seal
from .validation import digest, request_digest, validate_recipients

TERMINAL = {'done', 'cancelled', 'declined', 'failed', 'quarantined'}
AUDIT_KINDS = {
    'DOCUMENT_SENT': 'envelope.sent', 'DOCUMENT_OPENED': 'envelope.viewed',
    'DOCUMENT_VIEWED': 'envelope.viewed', 'DOCUMENT_RECIPIENT_COMPLETED': 'envelope.signed',
    'DOCUMENT_COMPLETED': 'envelope.completed', 'DOCUMENT_REJECTED': 'envelope.declined',
    'DOCUMENT_CANCELLED': 'envelope.cancelled',
    'DOCUMENT_RECIPIENT_REJECTED': 'envelope.declined',
    'DOCUMENT_RECIPIENT_EXPIRED': 'envelope.expired',
    'EMAIL_SENT': 'native_email.alert',
}


def record_fact(workflow, kind, source_id, data=None, *, actor=None):
    from dealroom.activity import record
    local = kind.startswith(('signer.', 'mail.', 'signing_deadline.', 'native_email.', 'release.', 'placement.'))
    defaults = {'occurred_at': instant((data or {}).get('occurred_at')) or timezone.now(),
        'recipient_id': (data or {}).get('recipient_id'), 'payload': {'data': data or {}}} if local else {}
    _, created = ObservedSignEvent.objects.get_or_create(workflow=workflow, source_id=str(source_id), kind=kind, defaults=defaults)
    if created:
        recipient_event = kind in {'envelope.viewed', 'envelope.signed', 'nda.signed'}
        actor = (workflow.member_id or 'sign:' + digest(str((data or {}).get('email', '')).encode())[:50]) if recipient_event else (actor or workflow.owner)
        record(kind, organization=workflow.room.organization, actor=actor, actor_kind='recipient' if recipient_event else 'staff',
               room_id=workflow.room_id, target_id=workflow.envelope_id or str(workflow.pk),
               data={'workflow_id': str(workflow.pk), 'member_id': workflow.member_id, 'source': 'sign', 'source_record_id': str(source_id), **(data or {})})


def command(*, owner, room, version, recipients, idempotency_key, purpose='room_document',
            member=None, policy=None, board_id=None, task_ref=None, requester=None, title=None, placement=None):
    automatic = placement == 'auto' or (placement is None and isinstance(recipients, list) and all(not r.get('fields') for r in recipients))
    if not idempotency_key or len(idempotency_key) > 200:
        raise ValidationError('An idempotency key of at most 200 characters is required.')
    metadata = {'placement': 'auto'} if automatic else {}
    if requester is not None or title is not None:
        if not board_id or purpose != 'room_document':
            raise ValidationError('Sender metadata requires a board document request.')
        if requester is not None:
            requester = requester_snapshot(requester)
            metadata['requester'] = requester
        if title is not None:
            title = clean_title(title)
            metadata['title'] = title
    existing = Workflow.objects.filter(owner=owner, idempotency_key=idempotency_key).first()
    if existing:
        normalized = validate_recipients(recipients, None, page_count=500, automatic=automatic, trusted_nda=purpose == 'nda')
        data = {'room': str(room.pk), 'version': str(version.pk), 'sha256': existing.source_sha256,
                'recipients': normalized, 'purpose': purpose, 'member': str(member.pk) if member else '',
                'policy': str(policy.revision) if policy else ''}
        if board_id:
            data.update(board_id=board_id, task_ref=task_ref)
        data.update(metadata)
        if request_digest(data) != existing.request_sha256 or (member and existing.member_email != member.email.strip().lower()) or (policy and policy.source_sha256 != existing.source_sha256):
            raise ValidationError('Idempotency key already used with different inputs.')
        if board_id:
            with transaction.atomic():
                legacy_request(existing, board_id, task_ref, requester=requester, title=title)
        return existing
    pdf = source_bytes(version)
    recipients = validate_recipients(recipients, pdf, automatic=automatic, trusted_nda=purpose == 'nda')
    if purpose == 'nda':
        if not member or len(recipients) != 1 or recipients[0]['email'] != member.email.strip().lower():
            raise ValidationError('NDA signer must match the verified member.')
        if not policy or digest(pdf) != policy.source_sha256:
            raise ValidationError('NDA source revision changed.')
    data = {'room': str(room.pk), 'version': str(version.pk), 'sha256': digest(pdf),
            'recipients': recipients, 'purpose': purpose,
            'member': str(member.pk) if member else '', 'policy': str(policy.revision) if policy else ''}
    if board_id:
        data.update(board_id=board_id, task_ref=task_ref)
    data.update(metadata)
    fingerprint = request_digest(data)
    analysis = None
    if automatic:
        analysis = place(pdf, recipients)
        if analysis['status'] != 'placed':
            raise PlacementRequired(analysis)
        recipients = [dict(r, fields=to_native_fields(analysis, r['email'])) for r in recipients]
        recipients = validate_recipients(recipients, pdf, trusted_placement=True)
    command_id = uuid.uuid4()
    with transaction.atomic():
        workflow, created = Workflow.objects.get_or_create(owner=owner, idempotency_key=idempotency_key, defaults={
            'id': command_id, 'room': room, 'request_sha256': fingerprint, 'purpose': purpose,
            'member_id': str(member.pk) if member else '', 'member_email': member.email.strip().lower() if member else '',
            'policy_revision': str(policy.revision) if policy else '', 'source_version': version,
            'source_sha256': digest(pdf), 'recipients': recipients, 'title': title or version.document.name,
            'external_id': f'dealroom:{getattr(settings, "SIGN_DEPLOYMENT_ID", "chief")}:{"auto" if automatic else "manual"}:{command_id}',
        })
        if workflow.request_sha256 != fingerprint:
            raise ValidationError('Idempotency key already used with different inputs.')
        if board_id:
            legacy_request(workflow, board_id, task_ref, requester=requester, title=title)
        if created:
            room_return.bind(workflow)
        if created and analysis:
            record_fact(workflow, 'placement.resolved', 'placement:' + workflow.source_sha256,
                        {'source_sha256': workflow.source_sha256, 'recipients_sha256': request_digest(recipients),
                         'placement': analysis})
    return workflow


class PlacementRequired(Exception):
    def __init__(self, result):
        self.result = {'status': 'needs_sender', 'reason': result['reason'],
                       'suggestions': result['fields'], 'placement_status': result['status'],
                       'model': result['model'], 'reason_code': result.get('reason_code', 'placement_review')}
        super().__init__(result['reason'])


def check_placement(workflow):
    fact = ObservedSignEvent.objects.filter(workflow=workflow, kind='placement.resolved').first()
    if not fact and workflow.external_id.startswith('dealroom:') and ':manual:' not in workflow.external_id:
        raise SignError('placement_evidence_missing')
    if fact:
        data = fact.payload.get('data', {})
        analysis = data.get('placement', {})
        if (data.get('source_sha256') != workflow.source_sha256
                or data.get('recipients_sha256') != request_digest(workflow.recipients)
                or analysis.get('status') != 'placed'
                or not validate_result(analysis, workflow.recipients)
                or any(to_native_fields(analysis, r['email']) != r['fields'] for r in workflow.recipients)):
            raise SignError('placement_evidence_changed')


def return_url(workflow):
    from .recipient_proxy import origin
    return origin() + '/s/return/' + str(workflow.pk)


def envelope_meta(workflow):
    """Room context Sign can show (spec: dealroom-shell.md §4) and the Fleet Dealroom email subject.
    The signer's name is already the recipient name (the verified room member's name for NDAs)."""
    title = workflow.title[:-4] if workflow.title.lower().endswith('.pdf') else workflow.title
    meta = {'subject': f'Fleet Dealroom: please sign {title}'[:254], 'dateFormat': 'yyyy-MM-dd'}
    if return_url(workflow):
        meta['redirectUrl'] = return_url(workflow)
    return meta


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
    check_placement(workflow)
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
            envelope_id = client.create(workflow, pdf, meta=envelope_meta(workflow))
            # Persist response before any second remote request; ambiguous create is never replayed.
            workflow.envelope_id = envelope_id
            workflow.save(update_fields=['envelope_id'])
            adopt(workflow, client, envelope_id)
    envelope = client.get(workflow.envelope_id)
    if not workflow.item_ids:
        envelope = adopt(workflow, client, workflow.envelope_id)
    validate_envelope(workflow, envelope)
    if workflow.state == 'draft' and envelope['status'] == 'DRAFT':
        from .counterparty import keyed_hash, sender_snapshot
        keyed_hash('link', b'pre-distribute-check')
        sender_snapshot(workflow)
        def mark_attempted():
            workflow.state = 'distributing'
            workflow.save(update_fields=['state'])
        client.distribute(workflow.envelope_id, external_id=workflow.external_id,
            redirect_url=return_url(workflow), before_distribute=mark_attempted)
        envelope = client.get(workflow.envelope_id)
        validate_envelope(workflow, envelope)
    if envelope['status'] == 'DRAFT':
        raise SignError('distribution_outcome_uncertain', uncertain=True)
    if workflow.state == 'distributing':
        client.verify_release(envelope)
    return reconcile(workflow, client, envelope)


def reconcile(workflow, client, envelope=None):
    with transaction.atomic():
        locked = Workflow.objects.select_for_update().select_related('owner', 'room__organization', 'source_version').get(pk=workflow.pk)
        return _reconcile_locked(locked, client, envelope)


def observe_native_mail(workflow, rows):
    for fact in rows:
        if fact.get('type') == 'EMAIL_SENT' and fact.get('id'):
            record_fact(workflow, 'native_email.alert', fact['id'])


def _reconcile_locked(workflow, client, envelope=None):
    audit = client.audit(workflow.envelope_id)
    audit_rows = audit if isinstance(audit, list) else audit.get('data', audit.get('logs', []))
    if workflow.state == 'done':
        observe_native_mail(workflow, audit_rows)
        return workflow
    envelope = envelope or client.get(workflow.envelope_id)
    validate_envelope(workflow, envelope)
    recipients = envelope['recipients']
    projection = [{k: r.get(k) for k in ('id', 'email', 'role', 'signingStatus', 'signedAt', 'readStatus', 'sentAt')} for r in recipients]
    status = envelope['status']
    if workflow.purpose == 'nda':
        if len(recipients) != 1 or recipients[0]['email'].strip().lower() != workflow.member_email:
            raise SignError('nda_identity_mismatch')
        workflow.signing_token = recipients[0].get('token', '')
    completion_id = next((f['id'] for f in audit_rows if f.get('type') == 'DOCUMENT_COMPLETED' and f.get('id')), None)
    staged = []
    seal = None
    if status == 'COMPLETED':
        for item_id in workflow.item_ids:
            original = client.pdf(f'envelope/item/{item_id}/download', params={'version': 'original'})
            if digest(original) != workflow.source_sha256:
                raise SignError('source_hash_changed')
        if not envelope.get('completedAt') or any(r.get('signingStatus') != 'SIGNED' for r in recipients if r.get('role') != 'CC'):
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
            for fact in audit_rows:
                if fact.get('type') == 'EMAIL_SENT' and fact.get('id'):
                    record_fact(locked, 'native_email.alert', fact['id'])
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
        ingest(workflow, audit_rows)
        SignatureRequest.objects.filter(workflow=workflow).update(audit_complete=True, audit_as_of=timezone.now(), state=workflow.state)
        if staged:
            publish(workflow, staged)
            for item in staged:
                if item["kind"] == "sealed_pdf":
                    snapshot_fields(workflow, item["sha256"], item["item_id"], envelope)
            workflow.completed_at = timezone.now()
            if workflow.purpose == 'nda':
                NdaAcceptance.objects.get_or_create(room=workflow.room, member_id=workflow.member_id,
                    policy_revision=workflow.policy_revision, defaults={'member_email': workflow.member_email, 'workflow': workflow})
                record_fact(workflow, 'nda.signed', completion_id, {'email': workflow.member_email})
            record_fact(workflow, 'fileback.completed', completion_id, seal)
        elif status == 'PENDING':
            record_fact(workflow, 'nda.sent' if workflow.purpose == 'nda' else 'envelope.sent', f'sent:{workflow.pk}')
        workflow.save(update_fields=['source_status', 'signer_projection', 'reconciled_at',
            'state', 'signing_token', 'completed_at'])
        from .counterparty import provision
        from .counterparty_mail import enqueue, enqueue_requester
        from .recipient_proxy import eligible
        release_time = next((instant(f.get('createdAt')) for f in audit_rows if f.get('type') == 'DOCUMENT_SENT'), None)
        for access in provision(workflow, envelope, released_at=release_time):
            if status == 'PENDING' and eligible(access, envelope):
                enqueue(access, 'invitation', 'release:' + access.revision)
            elif staged and access.completed_at:
                enqueue(access, 'fully_signed', completion_id)
        if staged:
            enqueue_requester(workflow, completion_id)
    return workflow


def watchable_workflows(now):
    # Late native mail is watched for one day; active signing always takes priority.
    cutoff = now - timedelta(days=1)
    return Workflow.objects.exclude(state__in=TERMINAL - {'done'}).filter(
        ~Q(state='done') | Q(completed_at__gte=cutoff) |
        Q(completed_at__isnull=True, created_at__gte=cutoff))


def process(workflow_id):
    now = timezone.now()
    # Long enough for bounded remote calls; CAS prevents concurrent webhook/poll runners.
    claimed = watchable_workflows(now).filter(pk=workflow_id, next_attempt_at__lte=now).filter(
        Q(lease_until__isnull=True) | Q(lease_until__lt=now)).update(lease_until=now + timedelta(minutes=5))
    if not claimed:
        return
    workflow = Workflow.objects.select_related('owner', 'room__organization', 'source_version__document').get(pk=workflow_id)
    try:
        credential = SignCredential.objects.get(owner=workflow.owner, enabled=True)
        with Documenso(credential) as client:
            if workflow.state == 'done':
                observe_native_mail(workflow, client.audit(workflow.envelope_id).get('data', []))
            else:
                execute(workflow, client)
        workflow.refresh_from_db()
        Workflow.objects.filter(pk=workflow.pk).update(last_error='',
            next_attempt_at=timezone.now()+timedelta(seconds=900 if workflow.state == 'done' else 15))
    except SignError as exc:
        workflow.refresh_from_db()
        if exc.code in {'sealed_bytes_conflict', 'duplicate_external_id', 'signer_identity_changed', 'source_hash_changed', 'envelope_items_changed', 'envelope_correlation_mismatch', 'nda_identity_mismatch', 'sign_team_mismatch', 'release_mail_settings_mismatch', 'placement_evidence_changed', 'placement_evidence_missing'}:
            workflow.state = 'quarantined'
        elif not workflow.envelope_id and workflow.state == 'creating':
            workflow.state = 'uncertain' if exc.uncertain else 'failed'
        if workflow.state != 'done':
            record_fact(workflow, 'release.error', uuid.uuid4(), {'error': exc.code})
        workflow.last_error = exc.code
        workflow.attempts += 1
        workflow.next_attempt_at = timezone.now() + timedelta(seconds=900 if workflow.state == 'done' else min(300, 15 * 2 ** min(workflow.attempts, 4)))
        workflow.save(update_fields=['state', 'last_error', 'attempts', 'next_attempt_at'])
    except Exception as exc:
        # Do not log exceptions containing remote credential or recipient tokens.
        workflow.refresh_from_db()
        if workflow.state != 'done':
            record_fact(workflow, 'release.error', uuid.uuid4(), {'error': 'integration_' + type(exc).__name__[:60]})
        workflow.attempts += 1
        Workflow.objects.filter(pk=workflow.pk).update(attempts=workflow.attempts,
            last_error='integration_' + type(exc).__name__[:60],
            next_attempt_at=timezone.now() + timedelta(seconds=900 if workflow.state == 'done' else min(300, 15 * 2 ** min(workflow.attempts, 4))))
    finally:
        Workflow.objects.filter(pk=workflow.pk).update(lease_until=None)


def sweep(limit=20):
    ids = watchable_workflows(timezone.now()).filter(next_attempt_at__lte=timezone.now()).annotate(
        watch_priority=Case(When(state='done', then=Value(1)), default=Value(0), output_field=IntegerField())
    ).order_by('watch_priority', 'next_attempt_at').values_list('pk', flat=True)[:limit]
    for workflow_id in list(ids):
        process(workflow_id)
    from .storage import recover_previews
    recover_previews()
    from .counterparty_mail import drain
    drain(limit)


def reset_nda(workflow):
    """Serialize reset with member start and leases; never replace a live signer token."""
    from .models import NdaPolicy
    from sharelinks.models import Viewer
    with transaction.atomic():
        policy = NdaPolicy.objects.select_for_update().get(room=workflow.room)
        work = Workflow.objects.select_for_update().get(pk=workflow.pk)
        latest = Workflow.objects.filter(room=work.room, purpose='nda', member_id=work.member_id,
            policy_revision=work.policy_revision).order_by('-created_at').first()
        if latest.pk != work.pk:
            return latest  # retry of a successful reset
        if work.state not in {'failed', 'quarantined', 'distributing', 'uncertain', 'awaiting_seal', 'cancelled', 'declined'}:
            raise ValidationError('Only failed or stuck NDA workflows can be reset.')
        if work.lease_until and work.lease_until > timezone.now():
            raise ValidationError('Workflow is being reconciled. Retry after its lease expires.')
        if str(policy.revision) != work.policy_revision:
            raise ValidationError('The NDA policy has changed; start its current revision.')
        member = Viewer.objects.get(pk=work.member_id, email=work.member_email)
        fields = recipient_fields(policy, member)
        credential = SignCredential.objects.get(owner=work.owner, enabled=True)
        with Documenso(credential) as client:
            ids = [work.envelope_id] if work.envelope_id else [e['id'] for e in client.find(work.external_id)]
            if len(ids) > 1:
                raise SignError('duplicate_external_id')
            for envelope_id in ids:
                client.cancel(envelope_id, work.external_id)
        generation = Workflow.objects.filter(room=work.room, purpose='nda', member_id=work.member_id,
            policy_revision=work.policy_revision).count()
        replacement = command(owner=work.owner, room=work.room, version=policy.source_version,
            recipients=[{'email': member.email, 'name': member.name,
                         'company': member.recipient_org.name if member.recipient_org else '',
                         'fields': fields}], placement='sender',
            idempotency_key=f'nda:{work.room_id}:{member.pk}:{policy.revision}:g{generation}',
            purpose='nda', member=member, policy=policy)
        work.state = 'cancelled'
        work.signing_token = ''
        work.save(update_fields=['state', 'signing_token'])
        record_fact(work, 'nda.reset', str(replacement.pk), {'replacement_id': str(replacement.pk)})
        return replacement
