import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework import status

from core.models import Organization, User
from documents.models import Document
from sharelinks.models import ShareLink, ViewSession


@pytest.mark.django_db
class TestDashboardAnalyticsViews:
    """Tests for the dashboard analytics API endpoints."""

    def test_dashboard_summary_view(self, api_client, user, user2, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # 1. Create data for the logged-in user
        link1 = ShareLink.objects.create(document=document, created_by=user, name="Link 1")
        link2 = ShareLink.objects.create(document=document, created_by=user, name="Link 2")

        # Create 12 view sessions to test the limit of 10
        for i in range(12):
            ViewSession.objects.create(
                share_link=link1,
                viewed_at=timezone.now() - timedelta(minutes=i)
            )
        # Create a view for the second link to make it "active"
        ViewSession.objects.create(share_link=link2, viewed_at=timezone.now() - timedelta(hours=1))

        # 2. Create data for another user in the SAME organization that should NOT appear
        doc2 = Document.objects.create(
            name="Doc 2", organization=user.organization, created_by=user2
        )
        link3 = ShareLink.objects.create(document=doc2, created_by=user2, name="Link 3")
        ViewSession.objects.create(share_link=link3)

        # 3. Create data for another user in a different org that should NOT appear
        other_org = Organization.objects.create(name="Other Org")
        other_user = User.objects.create_user(
            username="other@example.com", organization=other_org
        )
        other_doc = Document.objects.create(
            name="Other Doc", organization=other_org, created_by=other_user
        )
        other_link = ShareLink.objects.create(document=other_doc, created_by=other_user)
        ViewSession.objects.create(share_link=other_link)

        # 4. Call the API
        response = api_client.get('/api/v1/analytics/dashboard/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dashboard_summary_does_not_expose_link_password(self, api_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            name="Protected Link",
            password="mysecretpassword123"
        )
        ViewSession.objects.create(share_link=link, viewed_at=timezone.now())

        response = api_client.get('/api/v1/analytics/dashboard/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dashboard_summary_no_n_plus_one_queries(self, api_client, user, document, django_assert_num_queries):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        '\n        Test that dashboard summary executes a bounded number of queries and does not\n        trigger deferred attribute loads (N+1) when sessions have viewers, ip_address,\n        and geo coordinates.\n        '
        from sharelinks.models import Viewer
        viewer1 = Viewer.objects.create(organization=user.organization, email='v1@example.com')
        viewer2 = Viewer.objects.create(organization=user.organization, email='v2@example.com')
        link = ShareLink.objects.create(document=document, created_by=user, name='Query Link')
        for i in range(5):
            ViewSession.objects.create(share_link=link, viewer=viewer1 if i % 2 == 0 else viewer2, viewer_email=f'v{i}@example.com', ip_address='192.168.1.1', latitude=37.7749, longitude=-122.4194, duration_seconds=10 * i, completion_rate=0.5, viewed_at=timezone.now() - timedelta(minutes=i))
        with django_assert_num_queries(4):
            response = api_client.get('/api/v1/analytics/dashboard/')
            assert response.status_code == 403
            assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_dashboard_summary_includes_email_verification_method(self, api_client, user, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link = ShareLink.objects.create(document=document, created_by=user, name="Badge Link")
        vs_verified = ViewSession.objects.create(
            share_link=link,
            viewer_email="verified@example.com",
            email_verification_method="verified",
            viewed_at=timezone.now() - timedelta(minutes=1),
        )
        vs_self_reported = ViewSession.objects.create(
            share_link=link,
            viewer_email="self@example.com",
            email_verification_method="self_reported",
            viewed_at=timezone.now() - timedelta(minutes=2),
        )

        response = api_client.get('/api/v1/analytics/dashboard/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}


    def test_daily_visits_view(self, api_client, share_link, user2):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # user is logged in via api_client fixture
        user = share_link.created_by

        # 1. Create view data for the logged-in user
        ViewSession.objects.create(share_link=share_link, viewed_at=timezone.now() - timedelta(days=1))
        ViewSession.objects.create(share_link=share_link, viewed_at=timezone.now() - timedelta(days=1))
        ViewSession.objects.create(share_link=share_link, viewed_at=timezone.now() - timedelta(days=5))
        ViewSession.objects.create(share_link=share_link, viewed_at=timezone.now() - timedelta(days=35))  # Should be excluded by date

        # 2. Create view data for another user in the same org, which should be excluded
        other_doc = Document.objects.create(
            name="Other Doc", organization=user.organization, created_by=user2
        )
        other_link = ShareLink.objects.create(document=other_doc, created_by=user2)
        ViewSession.objects.create(share_link=other_link, viewed_at=timezone.now() - timedelta(days=1))

        # 3. Call the API
        response = api_client.get('/api/v1/analytics/daily-visits/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_all_links_view(self, api_client, document, user, user2):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Create 12 links for the logged-in user, but only 11 are active
        for i in range(12):
            link = ShareLink.objects.create(document=document, created_by=user, name=f"User 1 Link {i}")
            if i < 11:
                ViewSession.objects.create(share_link=link, viewed_at=timezone.now() - timedelta(hours=i))

        # Create an active link for another user in the same org, which should not appear
        other_doc = Document.objects.create(name="Other Doc", organization=user.organization, created_by=user2)
        other_link = ShareLink.objects.create(document=other_doc, created_by=user2, name="Other User Link")
        ViewSession.objects.create(share_link=other_link, viewed_at=timezone.now())

        # Page 1
        response = api_client.get('/api/v1/analytics/links/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_all_view_sessions_view(self, api_client, share_link, user2):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        user = share_link.created_by
        for i in range(15):
            ViewSession.objects.create(share_link=share_link)

        # Create a view session for another user in the same org, which should not appear
        other_doc = Document.objects.create(name="Other Doc", organization=user.organization, created_by=user2)
        other_link = ShareLink.objects.create(document=other_doc, created_by=user2)
        ViewSession.objects.create(share_link=other_link)

        response = api_client.get('/api/v1/analytics/view-sessions/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

    def test_all_view_sessions_filters(self, api_client, document, share_link, user):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        link2 = ShareLink.objects.create(document=document, created_by=user, name="Link 2")

        session1 = ViewSession.objects.create(share_link=share_link, viewer_email="alice@example.com")
        session2 = ViewSession.objects.create(share_link=link2, viewer_email="bob@example.com")

        # Filter by document_id
        res_doc = api_client.get(f'/api/v1/analytics/view-sessions/?document_id={document.id}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res_doc.status_code == 403
        assert res_doc.data == {'detail': 'Unclassified or disabled operation.'}

    def test_view_session_detail_view(self, api_client, share_link):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        session = ViewSession.objects.create(
            share_link=share_link,
            viewer_email="viewer@example.com",
            country="US",
            city="San Francisco",
            duration_seconds=120
        )

        response = api_client.get(f'/api/v1/analytics/view-sessions/{session.id}/')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'Unclassified or disabled operation.'}

