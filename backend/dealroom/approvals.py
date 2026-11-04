import hashlib
import json
from datetime import timedelta
from django.db import transaction
from django.urls import resolve
from django.utils import timezone
from django.core.mail import send_mail
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate
from core.models import APIKey
from .models import AccessApproval, Drift
from .registry import widens_access
from .activity import record
from .brand import load_brand


class PendingApproval(APIException):
    status_code = 202
    default_code = 'pending_approval'


def digest(method, path, payload):
    return hashlib.sha256(json.dumps([method, path, payload], sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def gate(request, view, operation):
    if request.method in ('GET', 'HEAD', 'OPTIONS') or operation.get('widens_access') is False:
        return
    if hasattr(view, 'validate_approval'):
        view.validate_approval(request)
    payload = dict(request.data)
    before = {}
    if hasattr(view, 'approval_before'):
        before = view.approval_before()
    elif getattr(view, 'kwargs', {}).get('pk') and hasattr(view, 'get_object'):
        before = dict(view.get_serializer(view.get_object()).data)
    if not widens_access(operation, before, payload):
        return
    approved = getattr(request._request, '_dealroom_approval', None)
    payload_hash = digest(request.method, request.path, payload)
    if approved and approved.payload_hash == payload_hash and approved.agent_key_id == request.auth.pk and approved.status == 'executing':
        return
    if any(k.lower() in {'password', 'secret', 'token', 'raw_key'} for k in payload):
        raise ValidationError('Sensitive payloads require direct staff administration.')
    approval = AccessApproval.objects.create(agent_key=request.auth, operation_id=operation['operation_id'], method=request.method, path=request.path, payload=payload, payload_hash=payload_hash, expires_at=timezone.now() + timedelta(hours=24))
    Drift.objects.create(approval=approval)
    record('approval.requested', organization=request.user.organization, actor=request.auth, target_id=approval.pk, data={'operation_id': operation['operation_id']})
    record('drift.detected', organization=request.user.organization, actor=request.auth, target_id=approval.pk, data={'rule': 'access_approval_required'})
    def notify():
        send_mail(f'{load_brand()["name"]}: access approval required', f'Approval {approval.pk} awaits a human staff decision. Operation: {approval.operation_id}', load_brand()['email_sender'], [request.user.email], fail_silently=True)
    transaction.on_commit(notify)
    error = PendingApproval()
    error.detail = {'status': 'pending_approval', 'approval_id': str(approval.pk)}
    raise error


def execute(approval, staff_request):
    from .hooks import human_staff
    if not human_staff(staff_request):
        raise PermissionDenied('Human staff JWT required.')
    if approval.status != 'pending_approval' or approval.expires_at <= timezone.now():
        raise ValidationError('Approval is expired or already decided.')
    key = approval.agent_key
    if not key.user.is_active or (key.expires_at and key.expires_at <= timezone.now()):
        raise PermissionDenied('Requesting key is inactive.')
    if digest(approval.method, approval.path, approval.payload) != approval.payload_hash:
        raise PermissionDenied('Approval payload changed.')
    approval.status = 'executing'
    approval.approved_by = staff_request.user
    approval.save(update_fields=['status', 'approved_by'])
    match = resolve(approval.path)
    req = APIRequestFactory().generic(approval.method, approval.path, json.dumps(approval.payload), content_type='application/json')
    req._dealroom_approval = approval
    req.resolver_match = match
    force_authenticate(req, user=key.user, token=key)
    result = match.func(req, *match.args, **match.kwargs)
    if result.status_code >= 400 or result.status_code == 202:
        raise ValidationError({'execution_failed': getattr(result, 'data', {}), 'http_status': result.status_code})
    approval.status = 'approved'
    # Never persist newly minted secret key material in an approval or activity record.
    response = dict(result.data) if isinstance(result.data, dict) else {'result': result.data}
    approval.result = {k: v for k, v in response.items() if k not in {'key', 'raw_key'}}
    approval.save(update_fields=['status', 'result'])
    Drift.objects.filter(approval=approval).update(resolved_at=timezone.now())
    record('approval.approved', organization=staff_request.user.organization, actor=staff_request.user, target_id=approval.pk)
    return response
