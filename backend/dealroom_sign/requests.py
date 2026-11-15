"""Board scope and truthful, nonsensitive request projections."""
from django.conf import settings
from django.db.models import Q, F
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import NotFound, PermissionDenied

from core.models import APIKey, User
from dealroom.models import Activity, KeyScope
from .models import BoardStaffBinding, SignatureRequest, ObservedSignEvent


def board_config(board):
    return getattr(settings, 'BOARD_SIGN_BOARDS', {}).get(board, {})


def request_scope(request, board=None):
    context = getattr(request, 'board_context', None)
    if context:
        if board and board != context['board']:
            raise PermissionDenied('forbidden')
        board = context['board']
        bindings = BoardStaffBinding.objects.filter(pk=request.board_binding.pk, enabled=True,
            send_user=request.user, send_user__is_active=True, send_user__is_staff=True)
    elif isinstance(request.auth, APIKey):
        bindings = BoardStaffBinding.objects.filter(send_user=request.user, enabled=True)
        if board:
            bindings = bindings.filter(board_id=board)
    else:
        raise PermissionDenied('forbidden')
    boards = list(bindings.values_list('board_id', flat=True))
    if not boards:
        raise PermissionDenied('forbidden')
    allowed = Q(pk__in=[])
    # A board assignment is explicit and rechecked; it never broadens legacy staff_room.
    for name in boards:
        cfg = board_config(name)
        allowed |= Q(board_id=name, workflow__owner_id__in=cfg.get('owner_ids', []),
                     workflow__room_id__in=cfg.get('room_ids', []),
                     workflow__owner__signcredential__team_id__in=cfg.get('team_ids', []),
                     workflow__owner__signcredential__enabled=True)
    rows = SignatureRequest.objects.filter(allowed, workflow__room__organization=request.user.organization,
        workflow__source_version__document__organization=request.user.organization,
        workflow__source_version__document__deleted_at__isnull=True).filter(
        Q(room__isnull=True) | Q(room_id=F('workflow__room_id'))).exclude(state='draft')
    if isinstance(request.auth, APIKey):
        scope = KeyScope.objects.filter(key=request.auth).first()
        if scope and scope.rooms is not None:
            rows = rows.filter(workflow__room_id__in=scope.rooms)
        if scope and scope.recipient_orgs not in (None, []):
            # No recipient-organisation mapping is asserted by slice 1.
            rows = rows.none()
    return rows.select_related('workflow__source_version', 'workflow__room', 'room', 'creator')


def scoped_request(request, request_id):
    try:
        row = request_scope(request).filter(pk=request_id).first()
    except (ValueError, TypeError):
        row = None
    if row is None:
        raise NotFound('not_found')
    return row


def people(row):
    projection = {p.get('email', '').lower(): p for p in row.workflow.signer_projection}
    bindings = {email.lower() for email in BoardStaffBinding.objects.filter(board_id=row.board_id, enabled=True,
        send_user__is_active=True).values_list('signer_email', flat=True)}
    result = []
    for person in row.workflow.recipients:
        email = person.get('email', '')
        native = projection.get(email.lower(), {})
        role = person.get('role', 'SIGNER')
        result.append({'recipient_id': native.get('id'), 'email': email, 'name': person.get('name'),
            'role': role, 'side': 'ours' if email.lower() in bindings else 'theirs',
            'status': 'COPIED' if role == 'CC' else native.get('signingStatus', 'NOT_SIGNED'),
            'read_status': native.get('readStatus'), 'signed_at': native.get('signedAt'), 'sent_at':native.get('sentAt')})
    return result


def list_row(row, request):
    persons = people(row)
    required = [p for p in persons if p['role'] != 'CC']
    work = row.workflow
    binding = getattr(request, 'board_binding', None)
    signer_emails = {binding.signer_email.lower()} if binding else {email.lower() for email in
        BoardStaffBinding.objects.filter(send_user=request.user, enabled=True, board_id=row.board_id)
        .values_list('signer_email', flat=True)}
    return {'id': str(row.pk), 'workflow_id': str(work.pk), 'title': row.title, 'kind': row.kind,
        'state': work.state, 'signed': sum(p['status'] == 'SIGNED' for p in required), 'required': len(required),
        'task': row.task_ref, 'room': {'id': str(row.room_id), 'name': row.room.name} if row.room_id else None,
        'people': persons, 'creator': row.creator.email, 'created_at': row.created_at,
        'completed_at':work.completed_at, 'last_activity_at': last_activity_at(row),
        'needs_you': any(p['email'].lower() in signer_emails and p['status'] != 'SIGNED' for p in required)
            and work.state == 'awaiting_signature'}


