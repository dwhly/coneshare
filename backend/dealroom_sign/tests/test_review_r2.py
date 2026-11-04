"""Gate 3 regressions; mutation evidence is recorded in the worker status."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from datarooms.models import Dataroom, DataroomDocument, DataroomFolder
from dealroom.models import KeyScope, RoomPolicy
from dealroom_sign.client import Documenso, SignError
from dealroom_sign.models import ExecutedArtifact, NdaAcceptance, NdaPolicy, Workflow
from dealroom_sign.storage import publish, verify_seal
from dealroom_sign.workflows import command, process
from sharelinks.models import ShareLink, ShareLinkAccessGrant, Viewer
from .test_workflows import fixture, pdf, recipients, agent_client

pytestmark = pytest.mark.django_db
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def human(fixture):
    fixture.user.is_staff = True
    fixture.user.role = 'admin'
    fixture.user.save()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(fixture.user).access_token))
    return client


@pytest.fixture
def member_context(fixture, recipients):
    link = ShareLink.objects.create(dataroom=fixture.room, created_by=fixture.user, restrict_to_grants=True, enable_watermark=True)
    RoomPolicy.objects.create(room=fixture.room, entry_link=link)
    member = Viewer.objects.create(organization=fixture.org, email='member@example.test', name='Member', verified_at=timezone.now())
    grant = ShareLinkAccessGrant.objects.create(share_link=link, email=member.email, created_by=fixture.user)
    policy = NdaPolicy.objects.create(room=fixture.room, source_version=fixture.version, source_sha256=fixture.work.source_sha256, fields=recipients[0]['fields'])
    client = APIClient()
    session = client.session
    now = timezone.now().timestamp()
    session['dealroom_member'] = {'room_id': str(fixture.room.pk), 'member_id': str(member.pk), 'email': member.email, 'expires': now+3600, 'last_seen': now}
    session.save()
    client.cookies['sessionid'] = session.session_key
    return SimpleNamespace(link=link, member=member, grant=grant, policy=policy, client=client)


def nda_work(fixture, member_context, pdf):
    ctx = member_context
    with patch('dealroom_sign.workflows.source_bytes', return_value=pdf):
        return command(owner=fixture.user, room=fixture.room, version=fixture.version,
            recipients=[{'email': ctx.member.email, 'name': ctx.member.name, 'fields': ctx.policy.fields}],
            idempotency_key=f'nda:{fixture.room.pk}:{ctx.member.pk}:{ctx.policy.revision}',
            purpose='nda', member=ctx.member, policy=ctx.policy)


@pytest.mark.parametrize('route', ['who-viewed', 'sources', 'nda-policy'])
@pytest.mark.parametrize('location', ['query', 'body'])
def test_path_room_cannot_be_overridden(fixture, agent_client, route, location):
    client, key = agent_client
    allowed = Dataroom.objects.create(organization=fixture.org, created_by=fixture.user, name='Allowed')
    KeyScope.objects.create(key=key, rooms=[str(allowed.pk)])
    url = f'/api/v1/dealroom-sign/{route}/{fixture.room.pk}/'
    if location == 'query':
        response = client.get(url, {'room_id': str(allowed.pk)})
    else:
        response = client.generic('GET', url, json.dumps({'room_id': str(allowed.pk)}), content_type='application/json')
    assert response.status_code == 403
    assert client.get(f'/api/v1/dealroom-sign/{route}/{allowed.pk}/').status_code == 200


def test_two_members_only_see_subject_executed_folders(fixture, member_context, pdf):
    ctx = member_context
    ctx.policy.enabled = False
    ctx.policy.save()
    own = nda_work(fixture, ctx, pdf)
    other = Viewer.objects.create(organization=fixture.org, email='other@example.test', name='Other', verified_at=timezone.now())
    ShareLinkAccessGrant.objects.create(share_link=ctx.link, email=other.email, created_by=fixture.user)
    for work in [own, fixture.work]:
        work.envelope_id = 'env_' + str(work.pk)
        work.save()
        publish(work, [{'item_id': 'item', 'kind': 'sealed_pdf', 'sha256': 'x'*64, 'size': 10, 'key': 'test.pdf', 'pages': 1}])
    response = ctx.client.get(f'/api/v1/dealroom/recipient/{ctx.link.slug}/room/')
    assert response.status_code == 200, response.data
    names = {row['name'] for row in response.data['folders']}
    assert f'{ctx.member.pk}-{ctx.policy.revision}' in names
    assert fixture.work.envelope_id not in names
    assert 'Agreements' not in names
    session = ctx.client.session
    session['dealroom_member'] = {**session['dealroom_member'], 'member_id': str(other.pk), 'email': other.email}
    session.save()
    response = ctx.client.get(f'/api/v1/dealroom/recipient/{ctx.link.slug}/room/')
    assert response.status_code == 200
    names = {row['name'] for row in response.data['folders']}
    assert not {'Executed', 'NDAs', 'Agreements', f'{ctx.member.pk}-{ctx.policy.revision}', fixture.work.envelope_id} & names


@pytest.mark.parametrize('state', ['failed', 'quarantined', 'distributing', 'uncertain', 'awaiting_seal', 'cancelled', 'declined'])
def test_staff_resets_one_member_with_fresh_generation(fixture, member_context, pdf, human, agent_client, state):
    work = nda_work(fixture, member_context, pdf)
    work.state = state
    work.envelope_id = 'env_stuck'
    work.signing_token = 'stale_token'
    work.save()
    url = f'/api/v1/dealroom-sign/nda-reset/{fixture.room.pk}/{work.pk}/'
    assert agent_client[0].post(url, {}, format='json').status_code == 403
    assert member_context.client.post(url, {}, format='json').status_code in {401, 403}
    with patch('dealroom_sign.workflows.Documenso') as factory, patch('dealroom_sign.workflows.source_bytes', return_value=pdf):
        client = factory.return_value.__enter__.return_value
        response = human.post(url, {}, format='json')
        assert response.status_code == 201, response.data
        client.cancel.assert_called_once_with('env_stuck', work.external_id)
        replacement = Workflow.objects.get(pk=response.data['id'])
        assert replacement.idempotency_key.endswith(':g1')
        assert replacement.state == 'queued'
        work.refresh_from_db()
        assert work.state == 'cancelled' and not work.signing_token
        assert human.post(url, {}, format='json').data['id'] == str(replacement.pk)
        assert client.cancel.call_count == 1
    response = member_context.client.post(f'/api/v1/dealroom-sign/nda/{fixture.room.pk}/', {}, format='json')
    assert response.status_code == 201 and response.data['state'] == 'queued'
    assert Workflow.objects.filter(purpose='nda').count() == 2
    assert NdaPolicy.objects.get(pk=member_context.policy.pk).revision == member_context.policy.revision


def test_reset_requires_confirmed_cancellation(fixture, member_context, pdf, human):
    work = nda_work(fixture, member_context, pdf)
    work.state = 'distributing'; work.envelope_id = 'env_stuck'; work.save()
    with patch('dealroom_sign.workflows.Documenso') as factory:
        factory.return_value.__enter__.return_value.cancel.side_effect = SignError('sign_transport_error', uncertain=True)
        response = human.post(f'/api/v1/dealroom-sign/nda-reset/{fixture.room.pk}/{work.pk}/', {}, format='json')
    assert response.status_code == 400
    assert Workflow.objects.filter(purpose='nda').count() == 1
    work.refresh_from_db(); assert work.state == 'distributing'


@pytest.mark.parametrize('status,route', [('DRAFT', 'delete'), ('PENDING', 'cancel')])
def test_native_reset_invalidates_old_envelope(fixture, status, route):
    calls = []
    def respond(request):
        calls.append(request)
        if request.method == 'POST':
            return httpx.Response(200, json={'success': True})
        return httpx.Response(200, json={'id': 'env_test', 'teamId': 3, 'externalId': 'correlation', 'status': 'CANCELLED' if len(calls)>1 else status})
    with Documenso(fixture.credential, httpx.MockTransport(respond)) as client:
        client.cancel('env_test', 'correlation')
    assert [r.url.path for r in calls if r.method == 'POST'] == ['/api/v2/envelope/'+route]


def test_staff_page_displays_stuck_nda_recovery():
    page = (ROOT/'backend/dealroom_sign/templates/dealroom_sign/staff.html').read_text()
    assert 'Reset NDA' in page and 'nda-reset/' in page and 'env.last_error' in page


def test_agent_catalog_has_no_recipient_signing_capabilities():
    source = (ROOT/'mcp-server/coneshare_mcp/tools/signing.py').read_text()
    names = {node.name for node in ast.walk(ast.parse(source)) if isinstance(node, ast.AsyncFunctionDef) and node.decorator_list}
    assert not {'recipient_nda_enter', 'recipient_nda_start', 'recipient_nda_status'} & names
    generated = json.loads((ROOT/'mcp-server/coneshare_mcp/dealroom_tools.json').read_text())
    assert not [tool for tool in generated if '/dealroom-sign/nda/' in tool['path']]


def test_policy_toggle_keeps_acceptance_revision(fixture, member_context, pdf, human):
    ctx = member_context
    work = nda_work(fixture, ctx, pdf)
    NdaAcceptance.objects.create(room=fixture.room, member_id=str(ctx.member.pk), member_email=ctx.member.email, policy_revision=str(ctx.policy.revision), workflow=work)
    url = f'/api/v1/dealroom-sign/nda-policy/{fixture.room.pk}/'
    with patch('dealroom_sign.views.source_bytes', return_value=pdf):
        for enabled in [False, True, True]:
            response = human.put(url, {'version_id':str(fixture.version.pk), 'fields':ctx.policy.fields, 'enabled':enabled}, format='json')
            assert response.status_code == 200, response.data
            assert str(response.data['revision']) == str(ctx.policy.revision)
        fields = [{**ctx.policy.fields[0], 'positionX': 11}]
        changed = human.put(url, {'version_id':str(fixture.version.pk), 'fields':fields, 'enabled':True}, format='json')
        assert str(changed.data['revision']) != str(ctx.policy.revision)


def test_duplicate_command_does_not_fetch_or_parse_pdf(fixture, recipients):
    with patch('dealroom_sign.workflows.source_bytes', side_effect=AssertionError('PDF re-fetched')), patch('dealroom_sign.validation.PdfReader', side_effect=AssertionError('PDF re-parsed')):
        again = command(owner=fixture.user, room=fixture.room, version=fixture.version, recipients=recipients, idempotency_key='test')
    assert again.pk == fixture.work.pk


@pytest.mark.parametrize('bad', ['Signature is Invalid.', 'Digest Mismatch.', ''])
def test_every_pdf_signature_must_validate(bad):
    output = 'Signature #1:\n  - Signature Validation: Signature is Valid.\n  - Total document signed\nSignature #2:\n  - Signature Validation: '+bad+'\n'
    with patch('dealroom_sign.storage.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=output)), pytest.raises(SignError, match='sealed_signature_invalid'):
        verify_seal(b'%PDF-fixture')


def test_valid_multisignature_pdf_accepted():
    output = 'Signature #1:\n  - Signature Validation: Signature is Valid.\nSignature #2:\n  - Signature Validation: Signature is Valid.\n  - Total document signed\n'
    with patch('dealroom_sign.storage.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=output)):
        assert verify_seal(b'%PDF-fixture')['signature_valid']


def test_unexpected_errors_increment_attempts_and_backoff(fixture):
    with patch('dealroom_sign.workflows.Documenso', side_effect=RuntimeError):
        for attempt in [1, 2, 3]:
            before = timezone.now()
            process(fixture.work.pk)
            fixture.work.refresh_from_db()
            assert fixture.work.attempts == attempt
            assert (fixture.work.next_attempt_at-before).total_seconds() >= 15*2**attempt
            assert fixture.work.lease_until is None


def test_credential_team_change_warns_before_stranding_work(fixture, human):
    response = human.put('/api/v1/dealroom-sign/credentials/', {'team_id': 99, 'token': 'api_replacement'}, format='json')
    assert response.status_code == 400 and 'strand' in str(response.data)
    fixture.credential.refresh_from_db(); assert fixture.credential.team_id == 3


def test_staff_port_is_tailnet_only():
    import yaml
    compose = yaml.safe_load((ROOT/'deploy/chief-glue-v1/docker-compose.yml').read_text())
    assert compose['services']['web']['ports'] == ['100.110.241.2:8797:80']


def test_member_start_can_enter_identity_and_revocation(fixture, member_context, pdf):
    ctx = member_context
    url = f'/api/v1/dealroom-sign/nda/{fixture.room.pk}/'
    with patch('dealroom_sign.workflows.source_bytes', return_value=pdf):
        response = ctx.client.post(url, {}, format='json')
    assert response.status_code == 201
    assert ctx.client.get(url).data['can_enter'] is False
    work = Workflow.objects.get(purpose='nda')
    work.state = 'awaiting_signature'; work.signing_token = 'recipient_token'
    work.signer_projection = [{'email': ctx.member.email}]; work.save()
    assert ctx.client.get(url).data['can_enter'] is True
    response = ctx.client.post(url+'enter/', {}, format='json')
    assert response.status_code == 200 and response.data['signing_url'].endswith('/sign/recipient_token')
    assert response['Referrer-Policy'] == 'no-referrer'
    work.signer_projection = [{'email': 'other@example.test'}]; work.save()
    assert ctx.client.get(url).data['can_enter'] is False
    assert ctx.client.post(url+'enter/', {}, format='json').status_code == 403
    work.signer_projection = []; work.save()
    assert ctx.client.post(url+'enter/', {}, format='json').status_code == 403
    ctx.grant.revoked_at = timezone.now(); ctx.grant.save()
    assert ctx.client.get(url).status_code == 403
    assert ctx.client.post(url+'enter/', {}, format='json').status_code == 403


def test_subject_can_open_own_nda_evidence(fixture, member_context, pdf, monkeypatch):
    from dealroom.policy import evaluate
    from rest_framework.exceptions import PermissionDenied
    ctx = member_context
    work = nda_work(fixture, ctx, pdf)
    work.state = 'done'; work.envelope_id='env_own'; work.save()
    NdaAcceptance.objects.create(room=fixture.room, member_id=str(ctx.member.pk), member_email=ctx.member.email, policy_revision=str(ctx.policy.revision), workflow=work)
    publish(work, [{'item_id':'item','kind':'sealed_pdf','sha256':'a'*64,'size':10,'key':'own.pdf','pages':1}])
    artifact = ExecutedArtifact.objects.get(workflow=work)
    item = DataroomDocument.objects.get(document=artifact.version.document)
    request = SimpleNamespace(session=ctx.client.session)
    assert evaluate(request, ctx.link, document_id=str(item.pk)).allowed
    from io import BytesIO
    from PIL import Image
    from unittest.mock import MagicMock
    image = BytesIO(); Image.new('RGB', (400, 500), 'white').save(image, format='PNG')
    renderer = MagicMock(); renderer.get_page_storage_key.return_value = 'page.png'
    monkeypatch.setattr('sharelinks.views.get_renderer', lambda version: renderer)
    monkeypatch.setattr('sharelinks.views.fileserver_client.generate_download_url', lambda *a, **k: 'http://internal/page.png')
    monkeypatch.setattr('sharelinks.views.requests.get', lambda *a, **k: Mock(content=image.getvalue(), status_code=200))
    session = ctx.client.session
    session['authorized_share_links'] = {str(ctx.link.pk): {'email_verified': True, 'email_method': 'verified', 'viewer_email': ctx.member.email, 'viewer_name': ctx.member.name, 'viewer_organisation_name': 'Test'}}
    session.save()
    page_url = f'/api/v1/links/{ctx.link.slug}/render-page/1/?dataroom_document_id={item.pk}'
    response = ctx.client.get(page_url)
    assert response.status_code == 200, getattr(response, 'data', None)
    assert response['Content-Type'] == 'image/jpeg'
    assert response['Cache-Control'] == 'private, no-store'
    ctx.grant.revoked_at=timezone.now(); ctx.grant.save()
    with pytest.raises(PermissionDenied):
        evaluate(request, ctx.link, document_id=str(item.pk))
    assert ctx.client.get(page_url).status_code == 403


def test_approved_nda_edit_takes_effect(fixture, member_context, pdf, human, agent_client):
    ctx = member_context
    response = agent_client[0].put(f'/api/v1/dealroom-sign/nda-policy/{fixture.room.pk}/', {'version_id': str(fixture.version.pk), 'fields':ctx.policy.fields, 'enabled':False}, format='json')
    assert response.status_code == 202, response.data
    ctx.policy.refresh_from_db(); assert ctx.policy.enabled
    from dealroom.models import AccessApproval
    approval = AccessApproval.objects.latest('created_at')
    with patch('dealroom_sign.views.source_bytes', return_value=pdf):
        result = human.post(f'/api/v1/dealroom/approvals/{approval.pk}/approve/', {}, format='json')
    assert result.status_code == 200, result.data
    ctx.policy.refresh_from_db(); assert not ctx.policy.enabled


def test_ordinary_file_cannot_expose_private_executed_folder(fixture, member_context, pdf):
    ctx = member_context
    ctx.policy.enabled = False; ctx.policy.save()
    work = nda_work(fixture, ctx, pdf)
    publish(work, [{'item_id':'item', 'kind':'sealed_pdf', 'sha256':'b'*64, 'size':10, 'key':'own.pdf', 'pages':1}])
    folder = DataroomDocument.objects.get(document__versions__executedartifact__workflow=work).folder
    # A staff placement error must not reveal signer identity through an ordinary PDF.
    fixture.version.is_primary = True; fixture.version.save()
    item = DataroomDocument.objects.get(document=fixture.version.document)
    item.folder = folder; item.save()
    other = Viewer.objects.create(organization=fixture.org, email='other@example.test', verified_at=timezone.now())
    ShareLinkAccessGrant.objects.create(share_link=ctx.link, email=other.email, created_by=fixture.user)
    session = ctx.client.session
    session['dealroom_member'] = {**session['dealroom_member'], 'member_id':str(other.pk), 'email':other.email}
    session.save()
    response = ctx.client.get(f'/api/v1/dealroom/recipient/{ctx.link.slug}/room/')
    assert response.status_code == 200
    assert response.data['folders'] == []
    assert response.data['files'] == []


def test_different_verified_member_cannot_enter_signing(fixture, member_context, pdf):
    ctx = member_context
    work = nda_work(fixture, ctx, pdf)
    work.state='awaiting_signature'; work.signing_token='subject_token'; work.signer_projection=[{'email':ctx.member.email}]; work.save()
    other = Viewer.objects.create(organization=fixture.org, email='other@example.test', verified_at=timezone.now())
    ShareLinkAccessGrant.objects.create(share_link=ctx.link, email=other.email, created_by=fixture.user)
    session = ctx.client.session
    session['dealroom_member'] = {**session['dealroom_member'], 'member_id':str(other.pk), 'email':other.email}
    session.save()
    response = ctx.client.post(f'/api/v1/dealroom-sign/nda/{fixture.room.pk}/enter/', {}, format='json')
    assert response.status_code in {403,404}
    assert 'subject_token' not in str(response.data)


@pytest.mark.parametrize('endpoint', ['retrieve', 'list'])
def test_scoped_workflow_query_uses_actual_target(fixture, agent_client, endpoint):
    client, key = agent_client
    allowed = Dataroom.objects.create(organization=fixture.org, created_by=fixture.user, name='Allowed')
    KeyScope.objects.create(key=key, rooms=[str(allowed.pk)])
    suffix = f'{fixture.work.pk}/' if endpoint == 'retrieve' else f'?room_id={fixture.room.pk}'
    response = client.generic('GET', '/api/v1/dealroom-sign/envelopes/'+suffix,
        json.dumps({'room_id': str(allowed.pk)}), content_type='application/json')
    assert response.status_code == 403


def test_stuck_nda_status_identifies_subject_for_staff(fixture, member_context, pdf, human):
    work = nda_work(fixture, member_context, pdf)
    work.state = 'failed'; work.save()
    response = human.get(f'/api/v1/dealroom-sign/envelopes/{work.pk}/')
    assert response.status_code == 200
    assert response.data['member_email'] == member_context.member.email
    page = (ROOT/'backend/dealroom_sign/templates/dealroom_sign/staff.html').read_text()
    assert 'env.member_email' in page


@pytest.mark.parametrize('route', ['who-viewed', 'sources', 'nda-policy'])
@pytest.mark.parametrize('location', ['query', 'body'])
def test_path_conflicts_rejected_for_human_staff(fixture, human, route, location):
    url = f'/api/v1/dealroom-sign/{route}/{fixture.room.pk}/'
    if location == 'query':
        response = human.get(url, {'room_id': 'conflicting-room'})
    else:
        response = human.generic('GET', url, json.dumps({'room_id':'conflicting-room'}), content_type='application/json')
    assert response.status_code == 403
