"""Phase-one domain state. Rooms, recipient orgs, members, grants and copies reuse Send models."""
import uuid
from django.db import models
from django.utils import timezone


class RoomPolicy(models.Model):
    room = models.OneToOneField('datarooms.Dataroom', on_delete=models.CASCADE, primary_key=True)
    entry_link = models.OneToOneField('sharelinks.ShareLink', on_delete=models.PROTECT)
    status = models.CharField(max_length=16, default='active')
    expires_at = models.DateTimeField(null=True, blank=True)
    invitation_mode = models.CharField(max_length=32, default='off')
    revision = models.PositiveIntegerField(default=1)


class MemberDeny(models.Model):
    room = models.ForeignKey('datarooms.Dataroom', on_delete=models.CASCADE)
    member = models.ForeignKey('sharelinks.Viewer', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['room', 'member'], name='dealroom_member_deny')]


class DomainConfirmation(models.Model):
    domain = models.CharField(max_length=253, unique=True)
    unicode_domain = models.CharField(max_length=253)
    organization = models.ForeignKey('sharelinks.ViewerOrganisation', on_delete=models.CASCADE)
    confirmed_by = models.ForeignKey('core.User', on_delete=models.PROTECT)
    confirmed_at = models.DateTimeField(auto_now_add=True)


class Challenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey('datarooms.Dataroom', on_delete=models.CASCADE)
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    code_hash = models.CharField(max_length=64)
    token_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True)


class IssuanceBudget(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    started_at = models.DateTimeField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE)
    event_type = models.CharField(max_length=100, db_index=True)
    actor_kind = models.CharField(max_length=16)
    actor_id = models.CharField(max_length=64)
    room_id = models.CharField(max_length=64, blank=True, db_index=True)
    target_id = models.CharField(max_length=64, blank=True)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']


class AccessApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_key = models.ForeignKey('core.APIKey', on_delete=models.PROTECT)
    operation_id = models.CharField(max_length=255)
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=1024)
    payload = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=32, default='pending_approval')
    approved_by = models.ForeignKey('core.User', null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    result = models.JSONField(default=dict)


class Drift(models.Model):
    approval = models.OneToOneField(AccessApproval, on_delete=models.CASCADE)
    acknowledged_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)


class OriginalException(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey('datarooms.Dataroom', on_delete=models.CASCADE)
    version = models.ForeignKey('documents.DocumentVersion', on_delete=models.PROTECT)
    member = models.ForeignKey('sharelinks.Viewer', on_delete=models.PROTECT)
    grant = models.ForeignKey('sharelinks.ShareLinkAccessGrant', on_delete=models.PROTECT)
    approved_by = models.ForeignKey('core.User', on_delete=models.PROTECT)
    reason = models.TextField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)
    max_uses = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class KeyScope(models.Model):
    key = models.OneToOneField('core.APIKey', on_delete=models.CASCADE, primary_key=True)
    parent = models.ForeignKey('core.APIKey', null=True, on_delete=models.PROTECT, related_name='children_scopes')
    operations = models.JSONField(null=True, default=None)
    rooms = models.JSONField(null=True, default=None)
    recipient_orgs = models.JSONField(null=True, default=None)


class CopyEvidence(models.Model):
    copy = models.OneToOneField('sharelinks.IssuedCopy', primary_key=True, on_delete=models.PROTECT, related_name='evidence')
    version = models.ForeignKey('documents.DocumentVersion', on_delete=models.PROTECT)
    brand_revision = models.CharField(max_length=64)
    source_sha256 = models.CharField(max_length=64, blank=True)
    artifact_sha256 = models.CharField(max_length=64, blank=True)
    receipt_sha256 = models.CharField(max_length=64, blank=True)
    original_exception = models.ForeignKey(OriginalException, null=True, on_delete=models.PROTECT)
