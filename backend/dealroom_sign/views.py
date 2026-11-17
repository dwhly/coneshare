import io
import uuid
from urllib.parse import urlencode

from PIL import Image
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import APIKeyAuthentication
from core.models import APIKey
from datarooms.models import Dataroom, DataroomDocument
from dealroom.activity import record
from dealroom.hooks import human_staff
from documents.models import DocumentPage, DocumentVersion
from documents.tasks import generate_pdf_pages_task
from sharelinks.models import Viewer

from . import storage as product_storage
from .board_auth import BoardProxyAuthentication
from .client import SignError
from .counterparty_mail import retry_email
from .evidence import fields_for_snapshot, projection as evidence_projection
from .exports import (
    SnapshotChanged, Unavailable, download, existing_artifact,
    manifest as artifact_manifest, resolve_artifact,
)
from .models import CounterpartyEffect, NdaAcceptance, NdaPolicy, SignCredential, SignatureRequest, Workflow
from .operations import require_export_actor
from .presentation import referrer_policy
from .requests import (
    activity as request_activity, board_config, freshness, integrity, list_row,
    request_scope, scoped_request,
)
from .serializers import (
    CredentialInputSerializer, NdaPolicyInputSerializer, NdaPolicySerializer,
    SendInputSerializer, SignatureExportInputSerializer, WorkflowSerializer,
)
from .storage import source_bytes
from .validation import digest, validate_recipients
from .workflows import PlacementRequired, command


def staff_room(request, room_id):
    reject_room_conflicts(request, room_id)
    return get_object_or_404(Dataroom, pk=room_id, organization=request.user.organization, created_by=request.user)


def room_version(room, version_id):
    version = get_object_or_404(DocumentVersion.objects.select_related('document'), pk=version_id,
                               document__organization=room.organization, document__deleted_at__isnull=True)
    if not DataroomDocument.objects.filter(dataroom=room, document=version.document).exists():
        raise ValidationError('Source version must belong to this room.')
    return version


def reject_room_conflicts(request, room_id):
    supplied = request.query_params.getlist('room_id')
    if 'room_id' in request.data:
        supplied.append(request.data['room_id'])
    if room_id is not None and any(str(value) != str(room_id) for value in supplied):
        raise PermissionDenied('room_id conflicts with the target room.')


def scoped_room(view, request):
    room_id = view.kwargs.get('room_id')
    if room_id is None and view.kwargs.get('pk'):
        room_id = str(view.get_object().room_id)
    if room_id is None:
        room_id = request.query_params.get('room_id') if request.method == 'GET' else request.data.get('room_id')
    reject_room_conflicts(request, room_id)
    if not room_id:
        raise PermissionDenied('Scoped signing queries require a room_id.')
    # Recipient-org-restricted keys cannot distribute to arbitrary emails.
    from dealroom.models import KeyScope
    scope = KeyScope.objects.filter(key=request.auth).first()
    if scope and scope.recipient_orgs is not None:
        raise PermissionDenied('Recipient-org scoped signing requires an explicit recipient-org mapping.')
    return [str(room_id)], []


class SigningEnvelopeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkflowSerializer

    def get_queryset(self):
        queryset = Workflow.objects.filter(owner=self.request.user).prefetch_related('artifacts').order_by('-created_at')
        room_id = self.request.query_params.get('room_id')
        return queryset.filter(room_id=room_id) if room_id else queryset

    def key_scope_targets(self, request):
        return scoped_room(self, request)

    def validate_approval(self, request):
        # Reject before an API-key request can create an approval or a workflow.
        if (isinstance(request.auth, APIKey) and isinstance(request.data, dict)
                and any(field in request.data for field in ('board_id', 'task_ref', 'requester', 'title'))):
            raise PermissionDenied('API keys cannot supply board_id or task_ref.')

    @extend_schema(request=SendInputSerializer, responses=WorkflowSerializer)
    def create(self, request):
        self.validate_approval(request)
        serializer = SendInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        room = staff_room(request, data['room_id'])
        version = room_version(room, data['version_id'])
        if not SignCredential.objects.filter(owner=request.user, enabled=True).exists():
            raise ValidationError('Configure your per-staff Sign credential first.')
        try:
            workflow = command(owner=request.user, room=room, version=version, recipients=data['recipients'],
                idempotency_key=data['idempotency_key'], board_id=data.get('board_id'), task_ref=data.get('task_ref'),
                requester=data.get('requester'), title=data.get('title'), placement=data.get('placement'))
        except PlacementRequired as exc:
            return Response(exc.result, status=409)
        return Response(WorkflowSerializer(workflow).data, status=201)


