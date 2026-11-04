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
        if not settings.DEALROOM_ENABLED:
            return original_dispatch(self, request, *args, **kwargs)
        from .activity import record
        with transaction.atomic():
            render = type(self).__name__ in {'WatermarkedPageRenderView', 'ShareLinkFileDownloadView', 'OriginalDownloadView'}
            if render:
                RENDER_SEMAPHORE.acquire()
            try:
                response = original_dispatch(self, request, *args, **kwargs)
                auth = getattr(getattr(self, 'request', None), 'auth', None)
                op = getattr(getattr(self, 'request', None), 'dealroom_operation', None)
                if response.status_code >= 400:
                    # API errors should never leave partial mutations. OTP attempts intentionally
                    # return a 200 state=refused so failed attempts commit and cannot be reset.
                    transaction.set_rollback(True)
                elif isinstance(auth, APIKey) and op:
                    record('agent.action', organization=auth.user.organization, actor=auth, data={'operation_id': op['operation_id'], 'status': response.status_code})
                return response
            finally:
                if render:
                    RENDER_SEMAPHORE.release()

    APIView.initial, APIView.dispatch = initial, dispatch
    APIView._dealroom_installed = True
