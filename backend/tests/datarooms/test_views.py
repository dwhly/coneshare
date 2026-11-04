import os
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from datarooms.models import Dataroom, DataroomDocument, DataroomFolder, DataroomItemOrder
from datarooms.services import touch_dataroom_folder_ancestors, get_dataroom_storage_used_bytes
from datarooms.utils import get_dataroom_storage_folder_name
from documents.models import Document, Folder
from documents.services import recalculate_user_document_size, is_dataroom_vault_document
from sharelinks.models import DataroomVisit, ShareLink, ViewSession

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def mock_dataroom_fileserver_get_info():
    with patch('datarooms.views.fileserver_client.get_file_info') as mock_info:
        def side_effect(storage_key):
            if 'overflow.pdf' in storage_key:
                return {'exists': True, 'size': 5 * 1024 * 1024}
            if 'big_deal_deck.pdf' in storage_key:
                return {'exists': True, 'size': 50 * 1024 * 1024}
            if 'sub_doc.pdf' in storage_key:
                return {'exists': True, 'size': 1 * 1024 * 1024}
            if 'doc.pdf' in storage_key:
                return {'exists': True, 'size': 2 * 1024 * 1024}
            if 'test_file.pdf' in storage_key:
                return {'exists': True, 'size': 331697}
            if 'orphan_file.pdf' in storage_key:
                return {'exists': True, 'size': 2048}
            if 'temp.txt' in storage_key:
                return {'exists': True, 'size': 12}
            return {'exists': True, 'size': 1024}

        mock_info.side_effect = side_effect
        yield mock_info


