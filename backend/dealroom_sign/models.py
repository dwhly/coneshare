"""Local integration state only. Signing evidence remains authoritative in Sign."""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
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
    occurred_at = models.DateTimeField(null=True, default=None)
    actor_email = models.EmailField(null=True, default=None)
    name = models.CharField(max_length=255, null=True, default=None)
    recipient_id = models.CharField(max_length=100, null=True, default=None)
    ip_address = models.GenericIPAddressField(null=True, default=None)
    user_agent = models.TextField(null=True, default=None)
    payload = models.JSONField(default=dict)
    schema_version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workflow', 'source_id', 'kind'], name='sign_observed_fact')]


def validate_room_capabilities(value):
    if not isinstance(value, list) or any(v not in ('read', 'write') for v in value):
        raise ValidationError('Room capabilities must be a list containing only read and write.')


class BoardStaffBinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board_id = models.CharField(max_length=100)
    login = models.CharField(max_length=254)
    send_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    signer_email = models.EmailField()
    enabled = models.BooleanField(default=True)
    room_capabilities = models.JSONField(default=list, blank=True, validators=[validate_room_capabilities])
    role = models.CharField(max_length=16, choices=[('reader', 'Reader'), ('writer', 'Writer'), ('manager', 'Manager')])

    def clean(self):
        super().clean()
        # JSONField(blank=True) skips field validators for empty objects/strings.
        if not isinstance(self.room_capabilities, list):
            raise ValidationError({'room_capabilities': 'Room capabilities must be a list.'})

    class Meta:
        constraints = [models.UniqueConstraint(fields=['board_id', 'login'], name='sign_board_login')]


class SignatureRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board_id = models.CharField(max_length=100)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    collaborator_ids = models.JSONField(default=list)
    workflow = models.OneToOneField(Workflow, null=True, on_delete=models.PROTECT, related_name='signature_request')
    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=16, default='unknown', choices=[('in', 'Incoming'), ('out', 'Outgoing'), ('std', 'Standard'), ('unknown', 'Unknown')])
    task_ref = models.JSONField(null=True, default=None)
    room = models.ForeignKey('datarooms.Dataroom', null=True, on_delete=models.PROTECT)
    source_context = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=24)
    previous_request = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    audit_complete = models.BooleanField(default=False)
    audit_as_of = models.DateTimeField(null=True, default=None)

    class Meta:
        indexes = [models.Index(fields=['board_id', 'state', 'created_at'], name='sign_request_board_state')]


class RequestArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(SignatureRequest, on_delete=models.PROTECT, related_name='snapshots')
    kind = models.CharField(max_length=24)
    snapshot_id = models.CharField(max_length=64)
    item_id = models.CharField(max_length=100)
    version = models.ForeignKey('documents.DocumentVersion', on_delete=models.PROTECT)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField()
    as_of = models.DateTimeField(default=timezone.now)
    source_sha256 = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['request', 'kind', 'snapshot_id'], name='sign_request_snapshot')]


class SignerAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name='signer_accesses')
    request = models.ForeignKey(SignatureRequest, null=True, on_delete=models.PROTECT)
    revision = models.CharField(max_length=64)
    native_recipient_id = models.CharField(max_length=100)
    native_token = encrypt(models.TextField())
    generation = models.PositiveBigIntegerField(default=1)
    capability_hash = models.CharField(max_length=64, unique=True)
    alternate_hash = models.CharField(max_length=64, unique=True)
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=16, default='SIGNER')
    sender = models.JSONField(default=dict)
    sending_staff = models.JSONField(default=dict)
    context = models.JSONField(default=dict)
    required_auth = models.CharField(max_length=16, default='link')
    released_at = models.DateTimeField()
    signing_expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
    room_expires_at = models.DateTimeField(null=True)
    revoked_at = models.DateTimeField(null=True)
    revocation_reason = models.CharField(max_length=500, blank=True)
    invite_state = models.CharField(max_length=24, default='pending')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workflow', 'revision', 'native_recipient_id'],
            name='sign_access_recipient_revision')]


class SignerSession(models.Model):
    session_hash = models.CharField(max_length=64, primary_key=True)
    access = models.ForeignKey(SignerAccess, on_delete=models.CASCADE, related_name='sessions')
    generation = models.PositiveBigIntegerField()
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    idle_expires_at = models.DateTimeField()
    code_verified_at = models.DateTimeField(null=True)
    disclosure_hash = models.CharField(max_length=64, blank=True)
    consented_at = models.DateTimeField(null=True)


class SignerHandoff(models.Model):
    token_hash = models.CharField(max_length=64, primary_key=True)
    access = models.ForeignKey(SignerAccess, on_delete=models.CASCADE)
    generation = models.PositiveBigIntegerField()
    viewer_id = models.CharField(max_length=64)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    revision = models.CharField(max_length=64)
    native_recipient_id = models.CharField(max_length=100)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)


class SignerChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access = models.ForeignKey(SignerAccess, on_delete=models.CASCADE)
    session = models.ForeignKey(SignerSession, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(default=timezone.now)


class CounterpartyEffect(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access = models.ForeignKey(SignerAccess, on_delete=models.PROTECT, related_name='effects')
    kind = models.CharField(max_length=24)
    source_id = models.CharField(max_length=200)
    state = models.CharField(max_length=24, default='pending', db_index=True)
    message_id = models.CharField(max_length=254)
    payload_hash = models.CharField(max_length=64, blank=True)
    last_error = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['access', 'kind', 'source_id'], name='sign_counterparty_effect')]
