import pytest
from pytest_bdd import parsers, scenario, given, when, then
from rest_framework import status

from documents.models import Document
from sharelinks.models import ShareLink

# Make common steps available
pytest_plugins = "bdd.step_definitions.common_steps"


@pytest.mark.django_db
def test_password_protected_share_link(api_client):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    from documents.models import Document
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ViewerOrganisation, ViewSession
    models = (Document, Dataroom, ShareLink, ViewerOrganisation, ViewSession)
    before = [model.objects.count() for model in models]
    response = api_client.get('/api/v1/links/RDxGQ2GCFJ_qJTfnBZtXJg/view-data/', {}, format='json')
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}
    assert [model.objects.count() for model in models] == before


@given(parsers.parse('I have a document named "{filename}"'), target_fixture="document")
def document(user_context, filename):
    """Create a document owned by the user, ready for viewing."""
    doc = Document.objects.create(
        organization=user_context['user'].organization,
        created_by=user_context['user'],
        name=filename,
        status='ready'
    )
    # Create a version and page to make it viewable
    version = doc.versions.create(
        is_primary=True,
        has_pages=True,
        num_pages=1,
        version_number=1
    )
    version.pages.create(page_number=1, storage_key=f"pages/{doc.id}-1.png")
    user_context['document'] = doc
    return doc


@given("I create a password-protected share link for that document", target_fixture="share_link")
def create_password_protected_share_link(user_context, document):
    """Create a password protected share link."""
    link = ShareLink.objects.create(
        document=document,
        created_by=user_context['user'],
        name="Password Protected Link",
        password="a-strong-password-hash"  # The presence of a hash is what matters
    )
    user_context['share_link'] = link
    return link


@when("an anonymous viewer tries to access the share link data", target_fixture="api_response_context")
def access_share_link_data(public_client, share_link):
    """An anonymous viewer attempts to access the share link data."""
    response = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
    return {'response': response}


@then("the API should respond with an unauthorized status")
def check_unauthorized_status(api_response_context):
    """Check that the API responds with 401 Unauthorized."""
    assert api_response_context['response'].status_code == status.HTTP_401_UNAUTHORIZED