class TestDataroomViewSet:
    def test_list_datarooms_scoped_to_user(self, api_client, user, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        Dataroom.objects.create(name="My Dataroom", organization=organization, created_by=user)
        Dataroom.objects.create(name="Other's Dataroom", organization=organization, created_by=user2)

        response = api_client.get('/api/v1/datarooms/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_list_datarooms_ordered_by_created_at_desc(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dr1 = Dataroom.objects.create(name="First Room", organization=organization, created_by=user)
        dr2 = Dataroom.objects.create(name="Second Room", organization=organization, created_by=user)
        dr3 = Dataroom.objects.create(name="Third Room", organization=organization, created_by=user)

        Dataroom.objects.filter(id=dr1.id).update(created_at=timezone.now() - timedelta(days=2))
        Dataroom.objects.filter(id=dr2.id).update(created_at=timezone.now() - timedelta(days=1))
        Dataroom.objects.filter(id=dr3.id).update(created_at=timezone.now())

        response = api_client.get('/api/v1/datarooms/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_create_dataroom(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        assert Dataroom.objects.count() == 0
        data = {'name': 'New API Dataroom'}
        response = api_client.post('/api/v1/datarooms/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_dataroom_branding_fields(self, api_client, dataroom):
        url = f'/api/v1/datarooms/{dataroom.id}/'
        response = api_client.patch(url, {
            "brand_primary_color": "#112233",
            "brand_secondary_color": "#445566",
            "brand_accent_color": "#778899AA",
            "show_file_index": False,
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_dataroom_branding_invalid_color_fails(self, api_client, dataroom):
        url = f'/api/v1/datarooms/{dataroom.id}/'
        response = api_client.patch(url, {"brand_primary_color": "blue"}, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_remove_dataroom_banner(self, api_client, dataroom):
        dataroom.branding_banner = SimpleUploadedFile("banner.jpg", b"fake-image-bytes", content_type="image/jpeg")
        dataroom.save()
        assert dataroom.branding_banner

        url = f'/api/v1/datarooms/{dataroom.id}/'
        response = api_client.patch(url, {"remove_branding_banner": True}, format="multipart")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_retrieve_dataroom_detail(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Add a document and a folder to the dataroom root
        dataroom_document = DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=None, name=document.name)
        DataroomFolder.objects.create(dataroom=dataroom, name="Subfolder", parent=None)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=dataroom.created_by)
        session = ViewSession.objects.create(share_link=link)
        DataroomVisit.objects.create(view_session=session, dataroom_document=dataroom_document)

        response = api_client.get(f'/api/v1/datarooms/{dataroom.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_cannot_access_other_users_dataroom_folders(self, api_client, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        other_dataroom = Dataroom.objects.create(name="Other DR", organization=organization, created_by=user2)
        other_folder = DataroomFolder.objects.create(name="Other Folder", dataroom=other_dataroom)

        # 1. Test listing: should not appear in the general list
        list_url = '/api/v1/dataroom-folders/'
        response = api_client.get(list_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_retrieve_folder_contents_is_performant(self, api_client, dataroom, organization, user, django_assert_num_queries):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        "\n        Test retrieving a nested folder's contents to check for N+1 query problems,\n        especially in the ancestor retrieval logic.\n        "
        level1 = DataroomFolder.objects.create(dataroom=dataroom, name='Level 1')
        level2 = DataroomFolder.objects.create(dataroom=dataroom, name='Level 2', parent=level1)
        target_folder = DataroomFolder.objects.create(dataroom=dataroom, name='Target', parent=level2)
        for i in range(5):
            doc = Document.objects.create(name=f'Doc {i}', organization=organization, created_by=user)
            DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=target_folder, name=doc.name)
        with django_assert_num_queries(6, exact=False):
            url = f'/api/v1/dataroom-folders/{target_folder.id}/'
            response = api_client.get(url)
            assert response.status_code == 403
            assert response.data == {'detail': 'Staff access is required.'}

    def test_delete_dataroom_permission_denied(self, api_client, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom_by_user2 = Dataroom.objects.create(
            organization=organization,
            created_by=user2,
            name="User2's Dataroom"
        )

        response = api_client.delete(f'/api/v1/datarooms/{dataroom_by_user2.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_delete_dataroom_success(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom_id = dataroom.id
        response = api_client.delete(f'/api/v1/datarooms/{dataroom.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file')
    def test_delete_dataroom_with_direct_upload_quota_balance(self, mock_fs_delete, api_client, dataroom, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user.total_document_size = 0
        user.save()

        file_size = 331697
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f"{dataroom.organization.id}/uploads/test_file.pdf",
            'unique_name': 'test_file.pdf',
            'file_size': file_size,
            'content_type': 'application/pdf',
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.generate_upload_url', return_value='http://fileserver/upload')
    @patch('documents.services.fileserver_client.delete_file')
    def test_direct_upload_does_not_consume_user_personal_quota(self, mock_fs_delete, mock_fs_upload, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user.custom_file_size_quota_mb = 10
        user.total_document_size = 0
        user.save()

        dataroom = Dataroom.objects.create(
            name="Deal Dataroom",
            organization=organization,
            created_by=user,
            storage_quota_mb=500,
            storage_version=2
        )

        file_size = 50 * 1024 * 1024  # 50 MB (exceeds user's 10 MB personal quota)
        url_request = f'/api/v1/datarooms/{dataroom.id}/uploads/request/'
        data_request = {
            'file_name': 'big_deal_deck.pdf',
            'file_size': file_size,
        }
        res_req = api_client.post(url_request, data_request, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_req.status_code == 403
        assert res_req.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.generate_upload_url', return_value='http://fileserver/upload')
    @patch('documents.services.fileserver_client.delete_file')
    def test_legacy_v1_direct_upload_consumes_user_personal_quota(self, mock_fs_delete, mock_fs_upload, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user.custom_file_size_quota_mb = 10
        user.total_document_size = 0
        user.save()

        dataroom = Dataroom.objects.create(
            name="Legacy Room",
            organization=organization,
            created_by=user,
            storage_quota_mb=500,
            storage_version=1
        )

        # 1. Attempt upload that exceeds personal quota (15 MB > 10 MB) -> must fail with 400
        url_request = f'/api/v1/datarooms/{dataroom.id}/uploads/request/'
        res_fail = api_client.post(url_request, {'file_name': 'too_big.pdf', 'file_size': 15 * 1024 * 1024}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_fail.status_code == 403
        assert res_fail.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file')
    def test_delete_dataroom_with_shared_direct_upload_preserves_shared_document(self, mock_fs_delete, api_client, dataroom, user, organization):

        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        second_dataroom = Dataroom.objects.create(
            name="Second Dataroom",
            organization=organization,
            created_by=user
        )

        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f'{dataroom.organization.id}/uploads/shared_file.pdf',
            'unique_name': 'shared_file.pdf',
            'file_size': 1024,
            'content_type': 'application/pdf',
        }

        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file')
    def test_delete_dataroom_with_colliding_shared_documents_handles_name_collisions_gracefully(self, mock_fs_delete, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from documents.models import Folder
        from datarooms.services import get_or_create_dataroom_storage_folder
        second_dataroom = Dataroom.objects.create(
            name="Second Dataroom",
            organization=organization,
            created_by=user
        )

        storage_folder = get_or_create_dataroom_storage_folder(dataroom)
        system_vault = storage_folder.parent

        # Create two physical subfolders in storage_folder
        sub1, _ = Folder.get_or_create_vault_subfolder(
            organization=organization,
            parent=storage_folder,
            name="Sub1",
        )
        sub2, _ = Folder.get_or_create_vault_subfolder(
            organization=organization,
            parent=storage_folder,
            name="Sub2",
        )

        # Create two physical documents with the same name in different subfolders
        doc1 = Document.objects.create(name="Contract.pdf", folder=sub1, created_by=user, organization=organization)
        doc2 = Document.objects.create(name="Contract.pdf", folder=sub2, created_by=user, organization=organization)

        # Link both to the dataroom being deleted as direct uploads
        DataroomDocument.objects.create(dataroom=dataroom, document=doc1, name="Contract.pdf", is_direct_upload=True)
        DataroomDocument.objects.create(dataroom=dataroom, document=doc2, name="Contract.pdf", is_direct_upload=True)

        # Also link both to second_dataroom so they are preserved
        DataroomDocument.objects.create(dataroom=second_dataroom, document=doc1, name="Contract.pdf")
        DataroomDocument.objects.create(dataroom=second_dataroom, document=doc2, name="Contract.pdf")

        # Delete the first dataroom - should succeed with 204 without IntegrityError 500
        res_delete = api_client.delete(f'/api/v1/datarooms/{dataroom.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_delete.status_code == 403
        assert res_delete.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file')
    def test_delete_dataroom_when_created_by_is_none(self, mock_fs_delete, api_client, dataroom, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.services import delete_dataroom

        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        storage_key = f'{dataroom.organization.id}/uploads/orphan_file.pdf'
        data_finalize = {
            'storage_key': storage_key,
            'unique_name': 'orphan_file.pdf',
            'file_size': 2048,
            'content_type': 'application/pdf',
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_content_to_dataroom(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        data = {'document_ids': [str(document.id)]}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_content_exceeding_dataroom_storage_quota_is_rejected(self, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom.storage_quota_mb = 10  # 10 MB cap
        dataroom.save(update_fields=['storage_quota_mb'])

        doc = Document.objects.create(
            name="Large Contract.pdf",
            organization=organization,
            created_by=user,
            file_size=15 * 1024 * 1024  # 15 MB
        )

        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        response = api_client.post(url, {'document_ids': [str(doc.id)]})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_upload_finalize_exceeding_dataroom_storage_quota_is_rejected(self, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom.storage_quota_mb = 10  # 10 MB cap
        dataroom.save(update_fields=['storage_quota_mb'])

        # Pre-fill 8 MB
        existing_doc = Document.objects.create(
            name="Existing.pdf",
            organization=organization,
            created_by=user,
            file_size=8 * 1024 * 1024
        )
        DataroomDocument.objects.create(dataroom=dataroom, document=existing_doc, name="Existing.pdf")

        # Try to finalize an upload of 5 MB (total 13 MB > 10 MB)
        url = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data = {
            'storage_key': f'{dataroom.organization.id}/uploads/overflow.pdf',
            'unique_name': 'overflow.pdf',
            'file_size': 5 * 1024 * 1024,
            'content_type': 'application/pdf',
        }

        response = api_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_folder_content_exceeding_dataroom_storage_quota_is_rejected(self, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from documents.models import Folder
        dataroom.storage_quota_mb = 10  # 10 MB cap
        dataroom.save(update_fields=['storage_quota_mb'])

        root_folder = Folder.objects.get(name="__root__", organization=organization, parent=None)
        folder = Folder.objects.create(name="Contracts", parent=root_folder, created_by=user, organization=organization)
        subfolder = Folder.objects.create(name="2026", parent=folder, created_by=user, organization=organization)

        Document.objects.create(
            name="Contract A.pdf",
            folder=subfolder,
            organization=organization,
            created_by=user,
            file_size=12 * 1024 * 1024  # 12 MB > 10 MB
        )

        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        response = api_client.post(url, {'folder_ids': [str(folder.id)]})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_existing_document_to_another_folder_does_not_double_count_quota(self, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom.storage_quota_mb = 10  # 10 MB cap
        dataroom.save(update_fields=['storage_quota_mb'])

        doc = Document.objects.create(
            name="Shared Doc.pdf",
            organization=organization,
            created_by=user,
            file_size=8 * 1024 * 1024  # 8 MB <= 10 MB
        )
        DataroomDocument.objects.create(dataroom=dataroom, document=doc, name="Shared Doc.pdf")

        # Create a second visual folder
        folder2 = DataroomFolder.objects.create(dataroom=dataroom, name="Folder 2")

        # Adding the same doc to Folder 2 adds 0 bytes of new physical storage
        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        response = api_client.post(url, {'document_ids': [str(doc.id)], 'destination_folder_id': str(folder2.id)})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_content_permission_denied_for_other_user_content(self, api_client, user, user2, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # `document` is created by `user`
        assert document.created_by == user

        # `user2` creates a dataroom that they own
        dataroom_by_user2 = Dataroom.objects.create(name="User2's Dataroom", organization=user2.organization, created_by=user2)

        # `user2` logs in
        api_client.force_authenticate(user=user2)

        # `user2` tries to add `user`'s document to their dataroom
        url = f'/api/v1/datarooms/{dataroom_by_user2.id}/add-content/'
        data = {'document_ids': [str(document.id)]}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_content_updates_existing_share_links(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Create a share link for the dataroom while it's empty.
        link = ShareLink.objects.create(dataroom=dataroom, name="Existing Link", created_by=user)
        assert link.dataroom_settings.count() == 0

        # 2. Add a document to the dataroom via the API.
        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        data = {'document_ids': [str(document.id)]}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_folder_content_to_dataroom(self, api_client, dataroom, user, organization, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        root_folder = Folder.objects.get_root_for_org(organization)
        source_folder = Folder.objects.create(name="Source", created_by=user, organization=organization, parent=root_folder)
        # Put the document inside the source folder
        document.folder = source_folder
        document.save()

        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        data = {'folder_ids': [str(source_folder.id)]}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_document_with_name_conflict_is_renamed(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Add the document once.
        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        data = {'document_ids': [str(document.id)]}
        response1 = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response1.status_code == 403
        assert response1.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_same_document_to_multiple_locations(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        '\n        Test that the same source document can be added to multiple locations\n        (e.g., root and a subfolder) inside a dataroom.\n        '
        dest_folder = DataroomFolder.objects.create(dataroom=dataroom, name='Destination')
        add_to_root_url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        add_to_root_data = {'document_ids': [str(document.id)]}
        api_client.post(add_to_root_url, add_to_root_data)
        add_to_folder_url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        add_to_folder_data = {'document_ids': [str(document.id)], 'destination_folder_id': str(dest_folder.id)}
        response = api_client.post(add_to_folder_url, add_to_folder_data)
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_remove_content_from_dataroom(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dd = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        assert DataroomDocument.objects.count() == 1

        url = f'/api/v1/datarooms/{dataroom.id}/remove-content/'
        data = {'dataroom_document_ids': [str(dd.id)]}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_remove_document_from_dataroom_by_document_id(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dd = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        assert DataroomDocument.objects.count() == 1

        url = f'/api/v1/datarooms/{dataroom.id}/remove-content/'
        data = {'dataroom_document_ids': [str(document.id)]}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_remove_document_with_wrong_key_returns_clean_400(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/datarooms/{dataroom.id}/remove-content/'
        data = {'document_ids': [str(document.id)]}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_remove_content_with_empty_payload_returns_400(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/datarooms/{dataroom.id}/remove-content/'
        response = api_client.post(url, {'dataroom_document_ids': []})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}



    def test_move_document_to_folder(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom_doc = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        dataroom_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Destination")

        url = f'/api/v1/datarooms/{dataroom.id}/move-content/'
        data = {
            'dataroom_document_ids': [str(dataroom_doc.id)],
            'destination_folder_id': str(dataroom_folder.id)
        }
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_folder_to_root(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        parent = DataroomFolder.objects.create(dataroom=dataroom, name="Parent")
        child = DataroomFolder.objects.create(dataroom=dataroom, name="Child", parent=parent)

        url = f'/api/v1/datarooms/{dataroom.id}/move-content/'
        data = {
            'dataroom_folder_ids': [str(child.id)],
            'destination_folder_id': ''
        }
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_folder_into_itself_fails(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Folder")
        url = f'/api/v1/datarooms/{dataroom.id}/move-content/'
        data = {
            'dataroom_folder_ids': [str(folder.id)],
            'destination_folder_id': str(folder.id)
        }
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_folder_with_conflict_resolves_name(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        folder_to_move = DataroomFolder.objects.create(dataroom=dataroom, name="My Folder")
        destination_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Destination")
        
        # Create conflicting folders in the destination
        DataroomFolder.objects.create(dataroom=dataroom, parent=destination_folder, name="My Folder")
        DataroomFolder.objects.create(dataroom=dataroom, parent=destination_folder, name="My Folder (2)")

        url = f'/api/v1/datarooms/{dataroom.id}/move-content/'
        data = {
            'dataroom_folder_ids': [str(folder_to_move.id)],
            'destination_folder_id': str(destination_folder.id)
        }
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reorder_items_mixed_root_success(self, api_client, dataroom, document, user, organization):
        doc2 = Document.objects.create(name="Doc 2", organization=organization, created_by=user)
        folder_a = DataroomFolder.objects.create(dataroom=dataroom, name="A")
        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        folder_b = DataroomFolder.objects.create(dataroom=dataroom, name="B")
        ddoc2 = DataroomDocument.objects.create(dataroom=dataroom, document=doc2, name=doc2.name)
        dataroom.show_file_index = True
        dataroom.save(update_fields=["show_file_index"])

        url = f'/api/v1/datarooms/{dataroom.id}/reorder-items/'
        response = api_client.post(url, {
            "ordered_items": [
                {"type": "document", "id": str(ddoc2.id)},
                {"type": "folder", "id": str(folder_b.id)},
                {"type": "document", "id": str(ddoc1.id)},
                {"type": "folder", "id": str(folder_a.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reorder_items_requires_full_scope_ids(self, api_client, dataroom, document):
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="A")
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        dataroom.show_file_index = True
        dataroom.save(update_fields=["show_file_index"])

        url = f'/api/v1/datarooms/{dataroom.id}/reorder-items/'
        response = api_client.post(url, {
            "ordered_items": [
                {"type": "folder", "id": str(folder.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_root_items_excludes_soft_deleted_documents(self, api_client, dataroom, document, user, organization):
        doc_active = document
        doc_trashed = Document.objects.create(name="Trashed Doc", organization=organization, created_by=user, deleted_at=timezone.now())
        ddoc_active = DataroomDocument.objects.create(dataroom=dataroom, document=doc_active, name=doc_active.name)
        ddoc_trashed = DataroomDocument.objects.create(dataroom=dataroom, document=doc_trashed, name=doc_trashed.name)

        # 1. Check GET /api/v1/datarooms/{id}/ does not return trashed document in items
        detail_url = f'/api/v1/datarooms/{dataroom.id}/'
        detail_res = api_client.get(detail_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert detail_res.status_code == 403
        assert detail_res.data == {'detail': 'Staff access is required.'}

    def test_reorder_items_other_user_dataroom_returns_404(self, api_client, user2, organization, document):
        other_room = Dataroom.objects.create(name="Other", organization=organization, created_by=user2)
        ddoc = DataroomDocument.objects.create(dataroom=other_room, document=document, name=document.name)

        url = f'/api/v1/datarooms/{other_room.id}/reorder-items/'
        response = api_client.post(url, {
            "ordered_items": [
                {"type": "document", "id": str(ddoc.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reorder_items_works_when_file_index_disabled(self, api_client, dataroom, document):
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        assert dataroom.show_file_index is True
        dataroom.show_file_index = False
        dataroom.save(update_fields=["show_file_index"])

        url = f'/api/v1/datarooms/{dataroom.id}/reorder-items/'
        response = api_client.post(url, {
            "ordered_items": [
                {"type": "document", "id": str(ddoc.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_folder_retrieve_preserves_item_order_when_file_index_disabled(self, api_client, dataroom, document, user, organization):
        parent_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Parent", parent=None)
        sub_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Sub", parent=parent_folder)
        doc2 = Document.objects.create(name="Doc In Folder", organization=organization, created_by=user)
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc2, name=doc2.name, folder=parent_folder)
        dataroom.show_file_index = False
        dataroom.save(update_fields=["show_file_index"])

        DataroomItemOrder.objects.create(
            dataroom=dataroom,
            parent_folder=parent_folder,
            item_type=DataroomItemOrder.ITEM_TYPE_DOCUMENT,
            dataroom_document=ddoc,
            position=0,
        )
        DataroomItemOrder.objects.create(
            dataroom=dataroom,
            parent_folder=parent_folder,
            item_type=DataroomItemOrder.ITEM_TYPE_FOLDER,
            folder=sub_folder,
            position=1,
        )

        folder_url = f'/api/v1/dataroom-folders/{parent_folder.id}/'
        response = api_client.get(folder_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_dataroom_folder_retrieve_excludes_soft_deleted_documents(self, api_client, dataroom, document, user, organization):
        parent_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Parent Folder", parent=None)
        doc_active = document
        doc_trashed = Document.objects.create(name="Trashed Doc in Folder", organization=organization, created_by=user, deleted_at=timezone.now())
        ddoc_active = DataroomDocument.objects.create(dataroom=dataroom, document=doc_active, name=doc_active.name, folder=parent_folder)
        ddoc_trashed = DataroomDocument.objects.create(dataroom=dataroom, document=doc_trashed, name=doc_trashed.name, folder=parent_folder)

        folder_url = f'/api/v1/dataroom-folders/{parent_folder.id}/'
        response = api_client.get(folder_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_reorder_items_after_moving_content_should_succeed(self, api_client, dataroom, document, user, organization):
        # 1. Setup a destination folder and a document inside it.
        folder_dest = DataroomFolder.objects.create(dataroom=dataroom, name="Destination")
        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name, folder=folder_dest)
        
        # 2. Call reorder endpoint once to initialize order rows for folder_dest.
        url_reorder = f'/api/v1/datarooms/{dataroom.id}/reorder-items/'
        response_reorder_init = api_client.post(url_reorder, {
            "parent_id": str(folder_dest.id),
            "ordered_items": [
                {"type": "document", "id": str(ddoc1.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_reorder_init.status_code == 403
        assert response_reorder_init.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reorder_source_folder_after_moving_item_avoids_orphaned_row_integrity_error(self, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        folder_src = DataroomFolder.objects.create(dataroom=dataroom, name="Source")
        folder_dest = DataroomFolder.objects.create(dataroom=dataroom, name="Dest")

        doc1 = Document.objects.create(name="Doc 1", organization=organization, created_by=user)
        doc2 = Document.objects.create(name="Doc 2", organization=organization, created_by=user)

        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, document=doc1, name=doc1.name, folder=folder_src)
        ddoc2 = DataroomDocument.objects.create(dataroom=dataroom, document=doc2, name=doc2.name, folder=folder_src)

        url_reorder = f'/api/v1/datarooms/{dataroom.id}/reorder-items/'

        # 1. Order folder_src: ddoc1 at 0, ddoc2 at 1
        res1 = api_client.post(url_reorder, {
            "parent_id": str(folder_src.id),
            "ordered_items": [
                {"type": "document", "id": str(ddoc1.id)},
                {"type": "document", "id": str(ddoc2.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res1.status_code == 403
        assert res1.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_content_does_not_delete_order_rows_in_other_datarooms(self, api_client, dataroom, user, organization):
        """
        Finding 2: Deleting order rows during move-content must be strictly scoped to the
        target dataroom. Passing foreign item IDs must not delete DataroomItemOrder in other datarooms.
        """
        from datarooms.models import DataroomItemOrder
        dataroom2 = Dataroom.objects.create(name="Other Dataroom", organization=organization, created_by=user)
        folder2 = DataroomFolder.objects.create(dataroom=dataroom2, name="Folder in Room 2")
        doc2 = Document.objects.create(name="Doc Room 2", organization=organization, created_by=user)
        ddoc2 = DataroomDocument.objects.create(dataroom=dataroom2, document=doc2, name=doc2.name, folder=folder2)

        order_row = DataroomItemOrder.objects.create(
            dataroom=dataroom2,
            parent_folder=folder2,
            item_type=DataroomItemOrder.ITEM_TYPE_DOCUMENT,
            dataroom_document=ddoc2,
            position=0,
        )

        # Call move-content on dataroom 1, maliciously or mistakenly passing ddoc2.id from dataroom 2
        url_move = f'/api/v1/datarooms/{dataroom.id}/move-content/'
        api_client.post(url_move, {
            "dataroom_document_ids": [str(ddoc2.id)],
            "dataroom_folder_ids": [],
            "destination_folder_id": None,
        }, format="json")

        # The order row in dataroom 2 must NOT be deleted
        assert DataroomItemOrder.objects.filter(id=order_row.id).exists()

    def test_move_content_within_same_folder_preserves_custom_order(self, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.models import DataroomItemOrder
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Ordered Folder")
        doc1 = Document.objects.create(name="Doc 1", organization=organization, created_by=user)
        doc2 = Document.objects.create(name="Doc 2", organization=organization, created_by=user)
        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, document=doc1, name=doc1.name, folder=folder)
        ddoc2 = DataroomDocument.objects.create(dataroom=dataroom, document=doc2, name=doc2.name, folder=folder)

        # Custom order: ddoc1 at 0, ddoc2 at 1
        url_reorder = f'/api/v1/datarooms/{dataroom.id}/reorder-items/'
        res_reorder = api_client.post(url_reorder, {
            "parent_id": str(folder.id),
            "ordered_items": [
                {"type": "document", "id": str(ddoc1.id)},
                {"type": "document", "id": str(ddoc2.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_reorder.status_code == 403
        assert res_reorder.data == {'detail': 'Unclassified or disabled operation.'}


    def test_reorder_items_after_adding_content_should_succeed(self, api_client, dataroom, document, user, organization):
        # 1. Setup a folder and a document inside it.
        folder_dest = DataroomFolder.objects.create(dataroom=dataroom, name="Destination")
        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name, folder=folder_dest)
        
        # 2. Call reorder endpoint once to initialize order rows for folder_dest.
        url_reorder = f'/api/v1/datarooms/{dataroom.id}/reorder-items/'
        response_reorder_init = api_client.post(url_reorder, {
            "parent_id": str(folder_dest.id),
            "ordered_items": [
                {"type": "document", "id": str(ddoc1.id)},
            ],
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_reorder_init.status_code == 403
        assert response_reorder_init.data == {'detail': 'Unclassified or disabled operation.'}


    def test_list_view_sessions_for_dataroom(self, api_client, user, dataroom, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Dataroom and link we are testing
        link1 = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        ViewSession.objects.create(share_link=link1, viewer_email="viewer1@test.com")

        # Other dataroom and link to ensure isolation
        other_dataroom = Dataroom.objects.create(name="Other Dataroom", organization=organization, created_by=user)
        other_link = ShareLink.objects.create(dataroom=other_dataroom, created_by=user)
        ViewSession.objects.create(share_link=other_link, viewer_email="other_viewer@test.com")

        url = f'/api/v1/datarooms/{dataroom.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_updating_link_to_disallow_downloads_does_not_cascade(self, dataroom, document, user):
        """
        Test that updating a parent share link's `allow_download` setting
        does not cascade to existing item settings.
        """
        # 1. Create a dataroom document and a share link.
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user, allow_download=True)

        # 2. Verify the initial setting is correct.
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        assert setting.allow_download is True

        # 3. Update the parent link.
        link.allow_download = False
        link.save()

        # 4. Verify the item setting has not changed.
        setting.refresh_from_db()
        assert setting.allow_download is True

    def test_updating_link_to_disable_watermarking_does_not_cascade(self, dataroom, document, user):
        """
        Test that updating a parent share link's `enable_watermark` setting
        does not cascade to existing item settings.
        """
        # 1. Create a dataroom document and a share link with watermarking enabled.
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user, enable_watermark=True)

        # 2. Verify the initial setting is correct.
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        assert setting.enable_watermark is True

        # 3. Update the parent link.
        link.enable_watermark = False
        link.save()

        # 4. Verify the item setting has not changed.
        setting.refresh_from_db()
        assert setting.enable_watermark is True

    def test_ensure_paths_in_dataroom(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/datarooms/{dataroom.id}/ensure-paths/'
        
        # 1. Post valid paths to ensure
        data = {
            'paths': [
                'Folder A',
                'Folder A/Subfolder B',
                'Folder C'
            ]
        }
        response = api_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_upload_request_in_dataroom(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        '\n        Test requesting upload URLs in a dataroom.\n        '
        from unittest.mock import patch
        with patch('documents.fileserver.fileserver_client.generate_upload_url') as mock_generate_url:
            mock_generate_url.return_value = 'https://fileserver.example.com/upload-token'
            url = f'/api/v1/datarooms/{dataroom.id}/uploads/request/'
            data = {'file_name': 'test_file.pdf', 'file_size': 1024}
            response = api_client.post(url, data, format='json')
            assert response.status_code == 403
            assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.fileserver.fileserver_client.generate_upload_url')
    def test_upload_request_inside_folder_with_path(self, mock_generate_url, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_generate_url.return_value = "https://fileserver.example.com/upload-token"

        # 1. Create a folder 'png' in the dataroom at root
        folder_png = DataroomFolder.objects.create(dataroom=dataroom, name="png", parent=None)

        # 2. Request upload for a file 'photo.png' inside folder 'png'
        # The frontend sends: destination_folder_id = folder_png.id, path = 'png/photo.png'
        url = f'/api/v1/datarooms/{dataroom.id}/uploads/request/'
        data = {
            'file_name': 'photo.png',
            'file_size': 1024,
            'destination_folder_id': str(folder_png.id),
            'path': 'png/photo.png'
        }
        response = api_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_upload_finalize_in_dataroom(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        
        # 1. Finalize root upload (no path, no parent folder)
        data = {
            'storage_key': f'{dataroom.organization.id}/uploads/test_file.pdf',
            'unique_name': 'test_file.pdf',
            'file_size': 1024,
            'content_type': 'application/pdf',
        }
        
        response = api_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_rename_updates_library_folder(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Test legacy v1 rename
        dataroom.storage_version = 1
        dataroom.save(update_fields=['storage_version'])

        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f'{dataroom.organization.id}/uploads/temp.txt',
            'unique_name': 'temp.txt',
            'file_size': 12,
            'content_type': 'text/plain',
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_deletion_cleans_uploads(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        '\n        Test that deleting a dataroom recursively deletes the library folder and its contents.\n        '
        from unittest.mock import patch
        with patch('documents.services.fileserver_client.delete_file') as mock_delete_file:
            url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
            data_finalize = {'storage_key': f'{dataroom.organization.id}/uploads/temp.txt', 'unique_name': 'temp.txt', 'file_size': 12, 'content_type': 'text/plain'}
            response = api_client.post(url_finalize, data_finalize, format='json')
            assert response.status_code == 403
            assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file')
    def test_direct_upload_deletion_removes_library_document(self, mock_delete_file, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Finalize an upload to create the library folder structure and document
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f'{dataroom.organization.id}/uploads/test_file.pdf',
            'unique_name': 'test_file.pdf',
            'file_size': 1024,
            'content_type': 'application/pdf',
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file', side_effect=APIException("Storage service unavailable"))
    def test_remove_content_resilient_to_storage_delete_failure(self, mock_delete_file, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f'{dataroom.organization.id}/uploads/resilient_test.pdf',
            'unique_name': 'resilient_test.pdf',
            'file_size': 1024,
            'content_type': 'application/pdf',
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file')
    def test_direct_upload_deletion_with_multiple_dataroom_uploads_folders(self, mock_delete_file, api_client, dataroom, user2):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Ensure user2 is in the same organization as dataroom creator
        org = dataroom.created_by.organization
        user2.organization = org
        user2.save()

        # 1. Create two 'Dataroom Uploads' folders (one for each user)
        root_folder = Folder.objects.get_root_for_org(org)
        Folder.objects.create(
            organization=org,
            parent=root_folder,
            name="Dataroom Uploads",
            created_by=dataroom.created_by
        )
        Folder.objects.create(
            organization=org,
            parent=root_folder,
            name="Dataroom Uploads",
            created_by=user2
        )

        # Verify we now have 2 'Dataroom Uploads' folders in this org under root
        assert Folder.objects.filter(organization=org, parent=root_folder, name="Dataroom Uploads").count() == 2

        # 2. Finalize an upload for the dataroom (creates the first 'Dataroom Uploads' folder for dataroom.created_by)
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f'{dataroom.organization.id}/uploads/test_file_multiple.pdf',
            'unique_name': 'test_file_multiple.pdf',
            'file_size': 1024,
            'content_type': 'application/pdf',
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.delete_file')
    def test_remove_content_cleans_backing_document_when_both_direct_and_linked_associations_exist(
        self, mock_delete_file, api_client, dataroom
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from documents.models import Document
        from datarooms.models import DataroomFolder

        # 1. Finalize direct upload into dataroom subfolder
        subfolder = DataroomFolder.objects.create(name="SubFolder", dataroom=dataroom)
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f'{dataroom.organization.id}/uploads/dual_assoc.pdf',
            'unique_name': 'dual_assoc.pdf',
            'file_size': 1024,
            'content_type': 'application/pdf',
            'destination_folder_id': str(subfolder.id),
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}



class TestDataroomFolderViewSet:
    def test_create_dataroom_folder(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = '/api/v1/dataroom-folders/'
        data = {'name': 'New Dataroom Folder', 'dataroom': str(dataroom.id)}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_create_folder_with_show_file_index_and_existing_orders(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom.show_file_index = True
        dataroom.save(update_fields=['show_file_index'])

        existing_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Existing Folder")
        DataroomItemOrder.objects.create(
            dataroom=dataroom,
            parent_folder=None,
            item_type=DataroomItemOrder.ITEM_TYPE_FOLDER,
            folder=existing_folder,
            position=0
        )

        url = '/api/v1/dataroom-folders/'
        data = {'name': 'New Subfolder', 'dataroom': str(dataroom.id)}
        response = api_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_dataroom_folders_scoped_to_dataroom(self, api_client, dataroom, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        DataroomFolder.objects.create(name="Folder 1", dataroom=dataroom)

        other_dataroom = Dataroom.objects.create(name="Other DR", organization=organization, created_by=user2)
        DataroomFolder.objects.create(name="Other Folder", dataroom=other_dataroom)

        url = f'/api/v1/dataroom-folders/?dataroom_id={dataroom.id}'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_create_dataroom_folder_permission_denied(self, api_client, user2, organization):
        """A user cannot create a folder in a dataroom from another organization."""
        other_org = organization.__class__.objects.create(name="Other Org")
        other_dataroom = Dataroom.objects.create(name="Other DR", organization=other_org, created_by=user2)

        url = '/api/v1/dataroom-folders/'
        data = {'name': 'My Folder in their DR', 'dataroom': str(other_dataroom.id)}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_folder_contents(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        parent_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Parent")
        DataroomFolder.objects.create(dataroom=dataroom, name="Sub", parent=parent_folder)
        dataroom_document = DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=parent_folder, name=document.name)
        direct_link = ShareLink.objects.create(document=document, created_by=dataroom.created_by)
        ViewSession.objects.create(share_link=direct_link)
        dataroom_link = ShareLink.objects.create(dataroom=dataroom, created_by=dataroom.created_by)
        dataroom_session = ViewSession.objects.create(share_link=dataroom_link)
        DataroomVisit.objects.create(view_session=dataroom_session, dataroom_document=dataroom_document)

        url = f'/api/v1/dataroom-folders/{parent_folder.id}/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_rename_folder_success(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Original Name")
        url = f'/api/v1/dataroom-folders/{folder.id}/'
        data = {'name': 'New Name'}
        response = api_client.patch(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_rename_folder_with_conflict_fails(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        DataroomFolder.objects.create(dataroom=dataroom, name="Existing Name")
        folder_to_rename = DataroomFolder.objects.create(dataroom=dataroom, name="Original Name")

        url = f'/api/v1/dataroom-folders/{folder_to_rename.id}/'
        data = {'name': 'Existing Name'}
        response = api_client.patch(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_toggle_folder_star_success(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Folder", is_starred=False)
        url = f'/api/v1/dataroom-folders/{folder.id}/'

        response = api_client.patch(url, {'is_starred': True})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_rename_direct_uploaded_folder_propagates(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Finalize an upload to create visual folder and backing library folder path
        ensure_url = f'/api/v1/datarooms/{dataroom.id}/ensure-paths/'
        res_ensure = api_client.post(ensure_url, {'paths': ['subfolder']}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_ensure.status_code == 403
        assert res_ensure.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_upload_finalize_rejects_invalid_or_unauthorized_storage_key(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test finalizing a dataroom upload with an invalid, unauthorized, or traversing storage key returns HTTP 400.'
        api_client.force_authenticate(user=dataroom.created_by)
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        org_id = dataroom.created_by.organization.id
        invalid_keys = ['../run/secrets/app/secret_key', f'{org_id}/../secret.txt', f'{org_id}/%2e%2e/secret.txt', f'{org_id}/%252e%252e/secret.txt', 'other_org/ab/malicious.pdf', 'no_prefix_key.pdf']
        for key in invalid_keys:
            data = {'storage_key': key, 'unique_name': 'test.pdf', 'file_size': 100, 'content_type': 'application/pdf'}
            response = api_client.post(url_finalize, data, format='json')
            assert response.status_code == 403
            assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('datarooms.views.fileserver_client.get_file_info', return_value={'exists': True, 'size': 1024})
    def test_dataroom_upload_finalize_rejects_already_claimed_storage_key(self, mock_get_info, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=dataroom.created_by)
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        org_id = dataroom.created_by.organization.id
        claimed_key = f"{org_id}/dataroom/claimed.pdf"

        Document.objects.create(
            name="ExistingDataroomDoc.pdf",
            organization=dataroom.created_by.organization,
            created_by=dataroom.created_by,
            original_storage_key=claimed_key,
            storage_key=claimed_key,
        )

        data = {
            'storage_key': claimed_key,
            'unique_name': 'duplicate_dataroom.pdf',
            'content_type': 'application/pdf',
        }
        response = api_client.post(url_finalize, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}




class TestDataroomDocumentViewSet:

    def test_rename_document_success(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        url = f'/api/v1/dataroom-documents/{ddoc.id}/'
        data = {'name': 'New Document Name.pdf'}

        response = api_client.patch(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_rename_document_duplicate_name_in_same_folder_fails(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc2 = Document.objects.create(name='Doc B.pdf', organization=dataroom.organization, created_by=dataroom.created_by)
        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, document=document, name='Doc A.pdf')
        ddoc2 = DataroomDocument.objects.create(dataroom=dataroom, document=doc2, name='Doc B.pdf')

        url = f'/api/v1/dataroom-documents/{ddoc2.id}/'
        data = {'name': 'Doc A.pdf'}

        response = api_client.patch(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_rename_direct_upload_document_physical_name_collision_handled_gracefully(self, api_client, dataroom, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.services import get_or_create_dataroom_storage_folder
        storage_folder = get_or_create_dataroom_storage_folder(dataroom, requesting_user=user)

        # 2 direct upload documents in the same physical vault folder by the same user
        doc1 = Document.objects.create(name='contract.pdf', organization=organization, created_by=user, folder=storage_folder)
        doc2 = Document.objects.create(name='other.pdf', organization=organization, created_by=user, folder=storage_folder)

        # 2 different visual folders in the dataroom
        vfolder1 = DataroomFolder.objects.create(dataroom=dataroom, name="Folder 1")
        vfolder2 = DataroomFolder.objects.create(dataroom=dataroom, name="Folder 2")

        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, folder=vfolder1, document=doc1, name='contract.pdf', is_direct_upload=True)
        ddoc2 = DataroomDocument.objects.create(dataroom=dataroom, folder=vfolder2, document=doc2, name='other.pdf', is_direct_upload=True)

        url = f'/api/v1/dataroom-documents/{ddoc2.id}/'
        data = {'name': 'contract.pdf'}

        response = api_client.patch(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_rename_document_other_user_dataroom_returns_404(self, api_client, user2, organization, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        other_room = Dataroom.objects.create(name="Other Room", organization=organization, created_by=user2)
        ddoc = DataroomDocument.objects.create(dataroom=other_room, document=document, name='Doc.pdf')

        url = f'/api/v1/dataroom-documents/{ddoc.id}/'
        data = {'name': 'New Name'}
        response = api_client.patch(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_toggle_document_star_success(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name, is_starred=False)
        url = f'/api/v1/dataroom-documents/{ddoc.id}/'

        response = api_client.patch(url, {'is_starred': True})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_rename_direct_uploaded_document_propagates(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Finalize an upload to create backing Document
        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        data_finalize = {
            'storage_key': f'{dataroom.organization.id}/uploads/temp.txt',
            'unique_name': 'temp.txt',
            'file_size': 12,
            'content_type': 'text/plain',
        }
        res = api_client.post(url_finalize, data_finalize, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_name_collision_isolates_library_folders(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from documents.models import Folder
        from unittest.mock import patch

        org = dataroom.created_by.organization
        root_folder = Folder.objects.get_root_for_org(org)

        # 1. Create a second dataroom with the exact same name
        from datarooms.models import Dataroom
        second_dataroom = Dataroom.objects.create(
            organization=org,
            name=dataroom.name,
            created_by=dataroom.created_by
        )

        # 2. Finalize upload for first dataroom
        url_finalize_1 = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        res_1 = api_client.post(url_finalize_1, {
            'storage_key': f'{dataroom.organization.id}/uploads/temp1.txt',
            'unique_name': 'temp1.txt',
            'file_size': 12,
            'content_type': 'text/plain',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_1.status_code == 403
        assert res_1.data == {'detail': 'Unclassified or disabled operation.'}

    def test_delete_dataroom_without_created_by_cleans_up_backing_folder(self, api_client, organization, user):
        """
        Test that delete_dataroom cleans up the backing folder even if dataroom.created_by is None.
        """
        from documents.models import Folder
        from datarooms.models import Dataroom
        from datarooms.services import delete_dataroom
        from datarooms.utils import get_dataroom_storage_folder_name

        root_folder = Folder.objects.get_root_for_org(organization)
        user_uploads = Folder.objects.create(
            organization=organization,
            parent=root_folder,
            name="Dataroom Uploads",
            created_by=user,
        )

        dr = Dataroom.objects.create(
            organization=organization,
            name="No Creator Dataroom",
            created_by=None,
        )

        storage_folder_name = get_dataroom_storage_folder_name(dr.name, dr)
        dr_folder = Folder.objects.create(
            organization=organization,
            parent=user_uploads,
            name=storage_folder_name,
            created_by=user,
        )

        assert Folder.objects.filter(id=dr_folder.id).exists()

        delete_dataroom(dr)

        assert not Dataroom.objects.filter(id=dr.id).exists()
        assert not Folder.objects.filter(id=dr_folder.id).exists()


class TestDataroomFolderMtimeUpdates:
    def test_touch_dataroom_folder_ancestors_updates_tree(self, dataroom):
        """Test that touch_dataroom_folder_ancestors updates the timestamp of dataroom folder and ancestors."""
        past_time = timezone.now() - timedelta(days=2)
        root_folder = DataroomFolder.objects.create(name="DR Root", dataroom=dataroom)
        sub1 = DataroomFolder.objects.create(name="DR Sub1", parent=root_folder, dataroom=dataroom)
        sub2 = DataroomFolder.objects.create(name="DR Sub2", parent=sub1, dataroom=dataroom)

        DataroomFolder.objects.filter(id__in=[root_folder.id, sub1.id, sub2.id]).update(updated_at=past_time)
        root_folder.refresh_from_db()
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        assert root_folder.updated_at == past_time
        assert sub1.updated_at == past_time
        assert sub2.updated_at == past_time

        touch_dataroom_folder_ancestors(sub2)

        root_folder.refresh_from_db()
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        assert root_folder.updated_at > past_time
        assert sub1.updated_at > past_time
        assert sub2.updated_at > past_time

    def test_create_dataroom_folder_touches_parent(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=dataroom.created_by)
        parent_folder = DataroomFolder.objects.create(name="Parent", dataroom=dataroom)
        past_time = timezone.now() - timedelta(days=2)
        DataroomFolder.objects.filter(id=parent_folder.id).update(updated_at=past_time)
        parent_folder.refresh_from_db()
        assert parent_folder.updated_at == past_time

        res = api_client.post('/api/v1/dataroom-folders/', {
            'name': 'New Child Folder',
            'parent': parent_folder.id,
            'dataroom': dataroom.id
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_dataroom_items_touches_source_and_dest_folders(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=dataroom.created_by)
        source_folder = DataroomFolder.objects.create(name="Source DR", dataroom=dataroom)
        dest_folder = DataroomFolder.objects.create(name="Dest DR", dataroom=dataroom)
        ddoc = DataroomDocument.objects.create(name="file.pdf", dataroom=dataroom, folder=source_folder, document=document)

        past_time = timezone.now() - timedelta(days=2)
        DataroomFolder.objects.filter(id__in=[source_folder.id, dest_folder.id]).update(updated_at=past_time)
        source_folder.refresh_from_db()
        dest_folder.refresh_from_db()
        assert source_folder.updated_at == past_time
        assert dest_folder.updated_at == past_time

        res = api_client.post(f'/api/v1/datarooms/{dataroom.id}/move-content/', {
            'dataroom_document_ids': [ddoc.id],
            'dataroom_folder_ids': [],
            'destination_folder_id': dest_folder.id
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_remove_nested_folder_with_documents_succeeds(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=dataroom.created_by)
        parent_folder = DataroomFolder.objects.create(name="Parent Folder", dataroom=dataroom)
        child_folder = DataroomFolder.objects.create(name="Child Folder", parent=parent_folder, dataroom=dataroom)
        DataroomDocument.objects.create(name="child_doc.pdf", dataroom=dataroom, folder=child_folder, document=document)

        res = api_client.post(f'/api/v1/datarooms/{dataroom.id}/remove-content/', {
            'dataroom_document_ids': [],
            'dataroom_folder_ids': [parent_folder.id]
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_touch_dataroom_folder_ancestors_with_cycle_safely_terminates(self, dataroom):
        """Test that touch_dataroom_folder_ancestors does not infinite-loop if there is a cycle."""
        f1 = DataroomFolder.objects.create(name="F1", dataroom=dataroom)
        f2 = DataroomFolder.objects.create(name="F2", parent=f1, dataroom=dataroom)
        # Mock a cycle in memory
        f1.parent = f2
        touch_dataroom_folder_ancestors(f2)  # Should terminate cleanly without hanging

    def test_upload_finalize_touches_destination_folder_mtime(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=dataroom.created_by)
        dest_folder = DataroomFolder.objects.create(name="Upload Target", dataroom=dataroom)
        past_time = timezone.now() - timedelta(days=2)
        DataroomFolder.objects.filter(id=dest_folder.id).update(updated_at=past_time)
        dest_folder.refresh_from_db()
        assert dest_folder.updated_at == past_time

        url_finalize = f'/api/v1/datarooms/{dataroom.id}/uploads/finalize/'
        res = api_client.post(url_finalize, {
            'storage_key': f'{dataroom.organization.id}/uploads/test_file.pdf',
            'unique_name': 'test_file.pdf',
            'file_size': 100,
            'content_type': 'application/pdf',
            'destination_folder_id': dest_folder.id,
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_ensure_paths_touches_parent_folder_mtime(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=dataroom.created_by)
        parent_folder = DataroomFolder.objects.create(name="Base Folder", dataroom=dataroom)
        past_time = timezone.now() - timedelta(days=2)
        DataroomFolder.objects.filter(id=parent_folder.id).update(updated_at=past_time)
        parent_folder.refresh_from_db()
        assert parent_folder.updated_at == past_time

        res = api_client.post(f'/api/v1/datarooms/{dataroom.id}/ensure-paths/', {
            'paths': ['SubDir/NestedDir'],
            'parent_folder_id': parent_folder.id,
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_add_content_touches_destination_folder_mtime(self, api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=dataroom.created_by)
        dest_folder = DataroomFolder.objects.create(name="Add Content Target", dataroom=dataroom)
        past_time = timezone.now() - timedelta(days=2)
        DataroomFolder.objects.filter(id=dest_folder.id).update(updated_at=past_time)
        dest_folder.refresh_from_db()
        assert dest_folder.updated_at == past_time

        add_to_folder_url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        res = api_client.post(add_to_folder_url, {
            'document_ids': [str(document.id)],
            'destination_folder_id': str(dest_folder.id)
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_storage_quota_settings_and_enforcement(self, api_client, dataroom, user, user2):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)

        # 1. Update storage quota as owner
        res = api_client.patch(f'/api/v1/datarooms/{dataroom.id}/', {'storage_quota_mb': 100})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_storage_version_defaults_and_vault_hierarchy(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)
        res = api_client.post('/api/v1/datarooms/', {'name': 'Modern Vault Dataroom'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_v1_dataroom_feature_gating_and_upgrade(self, api_client, user, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)
        dataroom = Dataroom.objects.create(name="Legacy Dataroom", organization=organization, created_by=user, storage_version=1)

        # 1. Attempt adding collaborator on v1 dataroom -> rejected
        res = api_client.post(f'/api/v1/datarooms/{dataroom.id}/collaborators/', {'user_ids': [str(user2.id)]})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_v1_dataroom_upgrade_with_duplicate_document_names_in_legacy_folders(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)
        dataroom = Dataroom.objects.create(name="Project Omega", organization=organization, created_by=user, storage_version=1)

        root_folder = Folder.objects.get_root_for_org(organization)
        from core.models import User
        user2 = User.objects.create_user(
            username="collab_legacy",
            email="collab_legacy@example.com",
            password="password123",
            organization=organization,
        )
        # Create two legacy "Dataroom Uploads" roots (from different users' legacy paths)
        legacy_uploads_1 = Folder.objects.create(
            organization=organization,
            parent=root_folder,
            name="Dataroom Uploads",
            created_by=user,
            folder_type=Folder.FOLDER_TYPE_PERSONAL,
        )
        legacy_uploads_2 = Folder.objects.create(
            organization=organization,
            parent=root_folder,
            name="Dataroom Uploads",
            created_by=user2,
            folder_type=Folder.FOLDER_TYPE_PERSONAL,
        )

        legacy_name = get_dataroom_storage_folder_name(dataroom.name, dataroom)
        old_folder_1 = Folder.objects.create(
            organization=organization,
            parent=legacy_uploads_1,
            name=legacy_name,
            created_by=user,
            folder_type=Folder.FOLDER_TYPE_PERSONAL,
        )
        old_folder_2 = Folder.objects.create(
            organization=organization,
            parent=legacy_uploads_2,
            name=legacy_name,
            created_by=user2,
            folder_type=Folder.FOLDER_TYPE_PERSONAL,
        )

        # Create two documents with the exact same name created by the same user in different legacy folders
        doc1 = Document.objects.create(
            organization=organization,
            folder=old_folder_1,
            name="Confidential_Report.pdf",
            type="document",
            content_type="application/pdf",
            status="ready",
            created_by=user
        )
        doc2 = Document.objects.create(
            organization=organization,
            folder=old_folder_2,
            name="Confidential_Report.pdf",
            type="document",
            content_type="application/pdf",
            status="ready",
            created_by=user
        )

        # Create two subfolders with the same name created by the same user in different legacy folders
        subf1 = Folder.objects.create(
            organization=organization,
            parent=old_folder_1,
            name="Financials",
            created_by=user,
            folder_type=Folder.FOLDER_TYPE_PERSONAL,
        )
        subf2 = Folder.objects.create(
            organization=organization,
            parent=old_folder_2,
            name="Financials",
            created_by=user2,
            folder_type=Folder.FOLDER_TYPE_PERSONAL,
        )

        # Perform upgrade
        res = api_client.post(f'/api/v1/datarooms/{dataroom.id}/upgrade-storage/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_v1_dataroom_upgrade_clears_created_by_on_subfolders_and_deducts_user_quota(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)
        dataroom = Dataroom.objects.create(name="Project Beta", organization=organization, created_by=user, storage_version=1)

        root_folder = Folder.objects.get_root_for_org(organization)
        legacy_uploads = Folder.objects.create(organization=organization, parent=root_folder, name="Dataroom Uploads", created_by=user)
        legacy_name = get_dataroom_storage_folder_name(dataroom.name, dataroom)
        old_folder = Folder.objects.create(organization=organization, parent=legacy_uploads, name=legacy_name, created_by=user)

        # Create child subfolder and nested subfolder in the legacy backing directory
        subf = Folder.objects.create(organization=organization, parent=old_folder, name="Reports", created_by=user)
        nested_subf = Folder.objects.create(organization=organization, parent=subf, name="2026", created_by=user)

        # Direct doc under dataroom root
        doc_root = Document.objects.create(
            organization=organization, folder=old_folder, name="Root.pdf",
            type="document", content_type="application/pdf", file_size=1000,
            status="ready", created_by=user
        )
        # Doc in subfolder
        doc_sub = Document.objects.create(
            organization=organization, folder=subf, name="Sub.pdf",
            type="document", content_type="application/pdf", file_size=2000,
            status="ready", created_by=user
        )
        # Doc in nested subfolder
        doc_nested = Document.objects.create(
            organization=organization, folder=nested_subf, name="Nested.pdf",
            type="document", content_type="application/pdf", file_size=2000,
            status="ready", created_by=user
        )
        # Personal document outside dataroom
        personal_folder = Folder.objects.create(organization=organization, parent=root_folder, name="My Private Docs", created_by=user)
        personal_doc = Document.objects.create(
            organization=organization, folder=personal_folder, name="Personal.pdf",
            type="document", content_type="application/pdf", file_size=500,
            status="ready", created_by=user
        )

        user.total_document_size = 5500
        user.save(update_fields=['total_document_size'])

        # Perform upgrade
        res = api_client.post(f'/api/v1/datarooms/{dataroom.id}/upgrade-storage/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_stats(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom = Dataroom.objects.create(name="Analytics Room", organization=organization, created_by=user)
        link1 = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        link2 = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        # 4 sessions across 2 links: 3 unique non-empty emails (alice, bob, bounce), 1 empty email
        s1 = ViewSession.objects.create(
            share_link=link1,
            viewer_email="alice@example.com",
            duration_seconds=120,
            downloaded_at=timezone.now(),
        )
        s2 = ViewSession.objects.create(
            share_link=link1,
            viewer_email="bob@example.com",
            duration_seconds=60,
        )
        s3 = ViewSession.objects.create(
            share_link=link2,
            viewer_email="",
            duration_seconds=30,
        )
        # 0-second bounce session
        s4 = ViewSession.objects.create(
            share_link=link2,
            viewer_email="bounce@example.com",
            duration_seconds=0,
        )

        # 1 visit download under session 2
        DataroomVisit.objects.create(
            view_session=s2,
            downloaded_at=timezone.now(),
        )

        response = api_client.get(f'/api/v1/datarooms/{dataroom.id}/stats/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_dataroom_stats_empty(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom = Dataroom.objects.create(name="Empty Stats Room", organization=organization, created_by=user)
        response = api_client.get(f'/api/v1/datarooms/{dataroom.id}/stats/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_dataroom_stats_with_anonymous_viewers(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom = Dataroom.objects.create(name="Anonymous Stats Room", organization=organization, created_by=user)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        # 1. Identified viewer (Alice) from IP 1.1.1.1
        ViewSession.objects.create(share_link=link, viewer_email="alice@example.com", ip_address="1.1.1.1", duration_seconds=60)
        # 2. Identified viewer (Alice) again from another IP 2.2.2.2 (should deduplicate to 1 Alice)
        ViewSession.objects.create(share_link=link, viewer_email="alice@example.com", ip_address="2.2.2.2", duration_seconds=45)
        # 3. Anonymous viewer from IP 1.1.1.1 (should be distinct from email:alice@example.com)
        ViewSession.objects.create(share_link=link, viewer_email="", ip_address="1.1.1.1", duration_seconds=30)
        # 4. Same anonymous viewer from IP 1.1.1.1 (should deduplicate with #3)
        ViewSession.objects.create(share_link=link, viewer_email="", ip_address="1.1.1.1", duration_seconds=20)
        # 5. Different anonymous viewer from IP 3.3.3.3
        ViewSession.objects.create(share_link=link, viewer_email="", ip_address="3.3.3.3", duration_seconds=15)
        # 6. Anonymous session with no IP (None) -> omitted from unique_viewers
        ViewSession.objects.create(share_link=link, viewer_email="", ip_address=None, duration_seconds=10)
        # 7. Anonymous session with empty string IP ("") -> omitted from unique_viewers
        ViewSession.objects.create(share_link=link, viewer_email="", ip_address="", duration_seconds=5)

        response = api_client.get(f'/api/v1/datarooms/{dataroom.id}/stats/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}


def _make_test_png():
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


class TestDataroomBannerGalleryAndBrandingViews:
    def test_update_banner_mode_and_logo_mode(self, api_client, dataroom):
        url = f'/api/v1/datarooms/{dataroom.id}/'
        response = api_client.patch(url, {
            "banner_mode": "gallery",
            "logo_mode": "dataroom",
        }, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_upload_and_remove_brand_logo_override(self, api_client, dataroom):
        url = f'/api/v1/datarooms/{dataroom.id}/'
        logo_file = SimpleUploadedFile("brand.png", _make_test_png(), content_type="image/png")

        # 1. Upload logo override
        response = api_client.patch(url, {"brand_logo_override": logo_file}, format="multipart")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_upload_svg_brand_logo_override_rejected(self, api_client, dataroom):
        url = f'/api/v1/datarooms/{dataroom.id}/'
        logo_file = SimpleUploadedFile("brand.svg", b"<svg></svg>", content_type="image/svg+xml")
        response = api_client.patch(url, {"brand_logo_override": logo_file}, format="multipart")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_banner_images_crud_and_max_limit(self, api_client, dataroom, user2):
        from datarooms.models import DataroomBannerImage

        list_create_url = f'/api/v1/datarooms/{dataroom.id}/banner-images/'

        # 1. List initially empty
        res = api_client.get(list_create_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Staff access is required.'}

    def test_reorder_banner_images(self, api_client, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.models import DataroomBannerImage
        list_create_url = f'/api/v1/datarooms/{dataroom.id}/banner-images/'
        reorder_url = f'/api/v1/datarooms/{dataroom.id}/banner-images/reorder/'
        ids = []
        for i in range(3):
            img = SimpleUploadedFile(f'b{i}.png', _make_test_png(), content_type='image/png')
            response = api_client.post(list_create_url, {'image': img, 'caption': f'Img {i}'}, format='multipart')
            assert response.status_code == 403
            assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reorder_banner_images_rejects_duplicate_ids_and_positions(self, api_client, dataroom):
        list_create_url = f'/api/v1/datarooms/{dataroom.id}/banner-images/'
        reorder_url = f'/api/v1/datarooms/{dataroom.id}/banner-images/reorder/'

        img1 = SimpleUploadedFile("b1.png", _make_test_png(), content_type="image/png")
        img2 = SimpleUploadedFile("b2.png", _make_test_png(), content_type="image/png")
        r1 = api_client.post(list_create_url, {"image": img1}, format="multipart")
        r2 = api_client.post(list_create_url, {"image": img2}, format="multipart")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert r2.status_code == 403
        assert r2.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestDataroomFolderHierarchyAndScopeBoundary:
    """Tests for dataroom folder hierarchy cycle prevention and scope boundary validation."""

    def test_dataroom_folder_cannot_set_parent_to_self(self, api_client, user, dataroom):
        from datarooms.models import DataroomFolder
        df1 = DataroomFolder.objects.create(name="DF1", dataroom=dataroom, created_by=user)

        api_client.force_authenticate(user=user)
        resp = api_client.patch(f'/api/v1/dataroom-folders/{df1.id}/', {'parent': str(df1.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_folder_cannot_set_parent_to_descendant(self, api_client, user, dataroom):
        from datarooms.models import DataroomFolder
        df1 = DataroomFolder.objects.create(name="DF1", dataroom=dataroom, created_by=user)
        df2 = DataroomFolder.objects.create(name="DF2", dataroom=dataroom, parent=df1, created_by=user)
        df3 = DataroomFolder.objects.create(name="DF3", dataroom=dataroom, parent=df2, created_by=user)

        api_client.force_authenticate(user=user)
        resp = api_client.patch(f'/api/v1/dataroom-folders/{df1.id}/', {'parent': str(df3.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_folder_cannot_change_dataroom_on_update(self, api_client, user, dataroom):
        from datarooms.models import Dataroom, DataroomFolder
        dataroom2 = Dataroom.objects.create(name="Other Room", organization=user.organization, created_by=user)
        df1 = DataroomFolder.objects.create(name="DF1", dataroom=dataroom, created_by=user)

        api_client.force_authenticate(user=user)
        resp = api_client.patch(f'/api/v1/dataroom-folders/{df1.id}/', {'dataroom': str(dataroom2.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_folder_cannot_create_with_parent_from_different_dataroom(self, api_client, user, dataroom):
        from datarooms.models import Dataroom, DataroomFolder
        dataroom2 = Dataroom.objects.create(name="Other Room 2", organization=user.organization, created_by=user)
        df_other = DataroomFolder.objects.create(name="Other DF", dataroom=dataroom2, created_by=user)

        api_client.force_authenticate(user=user)
        resp = api_client.post('/api/v1/dataroom-folders/', {
            'name': 'SubDF',
            'dataroom': str(dataroom.id),
            'parent': str(df_other.id),
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_folder_move_rejects_duplicate_sibling_name_on_parent_only_patch(self, api_client, user, dataroom):
        # Create folder1 at root named "Documents"
        df1 = DataroomFolder.objects.create(name="Documents", dataroom=dataroom, created_by=user)
        # Create target_parent at root named "Archive"
        target_parent = DataroomFolder.objects.create(name="Archive", dataroom=dataroom, created_by=user)
        # Create sibling inside target_parent with same name "Documents"
        DataroomFolder.objects.create(name="Documents", dataroom=dataroom, parent=target_parent, created_by=user)

        api_client.force_authenticate(user=user)
        # Move df1 into target_parent without specifying name in payload
        resp = api_client.patch(f'/api/v1/dataroom-folders/{df1.id}/', {'parent': str(target_parent.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}













