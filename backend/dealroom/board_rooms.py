"""Board-only room reads. All projections are explicit and contain no storage capabilities."""
import re

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from core.models import User
from datarooms.models import DataroomDocument
from dealroom_sign.board_auth import BoardProxyAuthentication, HUMAN_VIAS
from dealroom_sign.models import BoardStaffBinding, ExecutedArtifact, NdaPolicy, NdaAcceptance
from documents.models import DocumentVersion
from documents.renderers import get_renderer
from sharelinks.models import ShareLinkAccessGrant, ViewSession, Viewer, NDAAcceptance, DataroomVisit
from . import hooks
from .models import Activity, BoardRoom, MemberDeny, RoomCommandReceipt
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


# Only these events belong in the room feed. Audit-only and unknown events stay private.
ACTIVITY_PHRASES = {
    'document.uploaded': 'uploaded', 'document.viewed': 'viewed',
    'document.downloaded': 'downloaded', 'document.removed': 'removed',
    'document.restored': 'restored', 'room.updated': 'updated the room',
    'room.created': 'created the room', 'room.archived': 'archived the room',
    'room.restored': 'restored the room', 'board.room.adopted': 'added the room to the board',
    'board.room.unadopted': 'removed the room from the board',
    'invitation.sent': 'sent an invitation', 'member.denied': 'removed access',
    'member.restored': 'restored access', 'nda.accepted': 'accepted the NDA',
    'room.visited': 'visited the room',
}


def staff_name(user):
    return (user.name or '').strip() or user.email


def excluded_folder(folder, room_id):
    seen = set()
    while folder:
        if folder.pk in seen or folder.dataroom_id != room_id or folder.name.casefold() == 'executed':
            return True
        seen.add(folder.pk)
        folder = folder.parent
    return False


def excluded_item(item):
    return (item.document.organization_id != item.dataroom.organization_id
            or excluded_document(item.document_id)
            or excluded_folder(item.folder, item.dataroom_id))


def excluded_document(document_id):
    return (hooks.is_protected_document(document_id)
            or ExecutedArtifact.objects.filter(version__document_id=document_id).exists())


def visible_items(room):
    return [item for item in room.documents.select_related('document', 'folder', 'dataroom')
            .prefetch_related('document__versions').order_by('created_at', 'pk') if not excluded_item(item)
            and not any(v.metadata.get('board_import_purpose') == 'nda' for v in item.document.versions.all())]


def activity_projection(fact):
    if fact.event_type not in ACTIVITY_PHRASES:
        return None
    sessions = ViewSession.objects.filter(share_link__dataroom_id=fact.room_id,
                                          share_link__dataroom__organization=fact.organization)
    data = fact.data if isinstance(fact.data, dict) else {}
    session = sessions.filter(pk=data.get('view_session_id')).first() if data.get('view_session_id') else None
    visit = DataroomVisit.objects.filter(pk=data.get('visit_id'), view_session__in=sessions).first() if data.get('visit_id') else None
    if session is None and visit:
        session = visit.view_session
    actor = None
    if fact.actor_kind == 'staff':
        user = User.objects.filter(pk=fact.actor_id, organization=fact.organization).first()
        actor = staff_name(user) if user else None
    elif fact.actor_kind in ('member', 'visitor'):
        viewer = Viewer.objects.filter(pk=fact.actor_id, organization=fact.organization).first()
        actor = session.viewer_email if session else viewer.email if viewer else None
    elif fact.actor_kind in ('operator', 'agent'):
        actor = {'operator': 'Operator', 'agent': 'Agent key'}[fact.actor_kind]
    document = None
    if fact.event_type.startswith('document.') and fact.target_id:
        item = DataroomDocument.objects.select_related('document', 'folder', 'dataroom').filter(
            dataroom_id=fact.room_id, document_id=fact.target_id, dataroom__organization=fact.organization).first()
        if excluded_item(item) if item else excluded_document(fact.target_id):
            return None
        document = (item.name or item.document.name) if item else None
    return {'id': str(fact.pk), 'event_type': fact.event_type, 'at': fact.created_at,
            'actor': actor or None, 'phrase': ACTIVITY_PHRASES[fact.event_type],
            'document': document, 'view_session_id': str(session.pk) if session else None,
            'visit_id': str(visit.pk) if visit else None}


def room_activity(room):
    facts = Activity.objects.filter(organization=room.organization, room_id=str(room.pk),
        event_type__in=ACTIVITY_PHRASES).order_by('-created_at', '-pk')[:50]
    events = [event for fact in facts if (event := activity_projection(fact)) is not None]
    # A stored ViewSession itself proves a visit, even where legacy capture wrote no Activity.
    sessions = ViewSession.objects.filter(share_link__dataroom=room).order_by('-viewed_at', '-pk')[:50]
    for session in sessions:
        events.append({'id': 'visit-' + str(session.pk), 'event_type': 'room.visited',
            'at': session.viewed_at, 'actor': session.viewer_email or None,
            'phrase': ACTIVITY_PHRASES['room.visited'], 'document': None,
            'view_session_id': str(session.pk), 'visit_id': None})
    return sorted(events, key=lambda a: (a['at'], a['id']), reverse=True)[:50]


