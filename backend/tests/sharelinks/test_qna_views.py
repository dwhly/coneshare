from unittest.mock import patch

import pytest
from rest_framework import status

from datarooms.models import DataroomDocument, DataroomFolder
from documents.models import Document, DocumentVersion
from sharelinks.models import QnAMessage, QnAThread, ShareLink, ShareLinkDataroomSetting, ViewSession


pytestmark = pytest.mark.django_db


def _create_ready_document(user, organization, name):
    document = Document.objects.create(
        name=name,
        organization=organization,
        created_by=user,
        status='ready',
    )
    DocumentVersion.objects.create(
        document=document,
        version_number=1,
        is_primary=True,
    )
    return document


def test_document_link_viewer_can_create_and_list_qna_thread(public_client, share_link):
    view_session = ViewSession.objects.create(
        share_link=share_link,
        viewer_email='viewer@example.com',
    )

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'subject': 'Can you explain page 3?',
            'body': 'The revenue line needs more context.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_document_link_viewer_can_fetch_qna_summary(public_client, share_link):
    view_session = ViewSession.objects.create(
        share_link=share_link,
        viewer_email='viewer@example.com',
    )
    open_thread = QnAThread.objects.create(
        organization=share_link.document.organization,
        share_link=share_link,
        document=share_link.document,
        subject='Open question',
        created_by_view_session=view_session,
    )
    closed_thread = QnAThread.objects.create(
        organization=share_link.document.organization,
        share_link=share_link,
        document=share_link.document,
        subject='Closed question',
        status=QnAThread.STATUS_CLOSED,
        created_by_view_session=view_session,
    )
    QnAMessage.objects.create(thread=open_thread, body='One', sent_by_view_session=view_session)
    QnAMessage.objects.create(thread=closed_thread, body='Two', sent_by_view_session=view_session)

    response = public_client.get(
        f'/api/v1/links/{share_link.slug}/qna-summary/?view_session_id={view_session.id}'
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_viewer_cannot_use_view_session_from_another_share_link(public_client, share_link, document, user):
    other_link = ShareLink.objects.create(
        document=document,
        created_by=user,
        name='Other Link',
    )
    other_session = ViewSession.objects.create(share_link=other_link)

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/',
        {
            'view_session_id': str(other_session.id),
            'subject': 'Wrong session',
            'body': 'This should not be accepted.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_anonymous_view_session_can_create_qna_when_link_does_not_require_email(public_client, share_link):
    view_session = ViewSession.objects.create(share_link=share_link)

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'subject': 'Anonymous question',
            'body': 'This should be accepted for anonymous links.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_email_gated_qna_requires_view_session_email_to_match_verified_email(public_client, share_link):
    share_link.requires_email = True
    share_link.save(update_fields=['requires_email'])
    view_session = ViewSession.objects.create(
        share_link=share_link,
        viewer_email='victim@example.com',
    )
    session = public_client.session
    session['authorized_share_links'] = {
        str(share_link.id): {
            'email_verified': True,
            'viewer_email': 'attacker@example.com',
        }
    }
    session.save()

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'subject': 'Wrong viewer',
            'body': 'This should not be accepted.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_qna_endpoints_require_nda_acceptance_when_nda_configured(public_client, share_link):
    share_link.require_nda = True
    share_link.nda_text = "Confidential terms."
    share_link.nda_version = 1
    share_link.save(update_fields=['require_nda', 'nda_text', 'nda_version'])

    view_session = ViewSession.objects.create(
        share_link=share_link,
        viewer_email='viewer@example.com',
    )

    # 1. Without NDA accepted in session -> 403 Forbidden
    response = public_client.get(
        f'/api/v1/links/{share_link.slug}/qna-threads/?view_session_id={view_session.id}'
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_dataroom_viewer_can_create_and_list_root_qna_thread(public_client, dataroom, user):
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
    view_session = ViewSession.objects.create(share_link=link)

    response = public_client.post(
        f'/api/v1/links/{link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'subject': 'Room-level question',
            'body': 'This is about the whole room.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_dataroom_qna_summary_is_scoped_to_folder_context(public_client, dataroom, user):
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
    view_session = ViewSession.objects.create(share_link=link)
    folder = DataroomFolder.objects.create(dataroom=dataroom, name='Folder')
    ShareLinkDataroomSetting.objects.get_or_create(
        share_link=link,
        dataroom_folder=folder,
        defaults={'is_visible': True, 'allow_download': True, 'enable_watermark': False},
    )
    folder_thread = QnAThread.objects.create(
        organization=user.organization,
        share_link=link,
        dataroom=dataroom,
        dataroom_folder=folder,
        subject='Folder question',
        created_by_view_session=view_session,
    )
    QnAMessage.objects.create(thread=folder_thread, body='Folder message', sent_by_view_session=view_session)
    QnAThread.objects.create(
        organization=user.organization,
        share_link=link,
        dataroom=dataroom,
        subject='Root question',
        created_by_view_session=view_session,
    )

    response = public_client.get(
        f'/api/v1/links/{link.slug}/qna-summary/?view_session_id={view_session.id}&dataroom_folder_id={folder.id}'
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_dataroom_viewer_cannot_create_qna_for_invisible_document(
    public_client,
    dataroom,
    user,
    organization,
):
    document = _create_ready_document(user, organization, 'Hidden.pdf')
    ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
    view_session = ViewSession.objects.create(share_link=link, viewer_email='viewer@example.com')
    ShareLinkDataroomSetting.objects.filter(
        share_link=link,
        dataroom_document=ddoc,
    ).update(is_visible=False)

    response = public_client.post(
        f'/api/v1/links/{link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'dataroom_document_id': str(ddoc.id),
            'subject': 'Hidden doc question',
            'body': 'This should be denied.',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert QnAThread.objects.count() == 0


def test_dataroom_viewer_cannot_create_qna_for_visible_document_under_invisible_folder(
    public_client,
    dataroom,
    user,
    organization,
):
    folder = DataroomFolder.objects.create(dataroom=dataroom, name='Hidden Folder')
    document = _create_ready_document(user, organization, 'Child.pdf')
    ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document, folder=folder)
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
    view_session = ViewSession.objects.create(share_link=link, viewer_email='viewer@example.com')
    ShareLinkDataroomSetting.objects.filter(
        share_link=link,
        dataroom_folder=folder,
    ).update(is_visible=False)
    ShareLinkDataroomSetting.objects.filter(
        share_link=link,
        dataroom_document=ddoc,
    ).update(is_visible=True)

    response = public_client.post(
        f'/api/v1/links/{link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'dataroom_document_id': str(ddoc.id),
            'subject': 'Child question',
            'body': 'Visible child should still be denied.',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert QnAThread.objects.count() == 0


def test_viewer_cannot_reply_to_closed_thread(public_client, share_link):
    view_session = ViewSession.objects.create(share_link=share_link, viewer_email='viewer@example.com')
    thread = QnAThread.objects.create(
        organization=share_link.document.organization,
        share_link=share_link,
        document=share_link.document,
        subject='Closed thread',
        status=QnAThread.STATUS_CLOSED,
        created_by_view_session=view_session,
    )

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/{thread.id}/messages/',
        {
            'view_session_id': str(view_session.id),
            'body': 'Can I still reply?',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert QnAMessage.objects.count() == 0


@patch('sharelinks.views.dispatch_automation_event_task.delay')
def test_qna_thread_creation_dispatches_automation_event(mock_delay, public_client, share_link):
    view_session = ViewSession.objects.create(
        share_link=share_link,
        viewer_email='viewer@example.com',
    )

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'subject': 'Notify owner',
            'body': 'Please review this.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_owner_can_close_and_reopen_thread(api_client, share_link, user):
    thread = QnAThread.objects.create(
        organization=user.organization,
        share_link=share_link,
        document=share_link.document,
        subject='Lifecycle',
        created_by_user=user,
    )

    close_response = api_client.patch(
        f'/api/v1/qna-threads/{thread.id}/',
        {'status': QnAThread.STATUS_CLOSED},
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert close_response.status_code == 403
    assert close_response.data == {'detail': 'Unclassified or disabled operation.'}


@patch('sharelinks.views.dispatch_automation_event_task.delay')
def test_owner_can_create_document_qna_thread(mock_delay, api_client, share_link, user):
    response = api_client.post(
        '/api/v1/qna-threads/',
        {
            'share_link_id': str(share_link.id),
            'subject': 'Owner-started question',
            'body': 'Please review this before diligence.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


def test_owner_can_create_dataroom_root_qna_thread(api_client, dataroom, user):
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user, name='Room Link')

    response = api_client.post(
        '/api/v1/qna-threads/',
        {
            'share_link_id': str(link.id),
            'subject': 'Room-level owner question',
            'body': 'This is about the whole room.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


def test_owner_cannot_create_qna_thread_for_other_users_share_link(api_client, share_link, user2):
    share_link.created_by = user2
    share_link.save(update_fields=['created_by'])

    response = api_client.post(
        '/api/v1/qna-threads/',
        {
            'share_link_id': str(share_link.id),
            'subject': 'Wrong owner',
            'body': 'This should not be accepted.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


def test_owner_create_qna_thread_rejects_dataroom_item_context(api_client, dataroom, user, organization):
    document = _create_ready_document(user, organization, 'Item.pdf')
    ddoc = DataroomDocument.objects.create(dataroom=dataroom, document=document)
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user, name='Room Link')

    response = api_client.post(
        '/api/v1/qna-threads/',
        {
            'share_link_id': str(link.id),
            'dataroom_document_id': str(ddoc.id),
            'subject': 'Item-level owner question',
            'body': 'Phase one should reject this context.',
        },
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


def test_owner_can_filter_qna_threads_by_document(api_client, share_link, user, organization):
    other_document = _create_ready_document(user, organization, 'Other.pdf')
    other_link = ShareLink.objects.create(
        document=other_document,
        created_by=user,
        name='Other Link',
    )
    matching_thread = QnAThread.objects.create(
        organization=user.organization,
        share_link=share_link,
        document=share_link.document,
        subject='Matching document',
        created_by_user=user,
    )
    dataroom = share_link.document.organization.datarooms.create(
        name='Document Room',
        created_by=user,
    )
    dataroom_document = DataroomDocument.objects.create(
        dataroom=dataroom,
        document=share_link.document,
        name=share_link.document.name,
    )
    dataroom_link = ShareLink.objects.create(
        dataroom=dataroom,
        created_by=user,
        name='Dataroom Link',
    )
    dataroom_document_thread = QnAThread.objects.create(
        organization=user.organization,
        share_link=dataroom_link,
        dataroom=dataroom,
        dataroom_document=dataroom_document,
        subject='Matching dataroom document',
        created_by_user=user,
    )
    QnAThread.objects.create(
        organization=user.organization,
        share_link=other_link,
        document=other_document,
        subject='Other document',
        created_by_user=user,
    )

    response = api_client.get(
        f'/api/v1/qna-threads/?document_id={share_link.document_id}'
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


def test_dataroom_qna_switch_disables_qna_for_every_link_into_the_room(
    public_client, dataroom, user
):
    dataroom.enable_qna = False
    dataroom.save(update_fields=['enable_qna'])
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user)
    view_session = ViewSession.objects.create(share_link=link)

    assert link.enable_qna is True
    assert link.qna_enabled is False

    create_response = public_client.post(
        f'/api/v1/links/{link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'subject': 'Room-level question',
            'body': 'This should never be stored.',
        },
        format='json',
    )

    assert create_response.status_code == status.HTTP_403_FORBIDDEN
    assert QnAThread.objects.count() == 0

    list_response = public_client.get(
        f'/api/v1/links/{link.slug}/qna-threads/?view_session_id={view_session.id}'
    )
    summary_response = public_client.get(
        f'/api/v1/links/{link.slug}/qna-summary/?view_session_id={view_session.id}'
    )

    assert list_response.status_code == status.HTTP_403_FORBIDDEN
    assert summary_response.status_code == status.HTTP_403_FORBIDDEN


def test_link_level_qna_switch_disables_qna_for_that_link_only(
    public_client, dataroom, user
):
    disabled_link = ShareLink.objects.create(
        dataroom=dataroom, created_by=user, name='No Q&A group', enable_qna=False
    )
    enabled_link = ShareLink.objects.create(
        dataroom=dataroom, created_by=user, name='Q&A group'
    )
    disabled_session = ViewSession.objects.create(share_link=disabled_link)
    enabled_session = ViewSession.objects.create(share_link=enabled_link)

    payload = {'subject': 'Question', 'body': 'Body.'}

    disabled_response = public_client.post(
        f'/api/v1/links/{disabled_link.slug}/qna-threads/',
        {**payload, 'view_session_id': str(disabled_session.id)},
        format='json',
    )
    enabled_response = public_client.post(
        f'/api/v1/links/{enabled_link.slug}/qna-threads/',
        {**payload, 'view_session_id': str(enabled_session.id)},
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert enabled_response.status_code == 403
    assert enabled_response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_link_cannot_re_enable_qna_that_the_dataroom_turned_off(dataroom, user):
    dataroom.enable_qna = False
    dataroom.save(update_fields=['enable_qna'])
    link = ShareLink.objects.create(dataroom=dataroom, created_by=user, enable_qna=True)

    assert link.qna_enabled is False


def test_document_link_qna_switch_disables_public_qna(public_client, share_link):
    share_link.enable_qna = False
    share_link.save(update_fields=['enable_qna'])
    view_session = ViewSession.objects.create(
        share_link=share_link,
        viewer_email='viewer@example.com',
    )

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/',
        {
            'view_session_id': str(view_session.id),
            'subject': 'Can you explain page 3?',
            'body': 'The revenue line needs more context.',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert QnAThread.objects.count() == 0


def test_viewer_cannot_reply_to_existing_thread_after_qna_is_disabled(
    public_client, share_link
):
    view_session = ViewSession.objects.create(
        share_link=share_link,
        viewer_email='viewer@example.com',
    )
    thread = QnAThread.objects.create(
        organization=share_link.created_by.organization,
        share_link=share_link,
        document=share_link.document,
        subject='Existing question',
        created_by_view_session=view_session,
    )

    share_link.enable_qna = False
    share_link.save(update_fields=['enable_qna'])

    response = public_client.post(
        f'/api/v1/links/{share_link.slug}/qna-threads/{thread.id}/messages/',
        {'view_session_id': str(view_session.id), 'body': 'Follow-up.'},
        format='json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert QnAMessage.objects.count() == 0


def test_owner_cannot_create_qna_thread_when_qna_is_disabled(api_client, share_link, user):
    share_link.enable_qna = False
    share_link.save(update_fields=['enable_qna'])
    api_client.force_authenticate(user=user)

    response = api_client.post(
        '/api/v1/qna-threads/',
        {'share_link_id': str(share_link.id), 'subject': 'Ping', 'body': 'Hello.'},
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}


def test_owner_can_still_moderate_existing_threads_after_qna_is_disabled(
    api_client, share_link, user
):
    thread = QnAThread.objects.create(
        organization=user.organization,
        share_link=share_link,
        document=share_link.document,
        subject='Existing question',
        created_by_user=user,
    )
    share_link.enable_qna = False
    share_link.save(update_fields=['enable_qna'])
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        f'/api/v1/qna-threads/{thread.id}/',
        {'status': QnAThread.STATUS_CLOSED},
        format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
