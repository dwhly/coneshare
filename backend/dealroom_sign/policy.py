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
        # Executed/ is reserved for subject-scoped evidence. An ordinary file
        # accidentally placed there must not make a private signer folder visible.
        from datarooms.models import DataroomDocument
        for item in DataroomDocument.objects.filter(document_id=document_id).select_related('folder'):
            folder = item.folder
            while folder and folder.parent_id:
                folder = folder.parent
            if folder and folder.name == 'Executed':
                return False
        return None
    workflow = artifact.workflow
    return (workflow.purpose == 'nda' and str(viewer.pk) == workflow.member_id
            and viewer.email.strip().lower() == workflow.member_email)
