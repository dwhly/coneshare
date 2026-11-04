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

@pytest.mark.django_db
def test_registry_covers_all_allowany_and_dynamic_recipient_views():
    from rest_framework.permissions import AllowAny
    from sharelinks import views
    from dealroom.registry import RECIPIENT
    found = {name for name, cls in vars(views).items() if isinstance(cls, type) and cls.__module__ == views.__name__ and AllowAny in getattr(cls, 'permission_classes', [])}
    assert len(found) == 16
    assert found <= RECIPIENT
    assert 'ViewSessionViewSet' in RECIPIENT
    assert all(e['boundary'] == 'denied' for e in registry().values() if e['operation_id'].startswith('filerequests_'))


@pytest.mark.django_db
def test_schema_mcp_static_parity():
    tools = json.loads((Path(__file__).resolve().parents[3] / 'mcp-server/coneshare_mcp/dealroom_tools.json').read_text())
    ids = {t['operation_id'] for t in tools}
    enabled = {oid for oid, entry in registry().items() if entry['boundary'] == 'staff'}
    assert enabled <= ids
    assert ids <= set(registry())
    assert len(tools) == len({t['name'] for t in tools})


def setup_recipient(staff):
    response = staff.post('/api/v1/dealroom/rooms/', {'name':'Recipient test'}, format='json')
    assert response.status_code == 201, response.data
    room_id = response.data['id']
    slug = response.data['entry_url'].split('/')[-1]
    grant = staff.post('/api/v1/dealroom/grants/', {'room':room_id,'email':'jane@acme.test'}, format='json')
    assert grant.status_code == 201, grant.data
    return room_id, slug


@pytest.mark.django_db
def test_otp_scanners_replay_wrong_room_attempt_caps_and_no_filename_leak(staff, settings, django_capture_on_commit_callbacks):
    import re
    from django.core import mail
    from dealroom.models import Challenge
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    room_id, slug = setup_recipient(staff)
    base = f'/api/v1/dealroom/recipient/{slug}'
    recipient = APIClient(enforce_csrf_checks=True)
    csrf = recipient.get(base+'/challenge/').data['csrf_token']
    assert recipient.post(base+'/challenge/', {'email':'jane@acme.test'}, format='json').status_code == 403
    with django_capture_on_commit_callbacks(execute=True):
        issued = recipient.post(base+'/challenge/', {'email':'jane@acme.test','name':'Jane'}, format='json', HTTP_X_CSRFTOKEN=csrf)
    assert issued.status_code == 200, issued.data
    code = re.search(r'code is (\d{6})', mail.outbox[-1].body)[1]
    cid = issued.data['challenge_id']
    assert recipient.get(base+'/room/').status_code in (401,403)
    recipient.get(base+'/challenge/?challenge='+cid)
    assert Challenge.objects.get(pk=cid).consumed_at is None
    for _ in range(5):
        result = recipient.post(base+'/confirm/', {'challenge_id':cid,'code':'000000' if code!='000000' else '111111'},format='json',HTTP_X_CSRFTOKEN=csrf)
        assert result.data['status'] == 'refused'
    assert Challenge.objects.get(pk=cid).attempts == 5
    assert recipient.post(base+'/confirm/', {'challenge_id':cid,'code':code},format='json',HTTP_X_CSRFTOKEN=csrf).data['status'] == 'refused'
    with django_capture_on_commit_callbacks(execute=True):
        fresh = recipient.post(base+'/challenge/', {'email':'jane@acme.test','name':'Jane'}, format='json',HTTP_X_CSRFTOKEN=csrf)
    cid = fresh.data['challenge_id']; code = re.search(r'code is (\d{6})', mail.outbox[-1].body)[1]
    result = recipient.post(base+'/confirm/', {'challenge_id':cid,'code':code},format='json',HTTP_X_CSRFTOKEN=csrf)
    assert result.data['status'] == 'verified', result.data
    assert recipient.get(base+'/room/').status_code == 200
    assert recipient.post(base+'/confirm/', {'challenge_id':cid,'code':code},format='json',HTTP_X_CSRFTOKEN=csrf).data['status'] == 'refused'
    for _ in range(3):
        assert recipient.post(base+'/challenge/', {'email':'jane@acme.test'},format='json',HTTP_X_CSRFTOKEN=csrf).status_code == 200
    assert recipient.post(base+'/challenge/', {'email':'jane@acme.test'},format='json',HTTP_X_CSRFTOKEN=csrf).status_code == 429


