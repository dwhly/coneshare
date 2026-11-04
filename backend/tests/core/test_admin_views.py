import csv
import io
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from core.models import AppConfiguration, Organization, User
from documents.models import Folder
from filerequests.models import FileRequest
from filerequests.models import SecurityThreatEvent


@pytest.mark.django_db
class TestAdminUserViewSetProtection:
    """
    Tests to ensure the last active admin of an organization cannot be removed.
    """

    def test_update_cannot_remove_last_admin(self, admin_api_client, admin_user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        organization = admin_user.organization

        # At this point, admin_user is the only active admin.
        # Try to demote self.
        url = f'/api/v1/admin/users/{admin_user.id}/'
        response_demote = admin_api_client.patch(url, {'role': 'user'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_demote.status_code == 403
        assert response_demote.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_cannot_demote_self_even_if_not_last(self, admin_api_client, admin_user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        organization = admin_user.organization
        # Create a second admin
        User.objects.create_user(
            username='otheradmin@example.com', email='otheradmin@example.com', organization=organization, role='admin'
        )

        # The logged-in admin (admin_user) tries to demote themselves.
        url = f'/api/v1/admin/users/{admin_user.id}/'
        response = admin_api_client.patch(url, {'role': 'user'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_demote_another_admin_if_not_last(self, admin_api_client, admin_user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        organization = admin_user.organization
        # Create a second admin to be the target of the demotion.
        other_admin = User.objects.create_user(
            username='otheradmin@example.com', email='otheradmin@example.com', organization=organization, role='admin'
        )

        # The logged-in admin (admin_user) tries to demote other_admin.
        # This should succeed because admin_user will remain as an active admin.
        url = f'/api/v1/admin/users/{other_admin.id}/'
        response = admin_api_client.patch(url, {'role': 'user'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_delete_another_admin_if_not_last(self, admin_api_client, admin_user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        organization = admin_user.organization
        # Create a second admin to be the target of deletion.
        target_admin = User.objects.create_user(
            username='target@example.com', email='target@example.com', organization=organization, role='admin'
        )

        # At this point, there are two active admins: admin_user (the actor, authenticated
        # via admin_api_client) and target_admin. The deletion should be allowed.
        url = f'/api/v1/admin/users/{target_admin.id}/'
        response = admin_api_client.delete(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_delete_self_is_prevented_when_last_admin(self, admin_api_client, admin_user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Ensure admin_user is the only active admin
        User.objects.filter(
            organization=admin_user.organization, role='admin', is_active=True
        ).exclude(pk=admin_user.pk).delete()

        url = f'/api/v1/admin/users/{admin_user.id}/'
        response = admin_api_client.delete(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestAdminUserCreation:
    def test_admin_create_user_requires_password(self, admin_api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        payload = {
            'email': 'nopassword@example.com',
            'name': 'No Password User',
            'role': 'member',
        }
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_create_user_with_valid_password(self, admin_api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        payload = {
            'email': 'validuser@example.com',
            'name': 'Valid User',
            'role': 'member',
            'password': 'ValidPassword123!',
        }
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestAdminSettingsTypedValues:
    def test_list_settings_includes_value_type(self, admin_api_client):
        response = admin_api_client.get('/api/v1/admin/settings/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_bool_setting_accepts_boolean_and_persists_canonical_value(self, admin_api_client):
        response = admin_api_client.patch(
            '/api/v1/admin/settings/ENABLE_PUBLIC_SIGNUP/',
            {'value': True},
            format='json',
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_int_setting_rejects_invalid_type(self, admin_api_client):
        response = admin_api_client.patch(
            '/api/v1/admin/settings/MAX_FILES_PER_UPLOAD/',
            {'value': 'not-an-int'},
            format='json',
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_watermark_file_size_rejects_negative_value(self, admin_api_client):
        response = admin_api_client.patch(
            '/api/v1/admin/settings/MAX_WATERMARK_FILE_SIZE_MB/',
            {'value': -50},
            format='json',
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_watermark_file_size_accepts_non_negative_value(self, admin_api_client):
        response = admin_api_client.patch(
            '/api/v1/admin/settings/MAX_WATERMARK_FILE_SIZE_MB/',
            {'value': 50},
            format='json',
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestAdminSecurityThreatEventsViewSet:
    def test_list_security_threat_events_scoped_to_org(self, admin_api_client, admin_user, file_request):
        own_event = SecurityThreatEvent.objects.create(
            organization=admin_user.organization,
            owner_user=admin_user,
            file_request=file_request,
            event_type=SecurityThreatEvent.EventType.MALWARE_DETECTED,
            severity=SecurityThreatEvent.Severity.HIGH,
            status=SecurityThreatEvent.Status.NEW,
            file_name='malware.exe',
            uploader_email='bad@example.com',
            scanner_message='FOUND',
        )

        other_org = Organization.objects.create(name='Other Org Threats')
        other_org_admin = User.objects.create_user(
            username='other-org-admin@example.com',
            email='other-org-admin@example.com',
            password='password',
            role='admin',
            organization=other_org,
        )
        other_org_root = Folder.objects.get_root_for_org(other_org)
        other_org_file_request = FileRequest.objects.create(
            name='Other Org Request',
            folder=other_org_root,
            created_by=other_org_admin,
        )
        SecurityThreatEvent.objects.create(
            organization=other_org,
            owner_user=other_org_admin,
            file_request=other_org_file_request,
            event_type=SecurityThreatEvent.EventType.SCAN_FAILED,
            severity=SecurityThreatEvent.Severity.MEDIUM,
            status=SecurityThreatEvent.Status.NEW,
            file_name='unknown.pdf',
            uploader_email='other@example.com',
            scanner_message='timeout',
        )

        response = admin_api_client.get('/api/v1/admin/security-threat-events/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_filter_security_threat_events(self, admin_api_client, admin_user, file_request):
        SecurityThreatEvent.objects.create(
            organization=admin_user.organization,
            owner_user=admin_user,
            file_request=file_request,
            event_type=SecurityThreatEvent.EventType.MALWARE_DETECTED,
            severity=SecurityThreatEvent.Severity.HIGH,
            status=SecurityThreatEvent.Status.NEW,
        )
        SecurityThreatEvent.objects.create(
            organization=admin_user.organization,
            owner_user=admin_user,
            file_request=file_request,
            event_type=SecurityThreatEvent.EventType.SCAN_FAILED,
            severity=SecurityThreatEvent.Severity.MEDIUM,
            status=SecurityThreatEvent.Status.RESOLVED,
        )

        response = admin_api_client.get('/api/v1/admin/security-threat-events/?severity=high&status=new')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_non_admin_cannot_list_security_threat_events(self, api_client):
        response = api_client.get('/api/v1/admin/security-threat-events/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminOrganizationView:
    def test_get_organization_branding(self, admin_api_client, admin_user):
        url = '/api/v1/admin/organization/'
        response = admin_api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_patch_organization_branding(self, admin_api_client, admin_user):
        url = '/api/v1/admin/organization/'
        data = {
            'brand_name': 'My Custom Brand',
            'brand_website_url': 'https://mycustombrand.com',
            'terms_url': 'https://mycustombrand.com/terms',
            'privacy_policy_url': 'https://mycustombrand.com/privacy',
        }
        response = admin_api_client.patch(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_patch_organization_branding_with_svg_logo_rejected(self, admin_api_client, admin_user):
        url = '/api/v1/admin/organization/'
        svg_content = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><circle cx="5" cy="5" r="4"/></svg>'
        svg_file = SimpleUploadedFile("logo.svg", svg_content, content_type="image/svg+xml")

        data = {
            'brand_name': 'My Custom Brand',
            'brand_logo': svg_file,
        }
        response = admin_api_client.patch(url, data, format='multipart')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_patch_organization_branding_with_corrupt_logo_rejected(self, admin_api_client, admin_user):
        url = '/api/v1/admin/organization/'
        corrupt_file = SimpleUploadedFile("logo.png", b"not-a-valid-image-binary", content_type="image/png")

        data = {
            'brand_name': 'My Custom Brand',
            'brand_logo': corrupt_file,
        }
        response = admin_api_client.patch(url, data, format='multipart')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_patch_organization_branding_with_png_logo(self, admin_api_client, admin_user):
        url = '/api/v1/admin/organization/'

        buf = io.BytesIO()
        img = Image.new('RGB', (10, 10), color='blue')
        img.save(buf, format='PNG')
        png_file = SimpleUploadedFile("logo.png", buf.getvalue(), content_type="image/png")

        data = {
            'brand_name': 'My Custom Brand',
            'brand_logo': png_file,
        }
        response = admin_api_client.patch(url, data, format='multipart')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_patch_organization_branding_clear_fields_and_partial_update(self, admin_api_client, admin_user):
        url = '/api/v1/admin/organization/'

        # 1. Set values first
        data = {
            'terms_url': 'https://mycustombrand.com/terms',
            'privacy_policy_url': 'https://mycustombrand.com/privacy',
        }
        response = admin_api_client.patch(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_non_admin_cannot_access_branding(self, api_client):
        url = '/api/v1/admin/organization/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_recalculate_user_quota_success(self, admin_api_client, admin_user):
        from documents.models import Document
        # Create a member user with corrupted total_document_size
        member = User.objects.create_user(
            username='member_quota@example.com',
            email='member_quota@example.com',
            organization=admin_user.organization,
            role='member',
            total_document_size=9999999,  # Corrupted / drifted value
        )

        # Create two active documents and one trashed document for this member.
        # Both active and trashed documents count toward storage quota until permanently purged.
        Document.objects.create(
            organization=admin_user.organization,
            created_by=member,
            name='doc1.pdf',
            file_size=1024,
            status='ready'
        )
        Document.objects.create(
            organization=admin_user.organization,
            created_by=member,
            name='doc2.pdf',
            file_size=2048,
            status='ready'
        )
        from django.utils import timezone
        Document.objects.create(
            organization=admin_user.organization,
            created_by=member,
            name='doc_deleted.pdf',
            file_size=5000,
            status='ready',
            deleted_at=timezone.now(),
        )

        url = f'/api/v1/admin/users/{member.id}/recalculate-quota/'
        response = admin_api_client.post(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_recalculate_user_quota_excludes_dataroom_vault_documents(self, admin_api_client, admin_user):
        from documents.models import Document, Folder
        from datarooms.models import Dataroom
        from datarooms.services import get_or_create_dataroom_storage_folder

        member = User.objects.create_user(
            username='member_vault_quota@example.com',
            email='member_vault_quota@example.com',
            organization=admin_user.organization,
            role='member',
            total_document_size=50 * 1024 * 1024 + 1024,  # Bloated with historical vault upload
        )

        # 1. Personal document (1024 bytes)
        Document.objects.create(
            organization=admin_user.organization,
            created_by=member,
            name='personal_notes.pdf',
            file_size=1024,
            status='ready'
        )

        # 2. Modern Dataroom vault document (50 MB)
        dataroom = Dataroom.objects.create(
            name="Confidential Deal",
            organization=admin_user.organization,
            created_by=member,
            storage_quota_mb=500,
            storage_version=2
        )
        vault_folder = get_or_create_dataroom_storage_folder(dataroom, member)
        Document.objects.create(
            organization=admin_user.organization,
            folder=vault_folder,
            created_by=member,
            name='deal_deck.pdf',
            file_size=50 * 1024 * 1024,
            status='ready'
        )

        # Admin triggers quota recalculation from user panel
        url = f'/api/v1/admin/users/{member.id}/recalculate-quota/'
        response = admin_api_client.post(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_recalculate_user_quota_non_admin_forbidden(self, api_client, user):
        url = f'/api/v1/admin/users/{user.id}/recalculate-quota/'
        response = api_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_recalculate_user_quota_other_org_not_found(self, admin_api_client, admin_user):
        other_org = Organization.objects.create(name="Other Org")
        other_user = User.objects.create_user(
            username='other_org_user@example.com',
            email='other_org_user@example.com',
            organization=other_org,
            role='member',
        )
        url = f'/api/v1/admin/users/{other_user.id}/recalculate-quota/'
        response = admin_api_client.post(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestAdminUserResetPassword:
    def test_admin_can_reset_user_password_and_invalidates_tokens(self, admin_api_client, admin_user, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

        # Generate a refresh token for user
        token = RefreshToken.for_user(user)
        refresh_str = str(token)

        url = f'/api/v1/admin/users/{user.id}/reset-password/'
        payload = {'password': 'BrandNewPassword2026!'}
        response = admin_api_client.post(url, payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reset_user_password_weak_password_fails(self, admin_api_client, user):
        url = f'/api/v1/admin/users/{user.id}/reset-password/'
        payload = {'password': '12'}  # Below minimum length
        response = admin_api_client.post(url, payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reset_user_password_missing_password_fails(self, admin_api_client, user):
        url = f'/api/v1/admin/users/{user.id}/reset-password/'
        response = admin_api_client.post(url, {}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reset_user_password_non_admin_forbidden(self, api_client, user):
        url = f'/api/v1/admin/users/{user.id}/reset-password/'
        response = api_client.post(url, {'password': 'ValidPassword2026!'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reset_user_password_other_org_not_found(self, admin_api_client, admin_user):
        other_org = Organization.objects.create(name="Other Org 2")
        other_user = User.objects.create_user(
            username='other_org_user2@example.com',
            email='other_org_user2@example.com',
            organization=other_org,
            role='member',
        )
        url = f'/api/v1/admin/users/{other_user.id}/reset-password/'
        response = admin_api_client.post(url, {'password': 'ValidPassword2026!'}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_reset_user_password_revocation_failure_rolls_back(self, admin_api_client, user, monkeypatch):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from rest_framework_simplejwt.tokens import RefreshToken
        RefreshToken.for_user(user)

        def mock_blacklist_all_user_tokens(*args, **kwargs):
            raise RuntimeError('Database error during token blacklisting')
        monkeypatch.setattr('core.serializers.blacklist_all_user_tokens', mock_blacklist_all_user_tokens)
        url = f'/api/v1/admin/users/{user.id}/reset-password/'
        payload = {'password': 'BrandNewPassword2026!'}
        response = admin_api_client.post(url, payload, format='json')
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestAdminUserListSearchFilterMetrics:
    def test_list_returns_kpi_metrics(self, admin_api_client, admin_user, user):
        from datarooms.models import Dataroom
        # Create a dataroom by user
        Dataroom.objects.create(
            name="Alpha Dataroom",
            organization=admin_user.organization,
            created_by=user,
        )

        response = admin_api_client.get('/api/v1/admin/users/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_subpage_omits_kpi_metrics(self, admin_api_client, admin_user):
        # Create enough users so page 2 has content (page_size=10)
        org = admin_user.organization
        for i in range(11):
            User.objects.create(
                email=f"subpage_user_{i}@example.com",
                username=f"subpage_user_{i}",
                name=f"Sub User {i}",
                organization=org,
            )

        # Page 1 includes metrics
        res1 = admin_api_client.get('/api/v1/admin/users/?page=1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res1.status_code == 403
        assert res1.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_search_by_name_and_email(self, admin_api_client, admin_user, user):
        user.name = "Unique Alice"
        user.save()

        # Search by name
        res = admin_api_client.get('/api/v1/admin/users/?search=Unique+Alice')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_filter_status_and_role(self, admin_api_client, admin_user, user):
        user.is_active = False
        user.save()

        # Filter admins
        res_admin = admin_api_client.get('/api/v1/admin/users/?status=admin')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_admin.status_code == 403
        assert res_admin.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_filter_dataroom_participant(self, admin_api_client, admin_user, user):
        from datarooms.models import Dataroom
        Dataroom.objects.create(
            name="Audit Room",
            organization=admin_user.organization,
            created_by=user,
        )

        res = admin_api_client.get('/api/v1/admin/users/?status=dataroom_participant')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_ordering(self, admin_api_client, admin_user, user):
        user.name = "Zoe User"
        user.save()
        admin_user.name = "Adam Admin"
        admin_user.save()

        res_asc = admin_api_client.get('/api/v1/admin/users/?ordering=name')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_asc.status_code == 403
        assert res_asc.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestAdminUserExport:
    """
    Tests for GET /api/v1/admin/users/export/ CSV export endpoint.
    """

    def test_admin_can_export_users_csv(self, admin_api_client, admin_user, user):
        user.total_document_size = 10 * 1024 * 1024
        user.custom_file_size_quota_mb = 500
        user.save()

        res = admin_api_client.get('/api/v1/admin/users/export/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_export_users_csv_respects_filters(self, admin_api_client, admin_user, user):
        user.is_active = False
        user.save()

        # Filter by inactive
        res = admin_api_client.get('/api/v1/admin/users/export/?status=inactive')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_export_users_csv_sanitizes_formula_injection(self, admin_api_client, admin_user):
        User.objects.create_user(
            username='formula_user',
            email='=calc|x!A0@example.com',
            name='@danger+cmd',
            password='password',
            role='member',
            organization=admin_user.organization,
        )

        res = admin_api_client.get('/api/v1/admin/users/export/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'Unclassified or disabled operation.'}

    def test_non_admin_cannot_export_users_csv(self, api_client, user):
        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/admin/users/export/')
        assert res.status_code == status.HTTP_403_FORBIDDEN




