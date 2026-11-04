import pytest
from unittest.mock import patch
from rest_framework import status

from core.models import User, Organization
from datarooms.models import Dataroom, DataroomCollaborator, DataroomFolder, DataroomDocument
from datarooms.utils import get_dataroom_storage_folder_name
from documents.models import Folder
from sharelinks.models import QnAThread, ShareLink, ViewSession
from sharelinks.views import _dispatch_automation_event

pytestmark = pytest.mark.django_db


class TestDataroomCollaborators:
    def test_list_collaborators(self, api_client, dataroom, user, organization):
        collab_user = User.objects.create_user(
            email="collab@test.com", username="collab@test.com", password="password", organization=organization, name="Collab User"
        )
        DataroomCollaborator.objects.create(
            dataroom=dataroom, user=collab_user, invited_by=user, role=DataroomCollaborator.ROLE_COLLABORATOR
        )

        response = api_client.get(f'/api/v1/datarooms/{dataroom.id}/collaborators/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_add_collaborators_by_user_ids(self, api_client, dataroom, organization):
        collab1 = User.objects.create_user(email="c1@test.com", username="c1@test.com", password="password", organization=organization)
        collab2 = User.objects.create_user(email="c2@test.com", username="c2@test.com", password="password", organization=organization)

        payload = {"user_ids": [str(collab1.id), str(collab2.id)]}
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_collaborator_by_email(self, api_client, dataroom, organization):
        collab = User.objects.create_user(email="by_email@test.com", username="by_email@test.com", password="password", organization=organization)

        payload = {"email": "by_email@test.com"}
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_collaborator_from_other_org_fails(self, api_client, dataroom):
        other_org = Organization.objects.create(name="Other Org")
        foreign_user = User.objects.create_user(email="foreign@other.com", username="foreign@other.com", password="password", organization=other_org)

        payload = {"user_ids": [str(foreign_user.id)]}
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_owner_as_collaborator_fails(self, api_client, dataroom, user):
        payload = {"user_ids": [str(user.id)]}
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_owner_in_batch_creates_no_collaborators(self, api_client, dataroom, user, organization):
        other_user = User.objects.create_user(email="batch_other@test.com", username="batch_other@test.com", password="password", organization=organization)
        payload = {"user_ids": [str(other_user.id), str(user.id)]}
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_collaborator_cannot_add_other_collaborators(self, api_client, dataroom, user, organization):
        collab_user = User.objects.create_user(email="collab1@test.com", username="collab1@test.com", password="password", organization=organization)
        target_user = User.objects.create_user(email="target@test.com", username="target@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab_user, invited_by=user)

        api_client.force_authenticate(user=collab_user)
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', {"user_ids": [str(target_user.id)]}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_org_admin_can_add_collaborator_to_any_dataroom(self, api_client, dataroom, organization):
        admin_user = User.objects.create_user(email="admin@test.com", username="admin@test.com", password="password", organization=organization, role='admin')
        target_user = User.objects.create_user(email="target@test.com", username="target@test.com", password="password", organization=organization)

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', {"user_ids": [str(target_user.id)]}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_remove_collaborator_as_owner(self, api_client, dataroom, user, organization):
        collab_user = User.objects.create_user(email="collab@test.com", username="collab@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab_user, invited_by=user)

        api_client.force_authenticate(user=user)
        response = api_client.delete(f'/api/v1/datarooms/{dataroom.id}/collaborators/{collab_user.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_collaborator_can_leave_dataroom(self, api_client, dataroom, user, organization):
        collab_user = User.objects.create_user(email="collab@test.com", username="collab@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab_user, invited_by=user)

        api_client.force_authenticate(user=collab_user)
        response = api_client.delete(f'/api/v1/datarooms/{dataroom.id}/collaborators/{collab_user.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_collaborator_cannot_remove_peer_collaborator(self, api_client, dataroom, user, organization):
        collab1 = User.objects.create_user(email="c1@test.com", username="c1@test.com", password="password", organization=organization)
        collab2 = User.objects.create_user(email="c2@test.com", username="c2@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab1, invited_by=user)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab2, invited_by=user)

        api_client.force_authenticate(user=collab1)
        response = api_client.delete(f'/api/v1/datarooms/{dataroom.id}/collaborators/{collab2.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DataroomCollaborator.objects.filter(dataroom=dataroom, user=collab2).exists()

    def test_transfer_ownership_success(self, api_client, dataroom, user, organization):
        from datarooms.services import get_or_create_dataroom_storage_folder
        vault_folder = get_or_create_dataroom_storage_folder(dataroom, requesting_user=user)
        assert vault_folder.name == str(dataroom.id)
        assert vault_folder.parent.name == "__datarooms__"

        collab_user = User.objects.create_user(email="new_owner@test.com", username="new_owner@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab_user, invited_by=user)

        api_client.force_authenticate(user=user)
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/transfer-ownership/', {"new_owner_id": str(collab_user.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_transfer_ownership_permission_denied_for_collaborator(self, api_client, dataroom, user, organization):
        collab1 = User.objects.create_user(email="c1@test.com", username="c1@test.com", password="password", organization=organization)
        collab2 = User.objects.create_user(email="c2@test.com", username="c2@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab1, invited_by=user)

        api_client.force_authenticate(user=collab1)
        response = api_client.post(f'/api/v1/datarooms/{dataroom.id}/transfer-ownership/', {"new_owner_id": str(collab2.id)}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_eligible_collaborators_list_and_search(self, api_client, dataroom, user, organization):
        u1 = User.objects.create_user(email="alice@test.com", username="alice@test.com", password="password", organization=organization, name="Alice Walker")
        u2 = User.objects.create_user(email="bob@test.com", username="bob@test.com", password="password", organization=organization, name="Bob Smith")
        collab = User.objects.create_user(email="charlie@test.com", username="charlie@test.com", password="password", organization=organization, name="Charlie Brown")
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab, invited_by=user)

        api_client.force_authenticate(user=user)
        # List all eligible (should contain Alice and Bob, exclude owner and Charlie)
        response = api_client.get(f'/api/v1/datarooms/{dataroom.id}/eligible-collaborators/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_collaborator_can_view_and_manage_dataroom(self, api_client, dataroom, user, organization):
        collab_user = User.objects.create_user(email="collab@test.com", username="collab@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab_user, invited_by=user)

        api_client.force_authenticate(user=collab_user)

        # List datarooms (should see shared dataroom)
        response = api_client.get('/api/v1/datarooms/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_scope_filters_on_dataroom_list(self, api_client, user, organization):
        other_user = User.objects.create_user(email="other@test.com", username="other@test.com", password="password", organization=organization)
        owned_room = Dataroom.objects.create(name="Owned Room", organization=organization, created_by=user)
        shared_room = Dataroom.objects.create(name="Shared Room", organization=organization, created_by=other_user)
        DataroomCollaborator.objects.create(dataroom=shared_room, user=user, invited_by=other_user)

        api_client.force_authenticate(user=user)

        # Scope: created_by_me
        r1 = api_client.get('/api/v1/datarooms/?scope=created_by_me')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert r1.status_code == 403
        assert r1.data == {'detail': 'Staff access is required.'}

    def test_collaborator_share_link_co_management(self, api_client, dataroom, user, organization):
        collab1 = User.objects.create_user(email="c1@test.com", username="c1@test.com", password="password", organization=organization)
        collab2 = User.objects.create_user(email="c2@test.com", username="c2@test.com", password="password", organization=organization)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab1, invited_by=user)
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab2, invited_by=user)

        # Collab 1 creates a share link for the dataroom
        api_client.force_authenticate(user=collab1)
        res = api_client.post('/api/v1/share-links/', {
            'dataroom': str(dataroom.id),
            'name': 'Collab1 Link',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_collaborator_folder_creation_sets_created_by(self, api_client, dataroom, user, organization):
        collab = User.objects.create_user(
            email="folder_collab@test.com", username="folder_collab@test.com", password="password", organization=organization, name="Folder Collab"
        )
        DataroomCollaborator.objects.create(dataroom=dataroom, user=collab, invited_by=user)

        api_client.force_authenticate(user=collab)
        res = api_client.post('/api/v1/dataroom-folders/', {
            'dataroom': str(dataroom.id),
            'name': 'Collab Financials',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_removed_collaborator_privileges_revocation(
        self, api_client, dataroom, user, organization
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        collab = User.objects.create_user(
            email="former_collab@test.com",
            username="former_collab@test.com",
            password="password",
            organization=organization,
            name="Former Collab",
        )
        membership = DataroomCollaborator.objects.create(
            dataroom=dataroom, user=collab, invited_by=user
        )

        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=collab,
            password="TestPassword123!",
            require_nda=True,
            nda_text="Confidential terms.",
            nda_version=1,
            enable_qna=True,
        )

        # 1. While still an active collaborator:
        api_client.force_authenticate(user=collab)
        res_view_data = api_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_view_data.status_code == 403
        assert res_view_data.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

