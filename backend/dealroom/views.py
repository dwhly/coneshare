from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, mixins, serializers, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import CursorPagination
from drf_spectacular.utils import extend_schema
from core.models import APIKey
from core.authentication import generate_raw_api_key
from datarooms.models import Dataroom
from sharelinks.models import ViewerOrganisation, Viewer, ShareLinkAccessGrant, ShareLink, IssuedCopy, ShareLinkDataroomSetting
from .models import RoomPolicy, DomainConfirmation, MemberDeny, AccessApproval, Activity, Drift, OriginalException, KeyScope
from .serializers import RoomSerializer, OrgSerializer, MemberSerializer, GrantSerializer, EntryLinkSerializer, ApprovalSerializer, ActivitySerializer, DriftSerializer, CopySerializer, FilePolicySerializer, OriginalExceptionSerializer
from .activity import record
from .brand import load_brand
from .domains import guarded_domain
from .hooks import human_staff
from .registry import registry, TIERS


class BrandView(APIView):
    permission_classes = [permissions.AllowAny]
    @extend_schema(responses=dict)
    def get(self, request):
        return Response(load_brand())


class BoundedPagination(CursorPagination):
    page_size = 50
    ordering = '-created_at'


class StaffViewSet(viewsets.ModelViewSet):
    pagination_class = BoundedPagination
    def fact(self, event, instance):
        record(event, organization=self.request.user.organization, actor=self.request.auth if isinstance(self.request.auth, APIKey) else self.request.user, target_id=instance.pk)
    def perform_update(self, serializer):
        obj = serializer.save()
        self.fact('policy.changed', obj)
    def perform_destroy(self, instance):
        self.fact('object.deleted', instance)
        instance.delete()


class RoomViewSet(StaffViewSet):
    serializer_class = RoomSerializer
    def approval_before(self):
        if self.action == 'policy':
            policy = RoomPolicy.objects.get(room=self.get_object())
            return {'status': policy.status, 'expires_at': policy.expires_at.isoformat() if policy.expires_at else None, 'invitation_mode': policy.invitation_mode}
        return dict(self.get_serializer(self.get_object()).data) if self.kwargs.get('pk') else {}
    def get_queryset(self):
        return Dataroom.objects.filter(organization=self.request.user.organization).order_by('name')
    def perform_create(self, serializer):
        room = serializer.save(organization=self.request.user.organization, created_by=self.request.user, enable_qna=False)
        link = ShareLink.objects.create(dataroom=room, created_by=self.request.user, name='Room entry', restrict_to_grants=True, requires_email=True, requires_email_verification=True, enable_watermark=True, enable_qna=False)
        RoomPolicy.objects.create(room=room, entry_link=link)
        self.fact('room.created', room)
    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['patch'])
    def policy(self, request, pk=None):
        room = self.get_object()
        policy = RoomPolicy.objects.select_for_update().get(room=room)
        allowed = {'status', 'expires_at', 'invitation_mode'}
        if set(request.data) - allowed:
            raise ValidationError('Unknown room policy fields.')
        if request.data.get('status', policy.status) not in ('active', 'archived'):
            raise ValidationError('Invalid room status.')
        if request.data.get('invitation_mode', 'off') != 'off':
            raise ValidationError('Invitations are phase 2; only off is available.')
        for key, value in request.data.items():
            if key == 'expires_at' and value:
                value = serializers.DateTimeField().run_validation(value)
            setattr(policy, key, value)
        policy.revision += 1
        policy.save()
        self.fact('room.updated', room)
        return Response({'status': policy.status, 'revision': policy.revision})
    @extend_schema(request={'multipart/form-data': {'type':'object','properties':{'file':{'type':'string','format':'binary'},'folder_id':{'type':'string'}},'required':['file']}}, responses=dict)
    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        from .uploads import upload
        if 'file' not in request.FILES:
            raise ValidationError('file required')
        item = upload(self.get_object(), request.auth if isinstance(request.auth, APIKey) else request.user, request.FILES['file'], request.data.get('folder_id'))
        return Response({'id': str(item.pk), 'document_id': str(item.document_id), 'status': 'processing'}, status=201)
    @extend_schema(request=dict, responses=dict)
    @action(detail=True, methods=['post'])
    def folders(self, request, pk=None):
        from datarooms.models import DataroomFolder
        name = serializers.CharField(max_length=255).run_validation(request.data.get('name'))
        folder = DataroomFolder.objects.create(dataroom=self.get_object(), name=name, created_by=request.user)
        return Response({'id': str(folder.pk), 'name': folder.name}, status=201)
    def perform_destroy(self, instance):
        RoomPolicy.objects.filter(room=instance).update(status='archived')
        self.fact('room.archived', instance)