class SignCredentialView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=dict)
    def get(self, request):
        credential = SignCredential.objects.filter(owner=request.user).first()
        return Response({'configured': bool(credential), 'enabled': bool(credential and credential.enabled), 'team_id': credential.team_id if credential else None})

    @extend_schema(request=CredentialInputSerializer, responses=dict)
    def put(self, request):
        from dealroom.hooks import human_staff
        if not human_staff(request):
            raise PermissionDenied('Only a human staff JWT may configure Sign credentials.')
        token = request.data.get('token', '')
        team_id = request.data.get('team_id')
        if not isinstance(token, str) or not token.startswith('api_') or len(token) > 512 or type(team_id) is not int or team_id <= 0:
            raise ValidationError('A team ID and Sign API token are required.')
        current = SignCredential.objects.filter(owner=request.user).first()
        if current and current.team_id != team_id and Workflow.objects.filter(owner=request.user).exclude(state__in=['done', 'cancelled', 'declined', 'failed']).exists():
            raise ValidationError('Changing Sign teams would strand in-flight envelopes. Resolve or reset them first.')
        SignCredential.objects.update_or_create(owner=request.user, defaults={'team_id': team_id, 'token': token, 'enabled': True})
        from dealroom.activity import record
        record('sign.credential_configured', organization=request.user.organization, actor=request.user)
        return Response({'configured': True, 'team_id': team_id})


class SigningNdaPolicyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def key_scope_targets(self, request):
        return scoped_room(self, request)

    @extend_schema(responses=dict)
    def get(self, request, room_id):
        room = staff_room(request, room_id)
        policy = NdaPolicy.objects.filter(room=room).first()
        return Response(NdaPolicySerializer(policy).data if policy else {'enabled': False})

    @extend_schema(request=NdaPolicyInputSerializer, responses=NdaPolicySerializer)
    def put(self, request, room_id):
        room = staff_room(request, room_id)
        if set(request.data) - {'version_id', 'fields', 'enabled'}:
            raise ValidationError('Unknown policy fields.')
        version = room_version(room, request.data.get('version_id'))
        pdf = source_bytes(version)
        fields = request.data.get('fields', [])
        validate_recipients([{'email': 'placeholder@example.test', 'name': 'Placeholder', 'fields': fields}], pdf,
                            automatic=not fields)
        enabled = request.data.get('enabled', True)
        if type(enabled) is not bool:
            raise ValidationError('enabled must be a boolean.')
        from django.db import transaction
        with transaction.atomic():
            Dataroom.objects.select_for_update().get(pk=room.pk)
            policy = NdaPolicy.objects.filter(room=room).first()
            revision = policy.revision if policy and (policy.source_version_id == version.pk and
                policy.source_sha256 == digest(pdf) and policy.fields == fields) else uuid.uuid4()
            policy, _ = NdaPolicy.objects.update_or_create(room=room, defaults={
                'revision': revision, 'source_version': version, 'source_sha256': digest(pdf), 'fields': fields, 'enabled': enabled,
            })
        from dealroom.activity import record
        record('nda.policy_updated', organization=request.user.organization, actor=request.auth if isinstance(request.auth, APIKey) else request.user,
               room_id=room.pk, data={'revision': str(policy.revision), 'enabled': enabled})
        return Response(NdaPolicySerializer(policy).data)


