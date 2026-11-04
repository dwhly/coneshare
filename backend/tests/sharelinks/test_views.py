import pytest
import requests
from unittest.mock import patch, mock_open, MagicMock
from datetime import timedelta
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from rest_framework.settings import api_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.text import get_valid_filename
from rest_framework import status

from datarooms.models import Dataroom, DataroomDocument, DataroomFolder, DataroomItemOrder
from documents.models import (Document, DocumentPage, DocumentVersion)
from documents.renderers.base import BasePreviewRenderer
from sharelinks.models import (DataroomVisit, EmailVerificationToken, PageView,
                               PreviewSession, ShareLink,
                               ShareLinkDataroomSetting, ViewSession, LinkClick)
from sharelinks.views import (DATAROOM_VIEWDATA_DEFAULT_LIMIT, _is_dataroom_folder_path_visible,
                              _build_dataroom_breadcrumbs, _resolve_dataroom_document_setting)
import zipfile
from io import BytesIO
try:
    from PIL import Image
except ImportError:
    Image = None

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
        DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True, original_storage_key="path/to/original.pdf")
        return doc
    return _create_document


@pytest.fixture
def dataroom_with_link_and_content(user, dataroom, document_factory):
    """
    Sets up a dataroom with a document, a folder, a dataroom document link,
    and a share link for the dataroom.
    """
    doc = document_factory(name="Test Doc.pdf")
    folder = DataroomFolder.objects.create(dataroom=dataroom, name="Test Folder")
    ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=folder)
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
    return {
        "link": link,
        "folder": folder,
        "ddoc": ddoc,
        "document": doc,
    }


pytestmark = pytest.mark.django_db