class OrgViewSet(StaffViewSet):
    serializer_class = OrgSerializer
    def get_queryset(self):
        return ViewerOrganisation.objects.filter(organization=self.request.user.organization).order_by('name')
    def save_org(self, serializer):
        domains = serializer.validated_data.get('email_domains', getattr(serializer.instance, 'email_domains', []))
        confirmed = serializer.validated_data.pop('confirm_domains', False)
        old = getattr(serializer.instance, 'email_domains', [])
        added = set(domains) - set(old)
        approval = getattr(self.request._request, '_dealroom_approval', None)
        staff = self.request.user if human_staff(self.request) else getattr(approval, 'approved_by', None)
        if added and (not confirmed or not staff):
            raise ValidationError('First use requires staff confirmation of the Unicode and A-label forms (confirm_domains=true).')
        for domain in domains:
            guarded_domain(domain)
            existing = DomainConfirmation.objects.filter(domain=domain).first()
            if existing and existing.organization_id != getattr(serializer.instance, 'pk', None):
                raise ValidationError('This domain is already bound to another recipient organization.')
        org = serializer.save(organization=self.request.user.organization, created_by=self.request.user)
        for domain in added:
            alabel, unicode_domain = guarded_domain(domain)
            DomainConfirmation.objects.create(domain=alabel, unicode_domain=unicode_domain, organization=org, confirmed_by=staff)
        self.fact('org.updated', org)
    perform_create = save_org
    perform_update = save_org


class MemberViewSet(StaffViewSet):
    serializer_class = MemberSerializer
    def get_queryset(self):
        return Viewer.objects.filter(organization=self.request.user.organization).order_by('email')
    def perform_create(self, serializer):
        member = serializer.save(organization=self.request.user.organization)
        self.fact('member.created', member)
    def perform_update(self, serializer):
        changed = any(k in serializer.validated_data and serializer.validated_data[k] != getattr(serializer.instance, k) for k in ('email', 'recipient_org'))
        member = serializer.save(**({'verified_at': None} if changed else {}))
        self.fact('member.updated', member)
    def perform_destroy(self, instance):
        instance.disabled_at = timezone.now()
        instance.save(update_fields=['disabled_at'])
        self.fact('member.disabled', instance)


class GrantViewSet(StaffViewSet):
    serializer_class = GrantSerializer
    def get_queryset(self):
        return ShareLinkAccessGrant.objects.filter(share_link__dataroom__organization=self.request.user.organization).order_by('created_at')
    def perform_create(self, serializer):
        room = serializer.validated_data.pop('room')
        policy = RoomPolicy.objects.get(room=room)
        grant = serializer.save(share_link=policy.entry_link, created_by=self.request.user)
        self.fact('grant.created', grant)
    def perform_update(self, serializer):
        serializer.validated_data.pop('room', None)
        grant = serializer.save()
        self.fact('grant.updated', grant)
    def perform_destroy(self, instance):
        instance.revoked_at = timezone.now()
        instance.save(update_fields=['revoked_at'])
        if instance.email:
            member = Viewer.objects.filter(organization=self.request.user.organization, email=instance.email).first()
            if member:
                MemberDeny.objects.get_or_create(room=instance.share_link.dataroom, member=member)
        self.fact('grant.revoked', instance)


class EntryLinkViewSet(StaffViewSet):
    serializer_class = EntryLinkSerializer
    def get_queryset(self):
        return ShareLink.objects.filter(dataroom__organization=self.request.user.organization).order_by('created_at')
    def perform_create(self, serializer):
        room = serializer.validated_data.get('dataroom')
        if not RoomPolicy.objects.filter(room=room).exists():
            raise ValidationError('Room policy required.')
        link = serializer.save(created_by=self.request.user, restrict_to_grants=True, requires_email=True, requires_email_verification=True, enable_watermark=True, enable_qna=False)
        canonical = room.roompolicy.entry_link
        for setting in canonical.dataroom_settings.all():
            ShareLinkDataroomSetting.objects.update_or_create(share_link=link, dataroom_document=setting.dataroom_document, dataroom_folder=setting.dataroom_folder, defaults={'is_visible':setting.is_visible, 'allow_download':setting.allow_download, 'enable_watermark':True})
        self.fact('share_link.created', link)
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        self.fact('share_link.revoked', instance)


class ApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = BoundedPagination
    serializer_class = ApprovalSerializer
    def get_queryset(self):
        return AccessApproval.objects.filter(agent_key__user__organization=self.request.user.organization).order_by('-created_at')
    @extend_schema(request=None, responses=dict)
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        from .approvals import execute
        approval = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
        result = execute(approval, request)
        return Response({'status': 'approved', 'result': result})
    @extend_schema(request=None, responses=dict)
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        approval = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
        if approval.status != 'pending_approval':
            raise ValidationError('Already decided.')
        approval.status = 'rejected'
        approval.approved_by = request.user
        approval.save()
        Drift.objects.filter(approval=approval).update(resolved_at=timezone.now())
        record('approval.rejected', organization=request.user.organization, actor=request.user, target_id=approval.pk)
        return Response({'status': 'rejected'})


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = BoundedPagination
    serializer_class = ActivitySerializer
    def get_queryset(self):
        return Activity.objects.filter(organization=self.request.user.organization)


class DriftViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DriftSerializer
    def get_queryset(self):
        return Drift.objects.filter(approval__agent_key__user__organization=self.request.user.organization).order_by('-pk')
    @extend_schema(request=None, responses=dict)
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        drift = self.get_object()
        drift.acknowledged_at = timezone.now()
        drift.save(update_fields=['acknowledged_at'])
        return Response({'status': 'acknowledged', 'access_approved': False})


class OperationViewSet(viewsets.ViewSet):
    @extend_schema(responses=dict)
    def list(self, request):
        return Response(list(registry().values()))
    @extend_schema(responses=dict)
    def retrieve(self, request, pk=None):
        from django.http import Http404
        if pk not in registry():
            raise Http404
        return Response(registry()[pk])


class CopyViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = BoundedPagination
    serializer_class = CopySerializer
    lookup_field = 'copy_id'
    def get_queryset(self):
        return IssuedCopy.objects.filter(share_link__dataroom__organization=self.request.user.organization).order_by('-created_at')


class FilePolicyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = FilePolicySerializer
    def get_queryset(self):
        return ShareLinkDataroomSetting.objects.filter(share_link__dataroom__organization=self.request.user.organization).order_by('pk')
    def perform_update(self, serializer):
        serializer.save(enable_watermark=True)


class OriginalExceptionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = OriginalExceptionSerializer
    def get_queryset(self):
        return OriginalException.objects.filter(room__organization=self.request.user.organization).order_by('-created_at')
    def perform_create(self, serializer):
        approval = getattr(self.request._request, '_dealroom_approval', None)
        approver = self.request.user if human_staff(self.request) else getattr(approval, 'approved_by', None)
        if not approver or not (approver.is_superuser or approver.role == 'admin'):
            raise PermissionDenied('Human staff administrator approval required.')
        obj = serializer.save(approved_by=approver)
        record('original_exception.approved', organization=self.request.user.organization, actor=self.request.user, room_id=obj.room_id, target_id=obj.pk)
    def perform_destroy(self, instance):
        instance.revoked_at = timezone.now()
        instance.save(update_fields=['revoked_at'])


class KeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['id', 'name', 'prefix', 'tier', 'expires_at', 'last_used_at']
        read_only_fields = ['id', 'prefix', 'last_used_at']


class AgentKeyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = KeySerializer
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user).order_by('-created_at')
    def validate_approval(self, request):
        if isinstance(request.auth, APIKey):
            parent = request.auth
            if TIERS.get(request.data.get('tier', 'read_only'), 99) > TIERS[parent.tier]:
                raise PermissionDenied('Child key cannot exceed parent tier.')
            expiry = request.data.get('expires_at')
            if parent.expires_at and (not expiry or serializers.DateTimeField().run_validation(expiry) > parent.expires_at):
                raise PermissionDenied('Child key cannot outlive parent.')
    def create(self, request):
        self.validate_approval(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw, prefix, hashed = generate_raw_api_key()
        key = serializer.save(user=request.user, prefix=prefix, hashed_key=hashed)
        if isinstance(request.auth, APIKey):
            parent_scope = KeyScope.objects.filter(key=request.auth).first()
            KeyScope.objects.create(key=key, parent=request.auth, operations=parent_scope.operations if parent_scope else None, rooms=parent_scope.rooms if parent_scope else None, recipient_orgs=parent_scope.recipient_orgs if parent_scope else None)
        record('agent_key.created', organization=request.user.organization, actor=request.user, target_id=key.pk)
        return Response({**self.get_serializer(key).data, 'key': raw}, status=201)
    def perform_destroy(self, instance):
        instance.expires_at = timezone.now()
        instance.save(update_fields=['expires_at'])


class PreferenceSerializer(serializers.Serializer):
    layout = serializers.ChoiceField(choices=['topbar','sidebar'])


class PreferencesView(APIView):
    @extend_schema(responses=PreferenceSerializer)
    def get(self, request):
        from .models import StaffPreference
        preference, _ = StaffPreference.objects.get_or_create(user=request.user)
        return Response({'layout':preference.layout})
    @extend_schema(request=PreferenceSerializer, responses=PreferenceSerializer)
    def patch(self, request):
        from .models import StaffPreference
        serializer=PreferenceSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        preference,_=StaffPreference.objects.update_or_create(user=request.user,defaults=serializer.validated_data)
        return Response({'layout':preference.layout})
