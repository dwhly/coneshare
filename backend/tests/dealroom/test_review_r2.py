"""Gate 3 regressions; exercise the deployed policy with real OTP proofs."""
import re
import pytest
from django.core import mail
from rest_framework.test import APIClient
from tests.dealroom.test_foundation import owner, staff, agent, setup_recipient


def verify(staff, slug, capture, email='jane@acme.test'):
    client = APIClient(enforce_csrf_checks=True)
    base = f'/api/v1/dealroom/recipient/{slug}'
    csrf = client.get(base + '/challenge/').data['csrf_token']
    with capture(execute=True):
        issued = client.post(base + '/challenge/', {'email': email, 'name': 'Jane'}, format='json', HTTP_X_CSRFTOKEN=csrf)
    code = re.search(r'code is (\d{6})', mail.outbox[-1].body)[1]
    result = client.post(base + '/confirm/', {'challenge_id': issued.data['challenge_id'], 'code': code}, format='json', HTTP_X_CSRFTOKEN=csrf)
    return client, result


@pytest.mark.django_db
def test_r2_03_recipient_folders_require_visible_permitted_content(staff, owner, django_capture_on_commit_callbacks, monkeypatch):
    from datarooms.models import DataroomFolder, DataroomDocument
    from documents.models import Document, DocumentVersion
    from sharelinks.models import ShareLink, ShareLinkDataroomSetting
    from rest_framework.exceptions import PermissionDenied
    import dealroom.recipient as recipient
    room, slug = setup_recipient(staff)
    link = ShareLink.objects.get(slug=slug)
    folders = {}
    for name in ('Financials', 'Bidder B – LOI', 'Empty', 'Executed', 'NDAs'):
        folders[name] = DataroomFolder.objects.create(dataroom_id=room, name=name, created_by=owner, parent=folders.get('Executed') if name == 'NDAs' else None)
    private_id = None
    for name in ('Financials', 'Bidder B – LOI', 'NDAs'):
        doc = Document.objects.create(organization=owner.organization, created_by=owner, name=name + '.pdf')
        DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True)
        item = DataroomDocument.objects.create(dataroom_id=room, folder=folders[name], document=doc)
        if name == 'NDAs':
            private_id = str(item.pk)
    ShareLinkDataroomSetting.objects.filter(share_link=link, dataroom_folder=folders['Bidder B – LOI']).update(is_visible=False)
    original = recipient.evaluate
    def subject_policy(request, link, **kwargs):
        if kwargs.get('document_id') == private_id:
            raise PermissionDenied('Execution artifact belongs to another member.')
        return original(request, link, **kwargs)
    monkeypatch.setattr(recipient, 'evaluate', subject_policy)
    client, result = verify(staff, slug, django_capture_on_commit_callbacks)
    assert result.data['status'] == 'verified'
    result = client.get(f'/api/v1/dealroom/recipient/{slug}/room/')
    assert result.status_code == 200
    assert [f['name'] for f in result.data['folders']] == ['Financials']
    assert [f['name'] for f in result.data['files']] == ['Financials.pdf']


@pytest.mark.django_db
@pytest.mark.parametrize('encoding', ['multipart', 'urlencoded'])
@pytest.mark.parametrize('case', ['grant_restore', 'member_restore', 'room_restore'])
def test_r2_01_form_mutations_cannot_restore_access(staff, agent, owner, encoding, case):
    from django.utils import timezone
    from sharelinks.models import ShareLinkAccessGrant, Viewer
    from dealroom.models import RoomPolicy, AccessApproval
    room, slug = setup_recipient(staff)
    if case == 'grant_restore':
        obj = ShareLinkAccessGrant.objects.get(email='jane@acme.test')
        obj.revoked_at = timezone.now(); obj.save()
        url, data, field = f'/api/v1/dealroom/grants/{obj.pk}/', {'revoked_at': ''}, 'revoked_at'
    elif case == 'member_restore':
        obj = Viewer.objects.create(organization=owner.organization, email='jane@acme.test', disabled_at=timezone.now())
        url, data, field = f'/api/v1/dealroom/members/{obj.pk}/', {'disabled_at': ''}, 'disabled_at'
    else:
        obj = RoomPolicy.objects.get(room_id=room); obj.status = 'archived'; obj.save()
        url, data, field = f'/api/v1/dealroom/rooms/{room}/policy/', {'status': 'active'}, 'status'
    before = getattr(obj, field)
    if encoding == 'multipart':
        result = agent.patch(url, data, format='multipart')
    else:
        from urllib.parse import urlencode
        result = agent.patch(url, urlencode(data), content_type='application/x-www-form-urlencoded')
    assert result.status_code == 415, result.data
    obj.refresh_from_db(); assert getattr(obj, field) == before
    assert not AccessApproval.objects.exists()


