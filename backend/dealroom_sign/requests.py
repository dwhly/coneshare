"""Board scope and truthful, nonsensitive request projections."""
from django.conf import settings
from django.db.models import Q, F
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from core.models import APIKey
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
    bindings = set(BoardStaffBinding.objects.filter(board_id=row.board_id, enabled=True,
        send_user__is_active=True).values_list('signer_email', flat=True))
    result = []
    for person in row.workflow.recipients:
        email = person.get('email', '')
        native = projection.get(email.lower(), {})
        role = person.get('role', 'SIGNER')
        result.append({'recipient_id': native.get('id'), 'email': email, 'name': person.get('name'),
            'role': role, 'side': 'ours' if email in bindings else 'theirs',
            'status': 'COPIED' if role == 'CC' else native.get('signingStatus', 'NOT_SIGNED'),
            'read_status': native.get('readStatus'), 'signed_at': native.get('signedAt'), 'sent_at':native.get('sentAt')})
    return result


def list_row(row, request):
    persons = people(row)
    required = [p for p in persons if p['role'] != 'CC']
    work = row.workflow
    return {'id': str(row.pk), 'workflow_id': str(work.pk), 'title': row.title, 'kind': row.kind,
        'state': work.state, 'signed': sum(p['status'] == 'SIGNED' for p in required), 'required': len(required),
        'task': row.task_ref, 'room': {'id': str(row.room_id), 'name': row.room.name} if row.room_id else None,
        'people': persons, 'creator': row.creator.email, 'created_at': row.created_at,
        'completed_at':work.completed_at, 'last_activity_at': work.reconciled_at or row.created_at,
        'needs_you': any(p['email'] == request.user.email and p['status'] != 'SIGNED' for p in required)
            and work.state == 'awaiting_signature'}


def activity(row):
    local = list(Activity.objects.filter(organization=row.workflow.room.organization).filter(
        Q(target_id=str(row.pk)) | Q(data__workflow_id=str(row.workflow_id))))
    result = [{'id': str(a.pk), 'kind': a.event_type, 'at': a.created_at,
               'actor': a.actor_id, 'sha256': a.data.get('sha256'), 'download_kind': a.data.get('kind')}
              for a in local]
    seen = {a.data.get('source_record_id') for a in local}
    for fact in ObservedSignEvent.objects.filter(workflow=row.workflow).exclude(kind='snapshot.fields'):
        if fact.source_id not in seen:
            result.append({'id':fact.source_id,'kind':fact.kind,'at':fact.occurred_at,'source':'sign'})
    return sorted(result, key=lambda item: (item['at'].isoformat() if item['at'] else '', item['id']))


def integrity(row):
    fact = Activity.objects.filter(event_type='fileback.completed', data__workflow_id=str(row.workflow_id)).order_by('-created_at').first()
    return {'source_sha256':row.workflow.source_sha256,
        'seal_valid':fact.data.get('signature_valid') if fact else None,
        'publicly_trusted':fact.data.get('trusted') if fact else None}


def freshness(row):
    at = row.workflow.reconciled_at
    return {'as_of': at or row.created_at, 'stale': not at or (timezone.now()-at).total_seconds() > 90}
