import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from core.models import APIKey
from core.authentication import generate_raw_api_key
from datarooms.models import Dataroom


def _create_client_with_api_key(user, tier):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=user,
        name=f'{tier} Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier=tier,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
    return client


@pytest.mark.django_db
def test_read_only_api_key_perm_on_datarooms(user):
    client = _create_client_with_api_key(user, 'read_only')
    dataroom = Dataroom.objects.create(name='Test Room', created_by=user, organization=user.organization)

    # 1. GET -> Allowed (200)
    list_resp = client.get(reverse('dataroom-list'))
    # Phase 1: this legacy request is denied before its former handler runs.
    assert list_resp.status_code == 403
    assert list_resp.data == {'detail': 'Staff access is required.'}


@pytest.mark.django_db
def test_read_write_api_key_perm_on_datarooms(user):
    client = _create_client_with_api_key(user, 'read_write')
    dataroom = Dataroom.objects.create(name='Test Room', created_by=user, organization=user.organization)

    # 1. POST -> Allowed (201)
    create_resp = client.post(reverse('dataroom-list'), {'name': 'New Write Room'}, format='json')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert create_resp.status_code == 403
    assert create_resp.data == {'detail': 'Unclassified or disabled operation.'}


@pytest.mark.django_db
def test_full_access_api_key_perm_on_datarooms(user):
    client = _create_client_with_api_key(user, 'full_access')
    dataroom = Dataroom.objects.create(name='Test Room', created_by=user, organization=user.organization)

    # DELETE -> Allowed (204)
    delete_resp = client.delete(reverse('dataroom-detail', args=[dataroom.id]))
    # Phase 1: this legacy request is denied before its former handler runs.
    assert delete_resp.status_code == 403
    assert delete_resp.data == {'detail': 'Unclassified or disabled operation.'}
