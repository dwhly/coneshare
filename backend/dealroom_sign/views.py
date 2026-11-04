import uuid

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from core.models import APIKey
from datarooms.models import Dataroom, DataroomDocument
from documents.models import DocumentVersion
from sharelinks.models import Viewer

from .models import NdaAcceptance, NdaPolicy, SignCredential, Workflow
from .serializers import CredentialInputSerializer, NdaPolicyInputSerializer, NdaPolicySerializer, SendInputSerializer, WorkflowSerializer
from .storage import source_bytes
from .validation import digest, validate_recipients
from .workflows import command


def staff_room(request, room_id):
    return get_object_or_404(Dataroom, pk=room_id, organization=request.user.organization, created_by=request.user)


def room_version(room, version_id):
    version = get_object_or_404(DocumentVersion.objects.select_related('document'), pk=version_id,
                               document__organization=room.organization, document__deleted_at__isnull=True)
    if not DataroomDocument.objects.filter(dataroom=room, document=version.document).exists():
        raise ValidationError('Source version must belong to this room.')
    return version


def scoped_room(view, request):
    room_id = view.kwargs.get('room_id')
    if room_id is None and view.kwargs.get('pk'):
        room_id = str(view.get_object().room_id)
    if room_id is None:
        room_id = request.query_params.get('room_id') if request.method == 'GET' else request.data.get('room_id')
    supplied = request.query_params.getlist('room_id')
    if 'room_id' in request.data:
        supplied.append(request.data['room_id'])
    if room_id is not None and any(str(value) != str(room_id) for value in supplied):
        raise PermissionDenied('room_id conflicts with the target room.')
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

    @extend_schema(request=SendInputSerializer, responses=WorkflowSerializer)
    def create(self, request):
        serializer = SendInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        room = staff_room(request, data['room_id'])
        version = room_version(room, data['version_id'])
        if not SignCredential.objects.filter(owner=request.user, enabled=True).exists():
            raise ValidationError('Configure your per-staff Sign credential first.')
        workflow = command(owner=request.user, room=room, version=version, recipients=data['recipients'], idempotency_key=data['idempotency_key'])
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
        validate_recipients([{'email': 'placeholder@example.test', 'name': 'Placeholder', 'fields': fields}], pdf)
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
        response['Referrer-Policy'] = 'no-referrer'
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
            work = command(owner=room.created_by, room=room, version=policy.source_version,
                recipients=[{'email': member.email, 'name': member.name, 'fields': policy.fields}],
                idempotency_key=f'nda:{room.pk}:{member.pk}:{policy.revision}', purpose='nda', member=member, policy=policy)
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
        from .client import identifier
        # Use only configured origin, never an upstream signingUrl or a caller URL.
        return Response({'signing_url': settings.SIGN_PUBLIC_URL.rstrip('/') + '/sign/' + identifier(work.signing_token)})


class SigningSourceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def key_scope_targets(self, request):
        return scoped_room(self, request)

    @extend_schema(responses=dict)
    def get(self, request, room_id):
        room = staff_room(request, room_id)
        versions = DocumentVersion.objects.filter(document__dataroomdocument__dataroom=room,
            document__deleted_at__isnull=True, content_type='application/pdf').select_related('document')
        return Response([{'id': str(v.pk), 'name': v.document.name, 'version_number': v.version_number} for v in versions])


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
        from .client import SignError
        if not human_staff(request):
            raise PermissionDenied('Only a human staff JWT may reset an NDA.')
        room = staff_room(request, room_id)
        work = get_object_or_404(Workflow, pk=workflow_id, room=room, purpose='nda')
        try:
            replacement = reset_nda(work)
        except SignError as exc:
            raise ValidationError({'code': exc.code}) from None
        return Response(WorkflowSerializer(replacement).data, status=201)