@pytest.mark.django_db
def test_member_rebinding_and_grant_expiry_edit_cannot_bypass_http_approval(staff, agent):
    from sharelinks.models import Viewer, ShareLinkAccessGrant
    room_id, slug = setup_recipient(staff)
    member = staff.post('/api/v1/dealroom/members/', {'email':'jane@acme.test','name':'Jane'},format='json')
    result = agent.patch(f'/api/v1/dealroom/members/{member.data["id"]}/',{'email':'bob@other.test'},format='json')
    assert result.status_code == 202
    assert Viewer.objects.get(pk=member.data['id']).email == 'jane@acme.test'
    grant = ShareLinkAccessGrant.objects.get(email='jane@acme.test')
    grant.expires_at = timezone.now() + timedelta(hours=1); grant.save()
    for patch in ({'expires_at':None}, {'download_ceiling':'original'}, {'revoked_at':None,'email':'replacement@other.test'}):
        result=agent.patch(f'/api/v1/dealroom/grants/{grant.pk}/',patch,format='json')
        assert result.status_code == 202, result.data
    grant.refresh_from_db()
    assert grant.download_ceiling == 'none' and grant.expires_at is not None and grant.email=='jane@acme.test'


@pytest.mark.django_db
def test_personalized_pages_private_no_store_success_and_warm_cache(staff, owner, monkeypatch):
    from PIL import Image
    from io import BytesIO
    from sharelinks.models import ShareLink, Viewer, ShareLinkDataroomSetting
    from datarooms.models import DataroomDocument
    from documents.models import Document, DocumentVersion
    room_id, slug=setup_recipient(staff)
    link=ShareLink.objects.get(slug=slug)
    member=Viewer.objects.create(organization=owner.organization,email='jane@acme.test',name='Jane',verified_at=timezone.now())
    doc=Document.objects.create(organization=owner.organization,created_by=owner,name='Test.pdf',type='pdf',content_type='application/pdf')
    DocumentVersion.objects.create(document=doc,version_number=1,is_primary=True,original_storage_key='test.pdf',storage_key='test.pdf',type='pdf',num_pages=1)
    item=DataroomDocument.objects.create(dataroom_id=room_id,document=doc)
    ShareLinkDataroomSetting.objects.filter(share_link=link,dataroom_document=item).update(enable_watermark=True)
    image=BytesIO(); Image.new('RGB',(400,500),'white').save(image,format='PNG')
    from unittest.mock import MagicMock
    renderer=MagicMock();renderer.get_page_storage_key.return_value='page.png'
    monkeypatch.setattr('sharelinks.views.get_renderer', lambda version:renderer)
    monkeypatch.setattr('sharelinks.views.fileserver_client.generate_download_url',lambda *a,**k:'http://internal/page.png')
    response=MagicMock();response.content=image.getvalue()
    monkeypatch.setattr('sharelinks.views.requests.get',lambda *a,**k:response)
    recipient=APIClient();session=recipient.session;now=timezone.now().timestamp()
    session['dealroom_member']={'room_id':room_id,'member_id':str(member.pk),'email':member.email,'expires':now+3600,'last_seen':now}
    session['authorized_share_links']={str(link.pk):{'email_verified':True,'email_method':'verified','viewer_email':member.email,'viewer_name':'Jane','viewer_organisation_name':'Acme'}};session.save()
    path=f'/api/v1/links/{slug}/render-page/1/?dataroom_document_id={item.pk}'
    first=recipient.get(path)
    assert first.status_code==200, getattr(first,'data',None)
    assert first['Cache-Control']=='private, no-store'
    assert first['X-Dealroom-Copy-ID']
    warm=recipient.get(path,HTTP_IF_NONE_MATCH='"cached"')
    assert warm.status_code==200 and warm['Cache-Control']=='private, no-store'
    assert warm['X-Dealroom-Copy-ID']==first['X-Dealroom-Copy-ID']