def member_context(request, room_id):
    from dealroom.models import RoomPolicy
    from dealroom.policy import evaluate
    policy = get_object_or_404(RoomPolicy.objects.select_related('room', 'entry_link'), room_id=room_id)
    decision = evaluate(request, policy.entry_link, skip_nda=True)
    member = get_object_or_404(Viewer, pk=decision.member_id)
    return policy.room, member


class RecipientNdaView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Referrer-Policy'] = referrer_policy(response)
        response['Cache-Control'] = 'private, no-store'
        return response

    @extend_schema(responses=dict)
    def get(self, request, room_id):
        room, member = member_context(request, room_id)
        policy = NdaPolicy.objects.filter(room=room, enabled=True).first()
        if not policy:
            return Response({'required': False, 'accepted': True})
        accepted = NdaAcceptance.objects.filter(room=room, member_id=str(member.pk), member_email=member.email.strip().lower(), policy_revision=str(policy.revision)).exists()
        workflow = Workflow.objects.filter(room=room, member_id=str(member.pk), member_email=member.email.strip().lower(), policy_revision=str(policy.revision)).order_by('-created_at').first()
        return Response({'required': True, 'accepted': accepted, 'state': workflow.state if workflow else 'not_started',
                         'can_enter': bool(workflow and workflow.state == 'awaiting_signature' and workflow.signing_token and workflow.signer_projection and workflow.signer_projection[0].get('email', '').strip().lower() == member.email.strip().lower() and not accepted),
                         'overdue': bool(workflow and workflow.state in {'awaiting_seal', 'quarantined', 'failed', 'distributing', 'uncertain', 'cancelled', 'declined'} and (timezone.now() - workflow.created_at).total_seconds() > 60)})

    @extend_schema(request=None, responses=dict)
    def post(self, request, room_id):
        SessionAuthentication().enforce_csrf(request)
        room, member = member_context(request, room_id)
        policy = get_object_or_404(NdaPolicy, room=room, enabled=True)
        if not SignCredential.objects.filter(owner=room.created_by, enabled=True).exists():
            raise ValidationError('Room owner has not configured signing.')
        from django.db import transaction
        with transaction.atomic():
            NdaPolicy.objects.select_for_update().get(pk=policy.pk)
            existing = Workflow.objects.filter(room=room, purpose='nda', member_id=str(member.pk), policy_revision=str(policy.revision)).order_by('-created_at').first()
            if existing:
                return Response({'state': existing.state}, status=201)
            try:
                work = command(owner=room.created_by, room=room, version=policy.source_version,
                    recipients=[{'email': member.email, 'name': member.name,
                                 'company': member.recipient_org.name if member.recipient_org else ''}],
                    placement='auto', idempotency_key=f'nda:{room.pk}:{member.pk}:{policy.revision}',
                    purpose='nda', member=member, policy=policy)
            except PlacementRequired as exc:
                return Response(exc.result, status=409)
        return Response({'state': work.state}, status=201)


class RecipientNdaEnterView(RecipientNdaView):
    http_method_names = ['post', 'options']

    @extend_schema(request=None, responses=dict)
    def post(self, request, room_id):
        SessionAuthentication().enforce_csrf(request)
        room, member = member_context(request, room_id)
        policy = get_object_or_404(NdaPolicy, room=room, enabled=True)
        work = Workflow.objects.filter(room=room, member_id=str(member.pk), member_email=member.email.strip().lower(), policy_revision=str(policy.revision)).order_by('-created_at').first()
        if not work:
            raise PermissionDenied('No signing workflow for this member.')
        if work.state != 'awaiting_signature' or not work.signing_token or not work.signer_projection or work.signer_projection[0].get('email', '').strip().lower() != member.email.strip().lower():
            raise PermissionDenied('Signing is not ready for this verified member.')
        from .counterparty import issue_handoff
        from .recipient_proxy import origin
        access = work.signer_accesses.filter(revision=work.policy_revision,
            email=member.email.strip().lower(), native_token__isnull=False).first()
        if not access or access.native_token != work.signing_token:
            raise PermissionDenied('Signing is not ready for this verified member.')
        return Response({'signing_url': origin() + '/s/nda/' + issue_handoff(access, member)})