@pytest.mark.parametrize('field,value', [('revoked_at', ['']), ('disabled_at', ['']), ('status', ['active']), ('name', {'nested': 'change'})])
def test_r2_01_non_scalar_changes_are_widening(field, value):
    from dealroom.registry import widens_access
    assert widens_access({'widens_access': 'evaluate_change'}, {field: 'old'}, {field: value})


@pytest.mark.django_db
def test_r2_02_grant_revoke_does_not_deny_org_member_and_restore_is_audited(staff, agent, owner, django_capture_on_commit_callbacks):
    from sharelinks.models import ViewerOrganisation, ShareLinkAccessGrant, ShareLink, Viewer
    from dealroom.models import MemberDeny, Activity
    room, slug = setup_recipient(staff)
    link = ShareLink.objects.get(slug=slug)
    org = ViewerOrganisation.objects.create(organization=owner.organization, name='Acme', email_domains=['acme.test'])
    ShareLinkAccessGrant.objects.create(share_link=link, viewer_organisation=org)
    client, result = verify(staff, slug, django_capture_on_commit_callbacks)
    assert result.data['status'] == 'verified'
    member = Viewer.objects.get(email='jane@acme.test')
    named = ShareLinkAccessGrant.objects.get(share_link=link, email=member.email)
    assert staff.delete(f'/api/v1/dealroom/grants/{named.pk}/').status_code == 204
    assert not MemberDeny.objects.exists()
    url = f'/api/v1/dealroom/recipient/{slug}/room/'
    assert client.get(url).status_code == 200
    payload = {'room': room, 'member': str(member.pk)}
    for action, expected in [('deny-member', 403), ('restore-member', 200)]:
        before = MemberDeny.objects.count()
        pending = agent.post(f'/api/v1/dealroom/grants/{action}/', payload, format='json')
        assert pending.status_code == 202, pending.data
        assert MemberDeny.objects.count() == before
        approved = staff.post(f'/api/v1/dealroom/approvals/{pending.data["approval_id"]}/approve/', {}, format='json')
        assert approved.status_code == 200, approved.data
        assert client.get(url).status_code == expected
    assert Activity.objects.filter(event_type='member.denied', room_id=room, target_id=str(member.pk)).count() == 1
    assert Activity.objects.filter(event_type='member.restored', room_id=room, target_id=str(member.pk)).count() == 1
    assert staff.post('/api/v1/dealroom/grants/', {'room': room, 'email': member.email}, format='json').status_code == 201


@pytest.mark.django_db
def test_r2_04_active_grants_normalized_unique_and_regrantable(staff, owner):
    from sharelinks.models import ShareLinkAccessGrant, ShareLink, ViewerOrganisation
    from dealroom.serializers import GrantSerializer
    from django.db import IntegrityError, transaction
    room, slug = setup_recipient(staff)
    assert GrantSerializer().validate_email(' Jane@Acme.test ') == 'jane@acme.test'
    url = '/api/v1/dealroom/grants/'
    duplicate = staff.post(url, {'room': room, 'email': ' Jane@Acme.test '}, format='json')
    assert duplicate.status_code == 400
    grant = ShareLinkAccessGrant.objects.get(email='jane@acme.test')
    assert staff.delete(f'{url}{grant.pk}/').status_code == 204
    replacement = staff.post(url, {'room': room, 'email': 'Jane@Acme.test'}, format='json')
    assert replacement.status_code == 201, replacement.data
    assert replacement.data['email'] == 'jane@acme.test'
    assert staff.patch(f'{url}{grant.pk}/', {'revoked_at': None}, format='json').status_code == 400
    link = ShareLink.objects.get(slug=slug)
    with pytest.raises(IntegrityError), transaction.atomic():
        ShareLinkAccessGrant.objects.create(share_link=link, email='jane@acme.test')
    org = ViewerOrganisation.objects.create(organization=owner.organization, name='Acme', email_domains=['acme.test'])
    data = {'room': room, 'viewer_organisation': str(org.pk)}
    created = staff.post(url, data, format='json'); assert created.status_code == 201
    assert staff.post(url, data, format='json').status_code == 400
    with pytest.raises(IntegrityError), transaction.atomic():
        ShareLinkAccessGrant.objects.create(share_link=link, viewer_organisation=org)
    assert staff.delete(f'{url}{created.data["id"]}/').status_code == 204
    assert staff.post(url, data, format='json').status_code == 201


