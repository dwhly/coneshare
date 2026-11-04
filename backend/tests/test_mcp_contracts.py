from unittest.mock import patch
import pytest
from django.urls import resolve, Resolver404
from documents.views import DocumentViewSet, DocumentUploadRequestView, DocumentUploadFinalizeView
from datarooms.views import DataroomViewSet
from sharelinks.views import ShareLinkViewSet
from analytics.views import AllViewSessionsView, ViewSessionDetailView
from core.admin_views import AdminUserViewSet, AdminLoginActivityViewSet


@pytest.mark.django_db
class TestMCPURLContracts:
    """
    Contract tests asserting that every endpoint invoked by the MCP server
    cleanly resolves to the expected DRF view/action in Django URLconf.
    """

    def test_legacy_analytics_document_url_does_not_exist(self):
        """The route /analytics/documents/{id}/ called by older MCP client does not exist."""
        with pytest.raises(Resolver404):
            resolve("/api/v1/analytics/documents/01ARZ3NDEKTSV4RRFFQ69G5FAV/")

    def test_document_stats_url_resolves_to_document_viewset_stats(self):
        """Document engagement stats live on /documents/{id}/stats/."""
        match = resolve("/api/v1/documents/01ARZ3NDEKTSV4RRFFQ69G5FAV/stats/")
        assert match.func.cls == DocumentViewSet
        assert match.func.actions.get('get') == 'stats'

    def test_dataroom_remove_content_url_resolves(self):
        match = resolve("/api/v1/datarooms/01ARZ3NDEKTSV4RRFFQ69G5FAV/remove-content/")
        assert match.func.cls == DataroomViewSet
        assert match.func.actions.get('post') == 'remove_content'

    def test_document_upload_urls_resolve(self):
        match_req = resolve("/api/v1/uploads/document/request/")
        assert match_req.func.view_class == DocumentUploadRequestView

        match_fin = resolve("/api/v1/uploads/document/finalize/")
        assert match_fin.func.view_class == DocumentUploadFinalizeView

    def test_all_mcp_client_endpoints_resolve(self):
        """
        Verify the complete inventory of paths called by ConeshareClient
        against Django URLconf.
        """
        sample_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        expected_endpoints = [
            # Documents & Folders
            ("/api/v1/documents/", DocumentViewSet),
            (f"/api/v1/documents/{sample_id}/", DocumentViewSet),
            (f"/api/v1/documents/{sample_id}/stats/", DocumentViewSet),
            ("/api/v1/folders/", None),
            (f"/api/v1/folders/{sample_id}/", None),
            ("/api/v1/actions/move/", None),
            ("/api/v1/uploads/document/request/", DocumentUploadRequestView),
            ("/api/v1/uploads/document/finalize/", DocumentUploadFinalizeView),
            # Datarooms
            ("/api/v1/datarooms/", DataroomViewSet),
            (f"/api/v1/datarooms/{sample_id}/", DataroomViewSet),
            (f"/api/v1/datarooms/{sample_id}/add-content/", DataroomViewSet),
            (f"/api/v1/datarooms/{sample_id}/remove-content/", DataroomViewSet),
            # Share Links
            ("/api/v1/share-links/", ShareLinkViewSet),
            (f"/api/v1/share-links/{sample_id}/", ShareLinkViewSet),
            # Analytics
            ("/api/v1/analytics/view-sessions/", AllViewSessionsView),
            (f"/api/v1/analytics/view-sessions/{sample_id}/", ViewSessionDetailView),
            # Admin
            ("/api/v1/admin/users/", AdminUserViewSet),
            (f"/api/v1/admin/users/{sample_id}/", AdminUserViewSet),
            ("/api/v1/admin/login-activities/", AdminLoginActivityViewSet),
        ]

        for path, expected_cls in expected_endpoints:
            match = resolve(path)
            if expected_cls is not None:
                view_cls = getattr(match.func, 'cls', getattr(match.func, 'view_class', None))
                assert view_cls == expected_cls, f"Expected {expected_cls} for {path}, got {view_cls}"


@pytest.mark.django_db
class TestMCPIntegrationLiveContracts:
    """
    Live integration contract tests asserting that MCP client request payloads correctly
    execute against DRF views with real API Key authentication and database persistence.
    These run automatically on GitHub CI during backend testing.
    """

    @pytest.fixture
    def mcp_api_client(self, user):
        from rest_framework.test import APIClient
        from core.models import APIKey
        from core.authentication import generate_raw_api_key

        client = APIClient()
        raw_key, prefix, hashed = generate_raw_api_key()
        APIKey.objects.create(user=user, name="MCP CI Key", prefix=prefix, hashed_key=hashed, tier="full_access")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_key}")
        return client

    def test_dataroom_remove_content_with_dataroom_document_ids_returns_204(self, mcp_api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from rest_framework import status
        from datarooms.models import DataroomDocument

        DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        assert DataroomDocument.objects.filter(dataroom=dataroom).count() == 1

        url = f"/api/v1/datarooms/{dataroom.id}/remove-content/"
        res = mcp_api_client.post(url, {"dataroom_document_ids": [str(document.id)]}, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dataroom_remove_content_with_wrong_keys_returns_clean_400(self, mcp_api_client, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from rest_framework import status
        from datarooms.models import DataroomDocument

        DataroomDocument.objects.create(dataroom=dataroom, document=document, name=document.name)
        url = f"/api/v1/datarooms/{dataroom.id}/remove-content/"
        res = mcp_api_client.post(url, {"document_ids": [str(document.id)]}, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_document_stats_endpoint_returns_200(self, mcp_api_client, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from rest_framework import status

        url = f"/api/v1/documents/{document.id}/stats/"
        res = mcp_api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Staff access is required.'}

    @patch('documents.views.fileserver_client.generate_upload_url', return_value='http://fileserver/upload')
    def test_document_upload_request_with_normalized_folder_path(self, mock_gen_url, mcp_api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from rest_framework import status
        from documents.models import Folder

        root_folder = Folder.objects.filter(organization=organization, name="__root__").first()
        Folder.objects.create(name="finance", organization=organization, created_by=user, parent=root_folder)

        url = "/api/v1/uploads/document/request/"
        payload = {
            "file_name": "quarterly_report.pdf",
            "file_size": 10240,
            "path": "finance/quarterly_report.pdf",
        }
        res = mcp_api_client.post(url, payload, format="json")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