GENERATED_ARTIFACT_NAME = r'^(sealed_pdf|certificate|audit)[-_]envelope_'


class SigningSourceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def key_scope_targets(self, request):
        return scoped_room(self, request)

    @extend_schema(responses=dict)
    def get(self, request, room_id):
        room = staff_room(request, room_id)
        # Signed copies, certificates and audit trails are outputs of signing, not sendable documents: hide them
        # (filed artifacts by their manifest row; older auto-named copies by their generated name).
        versions = DocumentVersion.objects.filter(document__dataroomdocument__dataroom=room,
            document__deleted_at__isnull=True, content_type='application/pdf', executedartifact__isnull=True,
        ).exclude(document__name__regex=GENERATED_ARTIFACT_NAME).select_related('document').distinct()
        selected = request.query_params.get('version_id')
        if selected:
            versions = versions.filter(pk=selected)
        return Response([{'id': str(v.pk), 'name': v.document.name, 'version_number': v.version_number,
                          **({'sha256': digest(source_bytes(v))} if selected else {})} for v in versions])


class SigningWhoViewedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def key_scope_targets(self, request):
        return scoped_room(self, request)

    @extend_schema(responses=dict)
    def get(self, request, room_id):
        from django.db.models import Sum, Count, Max
        from sharelinks.models import ViewSession
        room = staff_room(request, room_id)
        rows = ViewSession.objects.filter(share_link__dataroom=room, email_verification_method='verified').values(
            'viewer_id', 'viewer_email', 'viewer_name').annotate(sessions=Count('id'),
            observed_seconds=Sum('duration_seconds'), last_seen=Max('viewed_at'))
        return Response({'room_id': str(room.pk), 'members': list(rows),
                         'measurement': 'Observed browser engagement, not proof of reading; missing heartbeats are unknown.'})


class SigningNdaResetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses=WorkflowSerializer)
    def post(self, request, room_id, workflow_id):
        from dealroom.hooks import human_staff
        from .workflows import reset_nda
        if not human_staff(request):
            raise PermissionDenied('Only a human staff JWT may reset an NDA.')
        room = staff_room(request, room_id)
        work = get_object_or_404(Workflow, pk=workflow_id, room=room, purpose='nda')
        try:
            replacement = reset_nda(work)
        except PlacementRequired as exc:
            return Response(exc.result, status=409)
        except SignError as exc:
            raise ValidationError({'code': exc.code}) from None
        return Response(WorkflowSerializer(replacement).data, status=201)


# Slice 1 read endpoints. Explicit authentication excludes the shared legacy staff JWT.
class SignatureProductView(APIView):
    authentication_classes = [BoardProxyAuthentication, APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, SignError):
            exc = Unavailable()
        response = super().handle_exception(exc)
        code = {400:'unsupported_kind', 403:'forbidden', 404:'not_found', 409:'snapshot_changed', 503:'send_unavailable'}.get(response.status_code)
        if code:
            response.data = {'code':code}
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        response['Referrer-Policy'] = referrer_policy(response)
        return response

    def key_scope_targets(self, request):
        if isinstance(self, SignatureExportView):
            require_export_actor(request, request.data.get('kind') if isinstance(request.data, dict) else None)
            serializer = SignatureExportInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            ids = serializer.validated_data['request_ids']
            # Resolve before filtering by key room scope, so denied room IDs are 403.
            rows = SignatureRequest.objects.filter(pk__in=ids, workflow__room__organization=request.user.organization)
        elif self.kwargs.get('request_id'):
            rows = SignatureRequest.objects.filter(pk=self.kwargs['request_id'], workflow__room__organization=request.user.organization)
        else:
            rows = request_scope(request, request.query_params.get('board'))
        return set(str(r.workflow.room_id) for r in rows), set()


LIST_PARAMETERS = [OpenApiParameter(name, str, required=name == 'board') for name in ['board','state','direction','q','cursor']]
PAGE_PARAMETERS = [OpenApiParameter('kind', str, enum=['original','partial','final']), OpenApiParameter('snapshot_id', str), OpenApiParameter('field_id', str)]


