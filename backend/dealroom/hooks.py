"""One DRF dispatch boundary, independent of view.permission_classes/get_permissions."""
from functools import wraps
from threading import BoundedSemaphore
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.models import APIKey
from .registry import resolve_operation, TIERS, RECIPIENT

RENDER_SEMAPHORE = BoundedSemaphore(1)


def human_staff(request):
    return bool(request.user.is_authenticated and request.user.is_staff and isinstance(request.successful_authenticator, JWTAuthentication) and not isinstance(request.auth, APIKey))


def enforce(view, request):
    from .approvals import gate
    from .policy import guard_recipient
    from .models import KeyScope
    op = resolve_operation(view, request.method)
    if op is None or op['boundary'] == 'denied':
        raise PermissionDenied('Unclassified or disabled operation.')
    request.dealroom_operation = op
    if type(view).__name__ in RECIPIENT or type(view).__module__.startswith('filerequests.'):
        guard_recipient(request, view)
    if op['boundary'] == 'staff' and not (request.user.is_authenticated and request.user.is_staff):
        raise PermissionDenied('Staff access is required.')
    if op['human_only'] and not human_staff(request):
        raise PermissionDenied('This operation requires a human staff JWT, never an API key.')
    if isinstance(request.auth, APIKey):
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and not (type(view).__name__ == 'RoomViewSet' and getattr(view, 'action', None) == 'upload'):
            if request.content_type.split(';', 1)[0].strip().lower() != 'application/json':
                from rest_framework.exceptions import UnsupportedMediaType
                raise UnsupportedMediaType(request.content_type, detail='Agent mutations require application/json; only room upload accepts multipart.')
        if not request.auth.user.is_staff or TIERS.get(request.auth.tier, -1) < TIERS[op['tier']]:
            raise PermissionDenied('Agent key tier does not permit this operation.')
        scope = KeyScope.objects.filter(key=request.auth).first()
        if scope:
            if scope.operations is not None and op['operation_id'] not in scope.operations:
                raise PermissionDenied('Operation outside key scope.')
            ancestor = scope
            seen = {request.auth.pk}
            while ancestor and ancestor.parent_id:
                from django.utils import timezone
                parent = ancestor.parent
                if parent.pk in seen or not parent.user.is_active or (parent.expires_at and parent.expires_at <= timezone.now()):
                    raise PermissionDenied('Parent key is inactive or delegation is cyclic.')
                seen.add(parent.pk)
                ancestor = KeyScope.objects.filter(key=parent).first()
            if scope.rooms is not None or scope.recipient_orgs is not None:
                # Scoped keys are fail-closed until the view supplies an explicit target resolver.
                resolver = getattr(view, 'key_scope_targets', None)
                if not resolver:
                    raise PermissionDenied('This operation cannot resolve restricted key targets.')
                rooms, orgs = resolver(request)
                if (scope.rooms is not None and not set(rooms) <= set(scope.rooms)) or (scope.recipient_orgs is not None and not set(orgs) <= set(scope.recipient_orgs)):
                    raise PermissionDenied('Target outside key scope.')
        gate(request, view, op)


def install():
    if getattr(APIView, '_dealroom_installed', False):
        return
    original_initial, original_dispatch = APIView.initial, APIView.dispatch

    @wraps(original_initial)
    def initial(self, request, *args, **kwargs):
        original_initial(self, request, *args, **kwargs)
        if settings.DEALROOM_ENABLED:
            enforce(self, request)

    @wraps(original_dispatch)
    def dispatch(self, request, *args, **kwargs):
        if not settings.DEALROOM_ENABLED or type(self).__name__ == 'HealthCheckView':
            return original_dispatch(self, request, *args, **kwargs)
        from .activity import record
        from contextlib import nullcontext
        with (nullcontext() if type(self).__name__ == 'OriginalDownloadView' else transaction.atomic()):
            render = type(self).__name__ in {'WatermarkedPageRenderView', 'ShareLinkFileDownloadView'}
            if render:
                RENDER_SEMAPHORE.acquire()
            try:
                response = original_dispatch(self, request, *args, **kwargs)
                auth = getattr(getattr(self, 'request', None), 'auth', None)
                op = getattr(getattr(self, 'request', None), 'dealroom_operation', None)
                if response.status_code >= 400:
                    # API errors should never leave partial mutations. OTP attempts intentionally
                    # return a 200 state=refused so failed attempts commit and cannot be reset.
                    if type(self).__name__ != 'OriginalDownloadView':
                        transaction.set_rollback(True)
                elif isinstance(auth, APIKey) and op:
                    record('agent.action', organization=auth.user.organization, actor=auth, data={'operation_id': op['operation_id'], 'status': response.status_code})
                if response.status_code == 200 and type(self).__name__ in {'WatermarkedPageRenderView', 'ShareLinkFileDownloadView'}:
                    import hashlib
                    from sharelinks.models import IssuedCopy, Viewer
                    from .models import CopyEvidence
                    copy_id = response.get('X-AmForge-Copy-ID')
                    copy = IssuedCopy.objects.select_related('share_link').filter(copy_id=copy_id).first()
                    if copy:
                        member_id = self.request.session.get('dealroom_member', {}).get('member_id')
                        member = Viewer.objects.get(pk=member_id)
                        downloaded = type(self).__name__ == 'ShareLinkFileDownloadView'
                        artifact_hash = hashlib.sha256(response.content).hexdigest()
                        record('document.downloaded' if downloaded else 'document.viewed', organization=copy.share_link.organization, actor=member, room_id=copy.share_link.dataroom_id, target_id=copy.document_id, data={'copy_id':copy_id,'level':'watermarked' if downloaded else 'view','page':self.kwargs.get('page_number'),'artifact_sha256':artifact_hash})
                        if downloaded:
                            CopyEvidence.objects.filter(copy=copy).update(artifact_sha256=artifact_hash)
                        response['X-Dealroom-Copy-ID'] = copy_id
            finally:
                if render:
                    RENDER_SEMAPHORE.release()
        if response.status_code in (401, 403):
            audit_denial(self, response)
        return response

    APIView.initial, APIView.dispatch = initial, dispatch
    APIView._dealroom_installed = True


def audit_denial(view, response):
    """Persist a safe access-attempt fact after the failed mutation has rolled back."""
    from .activity import record
    request = view.request
    actor = request.auth if isinstance(request.auth, APIKey) else request.user
    organization = getattr(request.user, 'organization', None)
    room_id = ''
    slug = getattr(view, 'kwargs', {}).get('slug')
    if slug:
        from sharelinks.models import ShareLink, Viewer
        link = ShareLink.objects.filter(slug=slug).first()
        if link:
            organization, room_id = link.organization, link.dataroom_id
            proof = request.session.get('dealroom_member', {})
            actor = Viewer.objects.filter(pk=proof.get('member_id'), organization=organization).first()
    if organization:
        op = getattr(request, 'dealroom_operation', {})
        data = {'operation_id': op.get('operation_id', ''), 'status': response.status_code}
        record('access.denied', organization=organization, actor=actor or 'anonymous', room_id=room_id, data=data)
        if isinstance(request.auth, APIKey):
            record('agent.action', organization=organization, actor=request.auth, room_id=room_id, data=data)
