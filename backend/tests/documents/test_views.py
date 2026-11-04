import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.exceptions import APIException

from core.models import Organization
from documents.models import (Document, DocumentPage, DocumentVersion, Folder)
from documents.renderers.pdf import PDFRenderer
from documents.services import QuotaExceededError
from sharelinks.models import (ShareLink, ViewSession)

User = get_user_model()


@pytest.fixture
def document_factory(user, organization):
    def _create_document(**kwargs):
        defaults = {
            "created_by": user,
            "organization": organization,
            "status": "ready",
        }
        defaults.update(kwargs)
        doc = Document.objects.create(**defaults)
        version_file_size = kwargs.get('file_size')
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            is_primary=True,
            original_storage_key="path/to/original.pdf",
            file_size=version_file_size
        )
        return doc
    return _create_document

@pytest.mark.django_db
def test_get_root_folder_contents(api_client, user, user2, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # Get the invisible root folder for the organization
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')

    # user's content
    user_root_folder = Folder.objects.create(
        name="My Root Folder", organization=organization, created_by=user, parent=root_folder
    )
    # This subfolder should not be in the root listing
    Folder.objects.create(
        name="My Subfolder", organization=organization, created_by=user, parent=user_root_folder
    )
    Document.objects.create(
        name="My Root Document", organization=organization, created_by=user, folder=root_folder
    )

    # user2's content (should not appear)
    Folder.objects.create(
        name="Other's Folder", organization=organization, created_by=user2, parent=root_folder
    )
    Document.objects.create(
        name="Other's Document", organization=organization, created_by=user2, folder=root_folder
    )

    response = api_client.get('/api/v1/folders/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_get_folder_contents_retrieve(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    parent_folder = Folder.objects.create(
        name="Parent Folder", organization=organization, created_by=user, parent=root_folder
    )
    sub_folder = Folder.objects.create(
        name="Subfolder 1", organization=organization, created_by=user, parent=parent_folder
    )
    Document.objects.create(
        name="Document In Folder", organization=organization, created_by=user, folder=parent_folder
    )

    response = api_client.get(f'/api/v1/folders/{parent_folder.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_list_root_folder_with_multiple_items(api_client, user, user2, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')

    # Items that should appear in the root listing for 'user'
    Folder.objects.create(name="Root Folder A", organization=organization, created_by=user, parent=root_folder)
    Folder.objects.create(name="Root Folder B", organization=organization, created_by=user, parent=root_folder)
    Document.objects.create(name="Root Doc A", organization=organization, created_by=user, folder=root_folder)

    # Item that should NOT appear (it is a sub-folder)
    parent = Folder.objects.create(name="Parent With Subfolder", organization=organization, created_by=user, parent=root_folder)
    Folder.objects.create(name="Subfolder", organization=organization, created_by=user, parent=parent)

    # Items that should NOT appear (owned by another user)
    Folder.objects.create(name="User2 Folder", organization=organization, created_by=user2, parent=root_folder)
    Document.objects.create(name="User2 Doc", organization=organization, created_by=user2, folder=root_folder)

    response = api_client.get('/api/v1/folders/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_list_sub_folder_contents_and_check_permissions(api_client, user, user2, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    
    # Structure for 'user'
    level1 = Folder.objects.create(name="Level 1", organization=organization, created_by=user, parent=root_folder)
    level2 = Folder.objects.create(name="Level 2", organization=organization, created_by=user, parent=level1)
    Folder.objects.create(name="Subfolder in Level 2", organization=organization, created_by=user, parent=level2)
    Document.objects.create(name="Doc in Level 2", organization=organization, created_by=user, folder=level2)
    
    # Item that should NOT appear in Level 2 listing
    Document.objects.create(name="Doc in Level 1", organization=organization, created_by=user, folder=level1)

    # Folder for 'user2' that 'user' should not be able to access
    user2_folder = Folder.objects.create(name="User2 Folder", organization=organization, created_by=user2, parent=root_folder)

    # 1. Test listing contents of 'user's 'level2' folder
    response = api_client.get(f'/api/v1/folders/{level2.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_create_folder(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # The __root__ folder is created automatically
    assert Folder.objects.count() == 1

    data = {'name': 'New API Folder'}
    response = api_client.post('/api/v1/folders/', data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_create_duplicate_root_folder_is_renamed(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    data = {'name': 'Duplicate Folder'}
    response1 = api_client.post('/api/v1/folders/', data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response1.status_code == 403
    assert response1.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_create_duplicate_subfolder_is_renamed(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # Create a parent folder via API
    parent_data = {'name': 'Parent'}
    parent_response = api_client.post('/api/v1/folders/', parent_data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert parent_response.status_code == 403
    assert parent_response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestEnsureFolderPathsView:
    """Tests for the EnsureFolderPathsView endpoint."""

    def test_ensure_paths_success_and_returns_mappings(self, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # __root__ folder exists
        assert Folder.objects.count() == 1

        path_data = {'paths': ['Reports/Q1', 'Data/Internal']}
        response = api_client.post('/api/v1/folders/ensure-paths/', path_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_ensure_paths_renames_conflicting_top_level_folder(self, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        root = Folder.objects.get(name='__root__', parent=None)
        Folder.objects.create(name="Reports", created_by=user, organization=user.organization, parent=root)
        assert Folder.objects.count() == 2  # __root__, Reports

        path_data = {'paths': ['Reports/Q1', 'Reports/Q2']}
        response = api_client.post('/api/v1/folders/ensure-paths/', path_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    # def test_ensure_paths_permission_denied(self, api_client, user2):
    #     """Test a user cannot create a subfolder inside another user's folder."""
    #     root = Folder.objects.get(name='__root__', parent=None, organization=user2.organization)
    #     user2_folder = Folder.objects.create(name="User2s-Folder", organization=user2.organization, created_by=user2, parent=root)
    #     assert Folder.objects.count() == 2

    #     path_data = {'paths': ["User2s-Folder/My-Stuff"]}
    #     response = api_client.post('/api/v1/folders/ensure-paths/', path_data)

    #     assert response.status_code == status.HTTP_403_FORBIDDEN
    #     assert Folder.objects.count() == 2  # No new folders created

    # def test_ensure_paths_is_atomic(self, api_client, user, user2):
    #     """Test that if one path fails, the whole transaction is rolled back."""
    #     root = Folder.objects.get(name='__root__', parent=None, organization=user2.organization)
    #     user2_folder = Folder.objects.create(name="User2s-Folder", organization=user2.organization, created_by=user2, parent=root)
    #     assert Folder.objects.count() == 2

    #     path_data = {'paths': ["Good-Folder/Sub", "User2s-Folder/My-Stuff"]}
    #     response = api_client.post('/api/v1/folders/ensure-paths/', path_data)

    #     assert response.status_code == status.HTTP_403_FORBIDDEN
    #     # Ensure no folders were created at all
    #     assert Folder.objects.count() == 2
    #     assert not Folder.objects.filter(created_by=user).exists()

    def test_ensure_paths_in_subfolder_success(self, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        root = Folder.objects.get(name='__root__', parent=None)
        parent = Folder.objects.create(name="Parent", created_by=user, organization=user.organization, parent=root)
        
        path_data = {
            'paths': ['NewFolder/Sub'],
            'parent_path': 'Parent'
        }
        response = api_client.post('/api/v1/folders/ensure-paths/', path_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_ensure_paths_in_subfolder_renames_conflict(self, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        root = Folder.objects.get(name='__root__', parent=None)
        parent = Folder.objects.create(name="Parent", created_by=user, organization=user.organization, parent=root)
        Folder.objects.create(name="Existing", created_by=user, organization=user.organization, parent=parent)
        
        path_data = {
            'paths': ['Existing/Sub'],
            'parent_path': 'Parent'
        }
        response = api_client.post('/api/v1/folders/ensure-paths/', path_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}
    
    def test_ensure_paths_with_invalid_parent_path(self, api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        path_data = {
            'paths': ['NewFolder/Sub'],
            'parent_path': 'NonExistent'
        }
        response = api_client.post('/api/v1/folders/ensure-paths/', path_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_ensure_paths_allows_separate_users_to_create_same_name_folder(self, api_client, user, user2):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # User A (the default user for api_client) creates a folder
        path_data_user_a = {'paths': ['Marketing']}
        response_a = api_client.post('/api/v1/folders/ensure-paths/', path_data_user_a)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_a.status_code == 403
        assert response_a.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_delete_folder_permission_denied(api_client, user2):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # user2 creates a folder
    folder_by_user2 = Folder.objects.create(
        organization=user2.organization,
        created_by=user2,
        name="User2's Folder"
    )

    # api_client (logged in as user) tries to delete it
    response = api_client.delete(f'/api/v1/folders/{folder_by_user2.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.services.fileserver_client.delete_file')
def test_soft_delete_folder_keeps_size_and_files(mock_fs_delete, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # 1. Setup folder structure and documents
    root_folder = Folder.objects.get_root_for_org(organization)
    folder_to_delete = Folder.objects.create(
        name="Top Level", organization=organization, created_by=user, parent=root_folder
    )
    subfolder = Folder.objects.create(
        name="Subfolder", organization=organization, created_by=user, parent=folder_to_delete
    )

    doc1_size = 1 * 1024 * 1024
    doc2_size = 2 * 1024 * 1024
    total_size = doc1_size + doc2_size

    doc1 = Document.objects.create(
        name="Doc1.pdf", organization=organization, created_by=user, folder=folder_to_delete, file_size=doc1_size
    )
    doc2 = Document.objects.create(
        name="Doc2.pdf", organization=organization, created_by=user, folder=subfolder, file_size=doc2_size
    )

    # Create versions and pages to check for file deletion
    v1 = DocumentVersion.objects.create(document=doc1, version_number=1, original_storage_key="doc1.pdf")
    DocumentPage.objects.create(document_version=v1, page_number=1, storage_key="doc1_page1.png")
    v2 = DocumentVersion.objects.create(document=doc2, version_number=1, original_storage_key="doc2.pdf")

    # 2. Set user's initial size
    user.total_document_size = total_size
    user.save()
    assert user.total_document_size == total_size

    # 3. Perform deletion
    response = api_client.delete(f'/api/v1/folders/{folder_to_delete.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.services.fileserver_client.delete_file')
def test_permanent_delete_trash_item_file_server_error_returns_500(mock_fs_delete, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    mock_fs_delete.side_effect = APIException("File server error")

    root_folder = Folder.objects.get_root_for_org(organization)
    folder = Folder.objects.create(name="Folder", organization=organization, created_by=user, parent=root_folder)
    doc = Document.objects.create(name="Doc.pdf", organization=organization, created_by=user, folder=folder, file_size=100)
    DocumentVersion.objects.create(document=doc, version_number=1, original_storage_key="doc.pdf")

    user.total_document_size = 100
    user.save()

    # Soft delete first
    api_client.delete(f'/api/v1/folders/{folder.id}/')

    # Now permanently delete from trash
    response = api_client.delete(f'/api/v1/trash/{folder.id}/permanent/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_update_folder_name(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    folder = Folder.objects.create(
        name="Original Name", organization=organization, created_by=user, parent=root_folder
    )

    response = api_client.patch(f'/api/v1/folders/{folder.id}/', {'name': 'New Name'})
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_update_folder_star_status(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    folder = Folder.objects.create(
        name="My Folder", organization=organization, created_by=user, parent=root_folder
    )
    assert folder.is_starred is False

    # Star the folder
    response = api_client.patch(f'/api/v1/folders/{folder.id}/', {'is_starred': True})
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_update_folder_permission_denied(api_client, user2, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    folder_by_user2 = Folder.objects.create(
        name="User2's Folder", organization=organization, created_by=user2, parent=root_folder
    )

    # api_client (logged in as user) tries to rename it
    response = api_client.patch(f'/api/v1/folders/{folder_by_user2.id}/', {'name': 'New Name'})
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_star_folder_permission_denied(api_client, user2, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    folder_by_user2 = Folder.objects.create(
        name="User2's Folder", organization=organization, created_by=user2, parent=root_folder, is_starred=False
    )

    # api_client (logged in as user) tries to star it
    response = api_client.patch(f'/api/v1/folders/{folder_by_user2.id}/', {'is_starred': True})
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_create_folder_with_other_users_parent_folder_fails(api_client, user2, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    parent_by_user2 = Folder.objects.create(
        name="User2's Parent", organization=organization, created_by=user2, parent=root_folder
    )

    data = {'name': 'My Subfolder', 'parent': str(parent_by_user2.id)}
    response = api_client.post('/api/v1/folders/', data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_create_folder_with_non_existent_parent_fails(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    non_existent_parent_id = 'fld_00000000000000000000000000'
    data = {'name': 'Subfolder', 'parent': non_existent_parent_id}
    response = api_client.post('/api/v1/folders/', data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_list_folder_contents_includes_share_link_views(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    doc = Document.objects.create(name="Doc with views", organization=organization, created_by=user, folder=root_folder)
    link = ShareLink.objects.create(document=doc, created_by=user)
    ViewSession.objects.create(share_link=link, viewer_email="viewer1@test.com")
    ViewSession.objects.create(share_link=link, viewer_email="viewer2@test.com")

    response = api_client.get('/api/v1/folders/')  # list root folder
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_list_folder_contents_includes_direct_share_link_view_count(api_client, user, organization, dataroom):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from datarooms.models import DataroomDocument
    from sharelinks.models import DataroomVisit

    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    doc = Document.objects.create(name="Doc with direct views", organization=organization, created_by=user, folder=root_folder)
    direct_link = ShareLink.objects.create(document=doc, created_by=user)
    ViewSession.objects.create(share_link=direct_link, viewer_email="viewer1@test.com")
    ViewSession.objects.create(share_link=direct_link, viewer_email="viewer2@test.com")

    dataroom_doc = DataroomDocument.objects.create(dataroom=dataroom, document=doc, name=doc.name)
    dataroom_link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
    dataroom_session = ViewSession.objects.create(share_link=dataroom_link, viewer_email="viewer3@test.com")
    DataroomVisit.objects.create(view_session=dataroom_session, dataroom_document=dataroom_doc)

    response = api_client.get('/api/v1/folders/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_list_documents_is_scoped_to_user_and_root_only(api_client, user, user2, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    folder = Folder.objects.create(organization=organization, created_by=user, name="Test Folder")
    Document.objects.create(
        name="My Root Document",
        organization=organization,
        created_by=user,
    )
    Document.objects.create(
        name="My Folder Document",
        organization=organization,
        created_by=user,
        folder=folder
    )
    Document.objects.create(
        name="Other User's Document",
        organization=organization,
        created_by=user2,
    )
    response = api_client.get('/api/v1/documents/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_list_documents_includes_direct_share_link_view_count(api_client, user, organization):
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    doc = Document.objects.create(
        name="Viewed Document",
        organization=organization,
        created_by=user,
        folder=root_folder,
    )
    link = ShareLink.objects.create(document=doc, created_by=user)
    ViewSession.objects.create(share_link=link, viewer_email="viewer1@test.com")
    ViewSession.objects.create(share_link=link, viewer_email="viewer2@test.com")

    response = api_client.get('/api/v1/documents/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_list_documents_in_folder(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get(organization=organization, parent=None, name='__root__')
    target_folder = Folder.objects.create(
        name="Target Folder", organization=organization, created_by=user, parent=root_folder
    )
    Document.objects.create(
        name="Document In Folder", organization=organization, created_by=user, folder=target_folder
    )
    Document.objects.create(
        name="Root Document", organization=organization, created_by=user, folder=root_folder
    )

    response = api_client.get(f'/api/v1/documents/?folder={target_folder.id}')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_create_document_is_deprecated(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # This endpoint is effectively deprecated by the async upload view.
    # A good test is to ensure it can't be used to bypass the async flow.
    # This example shows a simple creation for demonstration.
    data = {
        'name': 'New API Doc',
        'type': 'docx',
        'content_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    response = api_client.post('/api/v1/documents/', data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.get_file_info', return_value={'exists': True, 'size': 123})
@patch('documents.views.fileserver_client.generate_upload_url')
def test_upload_document_with_path(mock_fs_upload_url, mock_fs_get_file_info, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    mock_fs_upload_url.return_value = "/files/upload/some-token"
    # First, create the folder structure
    path_data = {'paths': ['Client Reports/Q4/Final']}
    response = api_client.post('/api/v1/folders/ensure-paths/', path_data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.get_file_info')
@patch('documents.views.fileserver_client.generate_upload_url')
def test_upload_duplicate_root_file_is_renamed(mock_fs_upload_url, mock_fs_get_file_info, api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    mock_fs_upload_url.return_value = "/files/upload/some-token"
    mock_fs_get_file_info.side_effect = [
        {'exists': True, 'size': 123},
        {'exists': True, 'size': 456},
    ]

    first_request_data = {'file_name': 'foo.txt', 'path': 'foo.txt', 'file_size': 123}
    first_request = api_client.post('/api/v1/uploads/document/request/', first_request_data)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert first_request.status_code == 403
    assert first_request.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.get_file_info', return_value={'exists': True, 'size': 1024})
@patch('documents.views.fileserver_client.generate_upload_url')
def test_finalize_duplicate_name_defensive_rename(mock_fs_upload_url, mock_fs_get_file_info, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    mock_fs_upload_url.return_value = "/files/upload/some-token"

    # Create initial document named 'README_zh.md'
    root_folder = Folder.objects.get_root_for_org(user.organization)
    Document.objects.create(name='README_zh.md', organization=user.organization, created_by=user, folder=root_folder)

    # Finalize a new upload where client passes 'README_zh.md' as unique_name
    finalize_data = {
        'storage_key': f"{user.organization.id}/storage/README_zh.md",
        'unique_name': 'README_zh.md',
        'content_type': 'text/markdown',
        'path': None
    }
    response = api_client.post('/api/v1/uploads/document/finalize/', finalize_data, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_finalize_invalid_or_unauthorized_storage_key(api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)

    # Key from different org
    response = api_client.post('/api/v1/uploads/document/finalize/', {
        'storage_key': 'other_org_id/ab/12345.pdf',
        'unique_name': 'test.pdf',
        'file_size': 100,
        'content_type': 'application/pdf',
    }, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_finalize_nonexistent_destination_path_returns_400(api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)

    response = api_client.post('/api/v1/uploads/document/finalize/', {
        'storage_key': f"{user.organization.id}/ab/12345.pdf",
        'unique_name': 'test.pdf',
        'file_size': 100,
        'content_type': 'application/pdf',
        'path': 'NonExistentFolder/SubFolder/test.pdf'
    }, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@override_settings(SITE_DOMAIN="http://test.coneshare.com")
@patch('documents.views.fileserver_client.generate_download_url')
def test_get_document_preview_data_for_image_document(
    mock_fs_download_url, api_client, image_document_with_content
):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    primary_version = image_document_with_content.versions.get(is_primary=True)
    mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/some-token"

    url = f'/api/v1/documents/{image_document_with_content.id}/preview-data/'
    response = api_client.get(url)
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@override_settings(SITE_DOMAIN="http://test.coneshare.com")
@override_settings(PDF_PREVIEW_ENGINE='server_pages')
@patch('documents.views.fileserver_client.generate_download_url')
def test_get_document_preview_data_success(mock_fs_download_url, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # Setup
    mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/some-token"
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        name="preview.pdf",
        num_pages=1,
        status='ready'
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        has_pages=True,
        num_pages=1
    )
    page = DocumentPage.objects.create(
        document_version=version, page_number=1, storage_key="pages/1.png"
    )

    # Action
    response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.fileserver.fileserver_client.generate_download_url')
def test_get_spreadsheet_document_preview_data_success(mock_fs_download_url, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/sheet-json"
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        name="sales.xlsx",
        type="spreadsheet",
        num_pages=2,
        status='ready'
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        has_pages=False,
        num_pages=2,
        type="spreadsheet",
        storage_key="documents/1/sales_spreadsheet.json",
        original_storage_key="documents/1/sales.xlsx",
        render_status="ready"
    )

    response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_get_document_preview_data_permission_denied_for_other_user(api_client, user2):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # user2 creates a document
    doc_by_user2 = Document.objects.create(
        organization=user2.organization,
        created_by=user2,
        name="user2_doc.pdf",
        status='ready'
    )
    
    # api_client (logged in as user) tries to access it
    response = api_client.get(f'/api/v1/documents/{doc_by_user2.id}/preview-data/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_get_document_preview_data_not_ready(api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        name="processing.pdf",
        status='processing'
    )
    response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@override_settings(MAX_PREVIEW_PAGES=10, PDF_PREVIEW_ENGINE='server_pages')
def test_get_document_preview_data_too_many_pages(api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        name="large_doc.pdf",
        status='ready',
        num_pages=11,
        type='pdf',
        content_type='application/pdf',
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        original_storage_key="large_doc.pdf",
        storage_key="large_doc.pdf",
        type='pdf',
        render_status=DocumentVersion.RENDER_FAILED,
        render_error="Document has too many pages to generate a preview.",
    )
    response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@override_settings(PDF_PREVIEW_ENGINE='server_pages')
@patch('documents.views.fileserver_client.delete_file')
@patch('documents.services.generate_pdf_pages_task.delay')
def test_post_rebuild_preview(mock_task_delay, mock_delete_file, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        status='ready',
        type='pdf',
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        original_storage_key="test_rebuild.pdf",
        storage_key="test_rebuild.pdf",
        type='pdf',
        is_primary=True,
        render_status=DocumentVersion.RENDER_READY,
        render_error="Some error",
        has_pages=True,
        num_pages=3,
    )
    
    # Create mock pages
    page1 = DocumentPage.objects.create(document_version=version, page_number=1, storage_key="page1.png")
    page2 = DocumentPage.objects.create(document_version=version, page_number=2, storage_key="page2.png")
    
    assert DocumentPage.objects.filter(document_version=version).count() == 2
    
    # Make request with POST rebuild-preview
    response = api_client.post(f'/api/v1/documents/{doc.id}/rebuild-preview/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.delete_file')
@patch('documents.services.generate_pdf_pages_task.delay')
def test_rebuild_preview_concurrency_conflict(mock_task_delay, mock_delete_file, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        status='ready',
        type='pdf',
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        original_storage_key="test_rebuild.pdf",
        storage_key="test_rebuild.pdf",
        type='pdf',
        is_primary=True,
        render_status=DocumentVersion.RENDER_PROCESSING,
        has_pages=False,
    )
    
    # Create a mock page
    DocumentPage.objects.create(document_version=version, page_number=1, storage_key="page1.png")
    
    # Request rebuild-preview
    response = api_client.post(f'/api/v1/documents/{doc.id}/rebuild-preview/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@override_settings(PDF_PREVIEW_ENGINE='server_pages')
@patch('documents.views.fileserver_client.delete_file')
@patch('documents.services.generate_pdf_pages_task.delay')
def test_rebuild_preview_force_override_processing_status(mock_task_delay, mock_delete_file, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        status='processing',
        type='pdf',
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        original_storage_key="test_force.pdf",
        storage_key="test_force.pdf",
        type='pdf',
        is_primary=True,
        render_status=DocumentVersion.RENDER_PROCESSING,
        has_pages=False,
    )

    response = api_client.post(f'/api/v1/documents/{doc.id}/rebuild-preview/', {'force': True}, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@override_settings(PDF_PREVIEW_ENGINE='server_pages')
@patch('documents.views.fileserver_client.delete_file')
@patch('documents.services.generate_pdf_pages_task.delay')
def test_rebuild_preview_stale_processing_task_auto_recovers(mock_task_delay, mock_delete_file, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        status='processing',
        type='pdf',
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        original_storage_key="test_stale.pdf",
        storage_key="test_stale.pdf",
        type='pdf',
        is_primary=True,
        render_status=DocumentVersion.RENDER_PROCESSING,
        has_pages=False,
    )
    # Simulate crashed worker task from 20 minutes ago
    DocumentVersion.objects.filter(id=version.id).update(
        updated_at=timezone.now() - timedelta(minutes=20)
    )

    response = api_client.post(f'/api/v1/documents/{doc.id}/rebuild-preview/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@override_settings(PDF_PREVIEW_ENGINE='server_pages')
@patch('documents.views.fileserver_client.delete_file')
@patch('documents.services.generate_pdf_pages_task.delay')
def test_enqueue_render_task_stamps_updated_at_preventing_premature_stale_rebuild(mock_task_delay, mock_delete_file, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        status='ready',
        type='pdf',
    )
    old_time = timezone.now() - timedelta(hours=2)
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        original_storage_key="test_queue.pdf",
        storage_key="test_queue.pdf",
        type='pdf',
        is_primary=True,
        render_status=DocumentVersion.RENDER_NOT_GENERATED,
        has_pages=False,
    )
    DocumentVersion.objects.filter(id=version.id).update(updated_at=old_time)

    # Enqueue render task
    renderer = PDFRenderer()
    renderer.enqueue_render_task(version)

    version.refresh_from_db()
    assert version.render_status == DocumentVersion.RENDER_QUEUED
    assert version.updated_at > old_time

    # Immediate rebuild-preview without force must return 409 Conflict
    response = api_client.post(f'/api/v1/documents/{doc.id}/rebuild-preview/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}



@pytest.mark.django_db
@override_settings(PDF_PREVIEW_ENGINE='server_pages')
@patch('documents.views.fileserver_client.delete_file')
@patch('documents.services.generate_pdf_pages_task.delay')
def test_rebuild_preview_no_existing_pages(mock_task_delay, mock_delete_file, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        organization=user.organization,
        created_by=user,
        status='ready',
        type='pdf',
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        original_storage_key="test_rebuild.pdf",
        storage_key="test_rebuild.pdf",
        type='pdf',
        is_primary=True,
        render_status=DocumentVersion.RENDER_FAILED,
        has_pages=False,
    )
    
    # Make request
    response = api_client.post(f'/api/v1/documents/{doc.id}/rebuild-preview/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}



@pytest.mark.django_db
def test_get_document_preview_data_wrong_org(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    other_org = Organization.objects.create(name="Other Org")
    other_user = User.objects.create_user(
        username='other@example.com', organization=other_org
    )
    doc = Document.objects.create(
        organization=other_org,
        created_by=other_user,
        status='ready'
    )
    
    response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.services.fileserver_client.delete_file')
def test_soft_delete_document_success(mock_fs_delete, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # Setup
    doc = Document.objects.create(organization=user.organization, created_by=user)
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        original_storage_key="delete_me.pdf"
    )
    DocumentPage.objects.create(
        document_version=version, page_number=1, storage_key="delete_me_page_1.png"
    )

    # Action
    response = api_client.delete(f'/api/v1/documents/{doc.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_delete_document_permission_denied(api_client, user, user2):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # Setup: user2 creates a document
    doc_by_user2 = Document.objects.create(
        organization=user2.organization, created_by=user2
    )

    # Action: api_client (logged in as user) tries to delete it
    response = api_client.delete(f'/api/v1/documents/{doc_by_user2.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_soft_delete_document_in_subfolder_success(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    # Setup: Create a document inside a subfolder
    root_folder = Folder.objects.get_root_for_org(organization)
    subfolder = Folder.objects.create(
        organization=organization, created_by=user, name="Subfolder", parent=root_folder
    )
    doc = Document.objects.create(
        organization=organization, created_by=user, folder=subfolder
    )

    # Action: Attempt to delete the document by its ID
    response = api_client.delete(f'/api/v1/documents/{doc.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestDocumentVersionUploadViews:
    """Tests for the two-step document version upload process."""

    @pytest.fixture
    def document_with_version(self, document):
        """Fixture for a document that has one version."""
        initial_version = document.versions.get(is_primary=True)
        return document, initial_version

    @patch('documents.views.fileserver_client.get_file_info', return_value={'exists': True, 'size': 11})
    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('documents.views.fileserver_client.generate_upload_url')
    def test_upload_new_version_success(self, mock_fs_upload_url, mock_task_delay, mock_fs_get_file_info, api_client, document_with_version):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_upload_url.return_value = "/files/upload/some-token"
        doc, initial_version = document_with_version

        # Step 1: Request upload URL
        request_url = f'/api/v1/uploads/document/{doc.id}/versions/request/'
        request_response = api_client.post(request_url, {'file_name': 'v2.pdf', 'file_size': 11})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert request_response.status_code == 403
        assert request_response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_finalize_version_rejects_invalid_or_unauthorized_storage_key(self, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test finalizing a new version with an invalid, unauthorized, or traversing storage key returns HTTP 400.'
        api_client.force_authenticate(user=user)
        doc = Document.objects.create(organization=user.organization, created_by=user, name='test_ver_doc.pdf', status='ready')
        DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True)
        finalize_url = f'/api/v1/uploads/document/{doc.id}/versions/finalize/'
        org_id = user.organization.id
        invalid_keys = ['../run/secrets/app/secret_key', f'{org_id}/../secret.txt', f'{org_id}/%2e%2e/secret.txt', f'{org_id}/%252e%252e/secret.txt', 'other_org/ab/malicious.pdf', 'no_prefix_key.pdf']
        for key in invalid_keys:
            finalize_data = {'storage_key': key, 'file_size': 100, 'content_type': 'application/pdf'}
            response = api_client.post(finalize_url, finalize_data)
            assert response.status_code == 403
            assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_upload_version_for_other_user_doc_permission_denied(self, api_client, user2):

        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc_by_user2 = Document.objects.create(
            organization=user2.organization, created_by=user2, name="user2_doc.pdf", status='ready'
        )
        DocumentVersion.objects.create(document=doc_by_user2, version_number=1, is_primary=True)

        request_url = f'/api/v1/uploads/document/{doc_by_user2.id}/versions/request/'
        response = api_client.post(request_url, {'file_name': 'v2.pdf'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestDocumentViewSet:
    def test_retrieve_document_with_share_link_views(self, api_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(document=document, created_by=user)
        ViewSession.objects.create(share_link=link, viewer_email="viewer1@test.com")

        response = api_client.get(f'/api/v1/documents/{document.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_document_views_pagination(self, api_client, document, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Create 15 views for the share link
        for i in range(15):
            ViewSession.objects.create(share_link=share_link, viewer_email=f"viewer{i+1}@example.com")

        # 1. Fetch the first page
        response = api_client.get(f'/api/v1/documents/{document.id}/view-sessions/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Staff access is required.'}

    def test_document_views_forbidden_for_non_owner_dataroom_collaborator(
        self, api_client, document, dataroom, user, user2, admin_user
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.models import DataroomCollaborator, DataroomDocument

        # Add user2 as collaborator to dataroom containing user's document
        DataroomCollaborator.objects.create(dataroom=dataroom, user=user2)
        DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)

        # 1. As collaborator (user2): document details are accessible (200 OK)
        api_client.force_authenticate(user=user2)
        doc_resp = api_client.get(f'/api/v1/documents/{document.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert doc_resp.status_code == 403
        assert doc_resp.data == {'detail': 'Staff access is required.'}

    def test_update_document_star_status(self, api_client, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        assert document.is_starred is False

        # Star the document
        response = api_client.patch(f'/api/v1/documents/{document.id}/', {'is_starred': True})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_star_document_permission_denied(self, api_client, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc_by_user2 = Document.objects.create(
            name="User2's Document",
            organization=organization,
            created_by=user2,
            is_starred=False
        )

        # api_client (logged in as user) tries to star it
        response = api_client.patch(f'/api/v1/documents/{doc_by_user2.id}/', {'is_starred': True})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.copy_document')
    def test_copy_document_api_success(self, mock_copy_document, api_client, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Arrange
        from core.fields import generate_ulid
        new_doc_id = generate_ulid()
        new_doc_instance = Document(
            id=new_doc_id,
            name="Copy of doc.pdf",
            created_by=user,
            organization=user.organization
        )
        mock_copy_document.return_value = new_doc_instance

        # Act
        response = api_client.post(f'/api/v1/documents/{document.id}/copy/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_copy_document_api_permission_denied(self, api_client, user2, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        document.created_by = user2
        document.save()

        response = api_client.post(f'/api/v1/documents/{document.id}/copy/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.copy_document')
    def test_copy_document_api_quota_exceeded(self, mock_copy_document, api_client, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_copy_document.side_effect = QuotaExceededError("Quota exceeded")

        response = api_client.post(f'/api/v1/documents/{document.id}/copy/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.fileserver_client.copy_file')
    def test_copy_document_api_fileserver_error(self, mock_copy_file, api_client, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        document.file_size = 1024  # Add file size to pass initial check
        document.save()

        api_exception = APIException("File server error")
        api_exception.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        mock_copy_file.side_effect = api_exception

        response = api_client.post(f'/api/v1/documents/{document.id}/copy/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.copy_document')
    def test_copy_document_api_throttling(self, mock_copy_document, api_client, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test that the copy document API is throttled at 5 requests per minute.'
        from django.core.cache import cache
        from core.fields import generate_ulid
        cache.clear()
        response = api_client.post(f'/api/v1/documents/{document.id}/copy/')
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestMoveItemsView:
    """Tests for the MoveItemsView endpoint."""

    @pytest.fixture
    def setup_folders(self, user, organization):
        """Setup initial folder structure for move tests."""
        root = Folder.objects.get_root_for_org(organization)
        folder_a = Folder.objects.create(name="Folder A", created_by=user, organization=organization, parent=root)
        folder_b = Folder.objects.create(name="Folder B", created_by=user, organization=organization, parent=root)
        subfolder_a = Folder.objects.create(name="Subfolder A", created_by=user, organization=organization, parent=folder_a)
        doc_in_a = Document.objects.create(name="Doc in A.pdf", created_by=user, organization=organization, folder=folder_a)
        doc_in_root = Document.objects.create(name="Doc in Root.pdf", created_by=user, organization=organization, folder=root)
        return {
            'root': root,
            'folder_a': folder_a,
            'folder_b': folder_b,
            'subfolder_a': subfolder_a,
            'doc_in_a': doc_in_a,
            'doc_in_root': doc_in_root,
        }

    def test_move_items_to_another_folder(self, api_client, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        data = {
            'document_ids': [str(setup_folders['doc_in_root'].id)],
            'folder_ids': [str(setup_folders['folder_a'].id)],
            'destination_folder_id': str(setup_folders['folder_b'].id)
        }
        response = api_client.post('/api/v1/actions/move/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_items_to_root(self, api_client, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        data = {
            'document_ids': [str(setup_folders['doc_in_a'].id)],
            'folder_ids': [str(setup_folders['subfolder_a'].id)],
            'destination_folder_id': None  # None signifies root
        }
        response = api_client.post('/api/v1/actions/move/', data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_folder_into_itself_fails(self, api_client, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        data = {
            'folder_ids': [str(setup_folders['folder_a'].id)],
            'destination_folder_id': str(setup_folders['folder_a'].id)
        }
        response = api_client.post('/api/v1/actions/move/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_folder_into_descendant_fails(self, api_client, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        data = {
            'folder_ids': [str(setup_folders['folder_a'].id)],
            'destination_folder_id': str(setup_folders['subfolder_a'].id)
        }
        response = api_client.post('/api/v1/actions/move/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_items_permission_denied_for_destination(self, api_client, user2, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        other_user_folder = Folder.objects.create(name="User2 Folder", created_by=user2, organization=user2.organization, parent=setup_folders['root'])
        data = {
            'document_ids': [str(setup_folders['doc_in_root'].id)],
            'destination_folder_id': str(other_user_folder.id)
        }
        response = api_client.post('/api/v1/actions/move/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_items_permission_denied_for_source(self, api_client, user2, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        other_user_doc = Document.objects.create(name="User2 Doc.pdf", created_by=user2, organization=user2.organization, folder=setup_folders['root'])
        data = {
            'document_ids': [str(other_user_doc.id)],
            'destination_folder_id': str(setup_folders['folder_a'].id)
        }
        response = api_client.post('/api/v1/actions/move/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_items_with_name_conflict_is_renamed(self, api_client, user, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Create a document in Folder B with the same name as a document in Folder A
        Document.objects.create(name="Doc in A.pdf", created_by=user, organization=user.organization, folder=setup_folders['folder_b'])
        
        data = {
            'document_ids': [str(setup_folders['doc_in_a'].id)],
            'destination_folder_id': str(setup_folders['folder_b'].id)
        }
        response = api_client.post('/api/v1/actions/move/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_move_no_items_fails(self, api_client, setup_folders):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        data = {
            'document_ids': [],
            'folder_ids': [],
            'destination_folder_id': str(setup_folders['folder_a'].id)
        }
        response = api_client.post('/api/v1/actions/move/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestQuotaAndSizeTracking:
    @pytest.fixture(autouse=True)
    def setup(self, user):
        user.total_document_size = 0
        user.save()

    @patch('documents.views.fileserver_client.get_file_info')
    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('documents.services.convert_office_to_pdf_task.delay')
    @patch('documents.views.fileserver_client.generate_upload_url')
    def test_document_lifecycle_updates_user_size(self, mock_fs_upload_url, mock_convert_task, mock_pdf_task, mock_fs_get_file_info, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_upload_url.return_value = "/files/upload/token"
        assert user.total_document_size == 0

        # 1. Create a document (1MB)
        file_size_1 = 1 * 1024 * 1024
        mock_fs_get_file_info.side_effect = [
            {'exists': True, 'size': file_size_1},
            {'exists': True, 'size': 2 * 1024 * 1024},
        ]
        finalize_data = {
            'storage_key': f"{user.organization.id}/key1",
            'unique_name': 'doc1.pdf',
            'content_type': 'application/pdf',
        }
        response = api_client.post('/api/v1/uploads/document/finalize/', finalize_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.generate_upload_url')
    def test_upload_request_respects_quota(self, mock_fs_upload_url, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)
        mock_fs_upload_url.return_value = "/files/upload/token"
        user.custom_file_size_quota_mb = 1
        user.save()

        # This should fail (2MB > 1MB)
        request_data_fail = {'file_name': 'large.pdf', 'file_size': 2 * 1024 * 1024}
        response_fail = api_client.post('/api/v1/uploads/document/request/', request_data_fail)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_fail.status_code == 403
        assert response_fail.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.generate_upload_url')
    def test_upload_request_nonexistent_folder_path_returns_400(self, mock_fs_upload_url, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)
        mock_fs_upload_url.return_value = "/files/upload/token"

        request_data = {
            'file_name': 'doc.pdf',
            'file_size': 1024,
            'path': 'NonExistentFolder/doc.pdf'
        }
        response = api_client.post('/api/v1/uploads/document/request/', request_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

@pytest.mark.django_db
@patch('documents.views.fileserver_client.generate_preview_url')
def test_get_document_preview_data_client_pdf(mock_fs_preview_url, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    'Test getting preview data for a PDF when PDF.js engine is used.'
    mock_fs_preview_url.return_value = 'https://mock.fileserver/client_pdf.pdf'
    doc = Document.objects.create(organization=user.organization, created_by=user, name='test_client.pdf', status='ready', type='pdf', content_type='application/pdf', download_only=False)
    DocumentVersion.objects.create(document=doc, version_number=1, type='pdf', is_primary=True, original_storage_key='test_client.pdf', render_status='not_generated')
    with override_settings(PDF_PREVIEW_ENGINE='pdfjs'):
        response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/')
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.generate_preview_url')
def test_get_document_preview_data_video_stream_ttl(mock_fs_preview_url, api_client, user):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    'Test that video preview URLs are generated with extended TTL based on video length.'
    mock_fs_preview_url.return_value = 'https://mock.fileserver/files/preview/token123'
    doc = Document.objects.create(organization=user.organization, created_by=user, name='test_video.mp4', status='ready', type='video', content_type='video/mp4')
    version = DocumentVersion.objects.create(document=doc, version_number=1, type='video', is_primary=True, original_storage_key='test_video.mp4', storage_key='org_1/docs/video_hls', render_status='ready', length=18000)
    with override_settings(ENABLE_VIDEO_PREVIEW=True):
        response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/')
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


def test_document_status_endpoint(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        name="Status Test.pdf",
        organization=organization,
        created_by=user,
        status="processing",
        status_message="Downloading from cloud..."
    )

    response = api_client.get(f'/api/v1/documents/{doc.id}/status/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_promote_version_endpoint_success(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        name="Promote API Test.pdf",
        organization=organization,
        created_by=user,
        status="ready",
        file_size=100,
    )
    v1 = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        file_size=100,
        content_type="application/pdf",
        original_storage_key="v1.pdf",
        storage_key="v1.pdf",
        type="pdf",
    )
    v2 = DocumentVersion.objects.create(
        document=doc,
        version_number=2,
        is_primary=False,
        file_size=200,
        content_type="application/pdf",
        original_storage_key="v2.pdf",
        storage_key="v2.pdf",
        type="pdf",
    )

    response = api_client.post(
        f'/api/v1/documents/{doc.id}/promote_version/',
        {'version_id': str(v2.id)}
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_promote_version_endpoint_wrong_doc(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc1 = Document.objects.create(
        name="Doc1.pdf",
        organization=organization,
        created_by=user,
    )
    doc2 = Document.objects.create(
        name="Doc2.pdf",
        organization=organization,
        created_by=user,
    )
    v_other = DocumentVersion.objects.create(
        document=doc2,
        version_number=1,
        is_primary=True,
        file_size=100,
        content_type="application/pdf",
        original_storage_key="other.pdf",
        storage_key="other.pdf",
        type="pdf",
    )

    response = api_client.post(
        f'/api/v1/documents/{doc1.id}/promote_version/',
        {'version_id': str(v_other.id)}
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.generate_download_url')
@patch('documents.views.fileserver_client.generate_preview_url')
def test_preview_data_endpoint_with_version_id(mock_preview_url, mock_download_url, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    'Test retrieving preview data for a specific inactive version.'
    mock_download_url.return_value = 'https://mock.fileserver/v1.pdf'
    mock_preview_url.return_value = 'https://mock.fileserver/client_pdf.pdf'
    doc = Document.objects.create(name='Preview Version Test.pdf', organization=organization, created_by=user, status='ready', file_size=100)
    v1 = DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True, file_size=100, content_type='application/pdf', original_storage_key='v1.pdf', storage_key='v1.pdf', type='pdf')
    v2 = DocumentVersion.objects.create(document=doc, version_number=2, is_primary=False, file_size=200, content_type='application/pdf', original_storage_key='v2.pdf', storage_key='v2.pdf', type='pdf', render_error='Stale preview failed')
    with override_settings(PDF_PREVIEW_ENGINE='pdfjs'):
        response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/?version_id={v2.id}')
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_list_versions_endpoint_success(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        name="List Versions Test.pdf",
        organization=organization,
        created_by=user,
    )
    v1 = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        file_size=100,
        content_type="application/pdf",
        original_storage_key="v1.pdf",
        storage_key="v1.pdf",
        type="pdf",
    )
    v2 = DocumentVersion.objects.create(
        document=doc,
        version_number=2,
        is_primary=False,
        file_size=200,
        content_type="application/pdf",
        original_storage_key="v2.pdf",
        storage_key="v2.pdf",
        type="pdf",
    )

    response = api_client.get(f'/api/v1/documents/{doc.id}/versions/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
@patch('core.services.get_dynamic_setting')
def test_promote_version_endpoint_respects_quota(mock_get_setting, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    def get_setting_mock(key):
        if key == 'FILE_SIZE_QUOTA_MB':
            return 1
        elif key == 'MAX_PREVIEW_FILE_SIZE_MB':
            return 100
        elif key == 'MAX_VIDEO_PREVIEW_SIZE_MB':
            return 100
        return 0
    mock_get_setting.side_effect = get_setting_mock

    doc = Document.objects.create(
        name="Doc.pdf",
        organization=organization,
        created_by=user,
        status="ready",
        file_size=500 * 1024,
    )
    v1 = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        file_size=500 * 1024,
        content_type="application/pdf",
        original_storage_key="v1.pdf",
        storage_key="v1.pdf",
        type="pdf",
    )
    v2 = DocumentVersion.objects.create(
        document=doc,
        version_number=2,
        is_primary=False,
        file_size=1500 * 1024,
        content_type="application/pdf",
        original_storage_key="v2.pdf",
        storage_key="v2.pdf",
        type="pdf",
    )
    user.total_document_size = 500 * 1024
    user.save()

    response = api_client.post(
        f'/api/v1/documents/{doc.id}/promote_version/',
        {'version_id': str(v2.id)}
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('core.services.get_dynamic_setting')
def test_promote_version_endpoint_vault_document_bypasses_user_quota(mock_get_setting, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    def get_setting_mock(key):
        if key == 'FILE_SIZE_QUOTA_MB':
            return 1  # 1 MB quota limit
        elif key == 'MAX_PREVIEW_FILE_SIZE_MB':
            return 100
        elif key == 'MAX_VIDEO_PREVIEW_SIZE_MB':
            return 100
        return 0
    mock_get_setting.side_effect = get_setting_mock

    root_folder = Folder.objects.create(
        name="__root__",
        organization=organization,
        created_by=None,
        parent=None,
        folder_type=Folder.FOLDER_TYPE_ROOT,
    )
    vault_folder = Folder.objects.create(
        name="__datarooms__",
        organization=organization,
        created_by=None,
        parent=root_folder,
        folder_type=Folder.FOLDER_TYPE_VAULT,
    )
    room_folder = Folder.objects.create(
        name="Room_1",
        organization=organization,
        created_by=None,
        parent=vault_folder,
        folder_type=Folder.FOLDER_TYPE_VAULT,
    )

    doc = Document.objects.create(
        name="VaultDoc.pdf",
        organization=organization,
        created_by=user,
        folder=room_folder,
        status="ready",
        file_size=500 * 1024,
    )
    v1 = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        file_size=500 * 1024,
        content_type="application/pdf",
        original_storage_key="v1.pdf",
        storage_key="v1.pdf",
        type="pdf",
    )
    v2 = DocumentVersion.objects.create(
        document=doc,
        version_number=2,
        is_primary=False,
        file_size=2 * 1024 * 1024,  # 2 MB (> 1 MB user personal quota)
        content_type="application/pdf",
        original_storage_key="v2.pdf",
        storage_key="v2.pdf",
        type="pdf",
    )
    user.total_document_size = 1024 * 1024
    user.save()

    response = api_client.post(
        f'/api/v1/documents/{doc.id}/promote_version/',
        {'version_id': str(v2.id)}
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.generate_upload_url')
@patch('core.services.get_dynamic_setting')
def test_version_upload_request_vault_document_bypasses_user_quota(mock_get_setting, mock_gen_url, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    mock_get_setting.side_effect = lambda key: 1 if key == 'FILE_SIZE_QUOTA_MB' else 100
    mock_gen_url.return_value = "https://files.coneshare.com/upload/mock"

    root_folder = Folder.objects.create(name="__root__", organization=organization, created_by=None, parent=None, folder_type=Folder.FOLDER_TYPE_ROOT)
    vault_folder = Folder.objects.create(name="__datarooms__", organization=organization, created_by=None, parent=root_folder, folder_type=Folder.FOLDER_TYPE_VAULT)
    room_folder = Folder.objects.create(name="Room_1", organization=organization, created_by=None, parent=vault_folder, folder_type=Folder.FOLDER_TYPE_VAULT)

    doc = Document.objects.create(name="VaultDoc.pdf", organization=organization, created_by=user, folder=room_folder, status="ready", file_size=500 * 1024)
    user.total_document_size = 1024 * 1024  # 1MB limit reached
    user.save()

    response = api_client.post(
        f'/api/v1/uploads/document/{doc.id}/versions/request/',
        {'file_name': 'VaultDoc_v2.pdf', 'file_size': 2 * 1024 * 1024}
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.get_file_info')
@patch('documents.services._route_document_for_processing')
@patch('core.services.get_dynamic_setting')
def test_version_upload_finalize_vault_document_does_not_consume_user_quota(mock_get_setting, mock_route, mock_get_info, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    mock_get_setting.side_effect = lambda key: 1 if key == 'FILE_SIZE_QUOTA_MB' else 100
    mock_get_info.return_value = {'exists': True, 'size': 2 * 1024 * 1024}

    root_folder = Folder.objects.create(name="__root__", organization=organization, created_by=None, parent=None, folder_type=Folder.FOLDER_TYPE_ROOT)
    vault_folder = Folder.objects.create(name="__datarooms__", organization=organization, created_by=None, parent=root_folder, folder_type=Folder.FOLDER_TYPE_VAULT)
    room_folder = Folder.objects.create(name="Room_1", organization=organization, created_by=None, parent=vault_folder, folder_type=Folder.FOLDER_TYPE_VAULT)

    doc = Document.objects.create(name="VaultDoc.pdf", organization=organization, created_by=user, folder=room_folder, status="ready", file_size=500 * 1024)
    user.total_document_size = 1000
    user.save()

    storage_key = f"{organization.id}/vault_v2_new.pdf"
    response = api_client.post(
        f'/api/v1/uploads/document/{doc.id}/versions/finalize/',
        {
            'storage_key': storage_key,
            'content_type': 'application/pdf',
        }
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
@patch('documents.views.fileserver_client.get_file_info')
@patch('documents.services._route_document_for_processing')
@patch('core.services.get_dynamic_setting')
def test_version_upload_finalize_vault_document_quota_exceeded_returns_400(mock_get_setting, mock_route, mock_get_info, api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from datarooms.models import Dataroom, DataroomDocument

    mock_get_setting.side_effect = lambda key: 100
    # 2MB version exceeds 1MB Dataroom quota
    mock_get_info.return_value = {'exists': True, 'size': 2 * 1024 * 1024}

    room = Dataroom.objects.create(
        name="Small Room",
        organization=organization,
        created_by=user,
        storage_quota_mb=1,
        storage_version=2,
    )

    root_folder = Folder.objects.create(name="__root__", organization=organization, created_by=None, parent=None, folder_type=Folder.FOLDER_TYPE_ROOT)
    vault_folder = Folder.objects.create(name="__datarooms__", organization=organization, created_by=None, parent=root_folder, folder_type=Folder.FOLDER_TYPE_VAULT)
    room_folder = Folder.objects.create(name="Small_Room", organization=organization, created_by=None, parent=vault_folder, folder_type=Folder.FOLDER_TYPE_VAULT)

    doc = Document.objects.create(name="VaultDoc.pdf", organization=organization, created_by=user, folder=room_folder, status="ready", file_size=500 * 1024)
    DataroomDocument.objects.create(dataroom=room, document=doc, name="VaultDoc.pdf")

    storage_key = f"{organization.id}/vault_v2_oversize.pdf"
    response = api_client.post(
        f'/api/v1/uploads/document/{doc.id}/versions/finalize/',
        {
            'storage_key': storage_key,
            'content_type': 'application/pdf',
        }
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}



def test_preview_data_endpoint_document_uploading_state(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    doc = Document.objects.create(
        name="Test.pdf",
        organization=organization,
        created_by=user,
        status="uploading",
        file_size=100,
    )
    v1 = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        file_size=100,
        content_type="application/pdf",
        original_storage_key="v1.pdf",
        storage_key="v1.pdf",
        type="pdf",
    )
    # Even with a specific version_id, preview should be rejected since document is uploading
    response = api_client.get(f'/api/v1/documents/{doc.id}/preview-data/?version_id={v1.id}')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_soft_deleted_document_not_accessible_via_document_viewset(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get_root_for_org(organization)
    doc = Document.objects.create(
        name="DeletedDoc.pdf",
        organization=organization,
        created_by=user,
        folder=root_folder,
        status="ready",
        file_size=100,
        type="pdf",
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        file_size=100,
        content_type="application/pdf",
        original_storage_key="v1.pdf",
        storage_key="v1.pdf",
        type="pdf",
    )

    # Soft delete the document
    api_client.delete(f'/api/v1/documents/{doc.id}/')

    # 1. Retrieve -> 404
    res = api_client.get(f'/api/v1/documents/{doc.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_soft_deleted_folder_not_accessible_via_folder_viewset(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    root_folder = Folder.objects.get_root_for_org(organization)
    folder = Folder.objects.create(
        name="TrashedFolder",
        organization=organization,
        parent=root_folder,
        created_by=user,
    )

    # Soft delete the folder
    api_client.delete(f'/api/v1/folders/{folder.id}/')

    # 1. Retrieve -> 404
    res = api_client.get(f'/api/v1/folders/{folder.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_restore_folder_with_duplicate_trashed_document_names_succeeds(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    '\n    Test: Restoring a folder with active/trashed documents of the same name\n    resolves collisions without throwing a 500 / IntegrityError.\n    '
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    reports = Folder.objects.create(name='Reports', organization=organization, created_by=user, parent=root_folder)
    doc1 = Document.objects.create(name='Q1.pdf', organization=organization, created_by=user, folder=reports, status='ready')
    response = api_client.delete(f'/api/v1/documents/{doc1.id}/')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_restore_document_with_trashed_parent_folder_is_rejected(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    parent_folder = Folder.objects.create(name="ParentFolder", organization=organization, created_by=user, parent=root_folder)
    sub_folder = Folder.objects.create(name="SubFolder", organization=organization, created_by=user, parent=parent_folder)
    doc = Document.objects.create(name="DocInSub.pdf", organization=organization, created_by=user, folder=sub_folder, status="ready")

    # Soft delete parent folder (cascades to sub_folder and doc)
    api_client.delete(f'/api/v1/folders/{parent_folder.id}/')

    # Attempt to restore document alone -> rejected
    res = api_client.post(f'/api/v1/trash/{doc.id}/restore/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_trash_list_filters_to_root_level_deleted_items_only(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    parent_folder = Folder.objects.create(name="ParentFolder", organization=organization, created_by=user, parent=root_folder)
    sub_folder = Folder.objects.create(name="SubFolder", organization=organization, created_by=user, parent=parent_folder)
    doc = Document.objects.create(name="DocInSub.pdf", organization=organization, created_by=user, folder=sub_folder, status="ready")

    # Soft delete parent folder (cascades to sub_folder and doc)
    api_client.delete(f'/api/v1/folders/{parent_folder.id}/')

    # Fetch trash list
    res = api_client.get('/api/v1/trash/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_trash_list_pagination_metadata(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from django.utils import timezone
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)

    # Create 25 soft-deleted documents
    now = timezone.now()
    Document.objects.bulk_create([
        Document(
            name=f"DeletedDoc_{i}.pdf",
            organization=organization,
            created_by=user,
            folder=root_folder,
            status="ready",
            deleted_at=now,
            deleted_by=user,
        )
        for i in range(25)
    ])

    # Fetch default page 1
    res = api_client.get('/api/v1/trash/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_trash_restore_returns_rename_feedback(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    '\n    RED Test: Restoring a soft-deleted document that undergoes collision renaming\n    must return detailed rename feedback (was_renamed=True, name, original_name) in API response.\n    '
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    trashed_doc = Document.objects.create(name='File.pdf', organization=organization, created_by=user, folder=root_folder, status='ready')
    response = api_client.delete(f'/api/v1/documents/{trashed_doc.id}/')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_independently_trashed_file_remains_in_trash_when_parent_folder_trashed(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    import time
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    src_folder = Folder.objects.create(name="src", organization=organization, created_by=user, parent=root_folder)
    foo_doc = Document.objects.create(name="foo.c", organization=organization, created_by=user, folder=src_folder, status="ready")

    # 1. Soft delete foo.c first
    api_client.delete(f'/api/v1/documents/{foo_doc.id}/')
    time.sleep(0.02)  # Ensure distinct timestamps

    # 2. Soft delete folder src second
    api_client.delete(f'/api/v1/folders/{src_folder.id}/')

    # 3. GET /api/v1/trash/ should list BOTH src AND foo.c (2 items)
    res = api_client.get('/api/v1/trash/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_restore_document_relinks_to_newly_created_active_parent_folder(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    "\n    RED Test: If original parent folder 'images' was soft-deleted, but user manually created a new\n    active folder named 'images', restoring a document from trash should automatically re-link to the new\n    active 'images' folder instead of failing.\n    "
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    old_images_folder = Folder.objects.create(name='images', organization=organization, created_by=user, parent=root_folder)
    doc = Document.objects.create(name='photo.jpeg', organization=organization, created_by=user, folder=old_images_folder, status='ready')
    response = api_client.delete(f'/api/v1/folders/{old_images_folder.id}/')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_restore_document_does_not_relink_to_another_users_active_parent_folder(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    other_user = User.objects.create_user(username="other@example.com", email="other@example.com", password="password", organization=organization)
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)

    # 1. User A creates folder 'images' and document inside it
    old_images_folder = Folder.objects.create(name="images", organization=organization, created_by=user, parent=root_folder)
    doc = Document.objects.create(name="photo.jpeg", organization=organization, created_by=user, folder=old_images_folder, status="ready")

    # 2. Soft delete old_images_folder
    api_client.delete(f'/api/v1/folders/{old_images_folder.id}/')

    # 3. Other user (User B) creates an active folder named 'images'
    other_user_images_folder = Folder.objects.create(name="images", organization=organization, created_by=other_user, parent=root_folder)

    # 4. User A attempts to restore photo.jpeg -> should be rejected because User A has no active 'images' folder
    res = api_client.post(f'/api/v1/trash/{doc.id}/restore/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_rename_document_with_duplicate_name_fails(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)

    # 1. Create two documents in the same folder
    doc1 = Document.objects.create(name="foo.c", organization=organization, created_by=user, folder=root_folder, status="ready")
    doc2 = Document.objects.create(name="foo.txt", organization=organization, created_by=user, folder=root_folder, status="ready")

    # 2. Attempt to rename doc1 to "foo.txt"
    response = api_client.patch(f'/api/v1/documents/{doc1.id}/', {'name': 'foo.txt'}, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_create_subfolder_touches_parent_folder_mtime(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    parent_folder = Folder.objects.create(name="Parent", organization=organization, created_by=user, parent=root_folder)
    past_time = timezone.now() - timedelta(days=2)
    Folder.objects.filter(id=parent_folder.id).update(updated_at=past_time)
    parent_folder.refresh_from_db()
    assert parent_folder.updated_at == past_time

    res = api_client.post('/api/v1/folders/', {'name': 'New Child', 'parent': parent_folder.id}, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_rename_subfolder_touches_parent_folder_mtime(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    parent_folder = Folder.objects.create(name="Parent", organization=organization, created_by=user, parent=root_folder)
    child_folder = Folder.objects.create(name="Old Child", organization=organization, created_by=user, parent=parent_folder)
    past_time = timezone.now() - timedelta(days=2)
    Folder.objects.filter(id=parent_folder.id).update(updated_at=past_time)
    parent_folder.refresh_from_db()
    assert parent_folder.updated_at == past_time

    res = api_client.patch(f'/api/v1/folders/{child_folder.id}/', {'name': 'Renamed Child'}, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_rename_document_touches_parent_folder_mtime(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    parent_folder = Folder.objects.create(name="Parent", organization=organization, created_by=user, parent=root_folder)
    doc = Document.objects.create(name="doc.pdf", organization=organization, created_by=user, folder=parent_folder, status="ready")
    past_time = timezone.now() - timedelta(days=2)
    Folder.objects.filter(id=parent_folder.id).update(updated_at=past_time)
    parent_folder.refresh_from_db()
    assert parent_folder.updated_at == past_time

    res = api_client.patch(f'/api/v1/documents/{doc.id}/', {'name': 'renamed_doc.pdf'}, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_bulk_move_items_touches_source_and_destination_folders(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    source_folder = Folder.objects.create(name="Source", organization=organization, created_by=user, parent=root_folder)
    dest_folder = Folder.objects.create(name="Dest", organization=organization, created_by=user, parent=root_folder)
    doc = Document.objects.create(name="move_me.pdf", organization=organization, created_by=user, folder=source_folder, status="ready")

    past_time = timezone.now() - timedelta(days=2)
    Folder.objects.filter(id__in=[source_folder.id, dest_folder.id]).update(updated_at=past_time)
    source_folder.refresh_from_db()
    dest_folder.refresh_from_db()
    assert source_folder.updated_at == past_time
    assert dest_folder.updated_at == past_time

    res = api_client.post('/api/v1/actions/move/', {
        'document_ids': [doc.id],
        'folder_ids': [],
        'destination_folder_id': dest_folder.id
    }, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_ensure_folder_paths_touches_parent_folder_mtime(api_client, user, organization):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    api_client.force_authenticate(user=user)
    root_folder = Folder.objects.get_root_for_org(organization)
    parent_folder = Folder.objects.create(name="Doc Base", organization=organization, created_by=user, parent=root_folder)
    past_time = timezone.now() - timedelta(days=2)
    Folder.objects.filter(id=parent_folder.id).update(updated_at=past_time)
    parent_folder.refresh_from_db()
    assert parent_folder.updated_at == past_time

    res = api_client.post('/api/v1/folders/ensure-paths/', {
        'paths': ['SubFolder/DeepNested'],
        'parent_path': parent_folder.name,
    }, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert res.status_code == 403
    assert res.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestDocumentUploadConstraints:
    """Upload request and finalize endpoints file size and attribute constraints."""

    def test_upload_request_rejects_negative_and_zero_file_size(self, api_client, user):
        api_client.force_authenticate(user=user)
        # Negative file_size
        res_neg = api_client.post('/api/v1/uploads/document/request/', {
            'file_name': 'test.pdf',
            'file_size': -100,
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_neg.status_code == 403
        assert res_neg.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.get_file_info')
    def test_upload_finalize_verifies_storage_file_size_and_ignores_client_value(self, mock_get_info, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)

        # 1. Physical file not found or size <= 0
        mock_get_info.return_value = {'exists': False, 'size': 0}
        res_missing = api_client.post('/api/v1/uploads/document/finalize/', {
            'storage_key': f'{organization.id}/missing.pdf',
            'unique_name': 'missing.pdf',
            'content_type': 'application/pdf',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_missing.status_code == 403
        assert res_missing.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.get_file_info')
    def test_finalize_rejects_conflicting_extension_and_content_type(self, mock_get_info, api_client, user, organization):
        api_client.force_authenticate(user=user)
        mock_get_info.return_value = {'exists': True, 'size': 1024}

        res = api_client.post('/api/v1/uploads/document/finalize/', {
            'storage_key': f'{organization.id}/sample.html',
            'unique_name': 'sample.html',
            'content_type': 'text/markdown',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.get_file_info')
    def test_finalize_rejects_dangerous_storage_key_extension_with_safe_name(self, mock_get_info, api_client, user, organization):
        api_client.force_authenticate(user=user)
        mock_get_info.return_value = {'exists': True, 'size': 1024}

        res = api_client.post('/api/v1/uploads/document/finalize/', {
            'storage_key': f'{organization.id}/sample.html',
            'unique_name': 'safe.md',
            'content_type': 'text/x-markdown',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.get_file_info')
    def test_version_upload_request_and_finalize_rejects_negative_and_zero_file_size(self, mock_get_info, api_client, user, organization):
        api_client.force_authenticate(user=user)
        doc = Document.objects.create(
            name="VersionDoc.pdf",
            organization=organization,
            created_by=user,
            file_size=1024,
        )
        DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True)

        res_req = api_client.post(f'/api/v1/uploads/document/{doc.id}/versions/request/', {
            'file_name': 'v2.pdf',
            'file_size': -500,
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_req.status_code == 403
        assert res_req.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.get_file_info', return_value={'exists': True, 'size': 1024})
    def test_upload_finalize_rejects_already_claimed_storage_key(self, mock_get_info, api_client, user, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        claimed_key = f"{organization.id}/doc/claimed.pdf"
        Document.objects.create(
            name="Claimed.pdf",
            organization=organization,
            created_by=user,
            original_storage_key=claimed_key,
            storage_key=claimed_key,
        )

        api_client.force_authenticate(user=user2)
        res = api_client.post('/api/v1/uploads/document/finalize/', {
            'storage_key': claimed_key,
            'unique_name': 'duplicate.pdf',
            'content_type': 'application/pdf',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.views.fileserver_client.get_file_info', return_value={'exists': True, 'size': 1024})
    def test_version_upload_finalize_rejects_already_claimed_storage_key(self, mock_get_info, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        claimed_key = f"{organization.id}/doc/version_claimed.pdf"
        Document.objects.create(
            name="Doc1.pdf",
            organization=organization,
            created_by=user,
            original_storage_key=claimed_key,
            storage_key=claimed_key,
        )
        doc2 = Document.objects.create(
            name="Doc2.pdf",
            organization=organization,
            created_by=user,
        )
        DocumentVersion.objects.create(document=doc2, version_number=1, is_primary=True)

        api_client.force_authenticate(user=user)
        res = api_client.post(f'/api/v1/uploads/document/{doc2.id}/versions/finalize/', {
            'storage_key': claimed_key,
            'content_type': 'application/pdf',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_patch_document_ignores_read_only_fields_and_preserves_folder(self, api_client, user, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        api_client.force_authenticate(user=user)
        root = Folder.objects.get_root_for_org(organization)
        user2_folder = Folder.objects.create(
            name="User2 Folder", organization=organization, created_by=user2, parent=root
        )
        vault_folder = Folder.objects.create(
            name="Vault Room", organization=organization, created_by=None, parent=root, folder_type=Folder.FOLDER_TYPE_VAULT
        )
        doc = Document.objects.create(
            name="TargetDoc.pdf",
            organization=organization,
            created_by=user,
            file_size=2048,
            storage_key="orig/target.pdf",
            original_storage_key="orig/target.pdf",
            status="ready",
        )

        # 1. System attributes must be ignored on PATCH
        res_patch = api_client.patch(f'/api/v1/documents/{doc.id}/', {
            'file_size': 9999999,
            'storage_key': 'other/target.pdf',
            'status': 'processing',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_patch.status_code == 403
        assert res_patch.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestFolderHierarchyBoundary:
    """Tests for folder hierarchy cycle prevention and parent validation."""

    def test_folder_cannot_set_parent_to_self(self, api_client, user, organization):
        from documents.models import Folder
        root = Folder.objects.get_root_for_org(organization)
        f1 = Folder.objects.create(name="Folder1", created_by=user, organization=organization, parent=root)

        api_client.force_authenticate(user=user)
        resp = api_client.patch(f'/api/v1/folders/{f1.id}/', {'parent': str(f1.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_folder_cannot_set_parent_to_descendant(self, api_client, user, organization):
        from documents.models import Folder
        root = Folder.objects.get_root_for_org(organization)
        f1 = Folder.objects.create(name="Folder1", created_by=user, organization=organization, parent=root)
        f2 = Folder.objects.create(name="Folder2", created_by=user, organization=organization, parent=f1)
        f3 = Folder.objects.create(name="Folder3", created_by=user, organization=organization, parent=f2)

        api_client.force_authenticate(user=user)
        resp = api_client.patch(f'/api/v1/folders/{f1.id}/', {'parent': str(f3.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}