class SignatureRequestListView(SignatureProductView):
    @extend_schema(parameters=LIST_PARAMETERS, responses={200:OpenApiTypes.OBJECT})
    def get(self, request):
        if set(request.query_params) - {'board','state','direction','q','cursor'}:
            raise ValidationError('Unsupported input property.')
        rows = request_scope(request, request.query_params.get('board')).order_by('-created_at', '-id')
        q = request.query_params.get('q', '').strip()[:200]
        if q:
            rows = rows.filter(Q(title__icontains=q) | Q(workflow__recipients__icontains=q) | Q(task_ref__icontains=q) | Q(room__name__icontains=q))
        direction = request.query_params.get('direction')
        if direction:
            if direction not in {'in','out','std','unknown'}:
                raise ValidationError('Invalid direction.')
            rows = rows.filter(kind=direction)
        projected = [list_row(r, request) for r in rows]
        # Sort the real activity projection before applying the cursor/page limit.
        # Import/creation order can otherwise hide an active older request on page two.
        projected.sort(key=lambda r: (-r['last_activity_at'].timestamp(), r['title'].casefold(), r['id']))
        def matches(r, state):
            return (state == 'needs_you' and r['needs_you'] or
                    state == 'waiting' and r['state'] == 'awaiting_signature' and r['signed'] < r['required'] or
                    r['state'] == state)
        counts = {state:sum(bool(matches(r, state)) for r in projected) for state in ['needs_you','waiting','done','declined']}
        counts['all'] = len(projected)
        state = request.query_params.get('state')
        if state:
            projected = [r for r in projected if matches(r, state)]
        cursor = request.query_params.get('cursor')
        if cursor:
            ids = [r['id'] for r in projected]
            if cursor not in ids:
                raise ValidationError('Invalid cursor.')
            projected = projected[ids.index(cursor)+1:]
        items = projected[:50]
        return Response({'items':items,'counts':counts,'next_cursor':items[-1]['id'] if len(projected)>50 else None,
            'as_of':timezone.now(),'stale':any(not r.workflow.reconciled_at or (timezone.now()-r.workflow.reconciled_at).total_seconds()>90 for r in rows)})


class SignatureOverviewView(SignatureProductView):
    @extend_schema(parameters=[OpenApiParameter('board', str, required=True)], responses={200:OpenApiTypes.OBJECT})
    def get(self, request):
        rows = list(request_scope(request, request.query_params.get('board')).order_by('-created_at')[:200])
        items = [list_row(r, request) for r in rows]
        context = getattr(request, 'board_context', None)
        room_ids = board_config(context['board']).get('room_ids', []) if context else []
        return Response({'needs_you':[r for r in items if r['needs_you']],
            'waiting':[r for r in items if r['state']=='awaiting_signature' and not r['needs_you']],
            'likely':[],'recent':items[:10],'source_states':{'predictions':'not_enabled'}, 'room_ids':room_ids,
            'as_of':timezone.now(),'stale':any(freshness(r)['stale'] for r in rows)})


class SignatureSignerRevokeView(SignatureProductView):
    @extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
    def post(self, request, request_id, signer_id):
        if not human_staff(request):
            raise PermissionDenied('forbidden')
        row = scoped_request(request, request_id)
        binding = getattr(request, 'board_binding', None)
        if request.user.pk != row.workflow.owner_id or (binding and binding.role not in {'writer', 'manager'}):
            raise PermissionDenied('forbidden')
        reason = request.data.get('reason')
        if set(request.data) != {'reason'} or not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
            raise ValidationError('A reason is required.')
        access = get_object_or_404(row.workflow.signer_accesses, pk=signer_id)
        from .counterparty import revoke
        revoke(access, reason.strip())
        return Response({'revoked': True})


def can_retry_email(request, row):
    if not human_staff(request):
        return False
    binding = getattr(request, 'board_binding', None)
    # Board writers may retry known failed mail; revoke separately requires ownership.
    # Request scope requires a board binding for human access.
    return bool(binding and binding.role in {'writer', 'manager'})


