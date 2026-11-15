"""Extend Send's registry; its dispatch, tier, approval and activity hooks stay authoritative."""

from rest_framework.exceptions import PermissionDenied, ValidationError
from core.models import APIKey
from dealroom import registry
from dealroom.hooks import human_staff
from dealroom.models import KeyScope

PROTECTED_KINDS = {'partial', 'audit', 'evidence_report', 'history_evidence'}
OPERATION = 'dealroom_sign_SignatureExportView_endpoint_post'


def install():
    registry.STAFF.update({'SigningEnvelopeViewSet', 'SignCredentialView', 'SigningNdaPolicyView', 'SigningSourceView', 'SigningWhoViewedView', 'SigningNdaResetView'})
    registry.STAFF.update({'SignatureRequestListView', 'SignatureOverviewView', 'SignatureRequestDetailView', 'SignaturePageListView', 'SignaturePageView', 'SignatureExportView', 'SignatureSignerRevokeView', 'SignatureEmailRetryView'})
    registry.HUMAN_ONLY.update({('SignaturePageListView', 'get'), ('SignaturePageView', 'get')})
    registry.PUBLIC.update({'RecipientNdaView', 'RecipientNdaEnterView'})
    registry.HUMAN_ONLY.update({('SignatureEmailRetryView', 'post'), ('SignatureSignerRevokeView', 'post'), ('SignCredentialView', 'put'), ('SigningNdaResetView', 'post')})
    # All signing mutations either expose a new recipient or alter the gate. The
    # default evaluate_change classification treats their unlisted fields as widening.
    # GET returns a redacted projection only; credentials are human-write, never read.


def require_export_actor(request, kind, row=None):
    if kind is not None and not isinstance(kind, str):
        raise ValidationError('unsupported_kind')
    if kind in PROTECTED_KINDS and not human_staff(request):
        raise PermissionDenied('forbidden')
    if row is not None and not human_staff(request):
        if not isinstance(request.auth, APIKey):
            raise PermissionDenied('forbidden')
        scope = KeyScope.objects.filter(key=request.auth).first()
        if (not scope or scope.operations is None or OPERATION not in scope.operations
                or scope.rooms is None or str(row.workflow.room_id) not in scope.rooms):
            raise PermissionDenied('forbidden')