@pytest.mark.django_db
class TestRecordPageView:
    @staticmethod
    def _authorize_link_session(client, link, viewer_email=''):
        session = client.session
        session['authorized_share_links'] = {
            str(link.id): {
                'password_verified': True,
                'email_verified': True,
                'viewer_email': viewer_email,
            }
        }
        session.save()

    def test_record_page_view_success(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, share_link)
        # 1. Create a View session
        view_session = ViewSession.objects.create(share_link=share_link, duration_seconds=10)
        assert PageView.objects.count() == 0

        # 2. Send tracking data
        data = {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 5
        }
        response = public_client.post('/api/v1/page-views/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_with_scroll_percentage_and_markdown(self, public_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc = Document.objects.create(name="README.md", type="markdown", created_by=user, organization=user.organization)
        link = ShareLink.objects.create(document=doc, created_by=user)
        self._authorize_link_session(public_client, link)
        view_session = ViewSession.objects.create(share_link=link)

        data = {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 12,
            'scroll_percentage': 85
        }
        response = public_client.post('/api/v1/page-views/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_with_spreadsheet_document(self, public_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc = Document.objects.create(name="Report.xlsx", type="spreadsheet", created_by=user, organization=user.organization)
        link = ShareLink.objects.create(document=doc, created_by=user)
        self._authorize_link_session(public_client, link)
        view_session = ViewSession.objects.create(share_link=link)

        data = {
            'view_session': view_session.id,
            'page_number': 2,
            'duration_seconds': 15,
            'media_type': 'spreadsheet'
        }
        response = public_client.post('/api/v1/page-views/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_scroll_percentage_range_validation(self, public_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc = Document.objects.create(name="README.md", type="markdown", created_by=user, organization=user.organization)
        link = ShareLink.objects.create(document=doc, created_by=user)
        self._authorize_link_session(public_client, link)
        view_session = ViewSession.objects.create(share_link=link)

        # > 100 should fail
        response = public_client.post('/api/v1/page-views/record/', {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 5,
            'scroll_percentage': 101
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_markdown_without_scroll_percentage_does_not_set_100_percent(self, public_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc = Document.objects.create(name="README.md", type="markdown", created_by=user, organization=user.organization)
        link = ShareLink.objects.create(document=doc, created_by=user)
        self._authorize_link_session(public_client, link)
        view_session = ViewSession.objects.create(share_link=link)

        response = public_client.post('/api/v1/page-views/record/', {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 5,
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_invalid_view_id(self, public_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        data = {
            'view_session': '01J4Z7YJ8ZJ4Z7YJ8ZJ4Z7YJ8Z',  # A valid but non-existent ULID
            'page_number': 1,
            'duration_seconds': 5
        }
        response = public_client.post('/api/v1/page-views/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_missing_data(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        view_session = ViewSession.objects.create(share_link=share_link)
        data = {
            'view_session': view_session.id,
            # 'page_number' is missing
            'duration_seconds': 5
        }
        response = public_client.post('/api/v1/page-views/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_updates_completion_rate(self, public_client, document, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        "\n        Test that recording page views correctly updates the parent ViewSession's\n        completion rate.\n        "
        document.num_pages = 4
        document.save()
        self._authorize_link_session(public_client, share_link)
        view_session = ViewSession.objects.create(share_link=share_link)
        assert view_session.completion_rate == 0.0
        response = public_client.post('/api/v1/page-views/record/', {'view_session': view_session.id, 'page_number': 1, 'duration_seconds': 5})
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_with_dataroom_visit(self, public_client, dataroom_with_link_and_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_link_and_content['link']
        ddoc = dataroom_with_link_and_content['ddoc']
        self._authorize_link_session(public_client, link)
        session = ViewSession.objects.create(share_link=link)
        visit = DataroomVisit.objects.create(view_session=session, dataroom_document=ddoc)
        
        assert PageView.objects.count() == 0

        data = {
            'view_session': session.id,
            'page_number': 1,
            'duration_seconds': 15,
            'dataroom_visit': visit.id
        }
        response = public_client.post('/api/v1/page-views/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_with_mismatched_dataroom_visit_fails(self, public_client, dataroom_with_link_and_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_link_and_content['link']
        ddoc = dataroom_with_link_and_content['ddoc']
        self._authorize_link_session(public_client, link)
        
        # Session A and its visit
        session_a = ViewSession.objects.create(share_link=link)
        visit_from_a = DataroomVisit.objects.create(view_session=session_a, dataroom_document=ddoc)
        
        # Session B (for the same link)
        session_b = ViewSession.objects.create(share_link=link)

        data = {
            'view_session': session_b.id,  # Trying to record for session B
            'page_number': 1,
            'duration_seconds': 15,
            'dataroom_visit': visit_from_a.id  # But using visit from session A
        }
        response = public_client.post('/api/v1/page-views/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_without_authorized_session_fails(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.password = 'testpass'
        share_link.save(update_fields=['password'])

        view_session = ViewSession.objects.create(share_link=share_link)
        response = public_client.post('/api/v1/page-views/record/', {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 5
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_inactive_link_fails(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, share_link)
        share_link.is_active = False
        share_link.save(update_fields=['is_active'])

        view_session = ViewSession.objects.create(share_link=share_link)
        response = public_client.post('/api/v1/page-views/record/', {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 5
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_expired_link_fails(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, share_link)
        share_link.expires_at = timezone.now() - timedelta(hours=1)
        share_link.save(update_fields=['expires_at'])

        view_session = ViewSession.objects.create(share_link=share_link)
        response = public_client.post('/api/v1/page-views/record/', {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 5
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_duration_seconds_bounds(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, share_link)
        view_session = ViewSession.objects.create(share_link=share_link)

        # 0 seconds should succeed (e.g. fast markdown scroll depth flush)
        resp_zero = public_client.post('/api/v1/page-views/record/', {
            'view_session': view_session.id,
            'page_number': 1,
            'duration_seconds': 0
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp_zero.status_code == 403
        assert resp_zero.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_page_view_numeric_range_validations(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, share_link)
        view_session = ViewSession.objects.create(share_link=share_link)

        # page_number: 0 (< 1) should fail
        resp = public_client.post('/api/v1/page-views/record/', {
            'view_session': view_session.id, 'page_number': 0, 'duration_seconds': 5
        })
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_create_session_stores_false_flags_and_rejects_subsequently_added_password(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Create view session through endpoint on open link
        resp_create = public_client.post('/api/v1/view-sessions/', {'share_link': share_link.id})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp_create.status_code == 403
        assert resp_create.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


@pytest.mark.django_db
class TestRecordLinkClick:
    def test_record_link_click_success(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        view_session = ViewSession.objects.create(share_link=share_link, duration_seconds=10)
        assert LinkClick.objects.count() == 0

        data = {
            'view_session': view_session.id,
            'url': 'https://google.com',
            'page_number': 1
        }
        response = public_client.post('/api/v1/link-clicks/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_link_click_dataroom_visit_mismatch(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        view_session = ViewSession.objects.create(share_link=share_link)
        other_session = ViewSession.objects.create(share_link=share_link)
        
        dataroom_visit = DataroomVisit.objects.create(view_session=other_session)

        data = {
            'view_session': view_session.id,
            'dataroom_visit': dataroom_visit.id,
            'url': 'https://google.com',
            'page_number': 1
        }
        response = public_client.post('/api/v1/link-clicks/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_link_click_invalid_url_protocol(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        view_session = ViewSession.objects.create(share_link=share_link)
        assert LinkClick.objects.count() == 0

        data = {
            'view_session': view_session.id,
            'url': 'javascript:alert(1)',
            'page_number': 1
        }
        response = public_client.post('/api/v1/link-clicks/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_link_click_whitespace_bypass(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        view_session = ViewSession.objects.create(share_link=share_link)
        data = {
            'view_session': view_session.id,
            'url': '   javascript:alert(1)',
            'page_number': 1
        }
        response = public_client.post('/api/v1/link-clicks/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_link_click_data_uri(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        view_session = ViewSession.objects.create(share_link=share_link)
        data = {
            'view_session': view_session.id,
            'url': 'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',
            'page_number': 1
        }
        response = public_client.post('/api/v1/link-clicks/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_link_click_http_success(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        view_session = ViewSession.objects.create(share_link=share_link)
        data = {
            'view_session': view_session.id,
            'url': 'http://example.com',
            'page_number': 1
        }
        response = public_client.post('/api/v1/link-clicks/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_link_click_inactive_link_rejected(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.is_active = False
        share_link.save()
        view_session = ViewSession.objects.create(share_link=share_link)
        data = {
            'view_session': view_session.id,
            'url': 'https://google.com',
            'page_number': 1
        }
        response = public_client.post('/api/v1/link-clicks/record/', data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}




@pytest.mark.django_db
class TestViewSessionViewSet:
    @patch('sharelinks.views.settings.GEOIP')
    def test_create_view_records_ip_and_user_agent(self, mock_geoip, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Mock the GeoIP2 lookup
        mock_city_data = {
            'city': 'Mountain View',
            'country_name': 'United States',
            'latitude': 37.422,
            'longitude': -122.084,
        }
        mock_geoip.city.return_value = mock_city_data
        assert ViewSession.objects.count() == 0

        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"

        response = public_client.post(
            '/api/v1/view-sessions/',
            {'share_link': share_link.id},
            HTTP_USER_AGENT=user_agent,
            REMOTE_ADDR='98.137.11.155'  # Example public IP for Yahoo
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.settings.GEOIP')
    def test_create_view_records_ip_from_trusted_proxy_x_real_ip(self, mock_geoip, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_geoip.city.return_value = {}  # Mock to avoid errors, not testing location here

        real_ip = "1.2.3.4"
        proxy_ip = "127.0.0.1"

        response = public_client.post(
            '/api/v1/view-sessions/',
            {'share_link': share_link.id},
            HTTP_X_REAL_IP=real_ip,
            REMOTE_ADDR=proxy_ip
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.settings.GEOIP')
    def test_create_view_ignores_spoofed_x_real_ip_from_untrusted_remote(self, mock_geoip, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_geoip.city.return_value = {}

        spoofed_ip = "203.0.113.7"
        untrusted_remote = "98.137.11.155"

        response = public_client.post(
            '/api/v1/view-sessions/',
            {'share_link': share_link.id},
            HTTP_X_REAL_IP=spoofed_ip,
            HTTP_X_FORWARDED_FOR=f'{spoofed_ip}, {untrusted_remote}',
            REMOTE_ADDR=untrusted_remote
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


    @patch('sharelinks.views.settings.GEOIP')
    def test_create_view_handles_geoip_city_none(self, mock_geoip, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_geoip.city.return_value = {
            'city': None,
            'country_name': 'China',
            'latitude': 34.7732,
            'longitude': 113.722,
        }

        response = public_client.post(
            '/api/v1/view-sessions/',
            {'share_link': share_link.id},
            REMOTE_ADDR='39.184.107.177'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_download_for_view_session(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.allow_download = True
        share_link.allow_original_download = True  # AmForge: originals need explicit opt-in
        share_link.save()
        # 1. Create a View session
        view_session = ViewSession.objects.create(share_link=share_link)
        assert view_session.downloaded_at is None

        # 2. Record the download via GET download-file
        url = f'/api/v1/links/{share_link.slug}/download-file/?view_session_id={view_session.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_record_download_disabled_endpoint_returns_404(self, public_client, share_link):
        """Test that the legacy /record-download/ POST endpoint is disabled and returns 404."""
        view_session = ViewSession.objects.create(share_link=share_link)
        url = f'/api/v1/view-sessions/{view_session.id}/record-download/'
        response = public_client.post(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_view_session_for_authenticated_user_records_email(self, api_client, share_link, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        assert ViewSession.objects.count() == 0

        response = api_client.post(
            '/api/v1/view-sessions/',
            {'share_link': share_link.id},
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._dispatch_automation_event')
    def test_create_view_session_triggers_email_notification(self, mock_dispatch, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.receive_email_notification = True
        share_link.save()

        response = public_client.post(
            '/api/v1/view-sessions/',
            {'share_link': share_link.id},
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._dispatch_automation_event')
    def test_create_view_session_does_not_trigger_email_notification(self, mock_dispatch, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.receive_email_notification = False
        share_link.save()

        response = public_client.post(
            '/api/v1/view-sessions/',
            {'share_link': share_link.id},
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


@pytest.mark.django_db
class TestShareLinkViewDataView:
    """Tests for the public ShareLinkViewDataView endpoint."""

    @pytest.fixture
    def document_with_pages(self, document):
        """Fixture for a document that has pages."""
        version = document.versions.get(is_primary=True)
        version.has_pages = True
        version.num_pages = 1
        version.save()
        DocumentPage.objects.create(
            document_version=version, page_number=1, storage_key="pages/shared_1.png"
        )
        document.num_pages = 1
        document.save()
        return document

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    def test_get_share_link_data_with_watermark_direct_document(self, public_client, share_link, document_with_pages):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Setup: Enable watermark on a direct document link
        share_link.enable_watermark = True
        share_link.watermark_text = "Test Watermark {{email}}"
        share_link.save()

        # Action: Request the view data
        # This will crash with a NameError if viewer_email is not defined in the direct document path.
        response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    def test_get_share_link_data_success(self, public_client, share_link, document_with_pages):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.allow_original_download = True  # AmForge: originals need explicit opt-in
        share_link.save()
        response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    def test_get_share_link_data_markdown_document(self, public_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test retrieval of share link data for markdown document exposes markdown_preview_url.'
        doc = Document.objects.create(name='README.md', type='markdown', status='ready', created_by=user, organization=user.organization)
        DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True, original_storage_key='org_1/notes.md', content_type='text/markdown', file_size=1024, render_status='ready')
        link = ShareLink.objects.create(document=doc, created_by=user)
        with patch('documents.fileserver.fileserver_client.generate_preview_url', return_value='http://test.coneshare.com/files/preview/abc123'):
            response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com", ENABLE_VIDEO_PREVIEW=True)
    def test_get_share_link_data_video_stream_ttl(self, public_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test that video stream URL generation passes extended TTL calculated from video length.'
        doc = Document.objects.create(name='presentation.mp4', type='video', status='ready', created_by=user, organization=user.organization)
        version = DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True, original_storage_key='org_1/presentation.mp4', storage_key='org_1/hls/presentation_hls', content_type='video/mp4', file_size=1024 * 1024, render_status='ready', length=18000)
        link = ShareLink.objects.create(document=doc, created_by=user)
        with patch('sharelinks.views.fileserver_client.generate_preview_url', return_value='http://test.coneshare.com/files/preview/stream123') as mock_preview_url:
            response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_share_link_data_includes_download_url(self, mock_fs_download_url, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Setup
        primary_version = share_link.document.versions.get(is_primary=True)
        primary_version.original_storage_key = "path/to/original.pdf"
        primary_version.save()
        mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/some-token"
        share_link.allow_original_download = True  # AmForge: originals need explicit opt-in
        share_link.save()

        # Action
        response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    @patch('documents.fileserver.fileserver_client.generate_download_url')
    def test_get_share_link_data_for_spreadsheet(self, mock_fs_download_url, public_client, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/sheet.json"
        doc = Document.objects.create(
            organization=user.organization,
            created_by=user,
            name="forecast.xlsx",
            type="spreadsheet",
            status="ready",
            num_pages=3
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            type="spreadsheet",
            is_primary=True,
            has_pages=False,
            num_pages=3,
            storage_key="documents/1/forecast_spreadsheet.json",
            original_storage_key="documents/1/forecast.xlsx",
            render_status="ready"
        )
        link = ShareLink.objects.create(
            created_by=user,
            document=doc,
            slug="sheet-slug-123"
        )
        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch.object(BasePreviewRenderer, 'enqueue_render_task')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_share_link_data_hides_download_url_when_downloads_disabled(self, mock_fs_download_url, mock_enqueue_preview, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Pending lazy previews must not expose original-file URLs when downloads are disabled.'
        share_link.allow_download = False
        share_link.save()
        document = share_link.document
        document.type = 'pdf'
        document.content_type = 'application/pdf'
        document.download_only = False
        document.save()
        primary_version = document.versions.get(is_primary=True)
        primary_version.original_storage_key = 'path/to/original.pdf'
        primary_version.storage_key = 'path/to/original.pdf'
        primary_version.type = 'pdf'
        primary_version.render_status = DocumentVersion.RENDER_NOT_GENERATED
        primary_version.has_pages = False
        primary_version.save()
        mock_fs_download_url.return_value = 'https://...'
        mock_enqueue_preview.return_value = DocumentVersion.RENDER_QUEUED
        with override_settings(PDF_PREVIEW_ENGINE='server_pages'):
            response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    def test_get_share_link_data_for_image_document(self, public_client, image_document_with_content, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Setup
        image_share_link = ShareLink.objects.create(
            document=image_document_with_content,
            created_by=user
        )

        # Action
        response = public_client.get(f'/api/v1/links/{image_share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_share_link_data_not_found(self, public_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        response = public_client.get('/api/v1/links/non-existent-slug/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_share_link_data_inactive(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.is_active = False
        share_link.save()
        response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_share_link_data_expired(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.expires_at = timezone.now() - timedelta(days=1)
        share_link.save()
        response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_share_link_data_password_protected(self, public_client, share_link_with_password):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        response = public_client.get(f'/api/v1/links/{share_link_with_password.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_share_link_data_dataroom_catalog_populates_effective_watermark_text(self, public_client, dataroom, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            enable_watermark=True,
            watermark_text="",
        )
        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_share_link_data_dataroom_catalog_gates_allow_download_on_watermark_size_and_video(
        self, public_client, dataroom, user, document_factory
    ):
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            allow_download=True,
            enable_watermark=True,
        )

        # 1. Normal PDF within size limit
        doc_normal = document_factory(name="Normal.pdf", type='pdf')
        v_normal = doc_normal.versions.filter(is_primary=True).first()
        v_normal.file_size = 5 * 1024 * 1024  # 5 MB
        v_normal.save()
        ddoc_normal = DataroomDocument.objects.create(dataroom=dataroom, document=doc_normal)

        # 2. Oversized PDF exceeding max watermark limit (100 MB)
        doc_oversized = document_factory(name="Oversized.pdf", type='pdf')
        v_oversized = doc_oversized.versions.filter(is_primary=True).first()
        v_oversized.file_size = 150 * 1024 * 1024  # 150 MB
        v_oversized.save()
        ddoc_oversized = DataroomDocument.objects.create(dataroom=dataroom, document=doc_oversized)

        # 3. Video (cannot be watermarked, so allow_download must be False)
        doc_video = document_factory(name="Movie.mp4", type='video')
        v_video = doc_video.versions.filter(is_primary=True).first()
        v_video.file_size = 20 * 1024 * 1024
        v_video.save()
        ddoc_video = DataroomDocument.objects.create(dataroom=dataroom, document=doc_video)

        # 4. Folder
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Presentations")

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_share_link_data_dataroom_catalog_gates_allow_download_on_link_allow_download_false(
        self, public_client, dataroom, user, document_factory
    ):
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            allow_download=False,
            enable_watermark=False,
        )

        doc = document_factory(name="Doc.pdf", type='pdf')
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc)
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Docs")

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


@pytest.mark.django_db
class TestDataroomVisitTracking:
    @pytest.fixture
    def dataroom_link_with_content(self, user, dataroom, document_factory):
        doc = document_factory(name="Test Doc.pdf")
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Test Folder")
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=folder)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        session = ViewSession.objects.create(share_link=link)
        return {
            "session": session,
            "folder": folder,
            "ddoc": ddoc,
        }

    def test_record_dataroom_document_visit(self, public_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        ddoc = dataroom_link_with_content['ddoc']
        
        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_document_id': str(ddoc.id)}
        
        assert DataroomVisit.objects.count() == 0
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_dataroom_folder_visit(self, public_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        folder = dataroom_link_with_content['folder']
        
        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_folder_id': str(folder.id)}
        
        assert DataroomVisit.objects.count() == 0
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_folder_get_full_path_hierarchy(self, dataroom):
        """Test hierarchical path calculation on DataroomFolder."""
        root = DataroomFolder.objects.create(dataroom=dataroom, name="Financials")
        sub1 = DataroomFolder.objects.create(dataroom=dataroom, parent=root, name="2026")
        sub2 = DataroomFolder.objects.create(dataroom=dataroom, parent=sub1, name="Q1")

        assert root.get_full_path() == "/Financials"
        assert sub1.get_full_path() == "/Financials/2026"
        assert sub2.get_full_path() == "/Financials/2026/Q1"

    def test_audit_trail_preserved_when_dataroom_document_deleted(self, api_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        ddoc = dataroom_link_with_content['ddoc']
        link = session.share_link
        doc_name = ddoc.document.name

        visit = DataroomVisit.objects.create(view_session=session, dataroom_document=ddoc)
        assert visit.item_name == doc_name
        assert visit.item_path == "/Test Folder"
        assert visit.document_type == ddoc.document.type

        # Now delete the dataroom document (simulates removal from room)
        ddoc.delete()

        # Fetch the session via API as the owner
        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_audit_trail_when_dataroom_document_renamed(self, api_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        ddoc = dataroom_link_with_content['ddoc']
        link = session.share_link
        original_name = ddoc.document.name

        visit = DataroomVisit.objects.create(view_session=session, dataroom_document=ddoc)
        assert visit.item_name == original_name

        # Rename the dataroom document alias
        ddoc.name = "Renamed Contract.pdf"
        ddoc.save()

        # Fetch the session via API as the owner
        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_audit_trail_preserved_when_dataroom_folder_deleted(self, api_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        folder = dataroom_link_with_content['folder']
        link = session.share_link
        folder_name = folder.name

        visit = DataroomVisit.objects.create(view_session=session, dataroom_folder=folder)
        assert visit.item_name == folder_name
        assert visit.item_type == 'folder'

        # Delete the folder
        folder.delete()

        # Fetch the session via API
        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_audit_trail_when_dataroom_folder_renamed(self, api_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        folder = dataroom_link_with_content['folder']
        link = session.share_link
        original_name = folder.name

        visit = DataroomVisit.objects.create(view_session=session, dataroom_folder=folder)
        assert visit.item_name == original_name

        # Rename the folder
        folder.name = "2026 Archived Financials"
        folder.save()

        # Fetch the session via API
        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_audit_trail_preserved_when_dataroom_document_moved(self, api_client, dataroom_link_with_content, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        ddoc = dataroom_link_with_content['ddoc']
        link = session.share_link

        visit = DataroomVisit.objects.create(view_session=session, dataroom_document=ddoc)
        assert visit.item_path == "/Test Folder"

        # Move document to a new folder
        new_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Archive")
        ddoc.folder = new_folder
        ddoc.save()

        # Fetch session via API
        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_audit_trail_preserved_when_dataroom_folder_moved(self, api_client, dataroom_link_with_content, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        link = session.share_link

        parent_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Parent")
        child_folder = DataroomFolder.objects.create(dataroom=dataroom, parent=parent_folder, name="Child")

        visit = DataroomVisit.objects.create(view_session=session, dataroom_folder=child_folder)
        assert visit.item_path == "/Parent/Child"

        # Move child_folder to a different parent folder
        new_parent = DataroomFolder.objects.create(dataroom=dataroom, name="Archive")
        child_folder.parent = new_parent
        child_folder.save()

        # Fetch session via API
        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_audit_trail_root_dataroom_download_item_status(self, api_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        link = session.share_link
        dataroom = link.dataroom
        now = timezone.now()

        visit = DataroomVisit.objects.create(
            view_session=session,
            item_type='folder',
            item_name=dataroom.name,
            item_path='/',
            visited_at=now,
            downloaded_at=now,
        )

        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_audit_trail_root_dataroom_download_when_renamed(self, api_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        link = session.share_link
        dataroom = link.dataroom
        original_name = dataroom.name
        now = timezone.now()

        visit = DataroomVisit.objects.create(
            view_session=session,
            item_type='folder',
            item_name=original_name,
            item_path='/',
            visited_at=now,
            downloaded_at=now,
        )

        dataroom.name = "Renamed Project"
        dataroom.save()

        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_record_visit_for_hidden_document_fails_with_404(self, public_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        ddoc = dataroom_link_with_content['ddoc']
        link = session.share_link

        # Hide the document on this share link
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.is_visible = False
        setting.save()

        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_document_id': str(ddoc.id)}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_visit_for_document_in_hidden_folder_fails_with_404(self, public_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        ddoc = dataroom_link_with_content['ddoc']
        folder = dataroom_link_with_content['folder']
        link = session.share_link

        # Hide the parent folder on this share link
        folder_setting = link.dataroom_settings.get(dataroom_folder=folder)
        folder_setting.is_visible = False
        folder_setting.save()

        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_document_id': str(ddoc.id)}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_visit_for_hidden_folder_fails_with_404(self, public_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        folder = dataroom_link_with_content['folder']
        link = session.share_link

        # Hide the folder on this share link
        folder_setting = link.dataroom_settings.get(dataroom_folder=folder)
        folder_setting.is_visible = False
        folder_setting.save()

        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_folder_id': str(folder.id)}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_visit_deeply_nested_document_path(self, public_client, dataroom_link_with_content, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        link = session.share_link

        l1 = DataroomFolder.objects.create(dataroom=dataroom, name="Level1")
        l2 = DataroomFolder.objects.create(dataroom=dataroom, parent=l1, name="Level2")
        l3 = DataroomFolder.objects.create(dataroom=dataroom, parent=l2, name="Level3")
        l4 = DataroomFolder.objects.create(dataroom=dataroom, parent=l3, name="Level4")
        deep_doc = DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=l4, name="Nested Doc")
        # Note: signals already created ShareLinkDataroomSetting with is_visible=True for link

        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_document_id': str(deep_doc.id)}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_visit_for_non_dataroom_link_fails(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = ViewSession.objects.create(share_link=share_link)
        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_folder_id': 'some_id'}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_record_visit_with_invalid_id_fails(self, public_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        
        url = f'/api/v1/view-sessions/{session.id}/record-visit/'
        data = {'dataroom_document_id': 'ddoc_00000000000000000000000000'}
        response = public_client.post(url, data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_sessions_for_dataroom_includes_page_views(self, api_client, dataroom_link_with_content):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = dataroom_link_with_content['session']
        ddoc = dataroom_link_with_content['ddoc']
        link = dataroom_link_with_content['session'].share_link

        # Create a visit and a page view for it
        visit = DataroomVisit.objects.create(view_session=session, dataroom_document=ddoc)
        PageView.objects.create(
            view_session=session,
            dataroom_visit=visit,
            page_number=1,
            duration_seconds=30
        )
        
        # The user who created the link is fetching the sessions
        url = f'/api/v1/share-links/{link.id}/view-sessions/'
        response = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_get_share_link_data_document_not_ready(self, public_client, share_link, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        document.status = 'processing'
        document.save()
        response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_hides_content_in_invisible_folder(self, public_client, user, organization, document_factory):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Setup Dataroom and content
        dataroom = Dataroom.objects.create(name="Test Dataroom", created_by=user, organization=organization)
        parent_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Parent Folder")
        sub_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Subfolder", parent=parent_folder)
        doc_in_subfolder = document_factory(name="Secret.pdf")
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc_in_subfolder, folder=sub_folder)

        # 2. Create share link (this will trigger signal to create settings)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        
        # 3. Update settings: make parent folder invisible, but document and subfolder visible
        parent_folder_setting = ShareLinkDataroomSetting.objects.get(share_link=link, dataroom_folder=parent_folder)
        parent_folder_setting.is_visible = False
        parent_folder_setting.save()

        doc_setting = ShareLinkDataroomSetting.objects.get(share_link=link, dataroom_document=ddoc)
        doc_setting.is_visible = True
        doc_setting.save()

        sub_folder_setting = ShareLinkDataroomSetting.objects.get(share_link=link, dataroom_folder=sub_folder)
        sub_folder_setting.is_visible = True
        sub_folder_setting.save()
        
        # 4. Access public data
        url = f'/api/v1/links/{link.slug}/view-data/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_data_with_duplicate_dataroom_setting_does_not_500(
        self, public_client, user, organization, document_factory
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom = Dataroom.objects.create(name="Duplicate Settings Dataroom", created_by=user, organization=organization)
        doc = document_factory(name="Doc.pdf")
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=None)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        # Signal already created one setting row
        setting = ShareLinkDataroomSetting.objects.get(share_link=link, dataroom_document=ddoc)

        # Test defensive resolution: simulate multiple matching records in the queryset
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value.first.return_value = setting

        with patch.object(type(link.dataroom_settings), 'select_related', return_value=mock_qs):
            resolved = _resolve_dataroom_document_setting(link, str(ddoc.id))
            assert resolved == setting

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


    def test_get_dataroom_link_data_root_scope_returns_only_root_direct_children(
        self, public_client, user, organization, document_factory
    ):
        dataroom = Dataroom.objects.create(name="Test Dataroom", created_by=user, organization=organization)
        root_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Root Folder")
        child_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Child Folder", parent=root_folder)
        root_doc = document_factory(name="Root Doc.pdf")
        child_doc = document_factory(name="Child Doc.pdf")
        DataroomDocument.objects.create(dataroom=dataroom, document=root_doc, folder=None)
        DataroomDocument.objects.create(dataroom=dataroom, document=child_doc, folder=child_folder)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_nested_scope_returns_direct_children(
        self, public_client, user, organization, document_factory
    ):
        dataroom = Dataroom.objects.create(name="Test Dataroom", created_by=user, organization=organization)
        parent = DataroomFolder.objects.create(dataroom=dataroom, name="Parent")
        child_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Child Folder", parent=parent)
        child_doc = document_factory(name="Child Doc.pdf")
        grandchild_doc = document_factory(name="Grandchild Doc.pdf")
        child_ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=child_doc, folder=parent)
        DataroomDocument.objects.create(dataroom=dataroom, document=grandchild_doc, folder=child_folder)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?parent_id={parent.id}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_uses_safe_default_pagination(
        self, public_client, user, organization, document_factory
    ):
        dataroom = Dataroom.objects.create(name="Paged Dataroom", created_by=user, organization=organization)
        for i in range(60):
            doc = document_factory(name=f"Doc {i}.pdf")
            DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=None)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_nested_scope_pagination_limit_and_offset(
        self, public_client, user, organization, document_factory
    ):
        dataroom = Dataroom.objects.create(name="Nested Paged Dataroom", created_by=user, organization=organization)
        parent = DataroomFolder.objects.create(dataroom=dataroom, name="Parent")
        for i in range(35):
            doc = document_factory(name=f"Nested Doc {i}.pdf")
            DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=parent)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        response_page_1 = public_client.get(
            f'/api/v1/links/{link.slug}/view-data/?parent_id={parent.id}&limit=20&offset=0'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_page_1.status_code == 403
        assert response_page_1.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_rejects_foreign_or_invisible_parent_id(
        self, public_client, user, organization, document_factory
    ):
        dataroom = Dataroom.objects.create(name="Test Dataroom", created_by=user, organization=organization)
        visible_parent = DataroomFolder.objects.create(dataroom=dataroom, name="Visible")
        invisible_parent = DataroomFolder.objects.create(dataroom=dataroom, name="Invisible")
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        invisible_setting = ShareLinkDataroomSetting.objects.get(
            share_link=link,
            dataroom_folder=invisible_parent,
        )
        invisible_setting.is_visible = False
        invisible_setting.save(update_fields=['is_visible'])

        other_dataroom = Dataroom.objects.create(name="Other", created_by=user, organization=organization)
        foreign_folder = DataroomFolder.objects.create(dataroom=other_dataroom, name="Foreign")

        response_invisible = public_client.get(
            f'/api/v1/links/{link.slug}/view-data/?parent_id={invisible_parent.id}'
        )
        assert response_invisible.status_code == status.HTTP_403_FORBIDDEN

        response_foreign = public_client.get(
            f'/api/v1/links/{link.slug}/view-data/?parent_id={foreign_folder.id}'
        )
        assert response_foreign.status_code == status.HTTP_403_FORBIDDEN

        # sanity check: visible parent should still be allowed
        response_visible = public_client.get(
            f'/api/v1/links/{link.slug}/view-data/?parent_id={visible_parent.id}'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_visible.status_code == 403
        assert response_visible.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_scope_ordering_uses_item_order_and_fallback(
        self, public_client, user, organization, document_factory
    ):
        dataroom = Dataroom.objects.create(name="Test Dataroom", created_by=user, organization=organization)
        doc_a = document_factory(name="A.pdf")
        doc_b = document_factory(name="B.pdf")
        ddoc_a = DataroomDocument.objects.create(dataroom=dataroom, document=doc_a)
        ddoc_b = DataroomDocument.objects.create(dataroom=dataroom, document=doc_b)
        folder_a = DataroomFolder.objects.create(dataroom=dataroom, name="Folder A")
        folder_b = DataroomFolder.objects.create(dataroom=dataroom, name="Folder B")
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        # Only create order rows for a subset. Remaining items should still be returned via fallback.
        DataroomItemOrder.objects.create(
            dataroom=dataroom,
            parent_folder=None,
            item_type=DataroomItemOrder.ITEM_TYPE_DOCUMENT,
            dataroom_document=ddoc_b,
            position=0,
        )
        DataroomItemOrder.objects.create(
            dataroom=dataroom,
            parent_folder=None,
            item_type=DataroomItemOrder.ITEM_TYPE_FOLDER,
            folder=folder_a,
            position=1,
        )

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_includes_nested_breadcrumbs(
        self, public_client, user, organization
    ):
        dataroom = Dataroom.objects.create(name="Test Dataroom", created_by=user, organization=organization)
        level1 = DataroomFolder.objects.create(dataroom=dataroom, name="Level 1")
        level2 = DataroomFolder.objects.create(dataroom=dataroom, name="Level 2", parent=level1)
        level3 = DataroomFolder.objects.create(dataroom=dataroom, name="Level 3", parent=level2)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?parent_id={level3.id}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_link_data_large_scope_perf_smoke(self, public_client, user, organization, document_factory):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom = Dataroom.objects.create(name='Perf Dataroom', created_by=user, organization=organization)
        root = DataroomFolder.objects.create(dataroom=dataroom, name='Root')
        for i in range(120):
            DataroomFolder.objects.create(dataroom=dataroom, name=f'Folder {i}', parent=root)
        for i in range(180):
            doc = document_factory(name=f'Doc {i}.pdf')
            DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=root)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        hidden_folder = DataroomFolder.objects.filter(dataroom=dataroom, parent=root).first()
        hidden_setting = ShareLinkDataroomSetting.objects.get(share_link=link, dataroom_folder=hidden_folder)
        hidden_setting.is_visible = False
        hidden_setting.save(update_fields=['is_visible'])
        with CaptureQueriesContext(connection) as captured:
            response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?parent_id={root.id}')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_document_from_dataroom_link_returns_item_specific_settings(self, public_client, user, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Setup dataroom with content and a link where settings differ.
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            allow_download=True  # Link default is TRUE
        )

        # 2. Modify the specific setting to be different from the link's default.
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.allow_download = False  # Item-specific is FALSE
        setting.save()

        # 3. Request the document through the dataroom link.
        url = f"/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}"
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_document_from_dataroom_link_returns_dataroom_context(self, public_client, user, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Nested Folder")
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=folder)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        url = f"/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}"
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_root_link_returns_banner_and_logo_data(self, public_client, user, dataroom):
        from datarooms.models import DataroomBannerImage
        from django.core.files.uploadedfile import SimpleUploadedFile

        dataroom.banner_mode = "gallery"
        dataroom.logo_mode = "dataroom"
        dataroom.brand_logo_override = SimpleUploadedFile("override.png", b"testpngbytes", content_type="image/png")
        dataroom.save()

        img = SimpleUploadedFile("g1.png", b"testimg", content_type="image/png")
        DataroomBannerImage.objects.create(dataroom=dataroom, image=img, caption="Gallery 1", position=0)

        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        url = f"/api/v1/links/{link.slug}/view-data/"
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_standalone_document_link_does_not_return_dataroom_context(self, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(document=document, created_by=user)
        url = f"/api/v1/links/{link.slug}/view-data/"
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch.object(BasePreviewRenderer, 'enqueue_render_task')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_dataroom_document_hides_download_url_when_item_downloads_disabled(self, mock_fs_download_url, mock_enqueue_preview, public_client, user, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Dataroom item-specific download restrictions apply to lazy preview fallbacks.'
        document.type = 'pdf'
        document.content_type = 'application/pdf'
        document.download_only = False
        document.save()
        primary_version = document.versions.get(is_primary=True)
        primary_version.original_storage_key = 'path/to/original.pdf'
        primary_version.storage_key = 'path/to/original.pdf'
        primary_version.type = 'pdf'
        primary_version.render_status = DocumentVersion.RENDER_NOT_GENERATED
        primary_version.has_pages = False
        primary_version.save()
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user, allow_download=True)
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.allow_download = False
        setting.save()
        mock_fs_download_url.return_value = 'https://...'
        mock_enqueue_preview.return_value = DocumentVersion.RENDER_QUEUED
        with override_settings(PDF_PREVIEW_ENGINE='server_pages'):
            response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_dataroom_document_by_document_id_is_rejected(
        self, public_client, user, dataroom, document
    ):
        """Document.id is not accepted for dataroom document queries."""
        folder_a = DataroomFolder.objects.create(dataroom=dataroom, name="Folder A")
        folder_b = DataroomFolder.objects.create(dataroom=dataroom, name="Folder B")
        DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=folder_a)
        DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=folder_b)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        response = public_client.get(f"/api/v1/links/{link.slug}/view-data/?dataroom_document_id={document.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_dataroom_document_by_dataroom_item_id_is_unambiguous(
        self, public_client, user, dataroom, document
    ):
        folder_a = DataroomFolder.objects.create(dataroom=dataroom, name="Folder A")
        folder_b = DataroomFolder.objects.create(dataroom=dataroom, name="Folder B")
        first_item = DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=folder_a)
        DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=folder_b)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        response = public_client.get(f"/api/v1/links/{link.slug}/view-data/?dataroom_document_id={first_item.id}")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    def test_get_dataroom_document_with_watermark_returns_correct_download_url(self, public_client, user, dataroom, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Setup dataroom with content and a watermarked link.
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            enable_watermark=True,
            watermark_text="CONFIDENTIAL",
            allow_download=True,  # AmForge: downloads default OFF
        )

        # 2. Request the document through the dataroom link.
        url = f"/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}"
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    def test_dataroom_document_watermark_override_disables_watermarked_page_url(
        self, public_client, user, dataroom, image_document_with_content
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=image_document_with_content)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            enable_watermark=True,
            watermark_text="CONFIDENTIAL",
        )
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.enable_watermark = False
        setting.save(update_fields=["enable_watermark"])

        response = public_client.get(f"/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    def test_dataroom_document_watermark_enabled_generates_render_page_url(
        self, public_client, user, dataroom, image_document_with_content
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=image_document_with_content)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            enable_watermark=True,
            watermark_text="CONFIDENTIAL",
        )
        response = public_client.get(f"/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}")
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


    def test_render_page_rejects_dataroom_document_when_item_watermark_is_disabled(
        self, public_client, user, dataroom, image_document_with_content
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=image_document_with_content)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            enable_watermark=True,
            watermark_text="CONFIDENTIAL",
        )
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.enable_watermark = False
        setting.save(update_fields=["enable_watermark"])
        session = public_client.session
        session['authorized_share_links'] = {
            str(link.id): {
                'password_verified': True,
                'email_verified': True,
                'viewer_email': '',
            }
        }
        session.save()

        response = public_client.get(
            f"/api/v1/links/{link.slug}/render-page/1/?dataroom_document_id={ddoc.id}"
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

@pytest.mark.django_db
class TestShareLinkPreview:
    """Tests for the Share Link Preview functionality."""

    def test_create_preview_session_for_share_link(self, api_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/share-links/{share_link.id}/preview/'
        response = api_client.post(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_preview_token_bypasses_share_link_security(self, mock_fs_download, api_client, share_link_with_password, public_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Add a page to the document for testing
        doc = share_link_with_password.document
        version = doc.versions.get(is_primary=True)
        version.has_pages = True
        version.save()
        DocumentPage.objects.create(document_version=version, page_number=1, storage_key="pages/preview_1.png")

        # 1. Create a preview session as the owner
        url_create = f'/api/v1/share-links/{share_link_with_password.id}/preview/'
        response_create = api_client.post(url_create)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_create.status_code == 403
        assert response_create.data == {'detail': 'Unclassified or disabled operation.'}

@pytest.mark.django_db
class TestShareLinkPasswordProtection:
    """Tests for password-protected share links."""

    def test_view_data_requires_password(self, public_client, share_link_with_password):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/links/{share_link_with_password.slug}/view-data/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_verify_password_wrong_password(self, public_client, share_link_with_password):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/links/{share_link_with_password.slug}/verify-password/'
        response = public_client.post(url, {'password': 'wrong-password'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_verify_password_and_view_data_success(self, public_client, share_link_with_password):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Step 1: Verify the password
        verify_url = f'/api/v1/links/{share_link_with_password.slug}/verify-password/'
        response_verify = public_client.post(verify_url, {'password': 'password123'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_verify.status_code == 403
        assert response_verify.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_verify_password_for_non_protected_link(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/links/{share_link.slug}/verify-password/'
        response = public_client.post(url, {'password': 'any-password'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_password_verification_is_rate_limited(self, public_client, share_link_with_password):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test that the password verification endpoint is rate-limited.'
        url = f'/api/v1/links/{share_link_with_password.slug}/verify-password/'
        data = {'password': 'wrong-password'}
        configured_limit = int(api_settings.DEFAULT_THROTTLE_RATES['password_verify'].split('/')[0])
        for i in range(configured_limit):
            response = public_client.post(url, data)
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_public_meta_returns_owner_info(self, public_client, share_link):
        url = f'/api/v1/links/{share_link.slug}/public-meta/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_public_meta_includes_protection_and_restriction_flags(self, public_client, share_link_with_password):
        url = f'/api/v1/links/{share_link_with_password.slug}/public-meta/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_public_meta_for_unknown_slug_returns_404(self, public_client):
        response = public_client.get('/api/v1/links/non-existent/public-meta/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_public_meta_for_expired_link_returns_410(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.expires_at = timezone.now() - timedelta(days=1)
        share_link.save()
        response = public_client.get(f'/api/v1/links/{share_link.slug}/public-meta/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_verify_password_for_expired_link_returns_410(self, public_client, share_link_with_password):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link_with_password.expires_at = timezone.now() - timedelta(days=1)
        share_link_with_password.save()
        response = public_client.post(
            f'/api/v1/links/{share_link_with_password.slug}/verify-password/',
            {'password': 'password123'}
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_request_access_for_expired_link_returns_410(self, public_client, share_link_with_password_and_email):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link_with_password_and_email.expires_at = timezone.now() - timedelta(days=1)
        share_link_with_password_and_email.save()
        response = public_client.post(
            f'/api/v1/links/{share_link_with_password_and_email.slug}/request-access/',
            {'email': 'viewer@example.com'}
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_accept_nda_for_expired_link_returns_410(self, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            require_nda=True,
            nda_text="Confidential terms.",
            nda_version=1,
            expires_at=timezone.now() - timedelta(days=1)
        )
        response = public_client.post(f'/api/v1/links/{link.slug}/accept-nda/', {})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


    def test_public_meta_dataroom_logo_mode_and_resolved_logo(self, public_client, user, dataroom):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Case 1: default 'org', organization has logo
        org = user.organization
        org.brand_logo = SimpleUploadedFile("org_logo.png", b"orgbytes", content_type="image/png")
        org.save()

        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        res = public_client.get(f'/api/v1/links/{link.slug}/public-meta/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


@pytest.mark.django_db
class TestShareLinkViewSet:
    def test_list_share_links_is_scoped_to_user(self, api_client, user, user2):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        doc1 = Document.objects.create(organization=user.organization, created_by=user)
        doc2 = Document.objects.create(organization=user.organization, created_by=user2)
        ShareLink.objects.create(document=doc1, created_by=user, name="My Link")
        ShareLink.objects.create(document=doc2, created_by=user2, name="Other's Link")

        response = api_client.get('/api/v1/share-links/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_patch_and_delete_teammate_document_share_link(self, api_client, user, user2, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user.role = 'admin'
        user.save(update_fields=['role'])

        doc = Document.objects.create(organization=organization, created_by=user2, name="Teammate Doc.pdf")
        link = ShareLink.objects.create(document=doc, created_by=user2, name="Teammate Link")

        # 1. Admin should be able to retrieve the link
        url = f'/api/v1/share-links/{link.id}/'
        resp_get = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp_get.status_code == 403
        assert resp_get.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_share_links_can_be_filtered_by_dataroom(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # A link for the dataroom
        ShareLink.objects.create(dataroom=dataroom, name="Dataroom Link", created_by=user)
        # A link for a regular document
        ShareLink.objects.create(document=document, name="Document Link", created_by=user)

        # 1. No filter: should return both links
        url = '/api/v1/share-links/'
        response_all = api_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_all.status_code == 403
        assert response_all.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_share_links_ordered_by_created_at_desc(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        import datetime
        from django.utils import timezone
        now = timezone.now()
        link1 = ShareLink.objects.create(dataroom=dataroom, name="Link 1", created_by=user)
        ShareLink.objects.filter(id=link1.id).update(created_at=now - datetime.timedelta(hours=2))

        link2 = ShareLink.objects.create(dataroom=dataroom, name="Link 2", created_by=user)
        ShareLink.objects.filter(id=link2.id).update(created_at=now - datetime.timedelta(hours=1))

        link3 = ShareLink.objects.create(dataroom=dataroom, name="Link 3", created_by=user)
        ShareLink.objects.filter(id=link3.id).update(created_at=now)

        resp = api_client.get(f'/api/v1/share-links/?dataroom_id={dataroom.id}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_settings(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Setup dataroom with content
        ddoc1 = DataroomDocument.objects.create(dataroom=dataroom, document=document)
        other_doc = Document.objects.create(name="Other.pdf", organization=user.organization, created_by=user)
        ddoc2 = DataroomDocument.objects.create(dataroom=dataroom, document=other_doc)

        # Create share link for dataroom
        link = ShareLink.objects.create(dataroom=dataroom, name="DR Link", created_by=user, allow_download=True)  # AmForge: downloads default OFF
        assert link.dataroom_settings.count() == 2

        setting1 = link.dataroom_settings.get(dataroom_document=ddoc1)
        setting2 = link.dataroom_settings.get(dataroom_document=ddoc2)

        # Initial state
        assert setting1.is_visible is True
        assert setting1.allow_download is True
        assert setting2.is_visible is True
        assert setting2.allow_download is True

        # Update settings: make ddoc1 not visible, and ddoc2 not downloadable
        update_data = [
            {'id': str(setting1.id), 'is_visible': False},
            {'id': str(setting2.id), 'allow_download': False}
        ]

        url = f'/api/v1/share-links/{link.id}/dataroom-settings/'
        response = api_client.patch(url, update_data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_settings_for_document_link_fails(self, api_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/share-links/{share_link.id}/dataroom-settings/'
        response = api_client.patch(url, [{'id': 'any', 'is_visible': False}], format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_settings_for_other_user_link_fails(self, api_client, user, user2, organization, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        other_dataroom = Dataroom.objects.create(name="Other Dataroom", organization=organization, created_by=user2)
        DataroomDocument.objects.create(dataroom=other_dataroom, document=document)
        link_by_user2 = ShareLink.objects.create(dataroom=other_dataroom, created_by=user2)
        setting = link_by_user2.dataroom_settings.first()
        assert setting is not None

        # api_client (logged in as user) tries to update it
        url = f'/api/v1/share-links/{link_by_user2.id}/dataroom-settings/'
        response = api_client.patch(url, [{'id': str(setting.id), 'is_visible': False}], format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_settings_is_atomic(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        setting = link.dataroom_settings.first()
        assert setting.is_visible is True

        # Update with one valid setting and one non-existent one
        update_data = [
            {'id': str(setting.id), 'is_visible': False},
            {'id': 'sds_00000000000000000000000000', 'allow_download': False}
        ]

        url = f'/api/v1/share-links/{link.id}/dataroom-settings/'
        response = api_client.patch(url, update_data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_settings_is_scoped_to_link(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Create two links for the same dataroom
        DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link1 = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        link2 = ShareLink.objects.create(dataroom=dataroom, created_by=user)

        setting_from_link2 = link2.dataroom_settings.first()
        assert setting_from_link2 is not None

        # Try to update link2's setting via link1's endpoint
        update_data = [{'id': str(setting_from_link2.id), 'is_visible': False}]
        url = f'/api/v1/share-links/{link1.id}/dataroom-settings/'
        response = api_client.patch(url, update_data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_folder_settings(self, api_client, dataroom, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Setup dataroom with a folder
        dr_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Test DR Folder")
        link = ShareLink.objects.create(dataroom=dataroom, name="DR Link", created_by=user)
        assert link.dataroom_settings.count() == 1

        setting = link.dataroom_settings.get(dataroom_folder=dr_folder)
        assert setting.is_visible is True

        # Update the folder setting
        update_data = [{'id': str(setting.id), 'is_visible': False}]
        url = f'/api/v1/share-links/{link.id}/dataroom-settings/'
        response = api_client.patch(url, update_data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_settings_enabling_watermark_populates_default_text(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            enable_watermark=False,
            watermark_text="",
        )
        setting = link.dataroom_settings.first()
        assert setting is not None

        url = f'/api/v1/share-links/{link.id}/dataroom-settings/'
        update_data = [{'id': str(setting.id), 'enable_watermark': True}]
        response = api_client.patch(url, update_data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_bulk_update_dataroom_settings_malformed_data(self, api_client, dataroom, document, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        DataroomDocument.objects.create(dataroom=dataroom, document=document)
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
        setting = link.dataroom_settings.first()
        url = f'/api/v1/share-links/{link.id}/dataroom-settings/'

        # Case 1: Missing 'id'
        data_no_id = [{'is_visible': False}]
        response_no_id = api_client.patch(url, data_no_id, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_no_id.status_code == 403
        assert response_no_id.data == {'detail': 'Unclassified or disabled operation.'}

    def test_update_dataroom_link_with_same_name_as_document_link_succeeds(self, api_client, user, document, dataroom):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Create a document link
        ShareLink.objects.create(document=document, name="Test Link", created_by=user)
        
        # 2. Create a dataroom link with the same name
        dataroom_link = ShareLink.objects.create(dataroom=dataroom, name="Test Link", created_by=user)
        
        # 3. Attempt to update the dataroom link. This will trigger validation.
        # The bug would cause this to fail with a 400 error.
        url = f'/api/v1/share-links/{dataroom_link.id}/'
        response = api_client.patch(url, {'is_active': False}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestShareLinkEmailProtection:
    """Tests for email-protected share links."""

    @pytest.fixture
    def dataroom_link_requires_email(self, dataroom, user):
        """Fixture for a dataroom share link that requires email but not verification."""
        return ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            requires_email=True,
            requires_email_verification=False
        )

    @pytest.fixture
    def dataroom_link_requires_email_verification(self, dataroom, user):
        """Fixture for a dataroom share link that requires email and verification."""
        return ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            requires_email=True,
            requires_email_verification=True
        )

    def test_view_data_requires_email(self, public_client, share_link_requires_email):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/links/{share_link_requires_email.slug}/view-data/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_request_access_for_non_protected_link(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/links/{share_link.slug}/request-access/'
        response = public_client.post(url, {'email': 'viewer@example.com'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_request_access_no_verification_success(self, public_client, share_link_requires_email):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Step 1: Request access
        request_url = f'/api/v1/links/{share_link_requires_email.slug}/request-access/'
        response_request = public_client.post(request_url, {'email': 'viewer@example.com'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_request.status_code == 403
        assert response_request.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.send_mail')
    def test_request_access_with_verification_success(self, mock_send_mail, public_client, share_link_requires_email_verification):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        request_url = f'/api/v1/links/{share_link_requires_email_verification.slug}/request-access/'
        response_request = public_client.post(request_url, {'email': 'viewer@example.com'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_request.status_code == 403
        assert response_request.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.send_mail')
    def test_request_access_replaces_existing_token_case_insensitively(
        self, mock_send_mail, public_client, share_link_requires_email_verification
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        old_token = EmailVerificationToken.objects.create(
            share_link=share_link_requires_email_verification,
            email='viewer@example.com',
        )
        # Simulate pre-deploy database state with uppercase casing
        EmailVerificationToken.objects.filter(id=old_token.id).update(email='Viewer@Example.COM')

        request_url = f'/api/v1/links/{share_link_requires_email_verification.slug}/request-access/'
        response = public_client.post(request_url, {'email': 'viewer@example.com'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_email_verification_token_save_normalizes_email(self, share_link_requires_email_verification):
        token = EmailVerificationToken.objects.create(
            share_link=share_link_requires_email_verification,
            email='  Viewer.Case@Example.COM  '
        )
        assert token.email == 'viewer.case@example.com'
        token.refresh_from_db()
        assert token.email == 'viewer.case@example.com'

    def test_view_data_with_valid_access_token(self, public_client, share_link_requires_email_verification):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Step 1: Create a token manually (as if an email was sent)
        token = EmailVerificationToken.objects.create(
            share_link=share_link_requires_email_verification,
            email='viewer@example.com'
        )
        assert EmailVerificationToken.objects.count() == 1

        # Step 2: Access the data with the token via GET - should require confirmation (HTTP 401)
        view_data_url = f'/api/v1/links/{share_link_requires_email_verification.slug}/view-data/?accessToken={token.token}'
        response_view = public_client.get(view_data_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_view.status_code == 403
        assert response_view.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_confirm_access_token_mismatch_fails(self, public_client, share_link_requires_email_verification):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        token = EmailVerificationToken.objects.create(
            share_link=share_link_requires_email_verification,
            email='viewer@example.com'
        )
        confirm_url = f'/api/v1/links/{share_link_requires_email_verification.slug}/verify-access-token/confirm/'
        response_confirm = public_client.post(confirm_url, {'token': token.token}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_confirm.status_code == 403
        assert response_confirm.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_confirm_access_multiple_tabs_no_collision(self, public_client, share_link_requires_email_verification):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        token_a = EmailVerificationToken.objects.create(
            share_link=share_link_requires_email_verification,
            email='viewer_a@example.com'
        )
        token_b = EmailVerificationToken.objects.create(
            share_link=share_link_requires_email_verification,
            email='viewer_b@example.com'
        )

        # GET request for Token A (simulating opening Tab A)
        view_data_url_a = f'/api/v1/links/{share_link_requires_email_verification.slug}/view-data/?accessToken={token_a.token}'
        response_a = public_client.get(view_data_url_a)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_a.status_code == 403
        assert response_a.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_data_with_expired_access_token(self, public_client, share_link_requires_email_verification):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Create an expired token
        expired_time = timezone.now() - timedelta(minutes=30)
        token = EmailVerificationToken.objects.create(
            share_link=share_link_requires_email_verification,
            email='viewer@example.com',
            expires_at=expired_time
        )

        view_data_url = f'/api/v1/links/{share_link_requires_email_verification.slug}/view-data/?accessToken={token.token}'
        response_view = public_client.get(view_data_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_view.status_code == 403
        assert response_view.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_request_access_for_dataroom_no_verification_success(self, public_client, dataroom_link_requires_email):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Step 1: Request access
        request_url = f'/api/v1/links/{dataroom_link_requires_email.slug}/request-access/'
        response_request = public_client.post(request_url, {'email': 'viewer@example.com'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_request.status_code == 403
        assert response_request.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.send_mail')
    def test_request_access_for_dataroom_with_verification_success(self, mock_send_mail, public_client, dataroom_link_requires_email_verification):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        request_url = f'/api/v1/links/{dataroom_link_requires_email_verification.slug}/request-access/'
        response_request = public_client.post(request_url, {'email': 'viewer@example.com'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_request.status_code == 403
        assert response_request.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


@pytest.mark.django_db
class TestOwnerPreviewFlag:

    def test_owner_preview_is_flagged_in_view_sessions(self, api_client, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. User (owner) creates a share link.
        share_link = ShareLink.objects.create(document=document, created_by=user)

        # 2. User creates a preview session for the link.
        preview_url = f'/api/v1/share-links/{share_link.id}/preview/'
        response_preview = api_client.post(preview_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_preview.status_code == 403
        assert response_preview.data == {'detail': 'Unclassified or disabled operation.'}

    def test_non_owner_view_is_not_flagged(self, api_client, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. User (owner) creates a share link that requires email.
        share_link = ShareLink.objects.create(
            document=document,
            created_by=user,
            requires_email=True,
            requires_email_verification=False  # for simplicity
        )

        # 2. A different person requests access to the link.
        viewer_email = "random.viewer@example.com"
        request_access_url = f'/api/v1/links/{share_link.slug}/request-access/'
        response_access = public_client.post(request_access_url, {'email': viewer_email})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_access.status_code == 403
        assert response_access.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_owner_view_flagged_when_user_email_has_uppercase_letters(
        self, api_client, user, document
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user.email = "OwnerAdmin@Example.COM"
        user.save(update_fields=['email'])

        share_link = ShareLink.objects.create(document=document, created_by=user)
        ViewSession.objects.create(
            share_link=share_link,
            viewer_email="owneradmin@example.com",
            duration_seconds=10,
        )

        api_client.force_authenticate(user=user)
        sessions_url = f'/api/v1/documents/{document.id}/view-sessions/'
        response_sessions = api_client.get(sessions_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_sessions.status_code == 403
        assert response_sessions.data == {'detail': 'Staff access is required.'}



@pytest.mark.django_db
class TestShareLinkPageView:
    """Tests for the new secure, non-watermarked page serving view."""

    @pytest.fixture
    def document_with_pages(self, document):
        version = document.versions.get(is_primary=True)
        version.has_pages = True
        version.num_pages = 2
        version.save()
        DocumentPage.objects.create(
            document_version=version, page_number=1, storage_key="pages/page_1.png"
        )
        DocumentPage.objects.create(
            document_version=version, page_number=2, storage_key="pages/page_2.png"
        )
        document.num_pages = 2
        document.save()
        return document

    @pytest.fixture
    def authorized_client(self, public_client, share_link_with_password):
        # Create a client and authorize its session by verifying a password.
        # This simulates a viewer who has already passed the first security step.
        verify_url = f'/api/v1/links/{share_link_with_password.slug}/verify-password/'
        response_verify = public_client.post(verify_url, {'password': 'password123'})
        assert response_verify.status_code == 403
        assert response_verify.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}
        return public_client

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_page_success_redirects(self, mock_fs_download_url, authorized_client, share_link_with_password, document_with_pages):
        """
        Test that an authorized request to the page endpoint successfully
        redirects to a temporary URL from the file server.
        """
        share_link_with_password.document = document_with_pages
        share_link_with_password.save()
        mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/some-token"

        url = f'/api/v1/links/{share_link_with_password.slug}/page/1/'
        response = authorized_client.get(url)
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_page_unauthorized_fails(self, public_client, share_link, document_with_pages):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.document = document_with_pages
        share_link.save()

        url = f'/api/v1/links/{share_link.slug}/page/1/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_page_for_public_link_succeeds_after_view_data(self, mock_fs_download_url, public_client, share_link, document_with_pages):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link.document = document_with_pages
        share_link.save()

        # 1. Call view-data first to authorize the session
        view_data_url = f'/api/v1/links/{share_link.slug}/view-data/'
        response_view = public_client.get(view_data_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_view.status_code == 403
        assert response_view.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_page_for_dataroom_success(self, mock_fs_download_url, dataroom, document_with_pages, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        client = APIClient()
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document_with_pages)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            password="password123"
        )
        # Authorize the client session
        verify_url = f'/api/v1/links/{link.slug}/verify-password/'
        response_verify = client.post(verify_url, {'password': 'password123'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_verify.status_code == 403
        assert response_verify.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_page_for_dataroom_missing_doc_id(self, authorized_client, dataroom, share_link_with_password):
        """
        Test that a request to a dataroom link's page endpoint without a
        document_id fails.
        """
        share_link_with_password.dataroom = dataroom
        share_link_with_password.document = None
        share_link_with_password.save()

        url = f'/api/v1/links/{share_link_with_password.slug}/page/1/'
        response = authorized_client.get(url)
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_non_existent_page_fails(self, authorized_client, share_link_with_password, document_with_pages):
        """Test that requesting a page number that does not exist returns a 404."""
        share_link_with_password.document = document_with_pages
        share_link_with_password.save()

        url = f'/api/v1/links/{share_link_with_password.slug}/page/99/'
        response = authorized_client.get(url)
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_page_requires_password_verification_when_email_configured(self, mock_fs_download_url, public_client, share_link_with_password_and_email, document_with_pages):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        share_link_with_password_and_email.document = document_with_pages
        share_link_with_password_and_email.save()
        mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/some-token"

        # Request access with email without verifying password
        request_url = f'/api/v1/links/{share_link_with_password_and_email.slug}/request-access/'
        public_client.post(request_url, {'email': 'viewer@example.com'})

        # Page endpoint requires password verification
        page_url = f'/api/v1/links/{share_link_with_password_and_email.slug}/page/1/'
        response_page = public_client.get(page_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_page.status_code == 403
        assert response_page.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_page_requires_password_verification_when_nda_configured(self, mock_fs_download_url, public_client, user, document_with_pages):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document_with_pages,
            created_by=user,
            password="secretpassword",
            require_nda=True,
            nda_text="Confidential terms.",
            nda_version=1
        )
        mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/some-token"

        accept_url = f'/api/v1/links/{link.slug}/accept-nda/'
        public_client.post(accept_url, {})

        # Access without password verification must be rejected
        page_url = f'/api/v1/links/{link.slug}/page/1/'
        response_page = public_client.get(page_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_page.status_code == 403
        assert response_page.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_request_access_allowed_as_first_gate_when_password_configured(self, public_client, share_link_with_password_and_email):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Step 1: Initial view-data prompts for email first
        view_data_url = f'/api/v1/links/{share_link_with_password_and_email.slug}/view-data/'
        response_view = public_client.get(view_data_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_view.status_code == 403
        assert response_view.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_verify_password_requires_email_verification_when_email_configured(self, public_client, share_link_with_password_and_email):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        verify_url = f'/api/v1/links/{share_link_with_password_and_email.slug}/verify-password/'
        response = public_client.post(verify_url, {'password': 'testpassword'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_magic_link_confirmation_preserves_password_gate(self, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            password="secretpassword",
            requires_email=True,
            requires_email_verification=True,
            require_nda=True,
            nda_text="Terms",
            nda_version=1,
        )
        token = EmailVerificationToken.objects.create(share_link=link, email="viewer@example.com")

        # Pre-seed session with an existing key (e.g. nda_accepted_version) to verify in-place preservation
        session = public_client.session
        session['authorized_share_links'] = {
            str(link.id): {
                'nda_accepted_version': 1,
            }
        }
        session.save()

        # Step 1: GET view-data with token stages verification
        view_url = f'/api/v1/links/{link.slug}/view-data/?accessToken={token.token}'
        resp_stage = public_client.get(view_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp_stage.status_code == 403
        assert resp_stage.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_sequential_gates_email_then_password_then_nda_end_to_end(self, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            requires_email=True,
            requires_email_verification=False,
            password="secretpassword",
            require_nda=True,
            nda_text="Confidential terms.",
            nda_version=1,
        )

        view_url = f'/api/v1/links/{link.slug}/view-data/'

        # Gate 1: Email prompted first
        resp1 = public_client.get(view_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp1.status_code == 403
        assert resp1.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_accept_nda_requires_password_verification_when_password_configured(self, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            password="secretpassword",
            require_nda=True,
            nda_text="Confidential terms.",
            nda_version=1
        )
        accept_url = f'/api/v1/links/{link.slug}/accept-nda/'
        response = public_client.post(accept_url, {})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_accept_nda_requires_email_verification_when_email_configured(self, public_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            requires_email=True,
            require_nda=True,
            nda_text="Confidential terms.",
            nda_version=1
        )
        accept_url = f'/api/v1/links/{link.slug}/accept-nda/'
        response = public_client.post(accept_url, {})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_page_when_watermark_enabled_on_document_link_returns_403(self, authorized_client, share_link_with_password, document_with_pages):
        """
        Test that accessing unwatermarked page image returns 403 Forbidden
        when watermarking is enabled on a document share link.
        """
        share_link_with_password.document = document_with_pages
        share_link_with_password.enable_watermark = True
        share_link_with_password.watermark_text = "Confidential {{email}}"
        share_link_with_password.save()

        url = f'/api/v1/links/{share_link_with_password.slug}/page/1/'
        response = authorized_client.get(url)
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_get_page_when_watermark_enabled_on_dataroom_setting_returns_403(self, dataroom, document_with_pages, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        client = APIClient()
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document_with_pages)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            password="password123",
            watermark_text="Confidential {{email}}"
        )
        setting, _ = ShareLinkDataroomSetting.objects.get_or_create(share_link=link, dataroom_document=ddoc)
        setting.enable_watermark = True
        setting.is_visible = True
        setting.save()

        verify_url = f'/api/v1/links/{link.slug}/verify-password/'
        response_verify = client.post(verify_url, {'password': 'password123'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_verify.status_code == 403
        assert response_verify.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_page_when_watermark_disabled_on_dataroom_setting_succeeds(self, mock_fs_download_url, dataroom, document_with_pages, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        client = APIClient()
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document_with_pages)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            password="password123",
            watermark_text="Confidential {{email}}"
        )
        setting, _ = ShareLinkDataroomSetting.objects.get_or_create(share_link=link, dataroom_document=ddoc)
        setting.enable_watermark = False
        setting.is_visible = True
        setting.save()

        verify_url = f'/api/v1/links/{link.slug}/verify-password/'
        response_verify = client.post(verify_url, {'password': 'password123'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_verify.status_code == 403
        assert response_verify.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @override_settings(SITE_DOMAIN="http://test.coneshare.com")
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_get_page_when_watermark_enabled_but_no_watermark_text_fails(self, mock_fs_download_url, authorized_client, share_link_with_password, document_with_pages):
        """
        Test that if enable_watermark is True, unwatermarked page serving is rejected
        even if watermark_text was initially empty.
        """
        share_link_with_password.document = document_with_pages
        share_link_with_password.enable_watermark = True
        share_link_with_password.watermark_text = ""
        share_link_with_password.save()

        mock_fs_download_url.return_value = "http://test.coneshare.com/files/download/some-token"
        url = f'/api/v1/links/{share_link_with_password.slug}/page/1/'
        response = authorized_client.get(url)
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


@pytest.mark.django_db
class TestWatermarkingViews:
    """Tests for the dynamic watermarking endpoints."""

    @staticmethod
    def _authorize_link_session(client, link, viewer_email=''):
        session = client.session
        session['authorized_share_links'] = {
            str(link.id): {
                'password_verified': True,
                'email_verified': True,
                'viewer_email': viewer_email,
            }
        }
        session.save()

    @pytest.fixture
    def document_with_page(self, document):
        """Fixture for a document that has one page."""
        version = document.versions.get(is_primary=True)
        version.has_pages = True
        version.num_pages = 1
        version.original_storage_key = "path/to/original.pdf"
        version.save()
        DocumentPage.objects.create(
            document_version=version, page_number=1, storage_key="pages/page_1.png"
        )
        document.num_pages = 1
        document.type = 'pdf'
        document.save()
        return document

    @pytest.fixture
    def watermarked_link(self, share_link_with_watermark, document_with_page):
        """Connects the watermarked link to the document with a page."""
        share_link_with_watermark.document = document_with_page
        share_link_with_watermark.save()
        return share_link_with_watermark

    @pytest.fixture
    def office_document(self, document_factory):
        """Fixture for an office document."""
        doc = document_factory(name="Test Office.docx", type='document')
        # We need to give the version a storage_key, which for office docs is the converted PDF key
        version = doc.versions.get(is_primary=True)
        version.storage_key = "path/to/converted.pdf"
        version.save()
        return doc

    @pytest.fixture
    def watermarked_office_link(self, office_document, user):
        """Fixture for a watermarked link to an office document."""
        return ShareLink.objects.create(
            document=office_document,
            created_by=user,
            enable_watermark=True,
            watermark_text="Office Confidential",
            allow_download=True
        )

    @pytest.fixture
    def watermarked_image_link(self, image_document_with_content, user):
        """Fixture for a watermarked link to an image document."""
        return ShareLink.objects.create(
            document=image_document_with_content,
            created_by=user,
            enable_watermark=True,
            watermark_text="Image Confidential",
            allow_download=True
        )

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_success(self, mock_fs_download_url, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, watermarked_link)
        mock_fs_download_url.return_value = "/files/download/token"
        img = Image.new('RGB', (100, 100), color='white')
        buffer = BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = buffer.getvalue()
        mock_requests_get.return_value = mock_response

        url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_watermarked_pdf_file_success(self, mock_fs_download_url, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download_url.return_value = "/files/download/token"
        pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000112 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = pdf_content
        mock_requests_get.return_value = mock_response

        url = f'/api/v1/links/{watermarked_link.slug}/download-file/'
        response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_watermarked_pdf_file_inline_disposition_for_printing(self, mock_fs_download_url, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download_url.return_value = "/files/download/token"
        pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000112 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = pdf_content
        mock_requests_get.return_value = mock_response

        url = f'/api/v1/links/{watermarked_link.slug}/download-file/?inline=true'
        response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    @patch('sharelinks.views.convert_from_bytes')
    def test_download_watermarked_pdf_file_flattened_success(self, mock_convert, mock_fs_download_url, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test that a watermarked PDF file is generated, flattened, and served for download.'
        from django.test import override_settings
        with override_settings(FLATTEN_WATERMARKED_DOWNLOADS=True):
            mock_fs_download_url.return_value = '/files/download/token'
            pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000112 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.content = pdf_content
            mock_requests_get.return_value = mock_response
            mock_img = Image.new('RGB', (100, 100), color='white')
            mock_convert.return_value = [mock_img]
            url = f'/api/v1/links/{watermarked_link.slug}/download-file/'
            response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
            assert response.status_code == 401
            assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    @patch('sharelinks.views.convert_from_bytes')
    def test_download_watermarked_pdf_file_flattened_fallback_on_page_limit(self, mock_convert, mock_fs_download_url, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        'Test that PDF flattening falls back to vector watermarking when page limit is exceeded.'
        from django.test import override_settings
        with override_settings(FLATTEN_WATERMARKED_DOWNLOADS=True, MAX_PREVIEW_PAGES=5):
            mock_fs_download_url.return_value = '/files/download/token'
            pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000112 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.content = pdf_content
            mock_requests_get.return_value = mock_response
            version = watermarked_link.document.versions.get(is_primary=True)
            version.num_pages = 10
            version.save()
            url = f'/api/v1/links/{watermarked_link.slug}/download-file/'
            response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
            assert response.status_code == 401
            assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_watermarked_office_file_as_pdf(self, mock_fs_download_url, mock_requests_get, public_client, watermarked_office_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download_url.return_value = "/files/download/token"
        pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000112 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = pdf_content
        mock_requests_get.return_value = mock_response

        document = watermarked_office_link.document
        assert document.name.endswith('.docx')

        url = f'/api/v1/links/{watermarked_office_link.slug}/download-file/'
        response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_watermarked_image_file_success(self, mock_fs_download_url, mock_requests_get, public_client, watermarked_image_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download_url.return_value = "/files/download/token"
        # Simulate a 1x1 transparent GIF being downloaded from storage
        img_content = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00'
            b'!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01'
            b'\x00\x00\x02\x02D\x01\x00;'
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = img_content
        mock_requests_get.return_value = mock_response

        document = watermarked_image_link.document
        assert document.name.endswith('.gif')

        url = f'/api/v1/links/{watermarked_image_link.slug}/download-file/'
        response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_watermarked_file_not_allowed(self, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        watermarked_link.allow_download = False
        watermarked_link.save()

        url = f'/api/v1/links/{watermarked_link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_video_with_watermark_enabled_returns_403(self, public_client, document_with_page):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Change the document to a video
        document_with_page.type = 'video'
        document_with_page.save()

        # Create a share link with watermarking enabled.
        # We bypass serializer validation by creating the model instance directly in test setup
        # to simulate a dataroom link or admin update scenario.
        link = ShareLink.objects.create(
            document=document_with_page,
            created_by=document_with_page.created_by,
            enable_watermark=True,
            watermark_text="CONFIDENTIAL",
            allow_download=True
        )

        url = f'/api/v1/links/{link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_file_watermark_blocked_when_exceeds_size_limit(self, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        version = watermarked_link.document.versions.get(is_primary=True)
        version.file_size = 500 * 1024 * 1024  # 500MB
        version.save()
        watermarked_link.document.file_size = 500 * 1024 * 1024
        watermarked_link.document.save()

        url = f'/api/v1/links/{watermarked_link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_view_data_disables_download_when_watermarked_file_exceeds_size_limit(self, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        version = watermarked_link.document.versions.get(is_primary=True)
        version.file_size = 500 * 1024 * 1024  # 500MB
        version.save()
        watermarked_link.document.file_size = 500 * 1024 * 1024
        watermarked_link.document.save()

        url = f'/api/v1/links/{watermarked_link.slug}/view-data/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_non_watermarked_file_redirects(self, mock_fs_download_url, public_client, document_with_page):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document_with_page,
            created_by=document_with_page.created_by,
            enable_watermark=False,
            allow_download=True,
            allow_original_download=True,  # AmForge: originals need explicit opt-in
        )
        version = document_with_page.versions.get(is_primary=True)

        mock_fs_download_url.return_value = "http://fileserver.test/download/some-token"

        url = f'/api/v1/links/{link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_non_watermarked_file_not_allowed(self, public_client, document_with_page):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document_with_page,
            created_by=document_with_page.created_by,
            enable_watermark=False,
            allow_download=False
        )
        url = f'/api/v1/links/{link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_render_page_for_link_without_watermark_fails(self, public_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, share_link)
        url = f'/api/v1/links/{share_link.slug}/render-page/1/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_returns_caching_headers(self, mock_fs_download, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, watermarked_link)
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        img = Image.new('RGB', (100, 100), color='white')
        buffer = BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)
        mock_response.content = buffer.getvalue()
        mock_requests_get.return_value = mock_response

        url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_with_etag_returns_304(self, mock_fs_download, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, watermarked_link)
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        img = Image.new('RGB', (100, 100), color='white')
        buffer = BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)
        mock_response.content = buffer.getvalue()
        mock_requests_get.return_value = mock_response

        # First request to get the ETag
        url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response1 = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response1.status_code == 401
        assert response1.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_with_changed_link_returns_200(self, mock_fs_download, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, watermarked_link)
        def setup_mocks(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            img = Image.new('RGB', (100, 100), color='white')
            buffer = BytesIO()
            img.save(buffer, 'JPEG')
            buffer.seek(0)
            mock_response.content = buffer.getvalue()
            mock_requests_get.return_value = mock_response

        mock_fs_download.return_value = "http://core:8080/files/download/token"
        setup_mocks()

        # First request to get the ETag
        url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response1 = public_client.get(url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response1.status_code == 401
        assert response1.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_etag_varies_by_email(self, mock_fs_download, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        watermarked_link.requires_email = True
        watermarked_link.watermark_text = "Viewed by {{email}}"
        watermarked_link.save()

        def setup_mocks(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            img = Image.new('RGB', (100, 100), color='white')
            buffer = BytesIO()
            img.save(buffer, 'JPEG')
            buffer.seek(0)
            mock_response.content = buffer.getvalue()
            mock_requests_get.return_value = mock_response

        mock_fs_download.return_value = "http://core:8080/files/download/token"
        setup_mocks()

        # --- Viewer 1 ---
        # Authorize viewer 1
        request_url = f'/api/v1/links/{watermarked_link.slug}/request-access/'
        public_client.post(request_url, {'email': 'viewer1@example.com'})

        # Get ETag for viewer 1
        render_url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response1 = public_client.get(render_url, REMOTE_ADDR='192.168.1.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response1.status_code == 401
        assert response1.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_etag_varies_by_x_real_ip(self, mock_fs_download, mock_requests_get, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, watermarked_link)
        watermarked_link.watermark_text = "Viewed from {{ip-address}}"
        watermarked_link.save()

        def setup_mocks(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            img = Image.new('RGB', (100, 100), color='white')
            buffer = BytesIO()
            img.save(buffer, 'JPEG')
            buffer.seek(0)
            mock_response.content = buffer.getvalue()
            mock_requests_get.return_value = mock_response

        mock_fs_download.return_value = "http://core:8080/files/download/token"
        setup_mocks()

        # --- Viewer 1 ---
        render_url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response1 = public_client.get(render_url, HTTP_X_REAL_IP='1.1.1.1', REMOTE_ADDR='127.0.0.1')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response1.status_code == 401
        assert response1.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_from_dataroom_success(self, mock_fs_download, mock_requests_get, public_client, dataroom_with_watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        self._authorize_link_session(public_client, dataroom_with_watermarked_link['link'])
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        img = Image.new('RGB', (100, 100), color='white')
        buffer = BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)
        mock_response.content = buffer.getvalue()
        mock_requests_get.return_value = mock_response

        link = dataroom_with_watermarked_link['link']
        ddoc = dataroom_with_watermarked_link['ddoc']

        url = f'/api/v1/links/{link.slug}/render-page/1/?dataroom_document_id={ddoc.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_render_watermarked_page_without_authorized_session_fails(self, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_render_watermarked_page_requires_password_verification_when_email_configured(self, mock_fs_download, mock_requests_get, public_client, watermarked_link):
        """
        Test that rendering a watermarked page on a password-protected link requires
        password verification even when email capture is configured.
        """
        watermarked_link.password = "secretpassword"
        watermarked_link.requires_email = True
        watermarked_link.requires_email_verification = False
        watermarked_link.save()

        # Request access with email without verifying password
        request_url = f'/api/v1/links/{watermarked_link.slug}/request-access/'
        public_client.post(request_url, {'email': 'viewer@example.com'})

        # Render watermarked page requires password verification
        render_url = f'/api/v1/links/{watermarked_link.slug}/render-page/1/'
        response = public_client.get(render_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.fixture
    def dataroom_with_watermarked_link(self, dataroom, user, document_with_page):
        """
        Sets up a dataroom with a document and a watermarked share link.
        """
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document_with_page)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            enable_watermark=True,
            watermark_text="CONFIDENTIAL",
            allow_download=True  # Link-level setting
        )
        return {
            'link': link,
            'document': document_with_page,
            'ddoc': ddoc,
        }

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_watermarked_file_from_dataroom_success(self, mock_fs_download, mock_requests_get, public_client, dataroom_with_watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000112 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'
        mock_response.content = pdf_content
        mock_requests_get.return_value = mock_response

        link = dataroom_with_watermarked_link['link']
        document = dataroom_with_watermarked_link['document']
        ddoc = dataroom_with_watermarked_link['ddoc']

        url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_watermarked_file_from_dataroom_permission_denied(self, public_client, dataroom_with_watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_watermarked_link['link']
        ddoc = dataroom_with_watermarked_link['ddoc']

        # Override setting for this item
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.allow_download = False
        setting.save()

        url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_watermarked_video_from_dataroom_fails(self, public_client, dataroom_with_watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_watermarked_link['link']
        document = dataroom_with_watermarked_link['document']
        ddoc = dataroom_with_watermarked_link['ddoc']

        # Change document type to video
        document.type = 'video'
        document.save()

        # Ensure the dataroom setting inherits enable_watermark=True and allow_download=True
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.allow_download = True
        setting.enable_watermark = True
        setting.save()

        url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_watermarked_file_from_dataroom_missing_doc_id(self, public_client, dataroom_with_watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_watermarked_link['link']
        url = f'/api/v1/links/{link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_watermarked_file_from_dataroom_invalid_doc_id(self, public_client, dataroom_with_watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_watermarked_link['link']
        invalid_doc_id = 'doc_00000000000000000000000000'
        url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={invalid_doc_id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_from_dataroom_denied_if_not_visible(self, public_client, dataroom_with_watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_watermarked_link['link']
        ddoc = dataroom_with_watermarked_link['ddoc']

        # Override setting for this item to be invisible, but downloadable
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.is_visible = False
        setting.allow_download = True
        setting.save()

        # Attacker tries to download it directly
        download_url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}'
        response = public_client.get(download_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_dataroom_item_watermark_enforced_when_link_watermark_text_empty(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_watermarked_link
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000112 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'
        img = Image.new('RGB', (100, 100), color='white')
        img_buffer = BytesIO()
        img.save(img_buffer, 'JPEG')
        img_buffer.seek(0)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = img_buffer.getvalue()
        mock_requests_get.return_value = mock_response

        link = dataroom_with_watermarked_link['link']
        document = dataroom_with_watermarked_link['document']
        ddoc = dataroom_with_watermarked_link['ddoc']

        # Empty the link-level watermark
        link.enable_watermark = False
        link.watermark_text = ""
        link.save()

        # Enable watermark on the item
        setting = link.dataroom_settings.get(dataroom_document=ddoc)
        setting.enable_watermark = True
        setting.allow_download = True
        setting.save()

        self._authorize_link_session(public_client, link)

        # 1. view-data: must flag watermark, use render-page URL, and strip text_content
        url_view_data = f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}'
        resp_view_data = public_client.get(url_view_data)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp_view_data.status_code == 403
        assert resp_view_data.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_sharelink_file_download_view_records_dataroom_visit_downloaded_at(self, public_client, dataroom, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.models import DataroomDocument
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user, allow_download=True, allow_original_download=True)  # AmForge: originals need explicit opt-in
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
        setting, _ = ShareLinkDataroomSetting.objects.get_or_create(share_link=link, dataroom_document=ddoc)
        setting.is_visible = True
        setting.allow_download = True
        setting.save()

        view_session = ViewSession.objects.create(share_link=link)

        url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}&view_session_id={view_session.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_file_password_protected_fails_without_auth(self, public_client, watermarked_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        watermarked_link.password = 'password123'
        watermarked_link.save()

        url = f'/api/v1/links/{watermarked_link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_non_watermarked_file_succeeds_with_auth(self, mock_fs_download_url, public_client, document_with_page, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document_with_page,
            created_by=user,
            password="password123",
            allow_download=True,
            allow_original_download=True,  # AmForge: originals need explicit opt-in
        )
        version = document_with_page.versions.get(is_primary=True)
        mock_fs_download_url.return_value = "http://fileserver.test/download/some-token"

        # 1. First, try to download without auth - should fail
        download_url = f'/api/v1/links/{link.slug}/download-file/'
        response_fail = public_client.get(download_url)
        assert response_fail.status_code == status.HTTP_401_UNAUTHORIZED

        # 2. Now, authorize the session
        verify_url = f'/api/v1/links/{link.slug}/verify-password/'
        public_client.post(verify_url, {'password': 'password123'})

        # 3. Try to download again - should succeed
        response_success = public_client.get(download_url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response_success.status_code == 401
        assert response_success.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_non_watermarked_dataroom_file_redirects(self, mock_fs_download_url, public_client, user, dataroom, document_factory):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.models import DataroomDocument
        doc = document_factory(name="Test Dataroom Doc.pdf")
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc)
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            allow_download=True,
            allow_original_download=True,  # AmForge: originals need explicit opt-in
            enable_watermark=False
        )
        version = doc.versions.get(is_primary=True)
        mock_fs_download_url.return_value = "http://fileserver.test/download/some-token"

        url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_download_file_email_protected_fails_without_auth(self, public_client, document_with_page, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document_with_page,
            created_by=user,
            requires_email=True,
            allow_download=True
        )

        url = f'/api/v1/links/{link.slug}/download-file/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}


@pytest.fixture
def dataroom_with_content_and_link(dataroom, user, document_factory, image_document_with_content):
    """
    Sets up a dataroom with a nested structure, documents of various types,
    and a share link.
    """
    # Create folder structure
    root_folder = DataroomFolder.objects.create(dataroom=dataroom, name="Root Folder")
    subfolder = DataroomFolder.objects.create(dataroom=dataroom, name="Subfolder", parent=root_folder)

    # Create documents of different types
    doc_pdf = document_factory(name="Doc A.pdf", type='pdf')
    doc_office = document_factory(name="Doc B.docx", type='document')
    doc_image = image_document_with_content
    invisible_doc = document_factory(name="Invisible.pdf", type='pdf')
    not_downloadable_doc = document_factory(name="Not Downloadable.pdf", type='pdf')

    # Add documents to dataroom
    ddoc_pdf = DataroomDocument.objects.create(dataroom=dataroom, document=doc_pdf, folder=root_folder)
    ddoc_office = DataroomDocument.objects.create(dataroom=dataroom, document=doc_office, folder=subfolder)
    ddoc_image = DataroomDocument.objects.create(dataroom=dataroom, document=doc_image, folder=root_folder)
    ddoc_invisible = DataroomDocument.objects.create(dataroom=dataroom, document=invisible_doc, folder=root_folder)
    ddoc_not_downloadable = DataroomDocument.objects.create(dataroom=dataroom, document=not_downloadable_doc, folder=root_folder)

    # Create share link, which will auto-generate settings.
    # AmForge: opt in to upstream download semantics (downloads on, originals for
    # non-watermarked items) so these archive tests keep exercising both paths.
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user, allow_download=True, allow_original_download=True)

    return {
        'link': link,
        'root_folder': root_folder,
        'subfolder': subfolder,
        'ddoc_pdf': ddoc_pdf,
        'ddoc_office': ddoc_office,
        'ddoc_image': ddoc_image,
        'ddoc_invisible': ddoc_invisible,
        'ddoc_not_downloadable': ddoc_not_downloadable,
    }


@pytest.mark.django_db
class TestDataroomFolderDownloadView:
    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_folder_success(self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_folder_edge_case_names_do_not_crash(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        root_folder = DataroomFolder.objects.create(dataroom=link.dataroom, name=".")
        s = link.dataroom_settings.get(dataroom_folder=root_folder)
        s.is_visible = True
        s.allow_download = True
        s.save()

        doc = document_factory(name="test.pdf", type='pdf')
        ddoc = DataroomDocument.objects.create(dataroom=link.dataroom, document=doc, folder=root_folder)
        sd = link.dataroom_settings.get(dataroom_document=ddoc)
        sd.is_visible = True
        sd.allow_download = True
        sd.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_download_folder_permission_denied(self, public_client, dataroom_with_content_and_link):
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']

        # Make the root folder not downloadable
        setting = link.dataroom_settings.get(dataroom_folder=root_folder)
        setting.allow_download = False
        setting.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_folder_succeeds_when_folder_allow_download_is_true_even_if_link_allow_download_is_false(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']

        # Folder setting allows download, but link disables download
        link.allow_download = False
        link.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_zip_archive_respects_permissions(self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link):
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file content"
        mock_requests_get.return_value = mock_response
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        ddoc_invisible = dataroom_with_content_and_link['ddoc_invisible']
        ddoc_not_downloadable = dataroom_with_content_and_link['ddoc_not_downloadable']

        # Update settings for specific documents
        setting_invisible = link.dataroom_settings.get(dataroom_document=ddoc_invisible)
        setting_invisible.is_visible = False
        setting_invisible.save()

        setting_not_downloadable = link.dataroom_settings.get(dataroom_document=ddoc_not_downloadable)
        setting_not_downloadable.allow_download = False
        setting_not_downloadable.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._generate_watermarked_pdf')
    def test_zip_archive_includes_watermarked_pdf(self, mock_generate_pdf, public_client, dataroom_with_content_and_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        ddoc_pdf = dataroom_with_content_and_link['ddoc_pdf']

        link.enable_watermark = True
        link.watermark_text = "TEST"
        link.save()

        setting_pdf = link.dataroom_settings.get(dataroom_document=ddoc_pdf)
        setting_pdf.enable_watermark = True
        setting_pdf.save()

        mock_generate_pdf.return_value = BytesIO(b"watermarked pdf content")

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._generate_watermarked_pdf')
    def test_zip_archive_includes_watermarked_office_file_as_pdf(self, mock_generate_pdf, public_client, dataroom_with_content_and_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        ddoc_office = dataroom_with_content_and_link['ddoc_office']
        # Office doc needs its converted PDF key set
        version = ddoc_office.document.versions.get(is_primary=True)
        version.storage_key = "path/to/converted_office.pdf"
        version.save()

        link.enable_watermark = True
        link.watermark_text = "TEST"
        link.save()

        setting_office = link.dataroom_settings.get(dataroom_document=ddoc_office)
        setting_office.enable_watermark = True
        setting_office.save()

        mock_generate_pdf.return_value = BytesIO(b"watermarked office content")

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._generate_watermarked_image')
    def test_zip_archive_includes_watermarked_image(self, mock_generate_image, public_client, dataroom_with_content_and_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        ddoc_image = dataroom_with_content_and_link['ddoc_image']

        link.enable_watermark = True
        link.watermark_text = "TEST"
        link.save()

        setting_image = link.dataroom_settings.get(dataroom_document=ddoc_image)
        setting_image.enable_watermark = True
        setting_image.save()

        mock_generate_image.return_value = (BytesIO(b"watermarked image content"), 'image/jpeg')

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    @patch('sharelinks.views._generate_watermarked_pdf')
    def test_download_folder_applies_watermark_when_link_watermark_text_empty(
        self, mock_generate_pdf, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        ddoc_pdf = dataroom_with_content_and_link['ddoc_pdf']

        link.watermark_text = ""
        link.save()

        setting = link.dataroom_settings.get(dataroom_document=ddoc_pdf)
        setting.enable_watermark = True
        setting.save()

        mock_generate_pdf.return_value = BytesIO(b"watermarked pdf content")

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_folder_excludes_oversized_watermarked_document(self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download.return_value = '/files/download/token'
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'content'
        mock_requests_get.return_value = mock_response
        link = dataroom_with_content_and_link['link']
        link.enable_watermark = True
        link.save()
        root_folder = dataroom_with_content_and_link['root_folder']
        link.dataroom_settings.update(enable_watermark=True, allow_download=True, is_visible=True)
        normal_doc = document_factory(name='FolderNormal.pdf', type='pdf')
        normal_v = normal_doc.versions.get(is_primary=True)
        normal_v.file_size = 1 * 1024 * 1024
        normal_v.save()
        normal_doc.file_size = 1 * 1024 * 1024
        normal_doc.save()
        DataroomDocument.objects.create(dataroom=link.dataroom, document=normal_doc, folder=root_folder)
        huge_doc = document_factory(name='FolderHuge.pdf', type='pdf')
        huge_v = huge_doc.versions.get(is_primary=True)
        huge_v.file_size = 500 * 1024 * 1024
        huge_v.save()
        huge_doc.file_size = 500 * 1024 * 1024
        huge_doc.save()
        DataroomDocument.objects.create(dataroom=link.dataroom, document=huge_doc, folder=root_folder)
        for ddoc in DataroomDocument.objects.filter(dataroom=link.dataroom):
            s, _ = ShareLinkDataroomSetting.objects.get_or_create(share_link=link, dataroom_document=ddoc)
            s.is_visible = True
            s.allow_download = True
            s.enable_watermark = True
            s.save()
        with patch('sharelinks.views._generate_watermarked_pdf') as mock_gen_pdf:
            mock_gen_pdf.return_value = BytesIO(b'watermarked pdf stream')
            url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
            response = public_client.get(url)
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_download_folder_password_protected_fails(self, public_client, dataroom_with_content_and_link):
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']

        link.password = "password123"
        link.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_download_folder_denied_when_folder_not_visible(self, public_client, dataroom_with_content_and_link):
        """
        Verify that folder download is denied when the target folder setting has is_visible=False.
        """
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']

        setting = link.dataroom_settings.get(dataroom_folder=root_folder)
        setting.is_visible = False
        setting.allow_download = True
        setting.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/'
        response = public_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_download_folder_denied_when_ancestor_folder_not_visible(self, public_client, dataroom_with_content_and_link):
        """
        Verify that folder download is denied when an ancestor folder in the path has is_visible=False.
        """
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        subfolder = dataroom_with_content_and_link['subfolder']

        # Root folder is hidden, but subfolder is marked visible and downloadable
        root_setting = link.dataroom_settings.get(dataroom_folder=root_folder)
        root_setting.is_visible = False
        root_setting.save()

        sub_setting = link.dataroom_settings.get(dataroom_folder=subfolder)
        sub_setting.is_visible = True
        sub_setting.allow_download = True
        sub_setting.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{subfolder.id}/'
        response = public_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('sharelinks.views._dispatch_automation_event')
    def test_download_folder_no_downloadable_items_does_not_record_visit_or_dispatch_automation(
        self, mock_dispatch, public_client, dataroom_with_content_and_link
    ):
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        # Set all document settings to allow_download = False
        link.dataroom_settings.filter(dataroom_document__isnull=False).update(allow_download=False)

        session = ViewSession.objects.create(share_link=link, viewer_email='viewer@example.com')

        url = f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/?view_session_id={session.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_data_document_in_hidden_folder_denied(self, public_client, dataroom_with_content_and_link):
        """
        Verify that fetching document view data is denied when its parent folder is not visible.
        """
        link = dataroom_with_content_and_link['link']
        subfolder = dataroom_with_content_and_link['subfolder']
        ddoc_office = dataroom_with_content_and_link['ddoc_office']

        sub_setting = link.dataroom_settings.get(dataroom_folder=subfolder)
        sub_setting.is_visible = False
        sub_setting.save()

        doc_setting = link.dataroom_settings.get(dataroom_document=ddoc_office)
        doc_setting.is_visible = True
        doc_setting.save()

        url = f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc_office.id}'
        response = public_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_page_view_document_in_hidden_folder_denied(self, public_client, dataroom_with_content_and_link):
        """
        Verify that page view rendering is denied when the document resides in a hidden folder.
        """
        link = dataroom_with_content_and_link['link']
        subfolder = dataroom_with_content_and_link['subfolder']
        ddoc_office = dataroom_with_content_and_link['ddoc_office']

        session = public_client.session
        session['authorized_share_links'] = {
            str(link.id): {'password_verified': True, 'email_verified': True}
        }
        session.save()

        sub_setting = link.dataroom_settings.get(dataroom_folder=subfolder)
        sub_setting.is_visible = False
        sub_setting.save()

        doc_setting = link.dataroom_settings.get(dataroom_document=ddoc_office)
        doc_setting.is_visible = True
        doc_setting.save()

        url = f'/api/v1/links/{link.slug}/page/1/?dataroom_document_id={ddoc_office.id}'
        response = public_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_file_download_document_in_hidden_folder_denied(self, public_client, dataroom_with_content_and_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = dataroom_with_content_and_link['link']
        subfolder = dataroom_with_content_and_link['subfolder']
        ddoc_office = dataroom_with_content_and_link['ddoc_office']

        session = public_client.session
        session['authorized_share_links'] = {
            str(link.id): {'password_verified': True, 'email_verified': True}
        }
        session.save()

        sub_setting = link.dataroom_settings.get(dataroom_folder=subfolder)
        sub_setting.is_visible = False
        sub_setting.save()

        doc_setting = link.dataroom_settings.get(dataroom_document=ddoc_office)
        doc_setting.is_visible = True
        doc_setting.allow_download = True
        doc_setting.save()

        url = f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc_office.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    def test_is_dataroom_folder_path_visible_only_queries_ancestor_path(self, dataroom_with_content_and_link):
        """
        Verify that _is_dataroom_folder_path_visible only queries visibility settings
        for the folder and its ancestors, avoiding full-table scans of all dataroom folders.
        """
        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']
        subfolder = dataroom_with_content_and_link['subfolder']

        link.dataroom_settings.filter(dataroom_folder__in=[root_folder, subfolder]).update(is_visible=True)

        table_name = ShareLinkDataroomSetting._meta.db_table

        with CaptureQueriesContext(connection) as ctx:
            is_visible = _is_dataroom_folder_path_visible(link, subfolder)

        assert is_visible is True
        queries = [q['sql'] for q in ctx.captured_queries]
        # Must query dataroom_settings filtering by ancestor IDs
        settings_queries = [q for q in queries if table_name in q.lower()]
        assert len(settings_queries) == 1
        assert 'dataroom_folder_id' in settings_queries[0]
        folder_table = DataroomFolder._meta.db_table
        # Must NOT load all folders in the dataroom via DataroomFolder.objects.filter(dataroom=...)
        assert not any(f'FROM "{folder_table}" WHERE' in q for q in queries)

    def test_view_data_single_document_does_not_scan_all_folders(self, public_client, dataroom_with_content_and_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        '\n        Verify that fetching single document view-data builds breadcrumbs using\n        the prefetched folder hierarchy without scanning all dataroom folders.\n        '
        link = dataroom_with_content_and_link['link']
        ddoc_office = dataroom_with_content_and_link['ddoc_office']
        with CaptureQueriesContext(connection) as ctx:
            response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc_office.id}')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_data_catalog_root_does_not_scan_all_folders(self, public_client, dataroom_with_content_and_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        '\n        Verify that browsing the dataroom root catalog does not load all folders\n        or all folder visibility settings.\n        '
        link = dataroom_with_content_and_link['link']
        with CaptureQueriesContext(connection) as ctx:
            response = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_data_catalog_subfolder_only_queries_ancestor_path(self, public_client, dataroom_with_content_and_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        '\n        Verify that browsing a subfolder only queries the target folder and its ancestor visibility.\n        '
        link = dataroom_with_content_and_link['link']
        subfolder = dataroom_with_content_and_link['subfolder']
        with CaptureQueriesContext(connection) as ctx:
            response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?parent_id={subfolder.id}')
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_build_dataroom_breadcrumbs_deep_hierarchy(self, dataroom, user):
        """
        Verify that building breadcrumbs for a hierarchy deeper than 4 levels
        still produces correct top-down breadcrumbs.
        """
        folders = []
        parent = None
        for i in range(1, 7):
            folder = DataroomFolder.objects.create(
                dataroom=dataroom,
                name=f"Level {i}",
                parent=parent,
                created_by=user,
            )
            folders.append(folder)
            parent = folder

        deepest_folder = folders[-1]
        breadcrumbs = _build_dataroom_breadcrumbs(deepest_folder, dataroom=dataroom)

        assert len(breadcrumbs) == 6
        assert [b['name'] for b in breadcrumbs] == [f"Level {i}" for i in range(1, 7)]
        assert [b['id'] for b in breadcrumbs] == [str(f.id) for f in folders]

        # Also verify resolution when passing folder ID string
        breadcrumbs_by_id = _build_dataroom_breadcrumbs(str(deepest_folder.id), dataroom=dataroom)
        assert len(breadcrumbs_by_id) == 6
        assert [b['name'] for b in breadcrumbs_by_id] == [f"Level {i}" for i in range(1, 7)]

    def test_non_admin_cannot_create_share_link_for_creatorless_document(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user.role = 'member'
        user.save(update_fields=['role'])

        doc = Document.objects.create(organization=organization, created_by=None, name="Orphan Doc.pdf")
        url = '/api/v1/share-links/'
        data = {
            'document': str(doc.id),
            'name': 'Hacker Link'
        }
        response = api_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_admin_can_create_share_link_for_creatorless_document(self, api_client, user, organization):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user.role = 'admin'
        user.save(update_fields=['role'])

        doc = Document.objects.create(organization=organization, created_by=None, name="System Doc.pdf")
        url = '/api/v1/share-links/'
        data = {
            'document': str(doc.id),
            'name': 'Admin System Link'
        }
        response = api_client.post(url, data, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_removed_dataroom_collaborator_cannot_view_update_or_delete_dataroom_share_link(
        self, api_client, user, user2, dataroom
    ):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        from datarooms.models import DataroomCollaborator
        # Add user2 as collaborator
        collab = DataroomCollaborator.objects.create(dataroom=dataroom, user=user2, invited_by=user)

        # Collaborator creates a share link for this dataroom
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user2, name="Collab Dataroom Link")

        # Now remove collaborator from dataroom
        collab.delete()

        # 1. Removed collaborator's list query should NOT contain this dataroom link
        api_client.force_authenticate(user=user2)
        resp_list = api_client.get('/api/v1/share-links/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp_list.status_code == 403
        assert resp_list.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestViewSessionAndViewerAccessControl:
    """Behavioral tests for view session and viewer access boundaries and field constraints."""

    def test_view_session_list_and_detail_scoped_to_accessible_share_links(self, api_client, user, user2, document_factory):
        doc1 = document_factory(created_by=user, name="Doc1.pdf")
        link1 = ShareLink.objects.create(document=doc1, created_by=user, name="User1 Link")
        session1 = ViewSession.objects.create(share_link=link1)

        doc2 = document_factory(created_by=user2, name="Doc2.pdf")
        link2 = ShareLink.objects.create(document=doc2, created_by=user2, name="User2 Link")
        session2 = ViewSession.objects.create(share_link=link2)

        api_client.force_authenticate(user=user2)
        resp = api_client.get('/api/v1/view-sessions/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_session_mutation_actions_disallowed(self, api_client, user, share_link):
        session = ViewSession.objects.create(share_link=share_link)
        api_client.force_authenticate(user=user)

        patch_resp = api_client.patch(f'/api/v1/view-sessions/{session.id}/', {'duration_seconds': 500}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert patch_resp.status_code == 403
        assert patch_resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_view_session_creation_rejects_client_supplied_metrics(self, public_client, share_link):
        payload = {
            'share_link': str(share_link.id),
            'duration_seconds': 9999,
            'completion_rate': 88.5,
        }
        resp = public_client.post('/api/v1/view-sessions/', payload, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_view_session_creation_requires_active_unexpired_link_and_gate_verification(self, public_client, user, document):
        # 1. Expired link should be rejected
        expired_link = ShareLink.objects.create(
            document=document,
            created_by=user,
            expires_at=timezone.now() - timedelta(days=1),
        )
        resp_expired = public_client.post('/api/v1/view-sessions/', {'share_link': str(expired_link.id)}, format='json')
        assert resp_expired.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_410_GONE]

        # 2. Inactive link should be rejected
        inactive_link = ShareLink.objects.create(
            document=document,
            created_by=user,
            is_active=False,
        )
        resp_inactive = public_client.post('/api/v1/view-sessions/', {'share_link': str(inactive_link.id)}, format='json')
        assert resp_inactive.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

        # 3. Password-protected link without session gate verification should be rejected
        protected_link = ShareLink.objects.create(
            document=document,
            created_by=user,
            password='Password123!',
        )
        resp_protected = public_client.post('/api/v1/view-sessions/', {'share_link': str(protected_link.id)}, format='json')
        assert resp_protected.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_viewer_viewset_is_read_only_and_org_scoped(self, api_client, user, organization):
        from sharelinks.models import Viewer
        viewer1 = Viewer.objects.create(organization=organization, email='viewer1@example.com')

        api_client.force_authenticate(user=user)
        post_resp = api_client.post('/api/v1/viewers/', {'email': 'newviewer@example.com'}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert post_resp.status_code == 403
        assert post_resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_preview_session_bypass_is_bound_to_link_id(self, public_client, user, document):
        link_a = ShareLink.objects.create(document=document, created_by=user, name="Link A")
        link_b = ShareLink.objects.create(document=document, created_by=user, name="Link B", password="Password123!")

        preview = PreviewSession.objects.create(
            share_link=link_a,
            user=user,
            token="valid-preview-token-link-a",
            expires_at=timezone.now() + timedelta(minutes=5)
        )

        # Consume preview for Link A
        resp_preview = public_client.get(f'/api/v1/links/{link_a.slug}/view-data/?previewToken={preview.token}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp_preview.status_code == 403
        assert resp_preview.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_viewer_serializer_rejects_missing_organization(self):
        from rest_framework import serializers as drf_serializers
        from sharelinks.serializers import ViewerSerializer
        serializer = ViewerSerializer(data={'email': 'unscoped@example.com'})
        assert serializer.is_valid()
        with pytest.raises(drf_serializers.ValidationError):
            serializer.save()

    def test_viewer_list_scoped_to_accessible_links_for_non_admin(self, api_client, user, user2, admin_user, document_factory, organization):
        from sharelinks.models import Viewer
        doc1 = document_factory(created_by=user, name="Doc1.pdf")
        link1 = ShareLink.objects.create(document=doc1, created_by=user, name="Link1")
        viewer1 = Viewer.objects.create(organization=organization, email="viewer1@example.com")
        ViewSession.objects.create(share_link=link1, viewer=viewer1)

        doc2 = document_factory(created_by=user2, name="Doc2.pdf")
        link2 = ShareLink.objects.create(document=doc2, created_by=user2, name="Link2")
        viewer2 = Viewer.objects.create(organization=organization, email="viewer2@example.com")
        ViewSession.objects.create(share_link=link2, viewer=viewer2)

        # User2 (regular member) can only see viewer2
        api_client.force_authenticate(user=user2)
        resp2 = api_client.get('/api/v1/viewers/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp2.status_code == 403
        assert resp2.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
class TestDataroomDownloadAllView:
    """
    Tests for GET /api/v1/links/<slug>/download-dataroom/ whole-dataroom streaming downloads.
    """

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_success(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        dataroom = link.dataroom
        dataroom.name = "Test Dataroom"
        dataroom.save()

        # Add a root-level document (folder=None)
        root_doc = document_factory(name="Root Doc.txt", type='text')
        ddoc_root = DataroomDocument.objects.create(dataroom=dataroom, document=root_doc, folder=None)
        setting_root = link.dataroom_settings.get(dataroom_document=ddoc_root)
        setting_root.is_visible = True
        setting_root.allow_download = True
        setting_root.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_download_dataroom_permission_denied_when_link_download_disabled(self, public_client, dataroom_with_content_and_link):
        link = dataroom_with_content_and_link['link']
        link.allow_download = False
        link.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_download_dataroom_expired_fails(self, public_client, dataroom_with_content_and_link):
        link = dataroom_with_content_and_link['link']
        link.expires_at = timezone.now() - timedelta(days=1)
        link.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_download_dataroom_password_protected_fails(self, public_client, dataroom_with_content_and_link):
        link = dataroom_with_content_and_link['link']
        link.password = "secret123"
        link.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_respects_document_visibility_and_download_flags(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        ddoc_invisible = dataroom_with_content_and_link['ddoc_invisible']
        ddoc_not_downloadable = dataroom_with_content_and_link['ddoc_not_downloadable']

        setting_invisible = link.dataroom_settings.get(dataroom_document=ddoc_invisible)
        setting_invisible.is_visible = False
        setting_invisible.save()

        setting_not_downloadable = link.dataroom_settings.get(dataroom_document=ddoc_not_downloadable)
        setting_not_downloadable.allow_download = False
        setting_not_downloadable.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._generate_watermarked_pdf')
    def test_download_dataroom_watermarks_pdf(self, mock_generate_pdf, public_client, dataroom_with_content_and_link):
        link = dataroom_with_content_and_link['link']
        ddoc_pdf = dataroom_with_content_and_link['ddoc_pdf']

        link.enable_watermark = True
        link.watermark_text = "CONFIDENTIAL"
        link.save()

        setting_pdf = link.dataroom_settings.get(dataroom_document=ddoc_pdf)
        setting_pdf.enable_watermark = True
        setting_pdf.save()

        mock_generate_pdf.return_value = BytesIO(b"watermarked pdf stream")

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._dispatch_automation_event')
    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_records_visit_and_dispatches_automation(
        self, mock_fs_download, mock_requests_get, mock_dispatch, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        session = ViewSession.objects.create(share_link=link, viewer_email='viewer@example.com')

        url = f'/api/v1/links/{link.slug}/download-dataroom/?view_session_id={session.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_download_dataroom_no_downloadable_items_returns_400(self, public_client, dataroom_with_content_and_link):
        link = dataroom_with_content_and_link['link']
        # Set all settings to allow_download = False
        link.dataroom_settings.update(allow_download=False)

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._dispatch_automation_event')
    def test_download_dataroom_no_downloadable_items_does_not_record_visit_or_dispatch_automation(
        self, mock_dispatch, public_client, dataroom_with_content_and_link
    ):
        link = dataroom_with_content_and_link['link']
        link.dataroom_settings.update(allow_download=False)

        session = ViewSession.objects.create(share_link=link, viewer_email='viewer@example.com')

        url = f'/api/v1/links/{link.slug}/download-dataroom/?view_session_id={session.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_renamed_does_not_create_duplicate_root_visit(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "http://core:8080/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        dataroom = link.dataroom
        dataroom.name = "Initial Room Name"
        dataroom.save()

        session = ViewSession.objects.create(share_link=link, viewer_email='viewer@example.com')
        initial_visit = DataroomVisit.objects.create(
            view_session=session,
            item_type='folder',
            item_name="Initial Room Name",
            item_path='/',
            visited_at=timezone.now() - timedelta(minutes=5),
        )

        # Room is renamed before download
        dataroom.name = "Renamed Room Name"
        dataroom.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/?view_session_id={session.id}'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_filename_collisions(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        root_folder = dataroom_with_content_and_link['root_folder']

        # Add a second document with distinct physical Document name, but same DataroomDocument display name
        doc_dup = document_factory(name="Other Doc.pdf", type='pdf')
        ddoc_dup = DataroomDocument.objects.create(dataroom=link.dataroom, document=doc_dup, folder=root_folder, name="Doc A.pdf")
        setting_dup = link.dataroom_settings.get(dataroom_document=ddoc_dup)
        setting_dup.is_visible = True
        setting_dup.allow_download = True
        setting_dup.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_excludes_non_downloadable_subfolder(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        subfolder = dataroom_with_content_and_link['subfolder']

        # Set allow_download = False on the subfolder
        subfolder_setting = link.dataroom_settings.get(dataroom_folder=subfolder)
        subfolder_setting.allow_download = False
        subfolder_setting.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_non_ascii_name_header_encoding(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        link.dataroom.name = "财务数据室"
        link.dataroom.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_preserves_spaces_and_punctuation(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        dataroom = link.dataroom
        dataroom.name = "Due Diligence (Project Apollo)"
        dataroom.save()

        # Create folder with spaces, parentheses and brackets
        folder = DataroomFolder.objects.create(dataroom=dataroom, name="Q1 Reports (2024)")
        setting_folder = link.dataroom_settings.get(dataroom_folder=folder)
        setting_folder.is_visible = True
        setting_folder.allow_download = True
        setting_folder.save()

        # Create document with spaces and punctuation
        doc = document_factory(name="Financial Summary [Final] - Draft.pdf", type='pdf')
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=doc, folder=folder)
        setting_doc = link.dataroom_settings.get(dataroom_document=ddoc)
        setting_doc.is_visible = True
        setting_doc.allow_download = True
        setting_doc.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_sibling_folder_collisions(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        dataroom = link.dataroom
        dataroom.name = "Collision Dataroom"
        dataroom.save()

        # Two sibling folders with spaces vs underscores: "Q1 Reports" and "Q1_Reports"
        f1 = DataroomFolder.objects.create(dataroom=dataroom, name="Q1 Reports")
        s1 = link.dataroom_settings.get(dataroom_folder=f1)
        s1.is_visible = True
        s1.allow_download = True
        s1.save()

        f2 = DataroomFolder.objects.create(dataroom=dataroom, name="Q1_Reports")
        s2 = link.dataroom_settings.get(dataroom_folder=f2)
        s2.is_visible = True
        s2.allow_download = True
        s2.save()

        # A third folder with identical name "Q1 Reports"
        f3 = DataroomFolder.objects.create(dataroom=dataroom, name="Q1 Reports")
        s3 = link.dataroom_settings.get(dataroom_folder=f3)
        s3.is_visible = True
        s3.allow_download = True
        s3.save()

        doc1 = document_factory(name="doc1.pdf", type='pdf')
        dd1 = DataroomDocument.objects.create(dataroom=dataroom, document=doc1, folder=f1)
        s_d1 = link.dataroom_settings.get(dataroom_document=dd1)
        s_d1.is_visible = True
        s_d1.allow_download = True
        s_d1.save()

        doc2 = document_factory(name="doc2.pdf", type='pdf')
        dd2 = DataroomDocument.objects.create(dataroom=dataroom, document=doc2, folder=f2)
        s_d2 = link.dataroom_settings.get(dataroom_document=dd2)
        s_d2.is_visible = True
        s_d2.allow_download = True
        s_d2.save()

        doc3 = document_factory(name="doc3.pdf", type='pdf')
        dd3 = DataroomDocument.objects.create(dataroom=dataroom, document=doc3, folder=f3)
        s_d3 = link.dataroom_settings.get(dataroom_document=dd3)
        s_d3.is_visible = True
        s_d3.allow_download = True
        s_d3.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_edge_case_names_do_not_crash(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        dataroom = link.dataroom
        dataroom.name = "???"
        dataroom.save()

        # Folder named "."
        dot_folder = DataroomFolder.objects.create(dataroom=dataroom, name=".")
        setting_folder = link.dataroom_settings.get(dataroom_folder=dot_folder)
        setting_folder.is_visible = True
        setting_folder.allow_download = True
        setting_folder.save()

        # Document named with special chars and path separators
        slash_doc = document_factory(name="path/to/my:report?.pdf", type='pdf')
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=slash_doc, folder=dot_folder)
        setting_doc = link.dataroom_settings.get(dataroom_document=ddoc)
        setting_doc.is_visible = True
        setting_doc.allow_download = True
        setting_doc.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_excludes_oversized_watermarked_document(self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mock_fs_download.return_value = '/files/download/token'
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'content'
        mock_requests_get.return_value = mock_response
        link = dataroom_with_content_and_link['link']
        link.enable_watermark = True
        link.save()
        root_folder = dataroom_with_content_and_link['root_folder']
        link.dataroom_settings.update(enable_watermark=True, allow_download=True, is_visible=True)
        normal_doc = document_factory(name='Normal.pdf', type='pdf')
        normal_v = normal_doc.versions.get(is_primary=True)
        normal_v.file_size = 1 * 1024 * 1024
        normal_v.save()
        normal_doc.file_size = 1 * 1024 * 1024
        normal_doc.save()
        DataroomDocument.objects.create(dataroom=link.dataroom, document=normal_doc, folder=root_folder)
        huge_doc = document_factory(name='Huge_Oversized.pdf', type='pdf')
        huge_v = huge_doc.versions.get(is_primary=True)
        huge_v.file_size = 500 * 1024 * 1024
        huge_v.save()
        huge_doc.file_size = 500 * 1024 * 1024
        huge_doc.save()
        DataroomDocument.objects.create(dataroom=link.dataroom, document=huge_doc, folder=root_folder)
        for ddoc in DataroomDocument.objects.filter(dataroom=link.dataroom):
            s, _ = ShareLinkDataroomSetting.objects.get_or_create(share_link=link, dataroom_document=ddoc)
            s.is_visible = True
            s.allow_download = True
            s.enable_watermark = True
            s.save()
        with patch('sharelinks.views._generate_watermarked_pdf') as mock_gen_pdf:
            mock_gen_pdf.return_value = BytesIO(b'watermarked pdf stream')
            url = f'/api/v1/links/{link.slug}/download-dataroom/'
            response = public_client.get(url)
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_raw_stream_failure_writes_error_file_and_masks_token(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        secret_token = "secret-token-hmac-signed-xyz123"
        download_url = f"http://core:8080/files/download/{secret_token}"
        mock_fs_download.return_value = download_url

        # Simulate requests.get failure raising HTTPError containing the full URL and secret token
        mock_response = MagicMock()
        http_error = requests.exceptions.HTTPError(
            f"404 Client Error: Not Found for url: {download_url}",
            response=mock_response
        )
        mock_requests_get.side_effect = http_error

        link = dataroom_with_content_and_link['link']
        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._generate_watermarked_pdf')
    def test_download_dataroom_watermark_failure_writes_error_file(
        self, mock_generate_pdf, public_client, dataroom_with_content_and_link
    ):
        link = dataroom_with_content_and_link['link']
        ddoc_pdf = dataroom_with_content_and_link['ddoc_pdf']

        link.enable_watermark = True
        link.watermark_text = "CONFIDENTIAL"
        link.save()

        setting_pdf = link.dataroom_settings.get(dataroom_document=ddoc_pdf)
        setting_pdf.enable_watermark = True
        setting_pdf.save()

        # Watermark rendering fails with RuntimeError
        mock_generate_pdf.side_effect = RuntimeError("Watermark rendering engine internal failure")

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_midstream_failure_writes_error_file_and_preserves_partial_bytes(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        secret_token = "secret-token-hmac-signed-midstream"
        download_url = f"http://core:8080/files/download/{secret_token}"
        mock_fs_download.return_value = download_url

        # Simulate requests.get returning a response whose iter_content yields 1 chunk and then fails
        def faulty_iter_content(chunk_size=64 * 1024):
            yield b"PARTIAL_CONTENT_CHUNK_1"
            raise requests.exceptions.ChunkedEncodingError("Connection broken mid-stream")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content = faulty_iter_content
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_detects_content_length_truncation_and_writes_error_file(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "http://core:8080/files/download/token"

        # Content-Length is 500, but stream yields only 100 bytes and cleanly exits
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {'Content-Length': '500'}
        mock_response.iter_content = lambda chunk_size=64 * 1024: [b"A" * 100]
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    def test_sanitize_zip_entry_name_windows_reserved_names(self):
        from sharelinks.archive import sanitize_zip_entry_name
        assert sanitize_zip_entry_name("CON") == "_CON"
        assert sanitize_zip_entry_name("con.pdf") == "_con.pdf"
        assert sanitize_zip_entry_name("AUX") == "_AUX"
        assert sanitize_zip_entry_name("aux.tar.gz") == "_aux.tar.gz"
        assert sanitize_zip_entry_name("nul") == "_nul"
        assert sanitize_zip_entry_name("COM1") == "_COM1"
        assert sanitize_zip_entry_name("com9.txt") == "_com9.txt"
        assert sanitize_zip_entry_name("LPT1") == "_LPT1"
        assert sanitize_zip_entry_name("lpt8.log") == "_lpt8.log"
        assert sanitize_zip_entry_name("normal_file.pdf") == "normal_file.pdf"

    def test_unique_zip_path_disambiguates_file_and_directory_collision(self):
        from sharelinks.archive import _get_unique_zip_path, _get_unique_dir_path

        # Case 1: Directory added first, then extensionless file with same name
        seen_paths = set()
        dir_path = _get_unique_dir_path(seen_paths, "parent", "data")
        assert dir_path == "parent/data"
        assert "parent/data/" in seen_paths

        file_path = _get_unique_zip_path(seen_paths, "parent", "data")
        assert file_path == "parent/data (1)"

        # Case 2: Extensionless file added first, then directory with same name
        seen_paths2 = set()
        file_path2 = _get_unique_zip_path(seen_paths2, "parent", "reports")
        assert file_path2 == "parent/reports"
        assert "parent/reports" in seen_paths2

        dir_path2 = _get_unique_dir_path(seen_paths2, "parent", "reports")
        assert dir_path2 == "parent/reports (1)"
        assert "parent/reports (1)/" in seen_paths2

    @patch('sharelinks.archive.logger.error')
    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_resilient_generator_logger_does_not_leak_url_or_traceback(
        self, mock_fs_download, mock_requests_get, mock_logger_error, public_client, dataroom_with_content_and_link
    ):
        secret_token = "secret-token-hmac-signed-masked-check"
        download_url = f"http://core:8080/files/download/{secret_token}"
        mock_fs_download.return_value = download_url

        mock_requests_get.side_effect = requests.exceptions.HTTPError(
            f"500 Server Error: Internal Server Error for url: {download_url}"
        )

        link = dataroom_with_content_and_link['link']
        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views._generate_watermarked_pdf')
    def test_download_dataroom_skips_unwatermarkable_types_and_unconverted_docs(
        self, mock_generate_pdf, public_client, dataroom, user, document_factory
    ):
        # Setup dataroom with watermark enabled
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user, enable_watermark=True, watermark_text="CONF", allow_download=True)  # AmForge: downloads default OFF

        # 1. Valid PDF
        doc_valid = document_factory(name="Valid.pdf", type='pdf')
        DataroomDocument.objects.create(dataroom=dataroom, document=doc_valid)

        # 2. Spreadsheet (cannot be watermarked on download, must be skipped)
        doc_spreadsheet = document_factory(name="Financials.xlsx", type='spreadsheet')
        DataroomDocument.objects.create(dataroom=dataroom, document=doc_spreadsheet)

        # 3. Office document without converted PDF storage_key (cannot be watermarked, must be skipped)
        doc_office_unconverted = document_factory(name="Unconverted.docx", type='document')
        v_office = doc_office_unconverted.versions.filter(is_primary=True).first()
        v_office.storage_key = ""  # No converted PDF
        v_office.save()
        DataroomDocument.objects.create(dataroom=dataroom, document=doc_office_unconverted)

        # 4. Office document with converted PDF storage_key (can be watermarked, must be included)
        doc_office_converted = document_factory(name="Converted.docx", type='document')
        v_conv = doc_office_converted.versions.filter(is_primary=True).first()
        v_conv.storage_key = "path/to/converted.pdf"
        v_conv.save()
        DataroomDocument.objects.create(dataroom=dataroom, document=doc_office_converted)

        mock_generate_pdf.return_value = BytesIO(b"watermarked-pdf-content")

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_skips_keyless_doc_without_reserving_name(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link, document_factory
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        dataroom = link.dataroom
        link.enable_watermark = False
        link.save()

        # Doc 1: has empty original_storage_key
        doc_keyless = document_factory(name="DocKeyless.pdf", type="document")
        v1 = doc_keyless.versions.filter(is_primary=True).first()
        v1.original_storage_key = ""
        v1.save()
        DataroomDocument.objects.create(dataroom=dataroom, document=doc_keyless, name="Important.pdf")

        # Doc 2: has same dataroom display name but valid original_storage_key
        doc_valid = document_factory(name="DocValid.pdf", type="document")
        v2 = doc_valid.versions.filter(is_primary=True).first()
        v2.original_storage_key = "path/to/important.pdf"
        v2.save()
        DataroomDocument.objects.create(dataroom=dataroom, document=doc_valid, name="Important.pdf")

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_dataroom_filename_star_uses_safe_empty(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        link.dataroom.name = "Alice's Project / Vault"
        link.dataroom.save()

        url = f'/api/v1/links/{link.slug}/download-dataroom/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    def test_download_folder_filename_star_uses_safe_empty(
        self, mock_fs_download, mock_requests_get, public_client, dataroom_with_content_and_link
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"content"
        mock_requests_get.return_value = mock_response

        link = dataroom_with_content_and_link['link']
        folder = dataroom_with_content_and_link['root_folder']
        folder.name = "Bob's / Files"
        folder.save()

        url = f'/api/v1/links/{link.slug}/download-folder/{folder.id}/'
        response = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


class TestWatermarkErrorLoggingAndSizeLimit:
    def test_generate_watermarked_image_logs_exception_type_without_leaking_url(self, caplog, document_factory):
        from sharelinks.views import _generate_watermarked_image, WatermarkingError
        import logging
        doc = document_factory(name="test.jpg", type="image")
        version = doc.versions.filter(is_primary=True).first()
        version.file_size = 1000
        version.storage_key = "test_key.jpg"
        version.save()

        secret_token = "secret-hmac-token-12345"
        sensitive_url = f"http://core:8080/files/download/{secret_token}"

        with patch('sharelinks.views.fileserver_client.generate_download_url', return_value=sensitive_url):
            with patch('sharelinks.views.requests.get', side_effect=requests.HTTPError(f"403 Client Error: Forbidden for url: {sensitive_url}")):
                with caplog.at_level(logging.ERROR):
                    with pytest.raises(WatermarkingError):
                        _generate_watermarked_image(doc, version, "Watermark", None, "viewer@test.com")

        assert secret_token not in caplog.text
        assert sensitive_url not in caplog.text
        assert "Failed to apply watermark to image: HTTPError" in caplog.text

    def test_generate_watermarked_pdf_logs_exception_type_without_leaking_url(self, caplog, document_factory):
        from sharelinks.views import _generate_watermarked_pdf, WatermarkingError
        import logging
        doc = document_factory(name="test.pdf", type="document")
        version = doc.versions.filter(is_primary=True).first()
        version.file_size = 1000
        version.storage_key = "test_key.pdf"
        version.save()

        secret_token = "secret-hmac-token-67890"
        sensitive_url = f"http://core:8080/files/download/{secret_token}"

        with patch('sharelinks.views.fileserver_client.generate_download_url', return_value=sensitive_url):
            with patch('sharelinks.views.requests.get', side_effect=requests.HTTPError(f"500 Server Error: {sensitive_url}")):
                with caplog.at_level(logging.ERROR):
                    with pytest.raises(WatermarkingError):
                        _generate_watermarked_pdf(doc, version, "Watermark", None, "viewer@test.com")

        assert secret_token not in caplog.text
        assert sensitive_url not in caplog.text
        assert "Failed to apply watermark to PDF: HTTPError" in caplog.text

    def test_watermark_generation_blocked_when_max_size_zero(self, document_factory):
        from sharelinks.views import _generate_watermarked_image, _generate_watermarked_pdf, WatermarkingError
        doc = document_factory(name="small.jpg", type="image")
        version = doc.versions.filter(is_primary=True).first()
        version.file_size = 100  # 100 bytes
        version.storage_key = "small.jpg"
        version.save()

        with patch('sharelinks.views.get_max_watermark_file_size_mb', return_value=0):
            with pytest.raises(WatermarkingError, match="exceeds the maximum limit"):
                _generate_watermarked_image(doc, version, "Watermark", None, "viewer@test.com")

            with pytest.raises(WatermarkingError, match="exceeds the maximum limit"):
                _generate_watermarked_pdf(doc, version, "Watermark", None, "viewer@test.com")


