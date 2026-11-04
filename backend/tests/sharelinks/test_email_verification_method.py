"""Tests for ViewSession.email_verification_method."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from sharelinks.models import EmailVerificationToken, PreviewSession, ViewSession
from sharelinks.views import _build_visitor_context

pytestmark = pytest.mark.django_db


def _create_session(client, link):
    response = client.post('/api/v1/view-sessions/', {'share_link': link.id})
    assert response.status_code == 403
    assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}
    assert not ViewSession.objects.filter(share_link=link).exists()
    return response


def test_no_email_gate_records_no_method(public_client, share_link):
    vs = _create_session(public_client, share_link)
    assert vs.status_code == 403


def test_typed_email_without_verification_is_self_reported(public_client, share_link_requires_email):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    with patch('sharelinks.views._dispatch_automation_event') as mock_dispatch:
        response = public_client.post(f'/api/v1/links/{share_link_requires_email.slug}/request-access/', {'email': 'typed@example.com'}, format='json')
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_clicked_verification_link_is_verified(public_client, share_link_requires_email_verification):
    """Phase 1: this legacy workflow is denied at its authorization boundary."""
    link = share_link_requires_email_verification
    token = EmailVerificationToken.objects.create(share_link=link, email='proven@example.com')
    public_client.get(f'/api/v1/links/{link.slug}/view-data/?accessToken={token.token}')
    with patch('sharelinks.views._dispatch_automation_event') as mock_dispatch:
        response = public_client.post(f'/api/v1/links/{link.slug}/verify-access-token/confirm/', {'token': token.token}, format='json')
        assert response.status_code == 403
        assert response.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_link_owner_is_owner(api_client, share_link, user):
    vs = _create_session(api_client, share_link)
    assert vs.status_code == 403


def test_other_logged_in_user_is_account(share_link, user2):
    client = APIClient()
    client.force_authenticate(user=user2)
    vs = _create_session(client, share_link)
    assert vs.status_code == 403


def test_staff_user_viewing_other_users_link_is_account(share_link, user2):
    user2.is_staff = True
    user2.save()
    client = APIClient()
    client.force_authenticate(user=user2)
    vs = _create_session(client, share_link)
    assert vs.status_code == 403


def test_staff_user_via_view_data_is_account(public_client, share_link, user2):
    user2.is_staff = True
    user2.save()
    public_client.force_authenticate(user=user2)
    r = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert r.status_code == 403
    assert r.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_pre_patch_session_dict_yields_empty_method(public_client, share_link_requires_email):
    session = public_client.session
    session['authorized_share_links'] = {
        str(share_link_requires_email.id): {'email_verified': True, 'viewer_email': 'old@example.com'},
    }
    session.save()
    vs = _create_session(public_client, share_link_requires_email)
    assert vs.status_code == 403


def test_field_exposed_in_api_and_webhook_context(api_client, share_link):
    vs = ViewSession.objects.create(
        share_link=share_link, viewer_email='a@example.com', email_verification_method='verified',
    )
    r = api_client.get(f'/api/v1/view-sessions/{vs.id}/')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert r.status_code == 403
    assert r.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_field_is_read_only_via_api(api_client, share_link):
    vs = ViewSession.objects.create(share_link=share_link)
    api_client.patch(f'/api/v1/view-sessions/{vs.id}/', {'email_verification_method': 'verified'}, format='json')
    vs.refresh_from_db()
    assert vs.email_verification_method == ''


def test_email_verification_with_nda_flow_records_verified(public_client, share_link_requires_email_verification):
    link = share_link_requires_email_verification
    link.require_nda = True
    link.nda_version = 1
    link.nda_text = "Standard NDA Text"
    link.save()

    token = EmailVerificationToken.objects.create(share_link=link, email='nda_signer@example.com')
    public_client.get(f'/api/v1/links/{link.slug}/view-data/?accessToken={token.token}')
    r_confirm = public_client.post(
        f'/api/v1/links/{link.slug}/verify-access-token/confirm/', {'token': token.token}, format='json',
    )
    # Phase 1: this legacy request is denied before its former handler runs.
    assert r_confirm.status_code == 403
    assert r_confirm.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_owner_preview_session_flow_records_owner(public_client, share_link, user):
    preview = PreviewSession.objects.create(
        share_link=share_link,
        user=user,
        token='owner-preview-token',
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    r = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/?previewToken={preview.token}')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert r.status_code == 403
    assert r.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}


def test_staff_preview_session_flow_records_account(public_client, share_link, user2):
    user2.is_staff = True
    user2.save()
    preview = PreviewSession.objects.create(
        share_link=share_link,
        user=user2,
        token='staff-preview-token',
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    r = public_client.get(f'/api/v1/links/{share_link.slug}/view-data/?previewToken={preview.token}')
    # Phase 1: this legacy request is denied before its former handler runs.
    assert r.status_code == 403
    assert r.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}
