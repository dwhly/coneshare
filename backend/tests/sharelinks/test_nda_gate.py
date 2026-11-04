import pytest
from rest_framework import status
from django.utils import timezone
from sharelinks.models import ShareLink, NDAAcceptance, ViewSession, Viewer
from documents.models import Document, DocumentVersion, DocumentPage

@pytest.fixture
def nda_share_link(user, document):
    # Setup document pages for viewing tests
    version = document.versions.get(is_primary=True)
    version.has_pages = True
    version.num_pages = 1
    version.save()
    DocumentPage.objects.create(
        document_version=version, page_number=1, storage_key="pages/shared_1.png"
    )
    document.num_pages = 1
    document.save()

    link = ShareLink.objects.create(
        document=document,
        created_by=user,
        require_nda=True,
        nda_text="Please sign this NDA text.",
        nda_version=1
    )
    return link

@pytest.mark.django_db
class TestShareLinkNDAGate:
    def test_public_meta_includes_nda_info(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        response = public_client.get(f'/api/v1/links/{nda_share_link.slug}/public-meta/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_data_gated_by_nda(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        response = public_client.get(f'/api/v1/links/{nda_share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_accept_nda_creates_session_and_acceptance(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        assert NDAAcceptance.objects.count() == 0
        assert ViewSession.objects.count() == 0

        # Accept NDA without providing view_session_id (anonymous flow)
        response = public_client.post(f'/api/v1/links/{nda_share_link.slug}/accept-nda/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_pages_and_renders_gated_by_nda(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Page view blocks
        response_page = public_client.get(f'/api/v1/links/{nda_share_link.slug}/page/1/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_page.status_code == 403
        assert response_page.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_nda_version_increment_requires_reacceptance(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Accept first NDA version
        response = public_client.post(f'/api/v1/links/{nda_share_link.slug}/accept-nda/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_accept_nda_triggers_notifications_and_automation(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test that accepting NDA triggers notifications and dispatch events if no session existed.'
        from unittest.mock import patch
        nda_share_link.receive_email_notification = True
        nda_share_link.save()
        with patch('sharelinks.views._dispatch_automation_event') as mock_dispatch:
            response = public_client.post(f'/api/v1/links/{nda_share_link.slug}/accept-nda/')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_nda_save_update_fields_increments_version(self, nda_share_link):
        """Test that update_fields=['nda_text'] save triggers version increment and updates database."""
        assert nda_share_link.nda_version == 1
        
        nda_share_link.nda_text = "Third NDA text terms."
        nda_share_link.save(update_fields=['nda_text'])
        
        nda_share_link.refresh_from_db()
        assert nda_share_link.nda_version == 2
        assert nda_share_link.nda_text == "Third NDA text terms."

    def test_accept_nda_email_verified_flow(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        org = nda_share_link.document.organization
        Viewer.objects.create(organization=org, email='viewer@example.com')

        nda_share_link.requires_email = True
        nda_share_link.save()

        # Step 1: Ensure email verification is prompted first
        response = public_client.get(f'/api/v1/links/{nda_share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_nda_acceptance_recognized_with_different_email_casing(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        org = nda_share_link.document.organization
        Viewer.objects.create(organization=org, email='Viewer@Example.COM')

        nda_share_link.requires_email = True
        nda_share_link.save()

        # 1. User with uppercase email accepts NDA
        session = public_client.session
        session['authorized_share_links'] = {
            str(nda_share_link.id): {
                'email_verified': True,
                'viewer_email': 'Viewer@Example.COM'
            }
        }
        session.save()

        response_accept = public_client.post(f'/api/v1/links/{nda_share_link.slug}/accept-nda/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_accept.status_code == 403
        assert response_accept.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


    def test_accept_nda_password_verified_flow(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        nda_share_link.password = "secret123"
        nda_share_link.save()

        # Step 1: Ensure password verification is prompted first
        response = public_client.get(f'/api/v1/links/{nda_share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_accept_nda_twice_reuses_view_session(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        assert ViewSession.objects.count() == 0

        # Accept NDA first time
        response1 = public_client.post(f'/api/v1/links/{nda_share_link.slug}/accept-nda/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response1.status_code == 403
        assert response1.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_preview_token_invalid_bypass_fails(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        response = public_client.get(
            f'/api/v1/links/{nda_share_link.slug}/view-data/',
            data={'previewToken': 'invalid-token-123'}
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_preview_token_valid_bypass_succeeds(self, public_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from sharelinks.models import PreviewSession
        import secrets
        from datetime import timedelta
        
        token = secrets.token_urlsafe(32)
        PreviewSession.objects.create(
            share_link=nda_share_link,
            user=nda_share_link.created_by,
            token=token,
            expires_at=timezone.now() + timedelta(minutes=5)
        )

        response = public_client.get(
            f'/api/v1/links/{nda_share_link.slug}/view-data/',
            data={'previewToken': token}
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_owner_clean_link_access_populates_session(self, api_client, nda_share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Force authentication as owner
        api_client.force_authenticate(user=nda_share_link.created_by)

        # GET view-data (owner bypasses checks)
        response = api_client.get(f'/api/v1/links/{nda_share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

