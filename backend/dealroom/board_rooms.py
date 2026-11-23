"""Board-only room reads. All projections are explicit and contain no storage capabilities."""
import re

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from datarooms.models import DataroomDocument
from dealroom_sign.board_auth import BoardProxyAuthentication, HUMAN_VIAS
from dealroom_sign.models import BoardStaffBinding, ExecutedArtifact, NdaPolicy, NdaAcceptance
from documents.models import DocumentVersion
from documents.renderers import get_renderer
from sharelinks.models import ShareLinkAccessGrant, ViewSession, Viewer, NDAAcceptance
from . import hooks
from .models import Activity, BoardRoom, MemberDeny
from .staff_preview import issue_staff_preview

PAGE_SIZE = 50


def board_room_scope(request):
    """Re-read the binding even when authentication has already resolved its identity."""
    if not isinstance(request.successful_authenticator, BoardProxyAuthentication):
        raise PermissionDenied('Board proxy authentication is required.')
    context = getattr(request, 'board_context', {})
    authenticated = getattr(request, 'board_binding', None)
    if context.get('via') not in HUMAN_VIAS or authenticated is None:
        raise PermissionDenied('Human board access is required.')
    binding = BoardStaffBinding.objects.select_related('send_user__organization').filter(
        pk=authenticated.pk, board_id=context.get('board'), login=context.get('login'),
        enabled=True, send_user_id=request.user.pk, send_user__is_active=True,
        send_user__is_staff=True).first()
    if (not binding or not isinstance(binding.room_capabilities, list)
            or 'read' not in binding.room_capabilities
            or any(c not in ('read', 'write') for c in binding.room_capabilities)):
        raise PermissionDenied('Room read capability is required.')
    request.board_binding = binding
    return BoardRoom.objects.filter(board_id=binding.board_id,
        room__organization_id=binding.send_user.organization_id).select_related('room', 'room__roompolicy')


def paginate(queryset, cursor, *, time_field, id_field):
    """Stable time + ID pagination; the cursor must itself belong to the scoped queryset."""
    if cursor:
        anchor = get_object_or_404(queryset, **{id_field: cursor})
        stamp = anchor
        for field in time_field.split('__'):
            stamp = getattr(stamp, field)
        queryset = queryset.filter(Q(**{time_field + '__lt': stamp}) |
                                   Q(**{time_field: stamp, id_field + '__lt': cursor}))
    rows = list(queryset.order_by('-' + time_field, '-' + id_field)[:PAGE_SIZE + 1])
    return rows[:PAGE_SIZE], str(getattr(rows[PAGE_SIZE - 1], id_field)) if len(rows) > PAGE_SIZE else None


def activity_projection(fact):
    return {'id': str(fact.pk), 'event_type': fact.event_type, 'time': fact.created_at,
            'actor_kind': fact.actor_kind, 'actor_id': fact.actor_id, 'target_id': fact.target_id or None}


def room_summary(row):
    policy = getattr(row.room, 'roompolicy', None)
    return {'id': str(row.room_id), 'name': row.room.name, 'board_id': row.board_id,
            'build_state': row.build_state, 'revision': row.revision,
            'lifecycle': policy.status if policy else 'active',
            'archived': bool(policy and policy.status == 'archived'),
            'ever_invited_at': row.ever_invited_at}


