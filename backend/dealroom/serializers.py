from django.utils import timezone
from rest_framework import serializers
from sharelinks.models import ViewerOrganisation, Viewer, ShareLinkAccessGrant, ShareLink, IssuedCopy, ShareLinkDataroomSetting
from datarooms.models import Dataroom
from .models import AccessApproval, Activity, Drift, OriginalException
from .domains import guarded_domain


class RoomSerializer(serializers.ModelSerializer):
    entry_url = serializers.SerializerMethodField()
    class Meta:
        model = Dataroom
        fields = ['id', 'name', 'entry_url']
        read_only_fields = ['id', 'entry_url']
    def get_entry_url(self, obj):
        policy = getattr(obj, 'roompolicy', None)
        return f'/view/{policy.entry_link.slug}' if policy else None


class OrgSerializer(serializers.ModelSerializer):
    confirm_domains = serializers.BooleanField(write_only=True, default=False)
    class Meta:
        model = ViewerOrganisation
        fields = ['id', 'name', 'email_domains', 'confirm_domains']
        read_only_fields = ['id']
    def validate_email_domains(self, values):
        return [guarded_domain(value)[0] for value in values]


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Viewer
        fields = ['id', 'name', 'email', 'recipient_org', 'verified_at', 'disabled_at']
        read_only_fields = ['id', 'verified_at']
    def validate_recipient_org(self, org):
        if org and org.organization_id != self.context['request'].user.organization_id:
            raise serializers.ValidationError('Wrong organization.')
        return org
    def validate_email(self, value):
        return value.strip().lower()


class GrantSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Dataroom.objects.all(), write_only=True)
    class Meta:
        model = ShareLinkAccessGrant
        fields = ['id', 'room', 'share_link', 'viewer_organisation', 'email', 'download_ceiling', 'expires_at', 'revoked_at']
        read_only_fields = ['id', 'share_link']
        validators = []
    def validate(self, data):
        tenant = self.context['request'].user.organization_id
        room = data.get('room')
        if not self.instance and not room:
            raise serializers.ValidationError('room is required')
        if room and room.organization_id != tenant:
            raise serializers.ValidationError('Wrong room.')
        if self.instance and room and self.instance.share_link.dataroom_id != room.pk:
            raise serializers.ValidationError('Grant room cannot be rebound.')
        org = data.get('viewer_organisation', getattr(self.instance, 'viewer_organisation', None))
        email = data.get('email', getattr(self.instance, 'email', ''))
        if bool(org) == bool(email):
            raise serializers.ValidationError('Specify exactly one recipient org or email.')
        if org and org.organization_id != tenant:
            raise serializers.ValidationError('Wrong recipient organization.')
        if data.get('download_ceiling', 'none') not in ('none', 'watermarked', 'original'):
            raise serializers.ValidationError('Invalid download ceiling.')
        return data


class EntryLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareLink
        fields = ['id', 'dataroom', 'name', 'slug', 'expires_at', 'is_active']
        read_only_fields = ['id', 'slug']
    def validate_dataroom(self, room):
        if not room or room.organization_id != self.context['request'].user.organization_id:
            raise serializers.ValidationError('Wrong room.')
        if self.instance and self.instance.dataroom_id != room.pk:
            raise serializers.ValidationError('Entry link room cannot be rebound.')
        return room


class ApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessApproval
        fields = ['id', 'operation_id', 'method', 'path', 'payload', 'payload_hash', 'status', 'created_at', 'expires_at', 'result']
        read_only_fields = fields


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'


class DriftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drift
        fields = '__all__'


class CopySerializer(serializers.ModelSerializer):
    issued_to = serializers.SerializerMethodField()
    class Meta:
        model = IssuedCopy
        fields = ['copy_id', 'issued_to', 'kind', 'document', 'created_at']
    def get_issued_to(self, obj):
        return {'name': obj.viewer_name, 'email': obj.viewer_email, 'org': obj.viewer_organisation_name, 'meaning': 'issued to; not proof of who disclosed it'}


class FilePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareLinkDataroomSetting
        fields = ['id', 'share_link', 'dataroom_document', 'dataroom_folder', 'is_visible', 'allow_download']
        read_only_fields = ['id', 'share_link', 'dataroom_document', 'dataroom_folder']


class OriginalExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OriginalException
        fields = ['id', 'room', 'version', 'member', 'grant', 'reason', 'expires_at', 'max_uses', 'used_count', 'revoked_at']
        read_only_fields = ['id', 'used_count']
    def validate(self, data):
        from datetime import timedelta
        from datarooms.models import DataroomDocument
        tenant = self.context['request'].user.organization_id
        room, member, grant, version = (data.get(k, getattr(self.instance, k, None)) for k in ('room','member','grant','version'))
        expiry = data.get('expires_at', getattr(self.instance, 'expires_at', None))
        if not expiry or not timezone.now() < expiry <= timezone.now() + timedelta(days=7):
            raise serializers.ValidationError('Expiry must be in the next seven days.')
        if room.organization_id != tenant or member.organization_id != tenant or grant.share_link.dataroom_id != room.pk or not DataroomDocument.objects.filter(dataroom=room, document_id=version.document_id).exists():
            raise serializers.ValidationError('Exception target mismatch.')
        if data.get('max_uses', 1) < 1 or data.get('max_uses', 1) > 100:
            raise serializers.ValidationError('Use bound must be 1–100.')
        if not data.get('reason', getattr(self.instance, 'reason', '')).strip():
            raise serializers.ValidationError('Reason required.')
        return data
