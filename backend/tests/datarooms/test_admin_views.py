import pytest
from rest_framework import status

from core.models import Organization, User
from datarooms.models import Dataroom, DataroomCollaborator

pytestmark = pytest.mark.django_db


class TestAdminDataroomViewSet:
    def test_admin_can_list_all_org_datarooms(self, admin_api_client, admin_user, user, user2):
        org = admin_user.organization
        other_org = Organization.objects.create(name="Other Corp")

        # Datarooms in same org
        d1 = Dataroom.objects.create(name="Room 1 (User)", organization=org, created_by=user, storage_version=2)
        d2 = Dataroom.objects.create(name="Room 2 (User2)", organization=org, created_by=user2, storage_version=2)
        # Dataroom in different org
        d_other = Dataroom.objects.create(name="Room 3 (Other Org)", organization=other_org, storage_version=2)

        response = admin_api_client.get('/api/v1/admin/datarooms/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_non_admin_forbidden_from_admin_datarooms(self, api_client, user):
        response = api_client.get('/api/v1/admin/datarooms/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_update_storage_quota(self, admin_api_client, admin_user, user):
        org = admin_user.organization
        room = Dataroom.objects.create(name="Test Room", organization=org, created_by=user, storage_quota_mb=0, storage_version=2)

        response = admin_api_client.patch(f'/api/v1/admin/datarooms/{room.id}/', {
            'storage_quota_mb': 1024
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_transfer_ownership(self, admin_api_client, admin_user, user, user2):
        org = admin_user.organization
        room = Dataroom.objects.create(name="Deal Room", organization=org, created_by=user, storage_version=2)

        response = admin_api_client.post(f'/api/v1/admin/datarooms/{room.id}/transfer-ownership/', {
            'new_owner_id': str(user2.id)
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_upgrade_storage_v1_to_v2(self, admin_api_client, admin_user, user):
        org = admin_user.organization
        room = Dataroom.objects.create(name="Legacy Room", organization=org, created_by=user, storage_version=1)

        response = admin_api_client.post(f'/api/v1/admin/datarooms/{room.id}/upgrade-storage/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_manage_collaborators(self, admin_api_client, admin_user, user, user2):
        org = admin_user.organization
        room = Dataroom.objects.create(name="Collab Room", organization=org, created_by=user, storage_version=2)

        # Add collaborator
        add_res = admin_api_client.post(f'/api/v1/admin/datarooms/{room.id}/collaborators/', {
            'user_ids': [str(user2.id)]
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert add_res.status_code == 403
        assert add_res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_eligible_collaborators_is_bounded_to_50(self, admin_api_client, admin_user, user):
        org = admin_user.organization
        room = Dataroom.objects.create(name="Collab Room", organization=org, created_by=user, storage_version=2)
        # Create 60 active users in the org
        User.objects.bulk_create([
            User(
                username=f"test_user_{i}@example.com",
                email=f"test_user_{i}@example.com",
                name=f"Test User {i:02d}",
                organization=org,
                is_active=True,
            )
            for i in range(60)
        ])

        res = admin_api_client.get(f'/api/v1/admin/datarooms/{room.id}/eligible-collaborators/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_delete_dataroom(self, admin_api_client, admin_user, user):
        org = admin_user.organization
        room = Dataroom.objects.create(name="Delete Me", organization=org, created_by=user, storage_version=2)

        del_res = admin_api_client.delete(f'/api/v1/admin/datarooms/{room.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert del_res.status_code == 403
        assert del_res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_workspace_list_vs_admin_list_scoping(self, admin_api_client, admin_user, user, user2):
        org = admin_user.organization
        # Room created by admin
        d_admin = Dataroom.objects.create(name="Admin's Personal Room", organization=org, created_by=admin_user, storage_version=2)
        # Room created by user (admin is NOT a member/collaborator)
        d_user = Dataroom.objects.create(name="User's Private Room", organization=org, created_by=user, storage_version=2)

        # 1. Standard Workspace listing (/api/v1/datarooms/): Admin only sees their own rooms
        ws_res = admin_api_client.get('/api/v1/datarooms/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert ws_res.status_code == 403
        assert ws_res.data == {'detail': 'Staff access is required.'}

    def test_admin_datarooms_sorting_and_filtering(self, admin_api_client, admin_user, user):
        org = admin_user.organization
        room_b = Dataroom.objects.create(name="Beta Room", organization=org, created_by=user, storage_version=1)
        room_a = Dataroom.objects.create(name="Alpha Room", organization=org, created_by=admin_user, storage_version=2)

        # 1. Sort by name asc
        res_asc = admin_api_client.get('/api/v1/admin/datarooms/?ordering=name')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_asc.status_code == 403
        assert res_asc.data == {'detail': 'Unclassified or disabled operation.'}

    def test_workspace_list_does_not_execute_n_plus_one_metric_queries(self, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        org = user.organization
        for i in range(5):
            Dataroom.objects.create(name=f'Room {i}', organization=org, created_by=user, storage_version=2)
        with CaptureQueriesContext(connection) as ctx:
            response = api_client.get('/api/v1/datarooms/')
            assert response.status_code == 403
            assert response.data == {'detail': 'Staff access is required.'}

    def test_workspace_list_does_not_allow_scope_org_escape_hatch(self, admin_api_client, admin_user, user):
        org = admin_user.organization
        admin_room = Dataroom.objects.create(name="Admin Room", organization=org, created_by=admin_user, storage_version=2)
        other_user_room = Dataroom.objects.create(name="Other User Room", organization=org, created_by=user, storage_version=2)

        # Standard workspace endpoint with scope=org should NOT return non-participating rooms
        res = admin_api_client.get('/api/v1/datarooms/?scope=org')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Staff access is required.'}

