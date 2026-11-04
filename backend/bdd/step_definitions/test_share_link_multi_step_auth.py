import pytest
from pytest_bdd import scenario, given, when, then, parsers

from documents.models import Document, DocumentVersion
from sharelinks.models import ShareLink

pytest_plugins = "bdd.step_definitions.common_steps"


@pytest.mark.django_db
def test_multi_step_auth(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.get('/api/v1/links/qXsXLhwcyXS9QQEgp-s-rA/view-data/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}
    assert [model.objects.count() for model in models] == before


@pytest.mark.django_db
def test_multi_step_auth_with_nda(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.get('/api/v1/links/qnu-I9K2DtIBInKfXVETcQ/view-data/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}
    assert [model.objects.count() for model in models] == before


@given("I have a document with a share link that requires a password and email", target_fixture="context")
def share_link_with_password_and_email(user_context):
    user = user_context['user']
    doc = Document.objects.create(
        name="Multi-Auth Doc.pdf",
        organization=user.organization,
        created_by=user,
        status='ready'
    )
    DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True)
    share_link = ShareLink.objects.create(
        document=doc,
        created_by=user,
        requires_email=True,
        password="password123"
    )
    return {'share_link': share_link}


@given("I have a document with a share link that requires email, password, and NDA", target_fixture="context")
def share_link_with_email_password_and_nda(user_context):
    user = user_context['user']
    doc = Document.objects.create(
        name="Multi-Auth NDA Doc.pdf",
        organization=user.organization,
        created_by=user,
        status='ready'
    )
    DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True)
    share_link = ShareLink.objects.create(
        document=doc,
        created_by=user,
        requires_email=True,
        password="password123",
        require_nda=True,
        nda_text="Confidential BDD NDA terms.",
        nda_version=1,
    )
    return {'share_link': share_link}


@when("a viewer first accesses the link", target_fixture="context")
def access_link_first_time(context, public_client):
    share_link = context['share_link']
    url = f'/api/v1/links/{share_link.slug}/view-data/'
    response = public_client.get(url)
    context['response'] = response
    return context


@then("they should be prompted for an email")
def check_prompted_for_email(context):
    response = context['response']
    assert response.status_code == 401
    assert response.json()['protectionType'] == 'email'


@when(parsers.parse('they submit the email "{email}"'), target_fixture="context")
def submit_email(context, public_client, email):
    share_link = context['share_link']
    request_url = f'/api/v1/links/{share_link.slug}/request-access/'
    response = public_client.post(request_url, {'email': email})
    assert response.status_code == 200

    # Re-fetch view data to see the next prompt
    view_url = f'/api/v1/links/{share_link.slug}/view-data/'
    view_response = public_client.get(view_url)
    context['response'] = view_response
    return context


@then("they should be prompted for a password")
def check_prompted_for_password(context):
    response = context['response']
    assert response.status_code == 401
    assert response.json()['protectionType'] == 'password'


@when(parsers.parse('they submit the correct password "{password}"'), target_fixture="context")
def submit_correct_password(context, public_client, password):
    share_link = context['share_link']
    verify_url = f'/api/v1/links/{share_link.slug}/verify-password/'
    response = public_client.post(verify_url, {'password': password})
    assert response.status_code == 200

    # Re-fetch view data to see the next prompt or content
    view_url = f'/api/v1/links/{share_link.slug}/view-data/'
    view_response = public_client.get(view_url)
    context['response'] = view_response
    return context


@then("they should be prompted for an NDA")
def check_prompted_for_nda(context):
    response = context['response']
    assert response.status_code == 401
    assert response.json()['protectionType'] == 'nda'


@when("they submit the NDA acceptance", target_fixture="context")
def submit_nda_acceptance(context, public_client):
    share_link = context['share_link']
    accept_url = f'/api/v1/links/{share_link.slug}/accept-nda/'
    response = public_client.post(accept_url, {})
    assert response.status_code == 200

    # Re-fetch view data to gain final access
    view_url = f'/api/v1/links/{share_link.slug}/view-data/'
    view_response = public_client.get(view_url)
    context['response'] = view_response
    return context


@then("they should be granted access to the document")
def check_access_granted(context):
    response = context['response']
    assert response.status_code == 200
    assert 'id' in response.json()
