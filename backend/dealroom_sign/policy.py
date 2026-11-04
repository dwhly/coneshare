from rest_framework.exceptions import PermissionDenied

from .models import ExecutedArtifact, NdaAcceptance, NdaPolicy


def check_nda(room, viewer):
    policy = NdaPolicy.objects.filter(room=room, enabled=True).first()
    if policy and not NdaAcceptance.objects.filter(
        room=room, member_id=str(viewer.pk), member_email=viewer.email.strip().lower(),
        policy_revision=str(policy.revision),
    ).exists():
        raise PermissionDenied({'code': 'nda_required', 'room_id': str(room.pk)})


def artifact_allowed(document_id, viewer):
    artifact = ExecutedArtifact.objects.select_related('workflow').filter(version__document_id=document_id).first()
    if not artifact:
        return None
    workflow = artifact.workflow
    return (workflow.purpose == 'nda' and str(viewer.pk) == workflow.member_id
            and viewer.email.strip().lower() == workflow.member_email)
