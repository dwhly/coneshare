from rest_framework import serializers

from .models import NdaPolicy, Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    artifacts = serializers.SerializerMethodField()

    def get_artifacts(self, obj):
        return list(obj.artifacts.values('kind', 'sha256', 'size', 'version_id'))

    class Meta:
        model = Workflow
        fields = ['id', 'room_id', 'purpose', 'envelope_id', 'state', 'source_status', 'signer_projection',
                  'created_at', 'reconciled_at', 'completed_at', 'last_error', 'artifacts']
        read_only_fields = fields


class SendInputSerializer(serializers.Serializer):
    room_id = serializers.CharField(max_length=64)
    version_id = serializers.CharField(max_length=64)
    idempotency_key = serializers.CharField(max_length=200)
    recipients = serializers.ListField(child=serializers.DictField(), min_length=1, max_length=20)


class NdaPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = NdaPolicy
        fields = ['room_id', 'revision', 'source_version_id', 'source_sha256', 'fields', 'enabled']
        read_only_fields = fields
