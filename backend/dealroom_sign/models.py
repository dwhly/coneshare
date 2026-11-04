"""Local integration state only. Signing evidence remains authoritative in Sign."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django_cryptography.fields import encrypt


class SignCredential(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    team_id = models.PositiveIntegerField()
    token = encrypt(models.TextField())
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class NdaPolicy(models.Model):
    room = models.OneToOneField('datarooms.Dataroom', on_delete=models.CASCADE)
    revision = models.UUIDField(default=uuid.uuid4, editable=False)
    source_version = models.ForeignKey('documents.DocumentVersion', on_delete=models.PROTECT)
    source_sha256 = models.CharField(max_length=64)
    # Explicit sender-selected fields; never infer a position on the document.
    fields = models.JSONField(default=list)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    room = models.ForeignKey('datarooms.Dataroom', on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=200)
    request_sha256 = models.CharField(max_length=64)
    purpose = models.CharField(max_length=24)  # nda | room_document
    member_id = models.CharField(max_length=64, blank=True)
    member_email = models.EmailField(blank=True)
    policy_revision = models.CharField(max_length=64, blank=True)
    source_version = models.ForeignKey('documents.DocumentVersion', on_delete=models.PROTECT)
    source_sha256 = models.CharField(max_length=64)
    recipients = models.JSONField(default=list)  # never tokens
    title = models.CharField(max_length=255)
    external_id = models.CharField(max_length=255, unique=True)
    envelope_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    item_ids = models.JSONField(default=list)
    state = models.CharField(max_length=24, default='queued', db_index=True)
    source_status = models.CharField(max_length=32, blank=True)
    signer_projection = models.JSONField(default=list)
    signing_token = encrypt(models.TextField(blank=True))
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=100, blank=True)  # safe code, not upstream body
    created_at = models.DateTimeField(auto_now_add=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'idempotency_key'], name='sign_command_idempotency')]


class ExecutedArtifact(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name='artifacts')
    item_id = models.CharField(max_length=100)
    kind = models.CharField(max_length=24)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField()
    version = models.OneToOneField('documents.DocumentVersion', on_delete=models.PROTECT)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workflow', 'item_id', 'kind'], name='sign_immutable_artifact')]


class NdaAcceptance(models.Model):
    room = models.ForeignKey('datarooms.Dataroom', on_delete=models.PROTECT)
    member_id = models.CharField(max_length=64)
    member_email = models.EmailField()
    policy_revision = models.CharField(max_length=64)
    workflow = models.OneToOneField(Workflow, on_delete=models.PROTECT)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['room', 'member_id', 'policy_revision'], name='sign_nda_revision_acceptance')]


class ObservedSignEvent(models.Model):
    """Dedup keys for authoritative Sign audit facts, not webhook payloads."""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    source_id = models.CharField(max_length=200)
    kind = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workflow', 'source_id', 'kind'], name='sign_observed_fact')]
