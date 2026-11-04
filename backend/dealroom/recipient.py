import hashlib
import hmac
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import serializers, permissions
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied, Throttled
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from sharelinks.models import ShareLink, Viewer, ViewSession, ShareLinkDataroomSetting
from backend.utils import get_client_ip
from .models import Challenge, IssuanceBudget
from .policy import select_grant, evaluate
from .brand import load_brand
from .activity import record


class ChallengeInput(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=255, allow_blank=True, default='')


class ConfirmInput(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.RegexField(r'^\d{6}$', required=False)
    token = serializers.CharField(max_length=128, required=False)


def csrf(request):
    check = CSRFCheck(lambda req: None)
    check.process_request(request._request)
    reason = check.process_view(request._request, lambda req: None, (), {})
    if reason:
        raise PermissionDenied(f'CSRF failed: {reason}')


def keyed(value):
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def get_link(slug):
    from django.shortcuts import get_object_or_404
    return get_object_or_404(ShareLink, slug=slug, dataroom__isnull=False)


def reserve_budget(scope, limit):
    key = hashlib.sha256(scope.encode()).hexdigest()
    budget, _ = IssuanceBudget.objects.get_or_create(key=key)
    budget = IssuanceBudget.objects.select_for_update().get(pk=budget.pk)
    now = timezone.now()
    if now - budget.started_at >= timedelta(hours=1):
        budget.count, budget.started_at = 0, now
    if budget.count >= limit:
        raise Throttled(wait=3600)
    budget.count += 1
    budget.save()


class RecipientChallengeView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses=dict)
    def get(self, request, slug):
        # A scanner may GET this or the SPA with a token; neither consumes a challenge.
        return Response({'csrf_token': get_token(request), 'brand': load_brand()})

    @extend_schema(request=ChallengeInput, responses=dict)
    def post(self, request, slug):
        csrf(request)
        data = ChallengeInput(data=request.data)
        data.is_valid(raise_exception=True)
        link = get_link(slug)
        email = data.validated_data['email'].strip().lower()
        with transaction.atomic():
            # Lock in consistent order; REMOTE_ADDR comes from the private edge, not caller XFF.
            reserve_budget('ip:' + (get_client_ip(request) or ''), 20)
            reserve_budget(f'email:{link.dataroom_id}:{email}', 5)
            challenge = Challenge(room=link.dataroom, email=email, name=data.validated_data['name'], expires_at=timezone.now() + timedelta(minutes=10))
            code, token = f'{secrets.randbelow(1000000):06d}', secrets.token_urlsafe(32)
            challenge.code_hash = keyed(f'{challenge.id}:{code}')
            challenge.token_hash = keyed(f'{challenge.id}:{token}')
            challenge.save()
            brand = load_brand()
            origin = getattr(settings, 'SITE_DOMAIN', '').rstrip('/')
            message = f'Your {brand["name"]} verification code is {code}. It expires in 10 minutes.\n\nConfirm explicitly at {origin}/view/{slug}?challenge={challenge.id}&token={token}\nOpening this link does not sign you in.'
            transaction.on_commit(lambda: send_mail(f'{brand["name"]}: your verification code', message, brand['email_sender'], [email]))
        # Same response and delivery whether or not the email currently has a grant.
        return Response({'status': 'code_sent', 'challenge_id': str(challenge.pk)})


class RecipientConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(request=ConfirmInput, responses=dict)
    def post(self, request, slug):
        csrf(request)
        data = ConfirmInput(data=request.data)
        data.is_valid(raise_exception=True)
        link = get_link(slug)
        challenge = Challenge.objects.select_for_update().filter(pk=data.validated_data['challenge_id'], room_id=link.dataroom_id).first()
        refused = {'status': 'refused', 'message': 'Code invalid, expired, or this verified email is not granted access.'}
        if not challenge or challenge.consumed_at or challenge.expires_at <= timezone.now() or challenge.attempts >= 5:
            return Response(refused)
        challenge.attempts += 1
        code = data.validated_data.get('code', '')
        token = data.validated_data.get('token', '')
        correct = bool(code and hmac.compare_digest(challenge.code_hash, keyed(f'{challenge.pk}:{code}'))) or bool(token and hmac.compare_digest(challenge.token_hash, keyed(f'{challenge.pk}:{token}')))
        if correct or challenge.attempts >= 5:
            challenge.consumed_at = timezone.now()
        challenge.save(update_fields=['attempts', 'consumed_at'])
        if not correct:
            return Response(refused)
        try:
            policy, grant, member = select_grant(link, challenge.email)
        except PermissionDenied:
            return Response(refused)
        member, _ = Viewer.objects.get_or_create(organization=link.organization, email=challenge.email)
        member.name = challenge.name or member.name or challenge.email
        member.verified_at = timezone.now()
        if grant.viewer_organisation_id:
            member.recipient_org = grant.viewer_organisation
        member.save()
        org = member.recipient_org
        session = ViewSession.objects.create(share_link=link, viewer=member, viewer_email=member.email, viewer_name=member.name, viewer_organisation=org, viewer_organisation_name=org.name if org else '', email_verification_method='verified')
        request.session.cycle_key()
        now = timezone.now().timestamp()
        request.session['dealroom_member'] = {'room_id': str(link.dataroom_id), 'member_id': str(member.pk), 'email': member.email, 'expires': now + 8 * 3600, 'last_seen': now}
        request.session['authorized_share_links'] = {str(link.pk): {'email_verified': True, 'email_method': 'verified', 'viewer_email': member.email, 'viewer_name': member.name, 'viewer_organisation_name': org.name if org else '', 'view_session_id': str(session.pk), 'password_verified': True}}
        request.session.set_expiry(8 * 3600)
        record('member.joined', organization=link.organization, actor=member, room_id=link.dataroom_id, target_id=member.pk)
        return Response({'status': 'verified'})


class RecipientRoomView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses=dict)
    def get(self, request, slug):
        link = get_link(slug)
        decision = evaluate(request, link)
        member = Viewer.objects.get(pk=decision.member_id)
        files = []
        for setting in ShareLinkDataroomSetting.objects.select_related('dataroom_document__document').filter(share_link=link, is_visible=True, dataroom_document__isnull=False):
            item = setting.dataroom_document
            try:
                file_decision = evaluate(request, link, document_id=str(item.pk))
            except PermissionDenied:
                continue
            version = item.document.versions.filter(is_primary=True).first()
            if not version:
                continue
            files.append({'id': str(item.pk), 'name': item.name or item.document.name, 'folder_id': str(item.folder_id or ''), 'page_count': version.num_pages or 1, 'download_level': file_decision.effective_download_level, 'page_url': f'/api/v1/links/{slug}/render-page/1/?dataroom_document_id={item.pk}', 'download_url': f'/api/v1/links/{slug}/download-file/?dataroom_document_id={item.pk}'})
        from sharelinks.views import _is_dataroom_folder_path_visible
        visible_folder_ids = {item['folder_id'] for item in files if item['folder_id']}
        folders = [
            {'id': str(folder.pk), 'name': folder.name}
            for folder in link.dataroom.folders.order_by('name', 'pk')
            if str(folder.pk) in visible_folder_ids
            and _is_dataroom_folder_path_visible(link, folder)
        ]
        return Response({'id': str(link.dataroom_id), 'name': link.dataroom.name, 'member': {'name': member.name, 'email': member.email, 'org': member.recipient_org.name if member.recipient_org else ''}, 'folders': folders, 'files': files, 'brand': load_brand()})


class RecipientLogoutView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses=dict)
    def post(self, request, slug):
        csrf(request)
        request.session.flush()
        return Response({'status': 'logged_out'})
