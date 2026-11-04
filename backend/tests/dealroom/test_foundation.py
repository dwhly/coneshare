import json
from pathlib import Path
from datetime import timedelta
import pytest
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import Organization, User, APIKey
from core.authentication import generate_raw_api_key
from dealroom.registry import widens_access, registry
from dealroom.domains import guarded_domain, canonical_domain
from dealroom.models import AccessApproval
from dealroom.management.commands.dealroom_registry import inventory


@pytest.fixture
def owner(db):
    org = Organization.objects.create(name='Dealroom tests')
    return User.objects.create_user(username='staff@acme.test', email='staff@acme.test', password='testpass', organization=org, is_staff=True, role='admin')


@pytest.fixture
def staff(owner):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(owner).access_token))
    return client


@pytest.fixture
def agent(owner):
    raw, prefix, hashed = generate_raw_api_key()
    APIKey.objects.create(user=owner, name='test agent', prefix=prefix, hashed_key=hashed, tier='full_access')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)
    return client


@pytest.mark.parametrize('before,after', [
    ({'download_ceiling':'none'}, {'download_ceiling':'watermarked'}),
    ({'download_ceiling':'watermarked'}, {'download_ceiling':'original'}),
    ({'expires_at':'2026-01-01'}, {'expires_at':'2027-01-01'}),
    ({'expires_at':'2026-01-01'}, {'expires_at':None}),
    ({'revoked_at':'2026-01-01'}, {'revoked_at':None}),
    ({'email':'jane@acme.test'}, {'email':'bob@other.test'}),
    ({'signer_email':'jane@acme.test'}, {'signer_email':'bob@other.test'}),
    ({'recipient':'jane'}, {'recipient':'bob'}),
    ({'domains':['acme.test']}, {'domains':['acme.test','other.test']}),
    ({'status':'archived'}, {'status':'active'}),
    ({'invitation_mode':'off'}, {'invitation_mode':'automatic_same_org'}),
    ({'password':'set'}, {'password':None}),
    ({'scope':['a']}, {'scope':['a','b']}),
    ({'destination_url':'https://a.test'}, {'destination_url':'https://b.test'}),
    ({'webhook_url':'https://a.test'}, {'webhook_url':'https://b.test'}),
    ({'disabled_at':'2026-01-01'}, {'disabled_at':None}),
    ({'requires_email':True}, {'requires_email':False}),
    ({'is_active':False}, {'is_active':True}),
    ({}, {'unknown_policy':'new'}),
])
def test_every_edit_to_widen_requires_approval(before, after):
    assert widens_access({'widens_access':'evaluate_change'}, before, after)


def test_unknown_mutation_is_widening():
    assert widens_access({}, {}, {})


def test_file_visibility_for_existing_grantees_not_widening():
    assert not widens_access({'widens_access':'evaluate_change'}, {'is_visible':False}, {'is_visible':True})


@pytest.mark.parametrize('value', ['gmail.com','yahoo.com','mailinator.com','gmaіl.com','*.acme.test'])
def test_domain_guard(value):
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        guarded_domain(value)


def test_idna_and_exact_domain():
    assert canonical_domain('BÜCHER.test')[0] == 'xn--bcher-kva.test'
    assert guarded_domain('acme.test')[0] == 'acme.test'


def test_all_served_operations_resolve_and_mutations_classified():
    assert inventory() == registry()
    assert len(registry()) > 200
    for entry in registry().values():
        assert entry['widens_access'] in (True, False, 'evaluate_change')


@pytest.mark.django_db
def test_agent_approval_no_effect_until_staff_jwt(agent, staff):
    room = staff.post('/api/v1/dealroom/rooms/', {'name':'Atlas'}, format='json')
    assert room.status_code == 201, room.data
    payload = {'room':room.data['id'], 'email':'jane@acme.test'}
    result = agent.post('/api/v1/dealroom/grants/', payload, format='json')
    assert result.status_code == 202, result.data
    approval = AccessApproval.objects.get(pk=result.data['approval_id'])
    from sharelinks.models import ShareLinkAccessGrant
    assert not ShareLinkAccessGrant.objects.exists()
    url = f'/api/v1/dealroom/approvals/{approval.pk}/approve/'
    assert agent.post(url).status_code == 403
    approved = staff.post(url)
    assert approved.status_code == 200, approved.data
    assert ShareLinkAccessGrant.objects.filter(email='jane@acme.test').exists()
    assert staff.post(url).status_code == 400


@pytest.mark.django_db
def test_read_only_cannot_mutate_even_overridden_permissions(owner):
    raw, prefix, hashed = generate_raw_api_key()
    assert len(prefix.removeprefix('cs_live_')) >= 8
    APIKey.objects.create(user=owner, name='reader', prefix=prefix, hashed_key=hashed, tier='read_only')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)
    assert client.get('/api/v1/dealroom/rooms/').status_code == 200
    assert client.post('/api/v1/dealroom/rooms/', {'name':'no'}, format='json').status_code == 403
    assert client.get('/api/v1/automation-destinations/').status_code in (403,404)


@pytest.mark.django_db
@pytest.mark.parametrize('path', ['/admin/', '/api-auth/login/'])
def test_operator_alternate_paths_closed(path):
    assert APIClient().get(path).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize('path', ['/api/v1/links/missing/render-page/1/', '/api/v1/links/missing/page/1/', '/api/v1/links/missing/view-data/'])
def test_personalized_pages_private_no_store(path):
    client = APIClient()
    for headers in ({}, {'HTTP_IF_NONE_MATCH':'"warm-cache"'}):
        response = client.get(path, **headers)
        assert response['Cache-Control'] == 'private, no-store'
        assert response['Referrer-Policy'] == 'no-referrer'
        assert response.status_code >= 400