@pytest.mark.django_db
def test_original_exception_bounded_approved_and_consumed_once(staff, agent, owner, monkeypatch):
    from unittest.mock import MagicMock
    from sharelinks.models import ShareLink, ShareLinkAccessGrant, Viewer, ShareLinkDataroomSetting
    from datarooms.models import DataroomDocument
    from documents.models import Document, DocumentVersion
    from dealroom.models import OriginalException, CopyEvidence
    from django.utils import timezone
    import zipfile,io,json,hashlib
    room_id,slug=setup_recipient(staff)
    link=ShareLink.objects.get(slug=slug)
    member=Viewer.objects.create(organization=owner.organization,email='jane@acme.test',name='Jane',verified_at=timezone.now())
    grant=ShareLinkAccessGrant.objects.get(share_link=link,email=member.email)
    grant.download_ceiling='original';grant.save()
    doc=Document.objects.create(organization=owner.organization,created_by=owner,name='Original.pdf',type='pdf',content_type='application/pdf')
    version=DocumentVersion.objects.create(document=doc,version_number=1,is_primary=False,original_storage_key='source.pdf',type='pdf')
    DocumentVersion.objects.create(document=doc,version_number=2,is_primary=True,original_storage_key='new.pdf',type='pdf')
    item=DataroomDocument.objects.create(dataroom_id=room_id,document=doc)
    ShareLinkDataroomSetting.objects.filter(share_link=link,dataroom_document=item).update(allow_download=True,download_ceiling='original',enable_watermark=True)
    payload={'room':room_id,'version':str(version.pk),'member':str(member.pk),'grant':str(grant.pk),'reason':'Approved diligence source','expires_at':(timezone.now()+timedelta(days=1)).isoformat(),'max_uses':1}
    pending=agent.post('/api/v1/dealroom/original-exceptions/',payload,format='json')
    assert pending.status_code==202,pending.data
    assert OriginalException.objects.count()==0
    approved=staff.post('/api/v1/dealroom/approvals/'+pending.data['approval_id']+'/approve/')
    assert approved.status_code==200,approved.data
    exception=OriginalException.objects.get()
    assert exception.approved_by==owner
    bad={**payload,'expires_at':(timezone.now()+timedelta(days=8)).isoformat()}
    assert staff.post('/api/v1/dealroom/original-exceptions/',bad,format='json').status_code==400
    recipient=APIClient();session=recipient.session;now=timezone.now().timestamp()
    session['dealroom_member']={'room_id':room_id,'member_id':str(member.pk),'email':member.email,'expires':now+3600,'last_seen':now}
    session['authorized_share_links']={str(link.pk):{'email_verified':True,'email_method':'verified','viewer_email':member.email,'viewer_name':'Jane'}};session.save()
    monkeypatch.setattr('dealroom.downloads.fileserver_client.generate_download_url',lambda *a,**k:'http://internal/source.pdf')
    response=MagicMock();response.__enter__.return_value=response;response.iter_content.return_value=[b'unchanged original bytes']
    monkeypatch.setattr('dealroom.downloads.requests.get',lambda *a,**k:response)
    url=f'/api/v1/dealroom/recipient/{slug}/original/{exception.pk}/'
    delivered=recipient.post(url)
    assert delivered.status_code==200,getattr(delivered,'data',None)
    bundle=zipfile.ZipFile(io.BytesIO(b''.join(delivered.streaming_content)))
    assert bundle.read('original.pdf')==b'unchanged original bytes'
    receipt=bundle.read('receipt.json')
    assert CopyEvidence.objects.get().receipt_sha256==hashlib.sha256(receipt).hexdigest()
    assert CopyEvidence.objects.get().version_id==version.pk
    exception.refresh_from_db();assert exception.used_count==1
    assert recipient.post(url).status_code==403
    owner.role='member';owner.save(update_fields=['role'])
    assert staff.post('/api/v1/dealroom/original-exceptions/',payload,format='json').status_code==403


def test_expiry_timezone_encoding_cannot_bypass_widening():
    assert widens_access({'widens_access':'evaluate_change'}, {'expires_at':'2026-11-04T12:00:00Z'}, {'expires_at':'2026-11-04T11:00:00-08:00'})


@pytest.mark.django_db
def test_room_expiry_patch_uses_room_policy_before_image(staff, agent):
    from dealroom.models import RoomPolicy
    room_id, slug=setup_recipient(staff)
    RoomPolicy.objects.filter(room_id=room_id).update(expires_at=timezone.now()+timedelta(hours=1))
    result=agent.patch(f'/api/v1/dealroom/rooms/{room_id}/policy/', {'expires_at':(timezone.now()+timedelta(days=1)).isoformat()},format='json')
    assert result.status_code==202,result.data
    assert RoomPolicy.objects.get(room_id=room_id).expires_at < timezone.now()+timedelta(hours=2)


def test_recipient_email_domain_uses_idna_alabel():
    from sharelinks.models import ViewerOrganisation
    assert ViewerOrganisation.normalize_domain('jane@bücher.test') == 'xn--bcher-kva.test'


def test_no_served_view_can_override_the_central_drf_hook():
    from rest_framework.views import APIView
    from drf_spectacular.generators import SchemaGenerator
    generator=SchemaGenerator();generator._initialise_endpoints()
    for _,_,_,callback in generator.endpoints:
        cls=callback.cls
        assert cls.initial is APIView.initial,cls
        assert cls.dispatch is APIView.dispatch,cls


