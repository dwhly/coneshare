"""One policy service for all recipient operations; no owner/account or preview-token shortcut."""
from dataclasses import dataclass
from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from sharelinks.models import ShareLink, Viewer, ViewSession
from .models import RoomPolicy, MemberDeny

LEVELS = {'none': 0, 'watermarked': 1, 'original': 2}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    grant_id: str = ''
    policy_revision: int = 0
    effective_download_level: str = 'none'
    member_id: str = ''


def select_grant(link, email):
    try:
        policy = RoomPolicy.objects.select_related('room', 'entry_link').get(room_id=link.dataroom_id)
    except RoomPolicy.DoesNotExist:
        raise PermissionDenied('Room policy is not configured.')
    now = timezone.now()
    if not link.is_active or (link.expires_at and link.expires_at <= now) or policy.status != 'active' or (policy.expires_at and policy.expires_at <= now):
        raise PermissionDenied('Room is unavailable.')
    member = Viewer.objects.filter(organization=link.organization, email=email).first()
    if member and (member.disabled_at or MemberDeny.objects.filter(room=policy.room, member=member).exists()):
        raise PermissionDenied('Member access is revoked.')
    grants = list(policy.entry_link.access_grants.select_related('viewer_organisation').filter(revoked_at__isnull=True))
    grants = [g for g in grants if not g.expires_at or g.expires_at > now]
    named = [g for g in grants if g.email == email]
    orgs = [g for g in grants if g.viewer_organisation and g.viewer_organisation.matches_email(email)]
    if len(orgs) > 1:
        raise PermissionDenied('Ambiguous recipient organization.')
    grant = (named or orgs or [None])[0]
    if grant is None:
        raise PermissionDenied('Your verified email is not granted access to this room.')
    return policy, grant, member


def evaluate(request, link, *, document_id=None, download=False, skip_nda=False):
    proof = request.session.get('dealroom_member', {})
    now = timezone.now().timestamp()
    if (proof.get('room_id') != str(link.dataroom_id) or now > proof.get('expires', 0) or now - proof.get('last_seen', 0) > 1800):
        raise NotAuthenticated('Email verification required.')
    policy, grant, member = select_grant(link, proof.get('email', ''))
    if member is None or str(member.pk) != proof.get('member_id') or not member.verified_at:
        raise PermissionDenied('Recipient identity has changed; verify again.')
    from django.apps import apps
    sign_enabled = apps.is_installed('dealroom_sign')
    if sign_enabled and not skip_nda:
        from dealroom_sign.policy import check_nda
        check_nda(policy.room, member)
    level = grant.download_ceiling
    if document_id:
        from sharelinks.models import ShareLinkDataroomSetting
        from sharelinks.views import _is_dataroom_folder_path_visible
        setting = ShareLinkDataroomSetting.objects.select_related('dataroom_document__document', 'dataroom_document__folder').filter(share_link=link, dataroom_document_id=document_id, dataroom_document__dataroom_id=link.dataroom_id, is_visible=True).first()
        if not setting or not _is_dataroom_folder_path_visible(link, setting.dataroom_document.folder):
            raise PermissionDenied('Document is not visible to this recipient.')
        if sign_enabled:
            from dealroom_sign.policy import artifact_allowed
            if artifact_allowed(setting.dataroom_document.document_id, member) is False:
                raise PermissionDenied('Execution artifact is private to its subject.')
        if setting.dataroom_document.document.deleted_at:
            raise PermissionDenied('Document is unavailable.')
        file_level = setting.download_ceiling if setting.allow_download else 'none'
        level = min((level, file_level), key=lambda v: LEVELS.get(v, 0))
    if download and level == 'none':
        raise PermissionDenied('Downloads are disabled.')
    proof['last_seen'] = now
    request.session['dealroom_member'] = proof
    return Decision(True, 'granted', str(grant.pk), policy.revision, level, str(member.pk))


def guard_recipient(request, view):
    """Called by the central DRF hook even on AllowAny and dynamic permissions branches."""
    name = type(view).__name__
    # The legacy OTP, public metadata, raw page/capability, Q&A, ZIP, analytics and upload paths
    # are explicit exclusions. The new recipient API releases no metadata before OTP.
    if name not in {'WatermarkedPageRenderView', 'ShareLinkFileDownloadView'}:
        raise PermissionDenied('This recipient operation is not enabled in phase 1; use the room entry route.')
    link = ShareLink.objects.filter(slug=view.kwargs.get('slug')).first()
    if not link:
        raise PermissionDenied('Room is unavailable.')
    decision = evaluate(request, link, document_id=request.query_params.get('dataroom_document_id'), download=name == 'ShareLinkFileDownloadView')
    if not request.query_params.get('dataroom_document_id'):
        raise PermissionDenied('A room document is required.')
    request.dealroom_decision = decision
    return decision