def room_people(room, grants):
    emails = {g.email for g in grants if g.email}
    orgs = {g.viewer_organisation_id for g in grants if g.viewer_organisation_id}
    people = list(Viewer.objects.filter(organization=room.organization)
                  .filter(Q(email__in=emails) | Q(recipient_org_id__in=orgs)).order_by('email'))
    denied = set(MemberDeny.objects.filter(room=room).values_list('member_id', flat=True))
    result = [{'id': str(p.pk), 'email': p.email, 'name': p.name or None,
               'disabled_at': p.disabled_at, 'denied': p.pk in denied} for p in people]
    known = {p.email for p in people}
    return result + [{'id': None, 'email': email, 'name': None, 'disabled_at': None, 'denied': False}
                     for email in sorted(emails - known)]


def room_summary(row):
    policy = getattr(row.room, 'roompolicy', None)
    activity = room_activity(row.room)
    last = activity[0] if activity else None
    phrase = ' '.join(filter(None, [last['actor'], last['phrase'], last['document']])) if last else None
    if last and not last['actor']:
        phrase = phrase[:1].upper() + phrase[1:]
    return {'document_count': len(visible_items(row.room)),
            'people_count': len(room_people(row.room, ShareLinkAccessGrant.objects.filter(share_link__dataroom=row.room))),
            'last_activity': {'at': last['at'], 'phrase': phrase} if last else None,
            'id': str(row.room_id), 'name': row.room.name, 'board_id': row.board_id,
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
    data['folders'] = [{'id': str(f.pk), 'parent_id': str(f.parent_id) if f.parent_id else None,
                        'name': f.name, 'order': folder_order.get(f.pk)}
                       for f in room.folders.order_by('created_at', 'pk') if not excluded_folder(f, room.pk)]
    data['items'] = []
    for item in visible_items(room):
        version = next((v for v in item.document.versions.all() if v.is_primary), None)
        data['items'].append({'item_id': str(item.pk), 'document_id': str(item.document_id),
            'version_id': str(version.pk) if version else None,
            'folder_id': str(item.folder_id) if item.folder_id else None,
            'name': item.name or item.document.name, 'order': item_order.get(item.pk),
            'type': item.document.type, 'lifecycle': 'removed' if item.document.deleted_at else 'active'})
    grants = list(ShareLinkAccessGrant.objects.filter(share_link__dataroom=room)
                  .select_related('viewer_organisation', 'share_link').order_by('created_at', 'pk'))
    data['grants'] = [{'id': str(g.pk), 'email': g.email or None,
        'recipient_org_id': str(g.viewer_organisation_id) if g.viewer_organisation_id else None,
        'recipient_org_name': g.viewer_organisation.name if g.viewer_organisation else None,
        'expires_at': g.expires_at, 'revoked_at': g.revoked_at, 'download_ceiling': g.download_ceiling,
        'link_active': g.share_link.is_active} for g in grants]
    data['people'] = room_people(room, grants)
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
    if row.draft_id or row.staged_import:
        data['staged_import'] = row.staged_import or None
        approved = RoomCommandReceipt.objects.filter(room=room, operation='create').first()
        data['access'] = approved.approved_manifest['access'] if approved else {'download_ceiling':'none','expires_at':None}
        for item in data['items']:
            version = DocumentVersion.objects.filter(pk=item['version_id']).first()
            item['sha256'] = version.metadata.get('source_sha256') if version else None
            item['status'] = preview_state(version, get_renderer(version))['status'] if version else 'failed'
    data['activity'] = room_activity(room)
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
    at = serializers.DateTimeField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    ip = serializers.IPAddressField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    browser = serializers.CharField(allow_null=True)
    device = serializers.CharField(allow_null=True)
    duration_seconds = serializers.IntegerField(allow_null=True)
    pages = serializers.ListField(child=serializers.IntegerField(), allow_null=True)
    downloaded = serializers.BooleanField(allow_null=True)
    activity = serializers.ListField(child=serializers.DictField())


def visit_projection(session, activities):
    all_visits = list(session.dataroom_visits.all())
    visit_ids = {str(v.pk) for v in all_visits}
    all_facts = [a for a in activities if str(a.data.get('view_session_id', '')) == str(session.pk)
             or str(a.data.get('visit_id', '')) in visit_ids]
    excluded_visits = {v.pk for v in all_visits
                       if (v.dataroom_document and excluded_item(v.dataroom_document))
                       or (v.dataroom_folder and excluded_folder(v.dataroom_folder, session.share_link.dataroom_id))}
    visits = [v for v in all_visits if v.pk not in excluded_visits]
    projected = [(a, event) for a in all_facts if (event := activity_projection(a)) is not None]
    facts = [a for a, _ in projected]
    views = [v for v in session.page_views.all() if v.dataroom_visit_id not in excluded_visits]
    pages = {v.page_number for v in views}
    pages.update(a.data['page'] for a in facts if type(a.data.get('page')) is int and a.data['page'] > 0)
    browser, device = stored_browser_device(session.user_agent)
    return {'id': str(session.pk), 'at': session.viewed_at, 'email': session.viewer_email or None,
            'ip': session.ip_address or None, 'city': session.city or None, 'country': session.country or None,
            'browser': browser, 'device': device,
            # Legacy zero defaults do not prove recorded zero engagement.
            'duration_seconds': session.duration_seconds if session.duration_seconds > 0 else
                        sum(v.duration_seconds for v in views) if views else None,
            'pages': sorted(pages) or None,
            # A session-wide download marker cannot establish a visible-item download
            # when some of its item-level evidence has been excluded.
            'downloaded': True if ((session.downloaded_at and not excluded_visits and len(facts) == len(all_facts))
                                   or any(v.downloaded_at for v in visits)
                                   or any(a.event_type == 'document.downloaded' for a in facts)) else None,
            'activity': [event for _, event in projected]}


def preview_target(request, pk, item_id):
    row = get_object_or_404(board_room_scope(request), room_id=pk)
    item = get_object_or_404(DataroomDocument.objects.select_related('document', 'folder'),
                            pk=item_id, dataroom=row.room,
                            document__organization_id=row.room.organization_id)
    if excluded_item(item):
        raise PermissionDenied('Use the authorized signature product operation.')
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


class PageContentNegotiation(DefaultContentNegotiation):
    def select_renderer(self, request, renderers, format_suffix=None):
        # Binary page success is an HttpResponse; failures remain JSON even for image-only Accept.
        if request.parser_context.get('view').action == 'page':
            return JSONRenderer(), 'application/json'
        return super().select_renderer(request, renderers, format_suffix)


class BoardRoomReadViewSet(viewsets.ViewSet):
    content_negotiation_class = PageContentNegotiation
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
    def list(self, request, format=None):
        rows, cursor = paginate(board_room_scope(request), request.query_params.get('cursor'),
                                time_field='room__created_at', id_field='room_id')
        return Response({'results': [room_summary(row) for row in rows], 'next': cursor})

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def retrieve(self, request, pk=None, format=None):
        return Response(room_detail(get_object_or_404(board_room_scope(request), room_id=pk)))

    @extend_schema(parameters=[CURSOR_PARAM], responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['get'])
    def visits(self, request, pk=None, format=None):
        row = get_object_or_404(board_room_scope(request), room_id=pk)
        sessions = ViewSession.objects.filter(share_link__dataroom=row.room).prefetch_related('dataroom_visits', 'page_views')
        rows, cursor = paginate(sessions, request.query_params.get('cursor'), time_field='viewed_at', id_field='id')
        session_ids = [str(s.pk) for s in rows]
        visit_ids = [str(v.pk) for s in rows for v in s.dataroom_visits.all()]
        activities = list(Activity.objects.filter(organization=row.room.organization, room_id=str(row.room_id))
                          .filter(Q(data__view_session_id__in=session_ids) | Q(data__visit_id__in=visit_ids)))
        return Response({'results': BoardVisitSerializer([visit_projection(s, activities) for s in rows], many=True).data,
                         'next': cursor})

    @extend_schema(parameters=[VERSION_PARAM], responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['get'], url_path=r'documents/(?P<item_id>[^/.]+)/pages')
    def pages(self, request, pk=None, item_id=None, format=None):
        row, item, version = preview_target(request, pk, item_id)
        renderer = get_renderer(version)
        if version.render_status == DocumentVersion.RENDER_NOT_GENERATED:
            transaction.on_commit(lambda: renderer.enqueue_render_task(version), robust=True)
        return Response(preview_state(version, renderer))

    @extend_schema(parameters=[VERSION_PARAM], responses={(200, 'image/png'): OpenApiTypes.BINARY})
    @action(detail=True, methods=['get'], url_path=r'documents/(?P<item_id>[^/.]+)/pages/(?P<page>[0-9]+)')
    def page(self, request, pk=None, item_id=None, page=None, format=None):
        row, item, version = preview_target(request, pk, item_id)
        renderer = get_renderer(version)
        state = preview_state(version, renderer)
        if state['status'] != 'ready':
            return Response(state, status=409)
        number = int(page)
        if number < 1 or number > state['page_count']:
            return Response({'detail': 'Page not found.'}, status=404)
        if not hooks.RENDER_SEMAPHORE.acquire(timeout=5):
            return Response({'detail': 'Preview is unavailable.'}, status=503)
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
