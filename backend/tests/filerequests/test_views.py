import pytest
from unittest.mock import patch
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from core.models import Organization
from documents.models import Document, Folder
from filerequests.models import FileRequest, SecurityThreatEvent, UploadedFile

pytestmark = pytest.mark.django_db


class TestFileRequestViewSet:
    def test_create_file_request_success(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        root_folder = Folder.objects.get_root_for_org(organization)
        data = {
            "name": "Q1 Reports Upload",
            "folder": str(root_folder.id),
        }
        response = api_client.post('/api/v1/file-requests/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_create_file_request_with_custom_fields(self, api_client, user, organization):
        root_folder = Folder.objects.get_root_for_org(organization)
        data = {
            "name": "Case Intake",
            "folder": str(root_folder.id),
            "custom_fields": [
                {
                    "id": "case_number",
                    "label": "Case Number",
                    "type": "text",
                    "required": True,
                    "placeholder": "CASE-2026-001",
                },
                {
                    "id": "document_type",
                    "label": "Document Type",
                    "type": "select",
                    "required": True,
                    "options": ["Invoice", "Contract"],
                },
            ],
        }

        response = api_client.post('/api/v1/file-requests/', data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_create_file_request_rejects_invalid_custom_field_schema(self, api_client, user, organization):
        root_folder = Folder.objects.get_root_for_org(organization)
        data = {
            "name": "Bad Intake",
            "folder": str(root_folder.id),
            "custom_fields": [
                {
                    "id": "document_type",
                    "label": "Document Type",
                    "type": "select",
                    "required": True,
                    "options": [],
                },
            ],
        }

        response = api_client.post('/api/v1/file-requests/', data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_create_file_request_for_other_user_folder_fails(self, api_client, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        other_user_folder = Folder.objects.create(name="User2 Folder", created_by=user2, organization=organization)
        data = {
            "name": "Illegal Upload",
            "folder": str(other_user_folder.id),
        }
        response = api_client.post('/api/v1/file-requests/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_file_requests_is_scoped_to_user_and_ordered(self, api_client, user, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        root_folder = Folder.objects.get_root_for_org(organization)
        # These are created sequentially, so request2 is newer
        FileRequest.objects.create(name="My First Request", folder=root_folder, created_by=user)
        FileRequest.objects.create(name="My Second Request", folder=root_folder, created_by=user)
        FileRequest.objects.create(name="Other User Request", folder=root_folder, created_by=user2)

        response = api_client.get('/api/v1/file-requests/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_file_request(self, api_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        new_name = "Updated Name"
        expires_at = timezone.now() + timedelta(days=7)
        data = {
            "name": new_name,
            "expires_at": expires_at.isoformat(),
        }
        response = api_client.patch(f'/api/v1/file-requests/{file_request.id}/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_delete_file_request(self, api_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        response = api_client.delete(f'/api/v1/file-requests/{file_request.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_create_file_request_for_other_organization_folder_fails(self, api_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        other_org = Organization.objects.create(name="Other Org")
        other_org_root_folder = Folder.objects.get_root_for_org(other_org)

        data = {
            "name": "Cross-Org Upload",
            "folder": str(other_org_root_folder.id),
        }
        response = api_client.post('/api/v1/file-requests/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


class TestPublicFileRequestViews:
    @pytest.fixture(autouse=True)
    def mock_fileserver_get_info(self):
        with patch('filerequests.views.fileserver_client.get_file_info') as mock_info:
            mock_info.return_value = {'exists': True, 'size': 54321}
            yield mock_info

    def test_get_public_details_success(self, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.name = "Public Name"
        file_request.save()
        url = f'/api/v1/public/file-requests/{file_request.slug}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_get_public_details_includes_custom_fields(self, public_client, file_request):
        file_request.custom_fields = [
            {
                "id": "case_number",
                "label": "Case Number",
                "type": "text",
                "required": True,
            }
        ]
        file_request.save(update_fields=['custom_fields'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_get_public_details_inactive(self, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.is_active = False
        file_request.save()
        url = f'/api/v1/public/file-requests/{file_request.slug}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_get_public_details_expired(self, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.expires_at = timezone.now() - timedelta(days=1)
        file_request.save()
        url = f'/api/v1/public/file-requests/{file_request.slug}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_get_public_details_folder_in_trash(self, public_client, file_request):
        file_request.folder.deleted_at = timezone.now()
        file_request.folder.save(update_fields=['deleted_at'])
        url = f'/api/v1/public/file-requests/{file_request.slug}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_request_upload_url_folder_in_trash(self, public_client, file_request):
        file_request.folder.deleted_at = timezone.now()
        file_request.folder.save(update_fields=['deleted_at'])
        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'test.pdf', 'file_size': 12345}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_finalize_upload_folder_in_trash(self, public_client, file_request):
        file_request.folder.deleted_at = timezone.now()
        file_request.folder.save(update_fields=['deleted_at'])
        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': 'test/key',
            'unique_name': 'test.pdf',
            'file_size': 100,
            'content_type': 'application/pdf',
            'uploader_name': 'Test User',
            'uploader_email': 'test@example.com',
        }
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.fileserver_client.generate_upload_url')
    def test_request_upload_url_success(self, mock_generate_url, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_generate_url.return_value = "http://fileserver/upload/token"
        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'test.pdf', 'file_size': 12345}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.fileserver_client.generate_upload_url')
    def test_request_upload_url_with_string_file_size(self, mock_generate_url, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_generate_url.return_value = "http://fileserver/upload/token"
        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'test.pdf', 'file_size': '12345'}  # file_size as string
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}
        
    def test_request_upload_url_exceeds_size_limit(self, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.max_file_size = 1000
        file_request.save()

        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'large-file.pdf', 'file_size': 1001}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_request_upload_url_disallowed_file_type(self, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.allowed_file_types = ['pdf', '.docx']
        file_request.save(update_fields=['allowed_file_types'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'archive.zip', 'file_size': 123}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.fileserver_client.generate_upload_url')
    def test_request_upload_url_allowed_file_type_normalized(self, mock_generate_url, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.allowed_file_types = ['pdf', '.docx']
        file_request.save(update_fields=['allowed_file_types'])
        mock_generate_url.return_value = "http://fileserver/upload/token"

        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'Quarterly.PDF', 'file_size': 12345}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.fileserver_client.generate_upload_url')
    def test_request_upload_url_allows_multi_part_extension(self, mock_generate_url, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.allowed_file_types = ['.tar.gz']
        file_request.save(update_fields=['allowed_file_types'])
        mock_generate_url.return_value = "http://fileserver/upload/token"

        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'backup.TAR.GZ', 'file_size': 4096}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.check_user_quota_on_upload')
    def test_request_upload_url_exceeds_user_quota(self, mock_check_quota, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from documents.services import QuotaExceededError
        mock_check_quota.side_effect = QuotaExceededError("Quota exceeded")
        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        data = {'file_name': 'test.pdf', 'file_size': 12345}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('filerequests.views.scan_storage_key_or_raise')
    def test_finalize_upload_success_and_creates_document(
        self,
        _mock_scan,
        _mock_on_commit,
        mock_dispatch_automation,
        mock_task_delay,
        public_client,
        file_request,
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.pdf",
            'unique_name': 'final-doc.pdf',

            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
        }
        
        assert Document.objects.count() == 0
        assert UploadedFile.objects.count() == 0
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.scan_storage_key_or_raise')
    def test_finalize_upload_rejects_invalid_or_unauthorized_storage_key(self, _mock_scan, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Finalizing a file request upload with an invalid, unauthorized, or traversing storage key returns HTTP 400.'
        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        org_id = file_request.created_by.organization.id
        invalid_keys = ['../run/secrets/app/secret_key', f'{org_id}/../secret.txt', f'{org_id}/%2e%2e/secret.txt', f'{org_id}/%252e%252e/secret.txt', 'other_org/ab/external.pdf', 'no_prefix_key.pdf']
        for key in invalid_keys:
            data = {'storage_key': key, 'unique_name': 'test.pdf', 'file_size': 1234, 'content_type': 'application/pdf', 'uploader_name': 'External User', 'uploader_email': 'user@example.com'}
            response = public_client.post(url, data)
            assert response.status_code == 403
            assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('filerequests.views.scan_storage_key_or_raise')
    def test_finalize_upload_persists_custom_field_values(

        self,
        _mock_scan,
        _mock_on_commit,
        _mock_dispatch_automation,
        _mock_task_delay,
        api_client,
        public_client,
        file_request,
    ):
        file_request.custom_fields = [
            {"id": "case_number", "label": "Case Number", "type": "text", "required": True},
            {"id": "document_type", "label": "Document Type", "type": "select", "required": True, "options": ["Contract", "Invoice"]},
            {"id": "due_date", "label": "Due Date", "type": "date", "required": False},
        ]
        file_request.save(update_fields=['custom_fields'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.pdf",
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
            'custom_field_values': {
                'case_number': ' CASE-2026-001 ',
                'document_type': 'Contract',
                'due_date': '2026-05-28',
            },
        }

        response = public_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_finalize_upload_rejects_missing_required_custom_field(self, public_client, file_request):
        file_request.custom_fields = [
            {"id": "case_number", "label": "Case Number", "type": "text", "required": True},
        ]
        file_request.save(update_fields=['custom_fields'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.pdf",
            'unique_name': 'final-doc.pdf',

            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
            'custom_field_values': {},
        }

        response = public_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_finalize_upload_rejects_required_checkbox_when_false(self, public_client, file_request):
        file_request.custom_fields = [
            {"id": "confirm_accuracy", "label": "Confirm Accuracy", "type": "checkbox", "required": True},
        ]
        file_request.save(update_fields=['custom_fields'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.pdf",
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
            'custom_field_values': {'confirm_accuracy': False},
        }

        response = public_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_finalize_upload_rejects_boolean_for_number_field(self, public_client, file_request):
        file_request.custom_fields = [
            {"id": "invoice_total", "label": "Invoice Total", "type": "number", "required": True},
        ]
        file_request.save(update_fields=['custom_fields'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.pdf",
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
            'custom_field_values': {'invoice_total': True},
        }

        response = public_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @pytest.mark.parametrize('non_finite_value', ['NaN', 'Infinity', '-Infinity'])
    def test_finalize_upload_rejects_non_finite_number_field(self, public_client, file_request, non_finite_value):
        file_request.custom_fields = [
            {"id": "invoice_total", "label": "Invoice Total", "type": "number", "required": True},
        ]
        file_request.save(update_fields=['custom_fields'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.pdf",
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
            'custom_field_values': {'invoice_total': non_finite_value},
        }

        response = public_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('filerequests.views.scan_storage_key_or_raise')
    def test_finalize_upload_allows_optional_checkbox_when_false(
        self,
        _mock_scan,
        _mock_on_commit,
        _mock_dispatch_automation,
        _mock_task_delay,
        public_client,
        file_request,
    ):
        file_request.custom_fields = [
            {"id": "subscribe_updates", "label": "Subscribe Updates", "type": "checkbox", "required": False},
        ]
        file_request.save(update_fields=['custom_fields'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.pdf",
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
            'custom_field_values': {'subscribe_updates': False},
        }

        response = public_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_finalize_upload_disallowed_file_type(self, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.allowed_file_types = ['.pdf']
        file_request.save(update_fields=['allowed_file_types'])
        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/some-key.exe",
            'unique_name': 'payload.exe',

            'file_size': 54321,
            'content_type': 'application/octet-stream',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
        }

        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('filerequests.views.scan_storage_key_or_raise')
    def test_finalize_upload_allows_multi_part_extension(
        self,
        _mock_scan,
        _mock_on_commit,
        mock_dispatch_automation,
        mock_task_delay,
        public_client,
        file_request,
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        file_request.allowed_file_types = ['tar.gz']
        file_request.save(update_fields=['allowed_file_types'])
        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        data = {
            'storage_key': f"{file_request.created_by.organization.id}/archive.tar.gz",
            'unique_name': 'archive.tar.gz',
            'file_size': 54321,
            'content_type': 'application/gzip',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
        }

        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.scan_storage_key_or_raise')
    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.fileserver_client.delete_file')
    def test_finalize_upload_rejects_malicious_file(
        self,
        mock_delete_file,
        mock_dispatch_automation,
        _mock_task_delay,
        mock_scan,
        public_client,
        file_request,
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from documents.malware_scan import MalwareDetectedError
        mock_scan.side_effect = MalwareDetectedError(
            "Upload blocked: security scan detected a potentially malicious file."
        )

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        storage_key = f"{file_request.created_by.organization.id}/malicious-key.pdf"
        data = {
            'storage_key': storage_key,
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
        }

        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.scan_storage_key_or_raise')
    @patch('documents.services.generate_pdf_pages_task.delay')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.fileserver_client.delete_file')
    def test_finalize_upload_malicious_file_cleanup_failure_is_recorded(
        self,
        mock_delete_file,
        mock_dispatch_automation,
        _mock_task_delay,
        mock_scan,
        public_client,
        file_request,
    ):
        from documents.malware_scan import MalwareDetectedError
        mock_scan.side_effect = MalwareDetectedError(
            "Upload blocked: security scan detected a potentially malicious file."
        )
        mock_delete_file.side_effect = Exception('delete failed')

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        storage_key = f"{file_request.created_by.organization.id}/malicious-key-2.pdf"
        data = {
            'storage_key': storage_key,
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
        }

        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.scan_storage_key_or_raise')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.fileserver_client.delete_file')
    def test_finalize_upload_scanner_unavailable_dispatches_security_event(
        self,
        mock_delete_file,
        mock_dispatch_automation,
        mock_scan,
        public_client,
        file_request,
    ):
        from documents.malware_scan import MalwareScannerUnavailableError
        mock_scan.side_effect = MalwareScannerUnavailableError(
            "Upload could not be verified by security scanner. Please try again later."
        )

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        storage_key = f"{file_request.created_by.organization.id}/scanner-down-key.pdf"
        data = {
            'storage_key': storage_key,
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
        }

        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.scan_storage_key_or_raise')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.fileserver_client.delete_file')
    def test_finalize_upload_scanner_unavailable_cleanup_failure_is_recorded(
        self,
        mock_delete_file,
        mock_dispatch_automation,
        mock_scan,
        public_client,
        file_request,
    ):
        from documents.malware_scan import MalwareScannerUnavailableError
        mock_scan.side_effect = MalwareScannerUnavailableError(
            "Upload could not be verified by security scanner. Please try again later."
        )
        mock_delete_file.side_effect = Exception('delete failed')

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        storage_key = f"{file_request.created_by.organization.id}/scanner-down-key-2.pdf"
        data = {
            'storage_key': storage_key,
            'unique_name': 'final-doc.pdf',
            'file_size': 54321,
            'content_type': 'application/pdf',
            'uploader_name': 'John Doe',
            'uploader_email': 'john.doe@example.com',
        }

        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestFileRequestUploadConstraints:
    """FileRequest upload request and finalize file size validation tests."""

    def test_request_upload_rejects_negative_and_zero_file_size(self, public_client, file_request):
        url = f'/api/v1/public/file-requests/{file_request.slug}/request-upload/'
        # Negative
        res_neg = public_client.post(url, {
            'file_name': 'test.pdf',
            'file_size': -100,
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_neg.status_code == 403
        assert res_neg.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.scan_storage_key_or_raise')
    @patch('filerequests.views.fileserver_client.get_file_info')
    def test_finalize_upload_verifies_storage_file_size_and_ignores_client_value(self, mock_get_info, _mock_scan, public_client, file_request):
        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        storage_key = f"{file_request.created_by.organization.id}/test-key.pdf"

        # Missing or zero size on storage server
        mock_get_info.return_value = {'exists': False, 'size': 0}
        res_missing = public_client.post(url, {
            'storage_key': storage_key,
            'unique_name': 'test.pdf',
            'content_type': 'application/pdf',
            'uploader_name': 'Alice',
            'uploader_email': 'alice@example.com',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_missing.status_code == 403
        assert res_missing.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.fileserver_client.get_file_info')
    @patch('filerequests.views.scan_storage_key_or_raise')
    def test_finalize_upload_enforces_max_file_size_and_owner_quota(self, _mock_scan, mock_get_info, public_client, file_request):
        file_request.max_file_size = 1000  # 1000 bytes max
        file_request.save(update_fields=['max_file_size'])

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        storage_key = f"{file_request.created_by.organization.id}/exceed-key.pdf"

        # Finalize when physical file size > max_file_size
        mock_get_info.return_value = {'exists': True, 'size': 5000}
        res_exceed = public_client.post(url, {
            'storage_key': storage_key,
            'unique_name': 'test.pdf',
            'file_size': 500,  # client-provided size is ignored; server uses physical file size
            'content_type': 'application/pdf',
            'uploader_name': 'Alice',
            'uploader_email': 'alice@example.com',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_exceed.status_code == 403
        assert res_exceed.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.scan_storage_key_or_raise')
    def test_finalize_upload_rejects_already_claimed_storage_key(self, _mock_scan, public_client, file_request):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        org_id = file_request.created_by.organization.id
        claimed_key = f"{org_id}/existing/document.pdf"

        Document.objects.create(
            name="Existing.pdf",
            organization=file_request.created_by.organization,
            created_by=file_request.created_by,
            original_storage_key=claimed_key,
            storage_key=claimed_key,
        )

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        response = public_client.post(url, {
            'storage_key': claimed_key,
            'unique_name': 'submitted.pdf',
            'content_type': 'application/pdf',
            'uploader_name': 'External User',
            'uploader_email': 'user@example.com',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('filerequests.views.fileserver_client.get_file_info', return_value={'exists': True, 'size': 1024})
    @patch('filerequests.views.scan_storage_key_or_raise')
    @patch('filerequests.views.dispatch_automation_event_task.delay')
    @patch('filerequests.views.safe_delete_storage_file', return_value=False)
    def test_finalize_upload_skipped_deletion_recorded_as_failed(
        self,
        mock_safe_delete,
        mock_dispatch_automation,
        mock_scan,
        mock_get_info,
        public_client,
        file_request,
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from documents.malware_scan import MalwareDetectedError
        mock_scan.side_effect = MalwareDetectedError("Threat detected.")

        url = f'/api/v1/public/file-requests/{file_request.slug}/finalize-upload/'
        storage_key = f"{file_request.created_by.organization.id}/threat-key.pdf"

        response = public_client.post(url, {
            'storage_key': storage_key,
            'unique_name': 'doc.pdf',
            'content_type': 'application/pdf',
            'uploader_name': 'External User',
            'uploader_email': 'user@example.com',
        }, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}




