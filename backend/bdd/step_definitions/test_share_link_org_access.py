import pytest
from unittest.mock import patch
from pytest_bdd import scenario, given, when, then, parsers

from datarooms.models import Dataroom, DataroomDocument
from documents.models import Document, DocumentVersion
from sharelinks.models import (EmailVerificationToken, ShareLink, ShareLinkAccessGrant,
                               ViewerOrganisation, ViewSession)

pytest_plugins = "bdd.step_definitions.common_steps"

FEATURE = '../features/share_link_org_access.feature'


@pytest.mark.django_db
def test_granted_org_viewer_gets_in(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/viewer-organisations/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@pytest.mark.django_db
def test_other_org_viewer_denied(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/viewer-organisations/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@pytest.mark.django_db
def test_explicit_email_grant(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/viewer-organisations/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@pytest.mark.django_db
def test_name_required(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/viewer-organisations/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@pytest.mark.django_db
def test_revoke_grant(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/viewer-organisations/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@pytest.mark.django_db
def test_grants_force_verification(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/viewer-organisations/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@pytest.mark.django_db
def test_download_defaults(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.post('/api/v1/viewer-organisations/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'Unclassified or disabled operation.'}
    assert [model.objects.count() for model in models] == before


@given(parsers.parse('a viewer organisation "{name}" with the email domain "{domain}"'), target_fixture="viewer_org")
def viewer_org(user_context, name, domain):
    client = user_context['api_client']
    response = client.post('/api/v1/viewer-organisations/', {'name': name, 'email_domains': [domain]}, format='json')
    assert response.status_code == 201, response.content
    return ViewerOrganisation.objects.get(id=response.data['id'])


@given("I have a data room link restricted to approved organisations", target_fixture="share_link_context")
def restricted_room_link(user_context):
    user = user_context['user']
    client = user_context['api_client']
    room = Dataroom.objects.create(organization=user.organization, name='Project Falcon', created_by=user)
    doc = Document.objects.create(
        name="Teaser.pdf", organization=user.organization, created_by=user, status='ready', type='pdf'
    )
    DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True, original_storage_key='k/teaser.pdf')
    ddoc = DataroomDocument.objects.create(dataroom=room, document=doc, name='Teaser.pdf')
    response = client.post('/api/v1/share-links/', {
        'dataroom': str(room.id), 'name': 'Buyers', 'restrict_to_grants': True,
    }, format='json')
    assert response.status_code == 201, response.content
    link = ShareLink.objects.get(id=response.data['id'])
    return {'share_link': link, 'dataroom': room, 'dataroom_document': ddoc}


@given(parsers.parse('the link is granted to the organisation "{name}"'))
def grant_org(user_context, share_link_context, name):
    org = ViewerOrganisation.objects.get(name=name)
    link = share_link_context['share_link']
    response = user_context['api_client'].post(
        f'/api/v1/share-links/{link.id}/access-grants/', {'viewer_organisation': str(org.id)}, format='json'
    )
    assert response.status_code == 201, response.content


@given(parsers.parse('the link is granted to the email "{email}"'))
def grant_email(user_context, share_link_context, email):
    link = share_link_context['share_link']
    response = user_context['api_client'].post(
        f'/api/v1/share-links/{link.id}/access-grants/', {'email': email}, format='json'
    )
    assert response.status_code == 201, response.content


@when(parsers.re(r'an anonymous viewer requests access as "(?P<name>[^"]*)" with the email "(?P<email>[^"]*)"'),
      target_fixture="api_response_context")
def request_access_with_name(public_client, share_link_context, name, email):
    link = share_link_context['share_link']
    with patch('sharelinks.views.send_mail') as mock_send_mail:
        response = public_client.post(f'/api/v1/links/{link.slug}/request-access/', {'email': email, 'name': name})
        return {'response': response, 'mock_send_mail': mock_send_mail}


@then(parsers.parse('a verification email should be sent to "{email}"'))
def check_email_sent(api_response_context, email):
    response = api_response_context['response']
    assert response.status_code == 200, response.content
    assert response.json()['verification_required'] is True
    mock_send_mail = api_response_context['mock_send_mail']
    mock_send_mail.assert_called_once()
    assert email in mock_send_mail.call_args.kwargs['recipient_list']


@then("the request is denied as not authorised")
def check_denied(api_response_context):
    response = api_response_context['response']
    assert response.status_code == 403
    assert response.json().get('accessDenied') is True


@then("no verification email is sent")
def check_no_email(api_response_context, share_link_context):
    api_response_context['mock_send_mail'].assert_not_called()
    assert not EmailVerificationToken.objects.filter(share_link=share_link_context['share_link']).exists()


@then("the request is rejected because the name is missing")
def check_name_missing(api_response_context):
    response = api_response_context['response']
    assert response.status_code == 400
    assert 'name' in response.json()


@when(parsers.parse('the viewer confirms the magic link sent to "{email}"'))
def confirm_magic_link(public_client, share_link_context, email):
    link = share_link_context['share_link']
    _confirm(public_client, link, email)


def _confirm(public_client, link, email):
    """Open the magic link (GET binds it to this browser), then confirm like the UI does."""
    token = EmailVerificationToken.objects.filter(share_link=link, email=email).latest('created_at')
    res_get = public_client.get(f'/api/v1/links/{link.slug}/view-data/?accessToken={token.token}')
    assert res_get.status_code == 401
    assert res_get.json()['requiresConfirmation'] is True
    res = public_client.post(f'/api/v1/links/{link.slug}/verify-access-token/confirm/', {'token': token.token})
    assert res.status_code == 200, res.content
    return res


@then("the viewer can open the data room")
def can_open(public_client, share_link_context):
    link = share_link_context['share_link']
    res = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
    assert res.status_code == 200, res.content
    assert res.json()['link_settings']['viewer_organisation_name'] == 'Acme Corp'


@then(parsers.parse('a view session records the name "{name}" and the organisation "{org}"'))
def view_session_identity(public_client, share_link_context, name, org):
    link = share_link_context['share_link']
    res = public_client.post('/api/v1/view-sessions/', {'share_link': link.id})
    assert res.status_code == 201, res.content
    session = ViewSession.objects.get(id=res.data['id'])
    assert session.viewer_name == name
    assert session.viewer_organisation is not None
    assert session.viewer_organisation.name == org
    assert session.viewer_organisation_name == org
    assert session.viewer.name == name


@when(parsers.parse('I revoke the grant for "{org_name}"'))
def revoke(user_context, share_link_context, org_name):
    link = share_link_context['share_link']
    grant = ShareLinkAccessGrant.objects.get(share_link=link, viewer_organisation__name=org_name)
    res = user_context['api_client'].delete(f'/api/v1/share-links/{link.id}/access-grants/{grant.id}/')
    assert res.status_code == 204


@then("the viewer can no longer open the data room")
def cannot_open(public_client, share_link_context):
    link = share_link_context['share_link']
    res = public_client.get(f'/api/v1/links/{link.slug}/view-data/')
    assert res.status_code == 403


@then("the link requires email verification")
def link_requires_verification(share_link_context):
    link = share_link_context['share_link']
    link.refresh_from_db()
    assert link.requires_email is True
    assert link.requires_email_verification is True


@then("the link does not allow downloads")
def link_no_downloads(share_link_context):
    link = share_link_context['share_link']
    link.refresh_from_db()
    assert link.allow_download is False
    assert all(not s.allow_download for s in link.dataroom_settings.all())


@then("the link has watermarking enabled")
def link_watermarked(share_link_context):
    link = share_link_context['share_link']
    link.refresh_from_db()
    assert link.enable_watermark is True


@then("the link does not allow original downloads")
def link_no_originals(share_link_context):
    link = share_link_context['share_link']
    link.refresh_from_db()
    assert link.allow_original_download is False


@then("downloading a document from the link is forbidden")
def download_forbidden(public_client, share_link_context):
    link = share_link_context['share_link']
    ddoc = share_link_context['dataroom_document']
    ShareLinkAccessGrant.objects.get_or_create(share_link=link, email='jane@acme.test')
    with patch('sharelinks.views.send_mail'):
        public_client.post(f'/api/v1/links/{link.slug}/request-access/', {'email': 'jane@acme.test', 'name': 'Jane Doe'})
    _confirm(public_client, link, 'jane@acme.test')
    res = public_client.get(f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={ddoc.id}')
    assert res.status_code == 403