class SignatureEmailRetryView(SignatureProductView):
    @extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
    def post(self, request, request_id, effect_id):
        row = scoped_request(request, request_id)
        if not can_retry_email(request, row):
            raise PermissionDenied('forbidden')
        if request.data:
            raise ValidationError('Unsupported input property.')
        effect = get_object_or_404(CounterpartyEffect, pk=effect_id, access__workflow=row.workflow)
        try:
            retry_email(effect, request.user)
        except SignError as exc:
            raise ValidationError(exc.code) from None
        return Response({'state': 'pending'})


class SignatureRequestDetailView(SignatureProductView):
    @extend_schema(responses={200:OpenApiTypes.OBJECT})
    def get(self, request, request_id):
        row = scoped_request(request, request_id)
        human = human_staff(request)
        evidence = evidence_projection(row) if human else []
        artifacts = artifact_manifest(row, human)
        # Field crops use only persisted native recipient/field geometry from audit events.
        if human:
            available = next((a for a in artifacts if a['kind'] == 'final' and a['available']), None)
            available = available or next((a for a in artifacts if a['kind'] == 'partial' and a['snapshot_id']), None)
            if available:
                for item in evidence:
                    field = signature_field(row, available['snapshot_id'], recipient_id=item['recipient_id'])
                    if field and item['signed_at']:
                        query = urlencode({'kind':available['kind'],'snapshot_id':available['snapshot_id'],'field_id':field['id']})
                        item['signature'] = {'snapshot_id':available['snapshot_id'],'page':field['page'],'field_id':field['id'],
                            'url':f'/api/v1/dealroom-sign/requests/{row.pk}/pages/{field["page"]}?{query}', 'type':'not_recorded'}
        return Response({**list_row(row, request),'revision':row.revision,'evidence':evidence,'activity':request_activity(row),
            'source_context':{'identity':row.source_context.get('identity', 'not_recorded')},
            'integrity':integrity(row),'settings':{},'completion':[],'artifacts':artifacts,'audit_complete':row.audit_complete,'audit_as_of':row.audit_as_of,
            'capabilities':{name:{'enabled':False,'reason':'read_only_slice'} for name in ['send','remind','void','revise','settings','evidence_report','history_evidence']},
            'email_effects': [{'id': str(effect.pk), 'kind': effect.kind, 'state': effect.state,
                'last_error': effect.last_error, 'can_retry': effect.state == 'failed' and can_retry_email(request, row)}
                for effect in CounterpartyEffect.objects.filter(access__workflow=row.workflow)] if human else [],
            'last_error': row.workflow.last_error, 'human':human, **freshness(row)})


def signature_field(row, snapshot_id, field_id=None, recipient_id=None):
    return next((field for field in fields_for_snapshot(row.workflow, snapshot_id)
        if field['inserted'] and (field_id is None or field['id'] == field_id)
        and (recipient_id is None or str(field['recipient_id']) == str(recipient_id))), None)


def page_artifact(request, row):
    if set(request.query_params) - {'kind','snapshot_id','field_id'}:
        raise ValidationError('Unsupported input property.')
    kind = request.query_params.get('kind', 'original')
    if kind not in {'original','partial','final'}:
        raise ValidationError('Invalid page kind.')
    snapshot = request.query_params.get('snapshot_id')
    artifact = existing_artifact(row, kind, snapshot)
    if artifact is None:
        artifact, _ = resolve_artifact(row, kind, snapshot)
    version = artifact.version
    if version.render_status == DocumentVersion.RENDER_FAILED:
        return artifact, Response({'code':'render_failed'}, status=422)
    if not version.has_pages:
        if version.render_status not in {DocumentVersion.RENDER_PROCESSING, DocumentVersion.RENDER_QUEUED}:
            DocumentVersion.objects.filter(pk=version.pk).update(render_status=DocumentVersion.RENDER_QUEUED)
            try:
                generate_pdf_pages_task.delay(version.pk)
            except Exception:
                raise Unavailable() from None
        return artifact, Response({'status':'processing','snapshot_id':artifact.snapshot_id}, status=202)
    return artifact, None


