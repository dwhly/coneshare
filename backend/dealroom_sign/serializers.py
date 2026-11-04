from rest_framework import serializers

from .models import NdaPolicy, Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    artifacts = serializers.SerializerMethodField()

    def get_artifacts(self, obj):
        return list(obj.artifacts.values('kind', 'sha256', 'size', 'version_id'))

    class Meta:
        model = Workflow
        fields = ['id', 'room_id', 'purpose', 'envelope_id', 'state', 'member_email', 'source_status', 'signer_projection',
                  'created_at', 'reconciled_at', 'completed_at', 'last_error', 'artifacts']
        read_only_fields = fields


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError('Unsupported input property.')
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
    fields = FieldInputSerializer(many=True)


class CredentialInputSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512, write_only=True)
    team_id = serializers.IntegerField(min_value=1)


class NdaPolicyInputSerializer(serializers.Serializer):
    version_id = serializers.CharField(max_length=64)
    fields = FieldInputSerializer(many=True)
    enabled = serializers.BooleanField(default=True)


class SendInputSerializer(StrictInputSerializer):
    room_id = serializers.CharField(max_length=64)
    version_id = serializers.CharField(max_length=64)
    idempotency_key = serializers.CharField(max_length=200)
    recipients = SignerInputSerializer(many=True)


class NdaPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = NdaPolicy
        fields = ['room_id', 'revision', 'source_version_id', 'source_sha256', 'fields', 'enabled']
        read_only_fields = fields
