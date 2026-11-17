"""The verified visitor's legal copy, independent of room document download rules."""
from io import BytesIO

from django.http import FileResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from dealroom_sign.models import ExecutedArtifact, NdaAcceptance, Workflow
from dealroom_sign.storage import source_bytes
from dealroom_sign.validation import digest
from sharelinks.models import Viewer
from .policy import evaluate


def copy_member(request, link):
    proof = request.session.get('dealroom_member', {})
    now = timezone.now().timestamp()
    if (proof.get('room_id') != str(link.dataroom_id) or now > proof.get('expires', 0)
            or now - proof.get('last_seen', 0) > 1800):
        raise NotAuthenticated('Verify your email to download your signed NDA.')
    member = Viewer.objects.filter(pk=proof.get('member_id'), organization=link.organization,
                                    email=proof.get('email'), verified_at__isnull=False).first()
    if not member:
        raise PermissionDenied('Recipient identity has changed; verify again.')
    proof['last_seen'] = now
    request.session['dealroom_member'] = proof
    return member


def own_workflow(link, member):
    return Workflow.objects.filter(room_id=link.dataroom_id, purpose='nda', member_id=str(member.pk),
        member_email=member.email.strip().lower()).order_by('-created_at').first()


def copy_status(request, link, member):
    work = own_workflow(link, member)
    acceptance = NdaAcceptance.objects.filter(workflow=work, member_id=str(member.pk),
                                              member_email=member.email).first() if work else None
    signer = next((s for s in work.signer_projection if s.get('email', '').lower() == member.email.lower()), {}) if work else {}
    signed = bool(acceptance or signer.get('signingStatus') == 'SIGNED')
    artifact = ExecutedArtifact.objects.filter(workflow=work, kind='sealed_pdf').first() if acceptance and work.state == 'done' else None
    can_enter = False
    if signed:
        try:
            evaluate(request, link)
            can_enter = True
        except (PermissionDenied, NotAuthenticated):
            pass
    return {'signed': signed, 'email': member.email, 'can_enter': can_enter,
        'state': work.state if work else 'not_started',
        'signed_at': signer.get('signedAt') or (acceptance.accepted_at.isoformat() if acceptance else None),
        'download_url': f'/api/v1/dealroom/recipient/{link.slug}/signed-nda/download/' if artifact else None}


class RecipientSignedNdaView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        response['Referrer-Policy'] = 'same-origin'
        return response

    @extend_schema(responses=dict)
    def get(self, request, slug):
        from .recipient import get_link
        link = get_link(slug)
        member = copy_member(request, link)
        return Response(copy_status(request, link, member))


class RecipientSignedNdaDownloadView(RecipientSignedNdaView):
    @extend_schema(responses={(200, 'application/pdf'): bytes})
    def get(self, request, slug):
        from .recipient import get_link
        link = get_link(slug)
        member = copy_member(request, link)
        status = copy_status(request, link, member)
        if not status['signed']:
            raise NotFound('No signed NDA for this visitor.')
        if not status['download_url']:
            return Response({'detail': 'Preparing your copy…'}, status=409)
        artifact = ExecutedArtifact.objects.select_related('version').get(
            workflow=own_workflow(link, member), kind='sealed_pdf')
        content = source_bytes(artifact.version)
        if digest(content) != artifact.sha256:
            raise PermissionDenied('Signed copy integrity check failed. Please contact the host.')
        return FileResponse(BytesIO(content), as_attachment=True, filename='Your signed NDA.pdf',
                            content_type='application/pdf')