class SignaturePageListView(SignatureProductView):
    @extend_schema(parameters=PAGE_PARAMETERS, responses={200:OpenApiTypes.OBJECT,202:OpenApiTypes.OBJECT,422:OpenApiTypes.OBJECT})
    def get(self, request, request_id):
        row = scoped_request(request, request_id)
        artifact, pending = page_artifact(request, row)
        if pending is not None:
            return pending
        query = urlencode({'kind':request.query_params.get('kind','original'),'snapshot_id':artifact.snapshot_id})
        pages = list(artifact.version.pages.order_by('page_number'))
        signature_pages = sorted({f['page'] for r in row.workflow.recipients for f in r.get('fields', []) if f.get('type') in {'SIGNATURE','FREE_SIGNATURE','INITIALS'}})
        if request.query_params.get('kind', 'original') != 'original':
            signature_pages = sorted({f['page'] for f in fields_for_snapshot(row.workflow, artifact.snapshot_id)})
        signatures = [{'recipient_id':f['recipient_id'],'field_id':f['id'],'page':f['page'],
            'url':f'/api/v1/dealroom-sign/requests/{row.pk}/pages/{f["page"]}?{query}&field_id={f["id"]}'}
            for f in fields_for_snapshot(row.workflow, artifact.snapshot_id) if f['inserted']]
        return Response({'sha256':artifact.sha256, 'signatures':signatures, 'version_id':str(artifact.version.pk),'snapshot_id':artifact.snapshot_id,'status':'ready',
            'page_count':len(pages),'signature_pages':signature_pages,
            'pages':[{'page':p.page_number,'url':f'/api/v1/dealroom-sign/requests/{row.pk}/pages/{p.page_number}?{query}'} for p in pages]})


class SignaturePageView(SignatureProductView):
    @extend_schema(parameters=PAGE_PARAMETERS, responses={200:OpenApiTypes.BINARY,202:OpenApiTypes.OBJECT,422:OpenApiTypes.OBJECT})
    def get(self, request, request_id, page):
        row = scoped_request(request, request_id)
        if not request.query_params.get('snapshot_id'):
            raise SnapshotChanged()
        artifact, pending = page_artifact(request, row)
        if pending is not None:
            return pending
        rendered = get_object_or_404(DocumentPage, document_version=artifact.version, page_number=page)
        try:
            content = product_storage.page_bytes(rendered)
            field_id = request.query_params.get('field_id')
            if field_id:
                field = signature_field(row, artifact.snapshot_id, field_id=field_id)
                if not field or field['page'] != page or request.query_params.get('kind') == 'original':
                    raise NotFound('not_found')
                with Image.open(io.BytesIO(content)) as img:
                    x, y = img.width*field['positionX']/100, img.height*field['positionY']/100
                    crop = img.crop((x,y,x+img.width*field['width']/100,y+img.height*field['height']/100))
                    out = io.BytesIO(); crop.convert('RGB').save(out, format='JPEG'); crop.close(); content = out.getvalue()
            record('signature.page_viewed', organization=row.workflow.room.organization, actor=request.user,
                room_id=row.workflow.room_id, target_id=row.pk,
                data={'snapshot_id':artifact.snapshot_id,'page':page,'field_id':field_id,'sha256':digest(content),'board_id':row.board_id})
        except NotFound:
            raise
        except Exception:
            raise Unavailable() from None
        return HttpResponse(content, content_type='image/jpeg')


class SignatureExportView(SignatureProductView):
    @extend_schema(request=SignatureExportInputSerializer, responses={200:OpenApiTypes.BINARY},
        description='Partial, audit, evidence_report and history_evidence require a verified human board session, even with full-access keys. Original/final/certificate require explicit operation, request and actual filing-room scope. Reports/CSV are reserved and disabled.')
    def post(self, request):
        require_export_actor(request, request.data.get('kind') if isinstance(request.data, dict) else None)
        serializer = SignatureExportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        row = scoped_request(request, data['request_ids'][0])
        return download(request, row, data)