def room_detail(row):
    room = row.room
    data = room_summary(row)
    orders = list(room.item_orders.all())
    folder_order = {o.folder_id: o.position for o in orders if o.folder_id}
    item_order = {o.dataroom_document_id: o.position for o in orders if o.dataroom_document_id}
    data['folders'] = [{'folder_id': str(f.pk), 'parent_id': str(f.parent_id) if f.parent_id else None,
                        'name': f.name, 'position': folder_order.get(f.pk)}
                       for f in room.folders.order_by('created_at', 'pk')]
    data['items'] = []
    for item in room.documents.select_related('document').prefetch_related('document__versions').order_by('created_at', 'pk'):
        version = next((v for v in item.document.versions.all() if v.is_primary), None)
        data['items'].append({'item_id': str(item.pk), 'document_id': str(item.document_id),
            'version_id': str(version.pk) if version else None,
            'folder_id': str(item.folder_id) if item.folder_id else None,
            'name': item.name or item.document.name, 'position': item_order.get(item.pk),
            'type': item.document.type, 'lifecycle': 'removed' if item.document.deleted_at else 'active'})
    grants = list(ShareLinkAccessGrant.objects.filter(share_link__dataroom=room)
                  .select_related('viewer_organisation', 'share_link').order_by('created_at', 'pk'))
    data['grants'] = [{'id': str(g.pk), 'email': g.email or None,
        'recipient_org_id': str(g.viewer_organisation_id) if g.viewer_organisation_id else None,
        'recipient_org_name': g.viewer_organisation.name if g.viewer_organisation else None,
        'expires_at': g.expires_at, 'revoked_at': g.revoked_at, 'download_ceiling': g.download_ceiling,
        'link_active': g.share_link.is_active} for g in grants]
    emails = {g.email for g in grants if g.email}
    orgs = {g.viewer_organisation_id for g in grants if g.viewer_organisation_id}
    people = list(Viewer.objects.filter(organization=room.organization)
                  .filter(Q(email__in=emails) | Q(recipient_org_id__in=orgs)).order_by('email'))
    denied = set(MemberDeny.objects.filter(room=room).values_list('member_id', flat=True))
    data['people'] = [{'id': str(p.pk), 'email': p.email, 'name': p.name or None,
                      'disabled_at': p.disabled_at, 'denied': p.pk in denied} for p in people]
    known = {p.email for p in people}
    data['people'] += [{'id': None, 'email': email, 'name': None, 'disabled_at': None, 'denied': False}
                       for email in sorted(emails - known)]
    nda = NdaPolicy.objects.filter(room=room).first()
    data['nda'] = {
        'enabled': bool((nda and nda.enabled) or room.share_links.filter(require_nda=True).exists()),
        'revision': str(nda.revision) if nda else None,
        'acceptances': [{'member_id': a.member_id, 'email': a.member_email,
                         'revision': a.policy_revision, 'accepted_at': a.accepted_at}
                        for a in NdaAcceptance.objects.filter(room=room).order_by('-accepted_at')],
        'legacy_policies': [{'id': str(link.pk), 'enabled': link.require_nda, 'version': link.nda_version}
                            for link in room.share_links.all()],
        'legacy_acceptances': [{'id': str(a.pk), 'version': a.nda_version,
                                'viewer_id': str(a.viewer_id) if a.viewer_id else None,
                                'view_session_id': str(a.view_session_id) if a.view_session_id else None,
                                'accepted_at': a.accepted_at}
                               for a in NDAAcceptance.objects.filter(share_link__dataroom=room)],
    }
    data['activity'] = [activity_projection(a) for a in Activity.objects.filter(
        organization=room.organization, room_id=str(room.pk)).order_by('-created_at', '-pk')[:50]]
    return data


def stored_browser_device(ua):
    if not ua:
        return None, None
    browser = next((name for pattern, name in [
        (r'Edg(?:e|A|iOS)?/', 'Edge'), (r'(?:OPR|Opera)/', 'Opera'),
        (r'(?:Chrome|CriOS)/', 'Chrome'), (r'(?:Firefox|FxiOS)/', 'Firefox'),
        (r'Version/.*Safari/', 'Safari'), (r'(?:MSIE |Trident/)', 'Internet Explorer')]
        if re.search(pattern, ua)), None)
    device = ('Tablet' if re.search(r'iPad|Tablet', ua, re.I) else
              'Mobile' if re.search(r'Mobile|iPhone|Android', ua, re.I) else
              'Desktop' if re.search(r'Windows|Macintosh|X11|Linux', ua, re.I) else None)
    return browser, device


class BoardVisitSerializer(serializers.Serializer):
    id = serializers.CharField()
    time = serializers.DateTimeField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    ip = serializers.IPAddressField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    browser = serializers.CharField(allow_null=True)
    device = serializers.CharField(allow_null=True)
    duration = serializers.IntegerField(allow_null=True)
    pages = serializers.ListField(child=serializers.IntegerField(), allow_null=True)
    downloaded = serializers.BooleanField(allow_null=True)
    activity = serializers.ListField(child=serializers.DictField())


def visit_projection(session, activities):
    visits = list(session.dataroom_visits.all())
    visit_ids = {str(v.pk) for v in visits}
    facts = [a for a in activities if str(a.data.get('view_session_id', '')) == str(session.pk)
             or str(a.data.get('visit_id', '')) in visit_ids]
    views = list(session.page_views.all())
    pages = {v.page_number for v in views}
    pages.update(a.data['page'] for a in facts if type(a.data.get('page')) is int and a.data['page'] > 0)
    browser, device = stored_browser_device(session.user_agent)
    return {'id': str(session.pk), 'time': session.viewed_at, 'email': session.viewer_email or None,
            'ip': session.ip_address or None, 'city': session.city or None, 'country': session.country or None,
            'browser': browser, 'device': device,
            # Legacy zero defaults do not prove recorded zero engagement.
            'duration': session.duration_seconds if session.duration_seconds > 0 else
                        sum(v.duration_seconds for v in views) if views else None,
            'pages': sorted(pages) or None,
            'downloaded': True if (session.downloaded_at or any(v.downloaded_at for v in visits)
                                   or any(a.event_type == 'document.downloaded' for a in facts)) else None,
            'activity': [activity_projection(a) for a in facts]}


