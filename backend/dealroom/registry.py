"""Normative operation classification; unknown operations are denied, unknown edits widen.

Worker C: add explicit RULES entries and regenerate the checked-in registry with
`manage.py dealroom_registry --write`; every enabled operation must have a tool.
"""
import json
from pathlib import Path
from drf_spectacular.openapi import AutoSchema

TIERS = {'read_only': 0, 'read_write': 1, 'full_access': 2}


class OperationSchema(AutoSchema):
    def get_operation_id(self):
        view = self.view
        return operation_id(view, self.method)


def operation_id(view, method):
    return f'{type(view).__module__.split(".")[0]}_{type(view).__name__}_{getattr(view, "action", None) or "endpoint"}_{method.lower()}'


# Widening predicates below are used on canonical serialized old state + validated new fields.
# Unknown keys (including nested policy changes) are conservatively widening.
SAFE_EDITS = {'name', 'description', 'reason'}

def widens_access(operation, before, after):
    classification = operation.get('widens_access', True)
    if classification is False:
        return False
    if classification is True:
        return True
    rank = {'none': 0, 'watermarked': 1, 'original': 2}
    invitation = {'off': 0, 'owner_approved': 1, 'automatic_same_org': 2}
    for key, value in after.items():
        old = before.get(key)
        if old == value or key in SAFE_EDITS:
            continue
        if key in ('download_ceiling',):
            if rank.get(value, 99) > rank.get(old, -1):
                return True
        elif key in ('expires_at',):
            if value is None:
                return True
            if old is not None:
                from datetime import datetime, timezone
                try:
                    def instant(v):
                        parsed = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
                        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
                    if instant(value) > instant(old):
                        return True
                except (ValueError, TypeError):
                    return True
        elif key in ('revoked_at', 'disabled_at'):
            if value is None:
                return True
        elif key == 'status':
            if value == 'active':
                return True
        elif key == 'is_active':
            if value:
                return True
        elif key == 'invitation_mode':
            if invitation.get(value, 99) > invitation.get(old, -1):
                return True
        elif key in ('email', 'email_normalized', 'recipient', 'member', 'viewer_organisation', 'organization', 'recipient_org', 'signer_email', 'url', 'destination_url', 'webhook_url', 'password', 'scope'):
            return True
        elif key in ('email_domains', 'domains'):
            if set(value or []) - set(old or []):
                return True
        elif key in ('allow_download', 'allow_original_download'):
            if value:
                return True
        elif key in ('requires_email', 'requires_email_verification', 'restrict_to_grants', 'enable_watermark'):
            if not value:
                return True
        elif key in ('is_visible', 'audiences'):
            # Existing grantees seeing new files is not a new subject or original permission.
            continue
        else:
            return True
    return False


PUBLIC = {'CustomTokenObtainPairView', 'TokenRefreshView', 'LanguagesView', 'PublicSettingsView', 'HealthCheckView', 'BrandView', 'RecipientChallengeView', 'RecipientConfirmView', 'RecipientRoomView', 'RecipientLogoutView', 'OriginalDownloadView'}
RECIPIENT = {'ShareLinkViewDataView', 'ShareLinkPublicMetaView', 'ShareLinkQnAThreadListCreateView', 'ShareLinkQnASummaryView', 'ShareLinkQnAMessageListCreateView', 'ShareLinkVerifyPasswordView', 'ShareLinkAcceptNDAView', 'ShareLinkRequestAccessView', 'ShareLinkConfirmAccessView', 'ShareLinkPageView', 'WatermarkedPageRenderView', 'ShareLinkFileDownloadView', 'DataroomFolderDownloadView', 'DataroomDownloadAllView', 'RecordPageView', 'RecordLinkClickView', 'ViewSessionViewSet'}
# All enabled staff surfaces have parity tools; remaining upstream surfaces are denied.
STAFF = {'RoomViewSet', 'OrgViewSet', 'MemberViewSet', 'GrantViewSet', 'EntryLinkViewSet', 'ApprovalViewSet', 'ActivityViewSet', 'DriftViewSet', 'OperationViewSet', 'CopyViewSet', 'AgentKeyViewSet', 'OriginalExceptionViewSet', 'FilePolicyViewSet'}
UPSTREAM_READ = {'DataroomViewSet', 'DataroomFolderViewSet', 'DataroomDocumentViewSet', 'DocumentViewSet', 'FolderViewSet', 'OrganizationViewSet', 'UserViewSet'}
HUMAN_ONLY = {('ApprovalViewSet', 'approve'), ('ApprovalViewSet', 'reject')}


def classify(view, method):
    name = type(view).__name__
    action = getattr(view, 'action', None) or method.lower()
    read = method in ('GET', 'HEAD', 'OPTIONS')
    entry = {'operation_id': operation_id(view, method), 'tier': 'read_only' if read else 'read_write', 'widens_access': False if read or method == 'DELETE' else 'evaluate_change', 'human_only': False, 'boundary': 'denied', 'reason': 'Deferred or operator-only surface; phase 1.'}
    if name in PUBLIC:
        entry.update(boundary='public', reason='Authentication/presentation or recipient-proof boundary.', widens_access=False)
    elif name in RECIPIENT:
        entry.update(boundary='recipient', reason='Central recipient policy; unsupported legacy actions denied.', widens_access=False)
    elif name in STAFF or (name in UPSTREAM_READ and read):
        entry.update(boundary='staff', reason='Phase-one staff business operation.')
    if name == 'RoomViewSet' and action in ('upload', 'folders'):
        entry['widens_access'] = False
    if name in STAFF and action == 'create':
        entry['widens_access'] = name not in {'RoomViewSet'}
    if name in {'ApprovalViewSet', 'AgentKeyViewSet', 'OriginalExceptionViewSet'} and not read:
        entry['tier'] = 'full_access'
    if name == 'ApprovalViewSet' or (name, action) in HUMAN_ONLY:
        entry['human_only'] = True
    if name == 'DriftViewSet' and action == 'acknowledge':
        entry['widens_access'] = False
    if name == 'AgentKeyViewSet' and action in ('create', 'rotate'):
        # Key material is returned only in a staff JWT response. Agents can request a bounded child via approval.
        entry['widens_access'] = True
    return entry


def registry():
    path = Path(__file__).with_name('operations.json')
    return json.loads(path.read_text()) if path.exists() else {}


def resolve_operation(view, method):
    return registry().get(operation_id(view, method))