@pytest.mark.django_db
def test_r2_05_agent_cannot_acknowledge_own_drift(staff, agent):
    from dealroom.models import Drift
    room, slug = setup_recipient(staff)
    pending = agent.post('/api/v1/dealroom/grants/', {'room': room, 'email': 'new@acme.test'}, format='json')
    drift = Drift.objects.get(approval_id=pending.data['approval_id'])
    url = f'/api/v1/dealroom/drift/{drift.pk}/acknowledge/'
    assert agent.post(url, {}, format='json').status_code == 403
    drift.refresh_from_db(); assert drift.acknowledged_at is None
    assert staff.post(url, {}, format='json').status_code == 200


@pytest.mark.django_db
def test_r2_07_used_org_archives_and_retains_evidence(staff, owner):
    from sharelinks.models import ShareLinkAccessGrant, ShareLink, ViewerOrganisation, Viewer
    from documents.models import Document, DocumentVersion
    from dealroom.models import OriginalException
    from django.utils import timezone
    from datetime import timedelta
    room, slug = setup_recipient(staff)
    org = ViewerOrganisation.objects.create(organization=owner.organization, name='Acme', email_domains=['acme.test'])
    grant = ShareLinkAccessGrant.objects.create(share_link=ShareLink.objects.get(slug=slug), viewer_organisation=org)
    member = Viewer.objects.create(organization=owner.organization, email='member@acme.test')
    document = Document.objects.create(organization=owner.organization, created_by=owner, name='Evidence')
    version = DocumentVersion.objects.create(document=document, version_number=1, is_primary=True)
    evidence = OriginalException.objects.create(room_id=room, grant=grant, member=member, version=version, reason='Retain audit', approved_by=owner, expires_at=timezone.now()+timedelta(days=1))
    assert staff.delete(f'/api/v1/dealroom/orgs/{org.pk}/').status_code == 204
    org.refresh_from_db(); grant.refresh_from_db(); evidence.refresh_from_db()
    assert org.archived_at and grant.revoked_at
    assert staff.post('/api/v1/dealroom/grants/', {'room': room, 'viewer_organisation': str(org.pk)}, format='json').status_code == 400


@pytest.mark.django_db
def test_r2_08_denial_survives_transaction_rollback(staff, owner, django_capture_on_commit_callbacks):
    from dealroom.models import Activity
    from sharelinks.models import ShareLinkAccessGrant
    from django.utils import timezone
    room, slug = setup_recipient(staff)
    client, result = verify(staff, slug, django_capture_on_commit_callbacks)
    assert result.data['status'] == 'verified'
    ShareLinkAccessGrant.objects.filter(email='jane@acme.test').update(revoked_at=timezone.now())
    assert client.get(f'/api/v1/dealroom/recipient/{slug}/room/').status_code == 403
    fact = Activity.objects.get(event_type='access.denied', room_id=room)
    assert fact.data['status'] == 403


@pytest.mark.django_db
def test_r2_08_original_download_does_not_acquire_render_semaphore(staff, monkeypatch):
    from dealroom import hooks
    from unittest.mock import Mock
    semaphore = Mock(); monkeypatch.setattr(hooks, 'RENDER_SEMAPHORE', semaphore)
    room, slug = setup_recipient(staff)
    result = APIClient().post(f'/api/v1/dealroom/recipient/{slug}/original/00000000-0000-0000-0000-000000000001/')
    assert result.status_code == 403
    semaphore.acquire.assert_not_called()


@pytest.mark.django_db
def test_r2_09_legacy_prefix_authenticates_only_matching_hash(owner):
    from core.authentication import generate_raw_api_key
    from core.models import APIKey
    raw, prefix, hashed = generate_raw_api_key()
    APIKey.objects.create(user=owner, name='Legacy key', prefix=raw[:12], hashed_key=hashed, tier='read_only')
    client = APIClient(); client.credentials(HTTP_AUTHORIZATION='Bearer '+raw)
    assert client.get('/api/v1/dealroom/rooms/').status_code == 200
    client.credentials(HTTP_AUTHORIZATION='Bearer '+raw[:-1]+('0' if raw[-1]!='0' else '1'))
    assert client.get('/api/v1/dealroom/rooms/').status_code == 401