def preview_target(request, pk, item_id):
    row = get_object_or_404(board_room_scope(request), room_id=pk)
    item = get_object_or_404(DataroomDocument.objects.select_related('document', 'folder'),
                            pk=item_id, dataroom=row.room,
                            document__organization_id=row.room.organization_id)
    if hooks.is_protected_document(item.document_id) or ExecutedArtifact.objects.filter(
            version__document_id=item.document_id).exists():
        raise PermissionDenied('Use the authorized signature product operation.')
    folder, seen = item.folder, set()
    while folder:
        if folder.pk in seen or folder.dataroom_id != row.room_id or folder.name.casefold() == 'executed':
            raise PermissionDenied('This folder is excluded from room previews.')
        seen.add(folder.pk)
        folder = folder.parent
    if item.document.deleted_at:
        raise PermissionDenied('Removed documents cannot be previewed.')
    version_id = request.query_params.get('version_id')
    if not version_id:
        raise ValidationError('version_id is required.')
    version = get_object_or_404(DocumentVersion, pk=version_id, document=item.document)
    return row, item, version


def preview_state(version, renderer):
    state = renderer.get_effective_render_status(version)
    if state == DocumentVersion.RENDER_READY:
        return {'status': 'ready', 'page_count': version.num_pages or version.pages.count()}
    return {'status': 'failed' if state in (DocumentVersion.RENDER_FAILED, DocumentVersion.RENDER_NOT_APPLICABLE)
            else 'processing', 'page_count': None}


VERSION_PARAM = OpenApiParameter('version_id', OpenApiTypes.STR, required=True)
CURSOR_PARAM = OpenApiParameter('cursor', OpenApiTypes.STR)


class BoardRoomReadViewSet(viewsets.ViewSet):
    authentication_classes = [BoardProxyAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'no-referrer'
        return response

    @extend_schema(parameters=[CURSOR_PARAM], responses=OpenApiTypes.OBJECT)
    def list(self, request):
        rows, cursor = paginate(board_room_scope(request), request.query_params.get('cursor'),
                                time_field='room__created_at', id_field='room_id')
        return Response({'items': [room_summary(row) for row in rows], 'next_cursor': cursor})

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def retrieve(self, request, pk=None):
        return Response(room_detail(get_object_or_404(board_room_scope(request), room_id=pk)))

    @extend_schema(parameters=[CURSOR_PARAM], responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['get'])
    def visits(self, request, pk=None):
        row = get_object_or_404(board_room_scope(request), room_id=pk)
        sessions = ViewSession.objects.filter(share_link__dataroom=row.room).prefetch_related('dataroom_visits', 'page_views')
        rows, cursor = paginate(sessions, request.query_params.get('cursor'), time_field='viewed_at', id_field='id')
        session_ids = [str(s.pk) for s in rows]
        visit_ids = [str(v.pk) for s in rows for v in s.dataroom_visits.all()]
        activities = list(Activity.objects.filter(organization=row.room.organization, room_id=str(row.room_id))
                          .filter(Q(data__view_session_id__in=session_ids) | Q(data__visit_id__in=visit_ids)))
        return Response({'items': BoardVisitSerializer([visit_projection(s, activities) for s in rows], many=True).data,
                         'next_cursor': cursor})

    @extend_schema(parameters=[VERSION_PARAM], responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['get'], url_path=r'documents/(?P<item_id>[^/.]+)/pages')
    def pages(self, request, pk=None, item_id=None):
        row, item, version = preview_target(request, pk, item_id)
        renderer = get_renderer(version)
        if version.render_status == DocumentVersion.RENDER_NOT_GENERATED:
            try:
                renderer.enqueue_render_task(version)
            except Exception:
                return Response({'status': 'failed', 'page_count': None})
        return Response(preview_state(version, renderer))

    @extend_schema(parameters=[VERSION_PARAM], responses={(200, 'image/png'): OpenApiTypes.BINARY})
    @action(detail=True, methods=['get'], url_path=r'documents/(?P<item_id>[^/.]+)/pages/(?P<page>[0-9]+)')
    def page(self, request, pk=None, item_id=None, page=None):
        row, item, version = preview_target(request, pk, item_id)
        renderer = get_renderer(version)
        state = preview_state(version, renderer)
        if state['status'] != 'ready':
            return Response(state, status=409)
        number = int(page)
        if number < 1 or number > state['page_count']:
            return Response({'detail': 'Page not found.'}, status=404)
        hooks.RENDER_SEMAPHORE.acquire()
        try:
            storage_key = renderer.get_page_storage_key(version, number)
            if not storage_key:
                return Response({'detail': 'Page not found.'}, status=404)
            content, copy_id = issue_staff_preview(request.board_binding, row.room, item, version, number, storage_key)
            response = HttpResponse(content, content_type='image/png')
            response['X-Dealroom-Copy-ID'] = copy_id
            return response
        except Exception:
            return Response({'detail': 'Preview is unavailable.'}, status=503)
        finally:
            hooks.RENDER_SEMAPHORE.release()
