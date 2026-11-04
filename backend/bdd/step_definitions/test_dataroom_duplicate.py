import pytest
from pytest_bdd import scenario, given, when, then, parsers

from datarooms.models import Dataroom, DataroomDocument, DataroomFolder
from documents.models import Document, DocumentVersion
from sharelinks.models import ShareLink, ShareLinkAccessGrant, ViewerOrganisation, ViewSession

pytest_plugins = "bdd.step_definitions.common_steps"


@pytest.mark.django_db
def test_duplicate_dataroom(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/share-links/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@given(parsers.parse('a viewer organisation "{name}" with the email domain "{domain}"'), target_fixture="viewer_org")
def viewer_org(user_context, name, domain):
    return ViewerOrganisation.objects.create(
        organization=user_context['user'].organization, name=name, email_domains=[domain]
    )


@given(parsers.parse('I have a data room "{room_name}" with a folder "{folder_name}" containing the document "{doc_name}"'),
       target_fixture="room_context")
def room_with_content(user_context, room_name, folder_name, doc_name):
    user = user_context['user']
    room = Dataroom.objects.create(organization=user.organization, name=room_name, created_by=user, enable_qna=False)
    folder = DataroomFolder.objects.create(dataroom=room, name=folder_name, created_by=user)
    doc = Document.objects.create(name=doc_name, organization=user.organization, created_by=user, status='ready', type='pdf')
    DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True, original_storage_key='k/model.pdf')
    ddoc = DataroomDocument.objects.create(dataroom=room, document=doc, folder=folder, name=doc_name)
    return {'room': room, 'folder': folder, 'document': doc, 'dataroom_document': ddoc}


@given(parsers.parse('the room has a link restricted to approved organisations granted to "{org_name}"'))
def room_link(user_context, room_context, org_name):
    room = room_context['room']
    res = user_context['api_client'].post('/api/v1/share-links/', {
        'dataroom': str(room.id), 'name': 'Buyers', 'restrict_to_grants': True,
        'allow_download': True, 'watermark_text': 'CONFIDENTIAL {{name}}',
    }, format='json')
    assert res.status_code == 201, res.content
    link = ShareLink.objects.get(id=res.data['id'])
    ShareLinkAccessGrant.objects.create(share_link=link, viewer_organisation=ViewerOrganisation.objects.get(name=org_name))
    # Hide the folder for this link so per-item settings must be mirrored.
    setting = link.dataroom_settings.get(dataroom_folder=room_context['folder'])
    setting.is_visible = False
    setting.save()
    room_context['link'] = link


@given("the link has a recorded view session")
def recorded_session(room_context):
    ViewSession.objects.create(share_link=room_context['link'], viewer_email='jane@acme.test', viewer_name='Jane Doe')


@when(parsers.parse('I duplicate the data room "{room_name}"'), target_fixture="duplicate_response")
def duplicate(user_context, room_context, room_name):
    room = Dataroom.objects.get(name=room_name)
    res = user_context['api_client'].post(f'/api/v1/datarooms/{room.id}/duplicate/', {'include_share_links': True}, format='json')
    assert res.status_code == 201, res.content
    assert res.data['folder_count'] == 1
    assert res.data['document_count'] == 1
    assert res.data['share_link_count'] == 1
    return res.data


@then(parsers.parse('a data room "{room_name}" exists with a folder "{folder_name}" containing the document "{doc_name}"'))
def check_copy(duplicate_response, room_name, folder_name, doc_name):
    copy = Dataroom.objects.get(id=duplicate_response['dataroom']['id'])
    assert copy.name == room_name
    assert copy.enable_qna is False
    folder = DataroomFolder.objects.get(dataroom=copy, name=folder_name)
    assert DataroomDocument.objects.filter(dataroom=copy, folder=folder, name=doc_name).exists()


@then("the copied document reuses the original stored document")
def check_doc_reused(duplicate_response, room_context):
    copy_ddoc = DataroomDocument.objects.get(dataroom_id=duplicate_response['dataroom']['id'])
    assert copy_ddoc.document_id == room_context['document'].id
    assert copy_ddoc.id != room_context['dataroom_document'].id
    assert Document.objects.filter(name=room_context['document'].name).count() == 1


@then(parsers.parse('the copy has an inactive link with the same settings granted to "{org_name}"'))
def check_link_copy(duplicate_response, room_context, org_name):
    original = room_context['link']
    link = ShareLink.objects.get(dataroom_id=duplicate_response['dataroom']['id'])
    assert link.slug != original.slug
    assert link.is_active is False
    assert link.restrict_to_grants is True
    assert link.allow_download is True
    assert link.enable_watermark is True
    assert link.watermark_text == 'CONFIDENTIAL {{name}}'
    assert link.access_grants.filter(viewer_organisation__name=org_name).exists()
    folder_setting = link.dataroom_settings.get(dataroom_folder__name='Financials')
    assert folder_setting.is_visible is False


@then("the copied link has no view sessions")
def check_no_sessions(duplicate_response):
    link = ShareLink.objects.get(dataroom_id=duplicate_response['dataroom']['id'])
    assert not ViewSession.objects.filter(share_link=link).exists()


@then(parsers.parse('the original data room "{room_name}" still exists'))
def check_original(room_context, room_name):
    assert Dataroom.objects.filter(id=room_context['room'].id, name=room_name).exists()
    assert ViewSession.objects.filter(share_link=room_context['link']).count() == 1