def event_time(value):
    try:
        at = parse_datetime(value) if isinstance(value, str) else value
        return timezone.make_aware(at) if at and timezone.is_naive(at) else at
    except (ValueError, TypeError):
        return None


def local_activity(row):
    return Activity.objects.filter(organization=row.workflow.room.organization).filter(
        Q(target_id=str(row.pk)) | Q(data__workflow_id=str(row.workflow_id)))


def last_activity_at(row):
    # Reconciliation, import and snapshot timestamps describe our observation, not
    # an action by a signer. In particular, never substitute fetch time for a gap.
    times = list(ObservedSignEvent.objects.filter(workflow=row.workflow)
        .exclude(kind='snapshot.fields').exclude(occurred_at=None).values_list('occurred_at', flat=True))
    for person in row.workflow.signer_projection:
        times.extend(event_time(person.get(key)) for key in ('sentAt', 'openedAt', 'readAt', 'signedAt'))
    for item in local_activity(row):
        if item.data.get('source') == 'sign' or item.data.get('source_record_id'):
            times.append(event_time(item.data.get('occurred_at')))
        elif item.event_type in {'envelope.sent', 'signature.download_requested', 'envelope.cancelled',
                                'envelope.declined', 'envelope.signed', 'envelope.viewed', 'signature.page_viewed'}:
            times.append(item.created_at)
    return max((at for at in times if at), default=row.created_at)


def event_pages(data):
    values = data.get('pages', [data.get('pageNumber', data.get('page'))])
    if not isinstance(values, list):
        values = [values]
    return [int(p) for p in values if isinstance(p, (int, str)) and str(p).isdigit() and int(p) > 0]


def activity(row):
    local = list(local_activity(row))
    facts = list(ObservedSignEvent.objects.filter(workflow=row.workflow).exclude(kind='snapshot.fields'))
    native = {f.source_id: f for f in facts}
    users = {str(u.pk): u for u in User.objects.filter(organization=row.workflow.room.organization,
        pk__in=[a.actor_id for a in local if a.actor_kind == 'staff'])}

    def observed(fact):
        data = fact.payload.get('data', {})
        return {'kind':fact.kind, 'at':fact.occurred_at, 'source':'sign',
            'actor_email':fact.actor_email, 'actor_name':fact.name,
            'recipient_id':fact.recipient_id, 'pages':event_pages(data),
            'error':data.get('error'), 'effect_id':data.get('effect_id'), 'attempt':data.get('attempt'),
            'next_attempt_at':data.get('next_attempt_at'), 'email_type':data.get('emailType'), 'source_kind':fact.payload.get('type'),
            'source_event_ids':[fact.source_id], **({'placement':data.get('placement'),
                'source_sha256':data.get('source_sha256')} if fact.kind == 'placement.resolved' else {})}

    result, seen = [], set()
    for item in local:
        source_id = item.data.get('source_record_id')
        fact = native.get(source_id)
        user = users.get(item.actor_id)
        native_source = item.data.get('source') == 'sign' or source_id
        event = {'id':str(item.pk), 'kind':item.event_type, 'recorded_at':item.created_at,
            'at':event_time(item.data.get('occurred_at')) if native_source else item.created_at,
            'actor':item.actor_id, 'actor_email':item.data.get('email') or (user.email if user else None),
            'actor_name':item.data.get('name') or (user.get_full_name() if user else None),
            'sha256':item.data.get('sha256'), 'download_kind':item.data.get('kind'),
            'pages':event_pages(item.data), 'recipient_id':item.data.get('recipient_id'),
            'related_event_id':item.data.get('audit_id'),
            'source_event_ids':[source_id] if source_id else [str(item.pk)]}
        if fact:
            details = observed(fact)
            event.update({k:v for k,v in details.items() if v is not None})
            seen.add(source_id)
        result.append(event)
    result.extend({'id':f.source_id, **observed(f)} for f in facts if f.source_id not in seen)
    return sorted(result, key=lambda item: (item['at'].isoformat() if item['at'] else '', item['id']))


def integrity(row):
    fact = Activity.objects.filter(event_type='fileback.completed', data__workflow_id=str(row.workflow_id)).order_by('-created_at').first()
    return {'source_sha256':row.workflow.source_sha256,
        'seal_valid':fact.data.get('signature_valid') if fact else None,
        'publicly_trusted':fact.data.get('trusted') if fact else None}


def freshness(row):
    at = row.workflow.reconciled_at
    return {'as_of': at or row.created_at, 'stale': not at or (timezone.now()-at).total_seconds() > 90}