@pytest.mark.django_db
@pytest.mark.parametrize('case', ['grant_ceiling','grant_expiry_extend','grant_expiry_clear','grant_restore','member_email','member_org','org_domain','room_restore','invitation_loosen','link_restore','link_expiry_clear','link_password','link_scope','automation_destination','webhook_destination','file_original'])
def test_each_edit_to_widen_cannot_bypass_the_http_gate(case,staff,agent,owner):
    from sharelinks.models import ShareLink,ShareLinkAccessGrant,Viewer,ViewerOrganisation,ShareLinkDataroomSetting
    from datarooms.models import DataroomDocument
    from documents.models import Document
    from dealroom.models import RoomPolicy
    room_id,slug=setup_recipient(staff)
    link=ShareLink.objects.get(slug=slug)
    grant=ShareLinkAccessGrant.objects.get(share_link=link,email='jane@acme.test')
    expected=202
    if case.startswith('grant_'):
        url=f'/api/v1/dealroom/grants/{grant.pk}/'
        if case=='grant_ceiling':data={'download_ceiling':'watermarked'}
        elif case=='grant_restore':grant.revoked_at=timezone.now();grant.save();data={'revoked_at':None}
        else:
            grant.expires_at=timezone.now()+timedelta(hours=1);grant.save()
            data={'expires_at':None if case=='grant_expiry_clear' else (timezone.now()+timedelta(days=1)).isoformat()}
    elif case.startswith('member_'):
        member=Viewer.objects.create(organization=owner.organization,email='jane@acme.test')
        org=ViewerOrganisation.objects.create(organization=owner.organization,name='Other',email_domains=['other.test'])
        url=f'/api/v1/dealroom/members/{member.pk}/'
        data={'email':'rebound@other.test'} if case=='member_email' else {'recipient_org':str(org.pk)}
    elif case=='org_domain':
        org=ViewerOrganisation.objects.create(organization=owner.organization,name='Acme',email_domains=['acme.test'])
        url=f'/api/v1/dealroom/orgs/{org.pk}/';data={'email_domains':['acme.test','other.test'],'confirm_domains':True}
    elif case in ('room_restore','invitation_loosen'):
        RoomPolicy.objects.filter(room_id=room_id).update(status='archived')
        url=f'/api/v1/dealroom/rooms/{room_id}/policy/'
        data={'status':'active'} if case=='room_restore' else {'invitation_mode':'automatic_same_org'}
    elif case.startswith('link_'):
        link.is_active=False;link.expires_at=timezone.now()+timedelta(hours=1);link.save()
        if case in ('link_password','link_scope'):
            url=f'/api/v1/share-links/{link.pk}/';data={'password':None} if case=='link_password' else {'dataroom':room_id};expected=403
        else:
            url=f'/api/v1/dealroom/share-links/{link.pk}/';data={'is_active':True} if case=='link_restore' else {'expires_at':None}
    elif case in ('automation_destination','webhook_destination'):
        from django.urls import resolve
        entries=[entry for entry in registry().values() if entry['operation_id'].startswith('automations_') and entry['method']=='PATCH']
        assert entries
        entry=entries[0];url=entry['path'].replace('{id}',str(link.pk)).replace('{id_2}',str(link.pk));data={'url':'https://outside.test'};expected=403
    else:
        doc=Document.objects.create(organization=owner.organization,created_by=owner,name='Ceiling.pdf',type='pdf',content_type='application/pdf')
        item=DataroomDocument.objects.create(dataroom_id=room_id,document=doc)
        policy=ShareLinkDataroomSetting.objects.get(share_link=link,dataroom_document=item)
        url=f'/api/v1/dealroom/file-policies/{policy.pk}/';data={'download_ceiling':'original'}
    result=agent.patch(url,data,format='json')
    assert result.status_code==expected,(case,result.data)
    if expected==202:
        assert AccessApproval.objects.get(pk=result.data['approval_id']).status=='pending_approval'


@pytest.mark.django_db
def test_layout_preference_has_ui_mcp_parity_and_defaults_topbar(staff):
    url='/api/v1/dealroom/preferences/'
    assert staff.get(url).data=={'layout':'topbar'}
    assert staff.patch(url,{'layout':'sidebar'},format='json').data=={'layout':'sidebar'}
    assert staff.get(url).data=={'layout':'sidebar'}
    assert staff.patch(url,{'layout':'unsafe'},format='json').status_code==400


@pytest.mark.django_db
def test_issuance_ip_cap_aggregates_emails_and_ignores_untrusted_spoof(staff,settings):
    room_id,slug=setup_recipient(staff)
    recipient=APIClient()
    settings.TRUSTED_PROXIES=['127.0.0.1']
    base=f'/api/v1/dealroom/recipient/{slug}/challenge/'
    for index in range(20):
        response=recipient.post(base,{'email':f'viewer{index}@other.test'},format='json',REMOTE_ADDR='198.51.100.8',HTTP_X_FORWARDED_FOR=f'203.0.113.{index}')
        assert response.status_code==200,response.data
    response=recipient.post(base,{'email':'different@other.test'},format='json',REMOTE_ADDR='198.51.100.8',HTTP_X_FORWARDED_FOR='203.0.113.250')
    assert response.status_code==429
