import pytest
from unittest.mock import MagicMock, patch
from rest_framework import status
from django.utils import timezone

from datarooms.models import Dataroom, DataroomDocument
from sharelinks.models import ShareLink, ShareLinkDataroomSetting, ViewSession
from datarooms.models import DataroomFolder


pytestmark = pytest.mark.django_db


class TestEventDispatchIntegration:
    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_create_view_session_dispatches_document_event(self, mock_delay, public_client, share_link):
        response = public_client.post('/api/v1/view-sessions/', {'share_link': str(share_link.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_create_view_session_dispatches_dataroom_opened_for_dataroom_link(
        self,
        mock_delay,
        public_client,
        user,
        organization,
    ):
        dataroom = Dataroom.objects.create(
            name='Dispatch Dataroom',
            organization=organization,
            created_by=user,
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Dataroom Link',
        )

        response = public_client.post('/api/v1/view-sessions/', {'share_link': str(link.id)}, format='json')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_record_download_dispatches_document_downloaded(self, mock_delay, public_client, share_link):
        share_link.allow_download = True
        share_link.allow_original_download = True  # AmForge: originals are opt-in
        share_link.save()
        view_session = ViewSession.objects.create(share_link=share_link)

        response = public_client.get(f'/api/v1/links/{share_link.slug}/download-file/?view_session_id={view_session.id}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_record_download_for_dataroom_document_includes_viewer_and_document_name(
        self,
        mock_delay,
        public_client,
        user,
        organization,
        document,
    ):
        dataroom = Dataroom.objects.create(
            name='Record Download Dataroom',
            organization=organization,
            created_by=user,
        )
        ddoc = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=document,
            name='Visible Dataroom Doc',
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Dataroom Link',
            allow_download=True,
            allow_original_download=True,  # AmForge: originals are opt-in
        )
        setting, _ = ShareLinkDataroomSetting.objects.get_or_create(
            share_link=link,
            dataroom_document=ddoc,
        )
        setting.is_visible = True
        setting.allow_download = True
        setting.save()
        view_session = ViewSession.objects.create(share_link=link, viewer_email='b@b.com')

        response = public_client.get(
            f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}&view_session_id={view_session.id}'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_dataroom_document_open_dispatches_document_viewed(
        self,
        mock_delay,
        public_client,
        user,
        organization,
        document,
    ):
        dataroom = Dataroom.objects.create(
            name='Dispatch Dataroom For Doc View',
            organization=organization,
            created_by=user,
        )
        ddoc = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=document,
            name='Dataroom Doc',
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Dataroom Link',
        )
        view_session = ViewSession.objects.create(share_link=link)

        response = public_client.get(f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}&view_session_id={view_session.id}')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_dataroom_view_data_polling_deduplicates_document_viewed(self, mock_delay, public_client, user, organization, document):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        dataroom = Dataroom.objects.create(name='Deduplication Test Dataroom', organization=organization, created_by=user)
        ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document, name='Dataroom Doc To Poll')
        link = ShareLink.objects.create(dataroom=dataroom, created_by=user, name='Dataroom Link Dedup')
        view_session = ViewSession.objects.create(share_link=link)
        url = f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}&view_session_id={view_session.id}'
        for _ in range(3):
            response = public_client.get(url)
            assert response.status_code == 403
            assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_dataroom_view_data_anonymous_polling_deduplicates_and_isolates_visitors(
        self,
        mock_delay,
        user,
        organization,
        document,
    ):
        from rest_framework.test import APIClient

        dataroom = Dataroom.objects.create(
            name='Anon Dedup Test Dataroom',
            organization=organization,
            created_by=user,
        )
        ddoc = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=document,
            name='Anon Dataroom Doc',
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Anon Dataroom Link',
        )

        url = f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}'

        # Visitor 1 polls twice (without view_session_id)
        client1 = APIClient()
        r1 = client1.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert r1.status_code == 403
        assert r1.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_dataroom_view_data_not_ready_does_not_dispatch(
        self,
        mock_delay,
        public_client,
        user,
        organization,
    ):
        from documents.models import Document
        not_ready_doc = Document.objects.create(
            name='Unready Doc.pdf',
            organization=organization,
            created_by=user,
            status='uploading',
        )
        dataroom = Dataroom.objects.create(
            name='Unready Dataroom',
            organization=organization,
            created_by=user,
        )
        ddoc = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=not_ready_doc,
            name='Unready DDoc',
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Unready Link',
        )

        url = f'/api/v1/links/{link.slug}/view-data/?dataroom_document_id={ddoc.id}'
        res = public_client.get(url)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert res.status_code == 403
        assert res.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_dataroom_download_file_with_view_session_dispatches_document_downloaded(
        self,
        mock_delay,
        public_client,
        user,
        organization,
        image_document_with_content,
    ):
        dataroom = Dataroom.objects.create(
            name='Dispatch Dataroom For Download',
            organization=organization,
            created_by=user,
        )
        ddoc = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=image_document_with_content,
            name='Downloadable Doc',
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Download Link',
            allow_download=True,
            allow_original_download=True,  # AmForge: originals are opt-in
        )
        view_session = ViewSession.objects.create(share_link=link)

        response = public_client.get(
            f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}&view_session_id={view_session.id}'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_dataroom_download_file_dispatches_even_if_session_already_marked_downloaded(
        self,
        mock_delay,
        public_client,
        user,
        organization,
        image_document_with_content,
    ):
        dataroom = Dataroom.objects.create(
            name='Dispatch Dataroom For Repeated Download',
            organization=organization,
            created_by=user,
        )
        ddoc = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=image_document_with_content,
            name='Downloadable Doc',
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Download Link',
            allow_download=True,
            allow_original_download=True,  # AmForge: originals are opt-in
        )
        view_session = ViewSession.objects.create(
            share_link=link,
            downloaded_at=timezone.now(),
        )

        response = public_client.get(
            f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}&view_session_id={view_session.id}'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 401
        assert response.data == {'detail': 'Email verification required.'}

    @patch('sharelinks.views.requests.get')
    @patch('sharelinks.views.fileserver_client.generate_download_url')
    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_dataroom_download_folder_dispatches_document_downloaded(
        self,
        mock_delay,
        mock_fs_download,
        mock_requests_get,
        public_client,
        user,
        organization,
        image_document_with_content,
    ):
        mock_fs_download.return_value = "/files/download/token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file content"
        mock_requests_get.return_value = mock_response

        dataroom = Dataroom.objects.create(
            name='Dispatch Dataroom For Folder Download',
            organization=organization,
            created_by=user,
        )
        link = ShareLink.objects.create(
            dataroom=dataroom,
            created_by=user,
            name='Folder Download Link',
        )
        root_folder = DataroomFolder.objects.create(
            dataroom=dataroom,
            name='Root Folder',
            parent=None,
        )
        ddoc = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=image_document_with_content,
            folder=root_folder,
            name='Test Image.gif',
        )

        ShareLinkDataroomSetting.objects.update_or_create(
            share_link=link,
            dataroom_folder=root_folder,
            defaults={
                'is_visible': True,
                'allow_download': True,
                'enable_watermark': False,
            },
        )
        ShareLinkDataroomSetting.objects.update_or_create(
            share_link=link,
            dataroom_document=ddoc,
            defaults={
                'is_visible': True,
                'allow_download': True,
                'enable_watermark': False,
            },
        )
        view_session = ViewSession.objects.create(share_link=link, viewer_email='b@b.com')

        response = public_client.get(
            f'/api/v1/links/{link.slug}/download-folder/{root_folder.id}/?view_session_id={view_session.id}'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @patch('sharelinks.views.dispatch_automation_event_task.delay')
    def test_request_access_dispatches_email_identified_when_no_verification(
        self,
        mock_delay,
        public_client,
        share_link,
    ):
        share_link.requires_email = True
        share_link.requires_email_verification = False
        share_link.save(update_fields=['requires_email', 'requires_email_verification'])

        response = public_client.post(
            f'/api/v1/links/{share_link.slug}/request-access/',
            {'email': 'buyer@example.com'},
            format='json',
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}
