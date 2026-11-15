from django.db.models import F
from rest_framework import serializers

from .client import SignError
from .models import NdaPolicy, Workflow
from .presentation import clean_title, requester_snapshot


class WorkflowSerializer(serializers.ModelSerializer):
    artifacts = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()

    def get_artifacts(self, obj):
        # document_id lets a front end (the board's Sign tab) fetch the signed copy through the documents API.
        return list(obj.artifacts.values('kind', 'sha256', 'size', 'version_id', document_id=F('version__document_id')))

    def get_recipients(self, obj):
        # Who the sender asked to sign (name + email only; field placement and tokens stay private).
        return [{'name': r.get('name', ''), 'email': r.get('email', '')} for r in (obj.recipients or [])]

    class Meta:
        model = Workflow
        fields = ['id', 'room_id', 'purpose', 'title', 'recipients', 'envelope_id', 'state', 'member_email', 'source_status',
                  'signer_projection', 'created_at', 'reconciled_at', 'completed_at', 'last_error', 'artifacts']
        read_only_fields = fields


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError({'non_field_errors': ['Unsupported input property.']})
        return super().to_internal_value(data)


class FieldInputSerializer(StrictInputSerializer):
    type = serializers.ChoiceField(choices=['SIGNATURE', 'FREE_SIGNATURE', 'INITIALS', 'NAME', 'EMAIL', 'DATE', 'TEXT', 'NUMBER', 'RADIO', 'CHECKBOX', 'DROPDOWN'])
    page = serializers.IntegerField(min_value=1, max_value=500)
    positionX = serializers.FloatField(min_value=0, max_value=100)
    positionY = serializers.FloatField(min_value=0, max_value=100)
    width = serializers.FloatField(min_value=0.01, max_value=100)
    height = serializers.FloatField(min_value=0.01, max_value=100)
    identifier = serializers.IntegerField(default=0, min_value=0, max_value=0)


class SignerInputSerializer(StrictInputSerializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=200)
    role = serializers.ChoiceField(choices=['SIGNER'], default='SIGNER')
    signingOrder = serializers.IntegerField(min_value=1, max_value=20, default=1)
    fields = FieldInputSerializer(many=True, required=False)
    company = serializers.CharField(max_length=200, required=False, allow_blank=True)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)


class CredentialInputSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512, write_only=True)
    team_id = serializers.IntegerField(min_value=1)


class NdaPolicyInputSerializer(serializers.Serializer):
    version_id = serializers.CharField(max_length=64)
    fields = FieldInputSerializer(many=True)
    enabled = serializers.BooleanField(default=True)


class TaskReferenceSerializer(StrictInputSerializer):
    id = serializers.CharField(max_length=500)
    title = serializers.CharField(max_length=500, required=False, allow_blank=True)


class SendInputSerializer(StrictInputSerializer):
    room_id = serializers.CharField(max_length=64)
    version_id = serializers.CharField(max_length=64)
    idempotency_key = serializers.CharField(max_length=200)
    recipients = SignerInputSerializer(many=True)
    placement = serializers.ChoiceField(choices=['auto', 'sender'], required=False)
    board_id = serializers.CharField(max_length=100, required=False)
    task_ref = TaskReferenceSerializer(required=False, allow_null=True)
    requester = serializers.JSONField(required=False)
    title = serializers.CharField(max_length=500, required=False)

    def validate_requester(self, value):
        try:
            return requester_snapshot(value)
        except SignError:
            raise serializers.ValidationError('A requester name and valid email are required.') from None

    def validate_title(self, value):
        return clean_title(value)

    def validate(self, data):
        if 'task_ref' in data and not data.get('board_id'):
            raise serializers.ValidationError('A task reference requires a board ID.')
        if any(field in data for field in ('requester', 'title')) and not data.get('board_id'):
            raise serializers.ValidationError('Sender metadata requires a board ID.')
        return data


class NdaPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = NdaPolicy
        fields = ['room_id', 'revision', 'source_version_id', 'source_sha256', 'fields', 'enabled']
        read_only_fields = fields


class SignatureExportInputSerializer(StrictInputSerializer):
    request_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=1)
    kind = serializers.ChoiceField(choices=['original', 'partial', 'final', 'certificate', 'audit'])
    format = serializers.ChoiceField(choices=['pdf'])
    snapshot_id = serializers.CharField(max_length=64, required=False)
    reason = serializers.CharField(max_length=500, default='Request page download')