@pytest.mark.django_db
def test_r2_10_magic_token_is_fragment_only(staff, django_capture_on_commit_callbacks):
    from urllib.parse import urlsplit, parse_qs
    room, slug = setup_recipient(staff)
    client, result = verify(staff, slug, django_capture_on_commit_callbacks)
    assert result.data['status'] == 'verified'
    url = re.search(r'Confirm explicitly at (\S+)', mail.outbox[-1].body)[1]
    assert not urlsplit(url).query
    assert set(parse_qs(urlsplit(url).fragment)) == {'challenge', 'token'}


@pytest.mark.django_db
def test_r2_06_approval_reports_target_current_state_and_proposed_change(staff, agent):
    from sharelinks.models import ShareLinkAccessGrant
    room, slug = setup_recipient(staff)
    grant = ShareLinkAccessGrant.objects.get(email='jane@acme.test')
    path = f'/api/v1/dealroom/grants/{grant.pk}/'
    pending = agent.patch(path, {'download_ceiling': 'watermarked'}, format='json')
    assert pending.status_code == 202
    result = staff.get(f'/api/v1/dealroom/approvals/{pending.data["approval_id"]}/')
    assert result.data['path'] == path
    assert result.data['current_state']['email'] == 'jane@acme.test'
    assert result.data['current_state']['download_ceiling'] == 'none'
    assert result.data['payload'] == {'download_ceiling': 'watermarked'}


@pytest.mark.django_db
@pytest.mark.parametrize('case', ['bob', 'member_deny', 'revoked_page', 'wrong_room', 'idle', 'grant_ceiling', 'file_ceiling'])
def test_r2_12_recipient_policy_after_real_otp(case, staff, owner, django_capture_on_commit_callbacks):
    from datetime import timedelta
    from django.utils import timezone
    from dealroom.models import MemberDeny
    from sharelinks.models import ShareLink, ShareLinkAccessGrant, Viewer, ViewerOrganisation, ShareLinkDataroomSetting
    from datarooms.models import DataroomDocument
    from documents.models import Document, DocumentVersion
    room, slug = setup_recipient(staff)
    link = ShareLink.objects.get(slug=slug)
    org = ViewerOrganisation.objects.create(organization=owner.organization, name='Acme', email_domains=['acme.test'])
    ShareLinkAccessGrant.objects.create(share_link=link, viewer_organisation=org, download_ceiling='original')
    grant = ShareLinkAccessGrant.objects.get(share_link=link, email='jane@acme.test')
    grant.download_ceiling = 'watermarked' if case == 'grant_ceiling' else 'original'; grant.save()
    doc = Document.objects.create(organization=owner.organization, created_by=owner, name='Confidential.pdf')
    DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True)
    item = DataroomDocument.objects.create(dataroom_id=room, document=doc)
    ShareLinkDataroomSetting.objects.filter(share_link=link, dataroom_document=item).update(allow_download=True, download_ceiling='watermarked' if case=='file_ceiling' else 'original')
    client, result = verify(staff, slug, django_capture_on_commit_callbacks, email='bob@other.test' if case=='bob' else 'jane@acme.test')
    url = f'/api/v1/dealroom/recipient/{slug}/room/'
    if case == 'bob':
        assert result.data['status'] == 'refused'
        assert client.get(url).status_code == 403
        return
    assert result.data['status'] == 'verified'
    assert client.get(url).status_code == 200
    if case == 'member_deny':
        MemberDeny.objects.create(room_id=room, member=Viewer.objects.get(email='jane@acme.test'))
        assert client.get(url).status_code == 403
    elif case == 'revoked_page':
        ShareLinkAccessGrant.objects.filter(share_link=link).update(revoked_at=timezone.now())
        result = client.get(f'/api/v1/links/{slug}/render-page/1/?dataroom_document_id={item.pk}')
        assert result.status_code == 403
    elif case == 'wrong_room':
        other = staff.post('/api/v1/dealroom/rooms/', {'name':'Other'}, format='json')
        other_slug = other.data['entry_url'].split('/')[-1]
        assert staff.post('/api/v1/dealroom/grants/', {'room': other.data['id'], 'email': 'jane@acme.test'}, format='json').status_code == 201
        assert client.get(f'/api/v1/dealroom/recipient/{other_slug}/room/').status_code == 403
    elif case == 'idle':
        session = client.session
        proof = session['dealroom_member']; proof['last_seen'] = timezone.now().timestamp()-1801
        session['dealroom_member'] = proof; session.save()
        assert client.get(url).status_code == 403
    else:
        assert client.get(url).data['files'][0]['download_level'] == 'watermarked'
