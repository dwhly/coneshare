"""Board allowlist and short legacy mutation lockout while an import is staged."""
from django.db.models import Q
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from datarooms.models import Dataroom, DataroomDocument
from sharelinks.models import ShareLink, ShareLinkAccessGrant, ShareLinkDataroomSetting
from .models import BoardRoom, OriginalException
from .room_commands import Conflict

READS = {'dealroom_BoardRoomReadViewSet_' + action + '_get' for action in ('list', 'retrieve', 'visits', 'pages', 'page')}
WRITES = {'dealroom_RoomViewSet_' + action + '_post' for action in ('create', 'folders', 'upload', 'imports', 'complete')}


def board_enforce(request, op):
    binding = request.board_binding
    oid = op['operation_id']
    if oid == 'dealroom_sign_NdaPlacementView_endpoint_post':
        if 'read' not in binding.room_capabilities:
            raise PermissionDenied('Room read capability required.')
        return
    if oid not in READS | WRITES or request.board_context['via'] not in {'tailscale', 'cloudflare'}:
        raise PermissionDenied('Board operation requires a human request.')
    capability = 'write' if oid in WRITES else 'read'
    if capability not in binding.room_capabilities or (capability == 'write' and binding.role not in {'writer', 'manager'}):
        raise PermissionDenied('Your Dealroom access changed.')
    if capability == 'write' and not getattr(settings, 'BOARD_ROOM_WRITES_ENABLED', False):
        raise PermissionDenied('Board room writes are not enabled.')


def legacy_lock(view, request):
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    name = type(view).__name__
    if name == 'RoomViewSet' and getattr(view, 'action', '') in {'imports', 'complete'}:
        raise PermissionDenied('Board approval required.')
    pk = view.kwargs.get('pk')
    data = request.data
    ids = set()
    for value in (view.kwargs.get('room_id'), data.get('room'), data.get('room_id'), data.get('dataroom')):
        if isinstance(value, (str, int)) and value:
            ids.add(value)
    if name in {'RoomViewSet', 'DataroomViewSet'} and pk:
        ids.add(pk)
    lookup = {
        'GrantViewSet': (ShareLinkAccessGrant, 'share_link__dataroom_id'),
        'EntryLinkViewSet': (ShareLink, 'dataroom_id'),
        'FilePolicyViewSet': (ShareLinkDataroomSetting, 'share_link__dataroom_id'),
        'OriginalExceptionViewSet': (OriginalException, 'room_id'),
    }
    if name in lookup and pk:
        model, field = lookup[name]
        ids.update(model.objects.filter(pk=pk).values_list(field, flat=True))
    if name == 'DocumentViewSet' and pk:
        ids.update(DataroomDocument.objects.filter(document_id=pk).values_list('dataroom_id', flat=True))
    if name == 'DataroomDocumentViewSet' and pk:
        ids.update(DataroomDocument.objects.filter(pk=pk).values_list('dataroom_id', flat=True))
    # Lock the underlying room, the same lock used by continuation writes.
    for room in Dataroom.objects.select_for_update().filter(pk__in=[x for x in ids if x]).order_by('pk'):
        if BoardRoom.objects.filter(room=room).filter(~Q(build_state='ready') | ~Q(staged_import='')).exists():
            raise Conflict('Room import is in progress; use its approved command.')
