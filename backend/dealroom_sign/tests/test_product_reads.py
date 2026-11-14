"""Slice 1 contracts. Native/storage transports are isolated; all identities are fixtures."""
import ast
import asyncio
import hashlib
import hmac
import io
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from datetime import timedelta

import httpx
import pytest
from django.core.management import call_command
from django.utils import timezone
from pypdf import PdfReader, PdfWriter
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.authentication import generate_raw_api_key
from core.models import APIKey, Organization, User
from datarooms.models import Dataroom, DataroomDocument
from dealroom.models import AccessApproval, Activity, KeyScope
from dealroom.registry import registry
from dealroom_sign import models
from dealroom_sign.client import Documenso
from dealroom_sign.evidence import refresh_audit, snapshot_fields
from dealroom_sign.exports import existing_artifact, stamp_partial
from dealroom_sign.models import ExecutedArtifact, ObservedSignEvent, SignCredential, Workflow
from documents.models import Document, DocumentPage, DocumentVersion

pytestmark = pytest.mark.django_db
PREFIX = '/api/v1/dealroom-sign'
KEY = 'fixture-board-proxy-key'
EXPORT_OP = 'dealroom_sign_SignatureExportView_endpoint_post'


def headers(method, path, body=b'', *, login='staff@example.test', board='fixture', via='tailscale', stamp=None):
    context = json.dumps({'board': board, 'login': login, 'via': via}, sort_keys=True, separators=(',', ':'))
    stamp = str(int(time.time()) if stamp is None else stamp)
    fields = [method, path, hashlib.sha256(body).hexdigest(), stamp, context]
    message = b''.join(str(len(f.encode())).encode() + b':' + f.encode() for f in fields)
    signature = hmac.new(KEY.encode(), message, hashlib.sha256).hexdigest()
    return {'HTTP_X_BOARD_CONTEXT': context, 'HTTP_X_BOARD_TIMESTAMP': stamp, 'HTTP_X_BOARD_SIGNATURE': signature}


@pytest.fixture(autouse=True)
def no_remote_network():
    with patch('httpx.HTTPTransport.handle_request', side_effect=AssertionError('Unexpected network call')), \
         patch('requests.sessions.Session.send', side_effect=AssertionError('Unexpected network call')):
        yield


@pytest.fixture
def base(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    settings.BOARD_SIGN_PROXY_KEY = KEY
    org = Organization.objects.create(name='Fixture Organisation')
    user = User.objects.create_user(username='staff@example.test', email='staff@example.test', password='fixture', organization=org, is_staff=True)
    room = Dataroom.objects.create(organization=org, created_by=user, name='Fixture room')
    settings.BOARD_SIGN_BOARDS = {'fixture': {'owner_ids': [str(user.pk)], 'team_ids': [3], 'room_ids': [str(room.pk)]}}
    out = io.BytesIO(); writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=600, height=800)
    writer.write(out); pdf = out.getvalue()
    doc = Document.objects.create(organization=org, created_by=user, name='Fixture agreement.pdf', type='pdf', content_type='application/pdf')
    version = DocumentVersion.objects.create(document=doc, version_number=1, type='pdf', content_type='application/pdf', original_storage_key='fixture.pdf', num_pages=2)
    DataroomDocument.objects.create(dataroom=room, document=doc)
    credential = SignCredential.objects.create(owner=user, team_id=3, token='fixture-token')
    work = Workflow.objects.create(owner=user, room=room, idempotency_key='fixture', request_sha256='a'*64, purpose='room_document', source_version=version, source_sha256=hashlib.sha256(pdf).hexdigest(), recipients=[{'email':'signer@example.test','name':'Signer','role':'SIGNER','fields':[{'type':'SIGNATURE','page':2,'positionX':10,'positionY':70,'width':30,'height':8}]}], title=doc.name, external_id='fixture', envelope_id='env_fixture', item_ids=['item_fixture'], state='awaiting_signature', signer_projection=[{'id':12,'email':'signer@example.test','role':'SIGNER','signingStatus':'NOT_SIGNED'}])
    return SimpleNamespace(user=user, org=org, room=room, version=version, work=work, credential=credential, pdf=pdf, settings=settings)


def product(base):
    assert hasattr(models, 'SignatureRequest'), 'Slice 1 durable SignatureRequest is not implemented'
    binding = models.BoardStaffBinding.objects.create(board_id='fixture', login=base.user.email, send_user=base.user, signer_email=base.user.email, role='manager')
    req = models.SignatureRequest.objects.create(board_id='fixture', creator=base.user, workflow=base.work, title=base.work.title, kind='out', state=base.work.state, task_ref=None, room=None)
    return req, binding


def get(path, **context):
    return APIClient().get(path, **headers('GET', path, **context))


def post(body, **context):
    raw = json.dumps(body, separators=(',', ':')).encode()
    return APIClient().generic('POST', PREFIX+'/exports', raw, content_type='application/json', **headers('POST', PREFIX+'/exports', raw, **context))


def export_body(req, kind='original', **kw):
    return {'request_ids':[str(req.pk)], 'kind':kind, 'format':'pdf', 'reason':'Fixture download', **kw}


def remote(base):
    client = Mock()
    client.get.return_value = {'id':base.work.envelope_id,'externalId':base.work.external_id,'status':'PENDING','envelopeItems':[{'id':'item_fixture'}], 'recipients':[{'id':12,'email':'signer@example.test','role':'SIGNER','signingStatus':'NOT_SIGNED'}]}
    client.get.return_value['fields'] = [{'id':7,'recipientId':12,'envelopeItemId':'item_fixture','type':'SIGNATURE','page':2,'positionX':10,'positionY':70,'width':30,'height':8,'inserted':True}]
    client.audit.return_value = {'data':[]}
    client.pdf.return_value = client.item_pdf.return_value = client.audit_pdf.return_value = base.pdf
    return client


def agent(base, req):
    raw, prefix, hashed = generate_raw_api_key()
    key = APIKey.objects.create(user=base.user, name='Fixture agent', prefix=prefix, hashed_key=hashed, tier='full_access')
    scope = KeyScope.objects.create(key=key, operations=[EXPORT_OP], rooms=[str(base.room.pk)], recipient_orgs=[])
    client = APIClient(); client.credentials(HTTP_AUTHORIZATION='Bearer '+raw)
    return client, scope


def test_board_actor_and_cross_board_denied(base):
    req, binding = product(base)
    path = PREFIX+'/requests?board=fixture'
    response = get(path)
    assert response.status_code == 200
    assert response.data['items'][0]['task'] is None
    assert response.data['items'][0]['id'] == str(req.pk)
    assert get(PREFIX+'/requests?board=other').status_code == 403
    req.board_id = 'other'; req.save()
    assert get(PREFIX+f'/requests/{req.pk}').status_code == 404
    req.board_id = 'fixture'; req.save()
    binding.enabled = False; binding.save()
    assert get(path).status_code == 403
    jwt = APIClient(); jwt.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(base.user).access_token))
    assert jwt.get(path).status_code == 403


def test_last_activity_uses_real_events_not_fetch_or_poll_time(base):
    req, _ = product(base)
    sent = timezone.now() - timedelta(days=3)
    opened = sent + timedelta(hours=2)
    models.SignatureRequest.objects.filter(pk=req.pk).update(created_at=sent - timedelta(minutes=1))
    base.work.signer_projection[0]['sentAt'] = sent.isoformat()
    base.work.reconciled_at = timezone.now()
    base.work.save()
    fact = ObservedSignEvent.objects.create(workflow=base.work, source_id='opened-real',
        kind='envelope.viewed', occurred_at=opened)
    ObservedSignEvent.objects.create(workflow=base.work, source_id='snapshot-new',
        kind='snapshot.fields', occurred_at=timezone.now())
    # Imported/native mirrors are recorded at fetch time but carry the original time.
    Activity.objects.create(organization=base.org, event_type='envelope.viewed', actor_id='sign:fixture',
        data={'workflow_id':str(base.work.pk), 'source':'sign', 'source_record_id':fact.source_id,
              'occurred_at':opened.isoformat()})
    for _ in range(2):
        base.work.reconciled_at = timezone.now(); base.work.save()
        result = get(PREFIX+'/requests?board=fixture').data['items'][0]
        assert result['last_activity_at'] == opened
        assert get(PREFIX+f'/requests/{req.pk}').data['last_activity_at'] == opened
    fact.occurred_at = opened + timedelta(hours=1); fact.kind = 'page_viewed'; fact.save()
    assert get(PREFIX+'/requests?board=fixture').data['items'][0]['last_activity_at'] == fact.occurred_at


def test_activity_preserves_actor_recipient_pages_and_original_source_ids(base):
    req, _ = product(base)
    at = timezone.now() - timedelta(days=2)
    ObservedSignEvent.objects.create(workflow=base.work, source_id='native-page', kind='page_viewed',
        occurred_at=at, actor_email='signer@example.test', name='Signer', recipient_id='12',
        payload={'type':'page_viewed','data':{'pageNumber':6}})
    download = Activity.objects.create(organization=base.org, event_type='signature.download_requested',
        actor_kind='staff', actor_id=str(base.user.pk), target_id=str(req.pk), data={'kind':'original'})
    events = get(PREFIX+f'/requests/{req.pk}').data['activity']
    page = next(e for e in events if e['id'] == 'native-page')
    assert page['actor_email'] == 'signer@example.test'
    assert page['recipient_id'] == '12' and page['pages'] == [6]
    assert page['source_event_ids'] == ['native-page']
    assert next(e for e in events if e['id'] == str(download.pk))['actor_email'] == base.user.email


def test_history_orders_real_activity_before_pagination(base):
    first, _ = product(base)
    at = timezone.now() - timedelta(days=1)
    base.work.signer_projection[0]['sentAt'] = at.isoformat()
    base.work.save()
    expected = [str(first.pk)]
    # Later-created requests have older activity.
    # The newest actual activity must still appear on page one of a full history.
    for index in range(1, 52):
        projection = [{**base.work.signer_projection[0], 'sentAt': (at - timedelta(hours=index)).isoformat()}]
        work = Workflow.objects.create(owner=base.user, room=base.room, source_version=base.version,
            source_sha256=base.work.source_sha256, idempotency_key=f'history-{index}',
            external_id=f'history-{index}', state='awaiting_signature',
            recipients=base.work.recipients, signer_projection=projection, reconciled_at=timezone.now())
        row = models.SignatureRequest.objects.create(board_id='fixture', creator=base.user, workflow=work,
            title=f'Agreement {index}', kind='out', state=work.state)
        expected.append(str(row.pk))
    response = get(PREFIX+'/requests?board=fixture')
    assert response.status_code == 200
    assert [row['id'] for row in response.data['items']] == expected[:50]
    assert response.data['next_cursor'] == expected[49]
    remainder = get(PREFIX+'/requests?board=fixture&cursor='+response.data['next_cursor'])
    assert [row['id'] for row in remainder.data['items']] == expected[50:]
    assert remainder.data['items'][-1]['last_activity_at'] == at - timedelta(hours=51)
    assert remainder.data['next_cursor'] is None


def test_domain_fallback_viewer_gets_no_requests_evidence_or_exports(base):
    req, _ = product(base)
    with patch('dealroom_sign.client.Documenso.request') as upstream:
        for path in ['/requests?board=fixture', f'/requests/{req.pk}', f'/requests/{req.pk}/pages?kind=original']:
            assert get(PREFIX+path, login='visitor@example.test').status_code == 403
        assert post(export_body(req), login='visitor@example.test').status_code == 403
        upstream.assert_not_called()


@pytest.mark.parametrize('via', ['service:fixture-agent','dev','cloudflare_access',''])
def test_board_context_via_service_or_dev_is_not_human_staff(base, via):
    req, _ = product(base)
    with patch('dealroom_sign.client.Documenso.request') as upstream:
        detail = get(PREFIX+f'/requests/{req.pk}', via=via)
        assert detail.status_code == 200
        assert detail.data['evidence'] == []
        assert '/pages/' not in detail.content.decode()
        assert get(PREFIX+f'/requests/{req.pk}/pages?kind=original', via=via).status_code == 403
        for kind in ['partial','audit','evidence_report','history_evidence']:
            assert post(export_body(req, kind), via=via).status_code == 403
        upstream.assert_not_called()


def test_hmac_timestamp_body_query_and_actor_are_bound(base):
    req, _ = product(base)
    path = PREFIX+'/requests?board=fixture'
    assert get(path, via='cloudflare').status_code == 200
    for stamp in [int(time.time())-61, int(time.time())+61]:
        assert get(path, stamp=stamp).status_code == 403
    signed = headers('GET', path)
    assert APIClient().get(path+'&q=other', **signed).status_code == 403
    signed['HTTP_X_BOARD_CONTEXT'] = signed['HTTP_X_BOARD_CONTEXT'].replace('staff@', 'other@')
    assert APIClient().get(path, **signed).status_code == 403
    raw = json.dumps(export_body(req)).encode()
    assert APIClient().generic('POST', PREFIX+'/exports', raw+b' ', content_type='application/json', **headers('POST', PREFIX+'/exports', raw)).status_code == 403


def test_audit_recipient_attribution_and_pagination(base):
    req, _ = product(base)
    pages = []
    def respond(request):
        page = int(request.url.params['page']); pages.append(page)
        return httpx.Response(200, json={'data':[{'id':str(page),'type':'DOCUMENT_OPENED' if page == 1 else 'DOCUMENT_RECIPIENT_COMPLETED','email':'sender@example.test','createdAt':f'2026-11-14T10:0{page}:00Z','data':{'recipientId':12,'recipientEmail':'signer@example.test'},'ipAddress':'192.0.2.10','userAgent':'Fixture browser'}], 'count':2})
    with Documenso(base.credential, httpx.MockTransport(respond)) as client:
        refresh_audit(req, client)
    assert pages == [1, 2]
    detail = get(PREFIX+f'/requests/{req.pk}').data
    row = detail['evidence'][0]
    assert row['recipient_id'] == 12 and row['opened_at'] and row['signed_at']
    assert row['source_event_ids'] == ['1', '2']
    assert row['classification']['value'] != 'staff'
    assert ObservedSignEvent.objects.get(source_id='1').actor_email == 'sender@example.test'
    req.refresh_from_db(); assert req.audit_complete and req.audit_as_of


def test_unknown_audit_fields_stay_unknown(base):
    req, _ = product(base)
    client = remote(base); client.audit.return_value = {'data':[{'id':'unknown','type':'FUTURE_EVENT','data':{'recipientId':12}}]}
    refresh_audit(req, client)
    fact = ObservedSignEvent.objects.get(source_id='unknown')
    assert fact.occurred_at is None and fact.ip_address is None and fact.actor_email is None
    row = get(PREFIX+f'/requests/{req.pk}').data['evidence'][0]
    assert row['pages'] == {'status':'not_recorded','items':[]}
    assert row['consent'] == {'status':'not_recorded','at':None}
    assert row['signed_at'] is None and row['identity']['observed'] is None


def test_version_page_proxy_has_no_raw_url(base):
    req, _ = product(base)
    base.version.has_pages = True; base.version.render_status = 'ready'; base.version.save()
    for page in (1, 2):
        DocumentPage.objects.create(document_version=base.version, page_number=page, storage_key=f'private/{page}.jpg')
    path = PREFIX+f'/requests/{req.pk}/pages?kind=original&snapshot_id={base.work.source_sha256}'
    manifest = get(path)
    assert manifest.status_code == 200
    assert manifest.data['signature_pages'] == [2]
    assert all(p['url'].startswith(PREFIX) for p in manifest.data['pages'])
    assert 'private/' not in json.dumps(manifest.data)
    with patch('dealroom_sign.storage.page_bytes', return_value=b'fixture-jpeg'):
        page = get(manifest.data['pages'][1]['url'])
        assert page.status_code == 200 and page.content == b'fixture-jpeg'
        assert page['Cache-Control'] == 'private, no-store'
    assert Activity.objects.filter(event_type='signature.page_viewed').exists()
    assert get(path.replace(base.work.source_sha256, 'changed')).status_code == 409
    base.version.has_pages = False; base.version.render_status = 'failed'; base.version.save()
    assert get(path).status_code == 422
    base.version.render_status = 'not_generated'; base.version.save()
    with patch('documents.tasks.generate_pdf_pages_task.delay') as enqueue:
        assert get(path).status_code == 202
        enqueue.assert_called_once()


def test_export_scope_log_and_checksum(base):
    req, _ = product(base)
    with patch('dealroom_sign.exports.source_bytes', return_value=base.pdf):
        response = post(export_body(req))
        assert response.status_code == 200
        assert response['X-Content-SHA256'] == hashlib.sha256(response.content).hexdigest()
        event = Activity.objects.get(pk=response['X-Dealroom-Audit-ID'])
        assert event.event_type == 'signature.download_requested'
        assert event.actor_id == str(base.user.pk)
        assert event.data['sha256'] == response['X-Content-SHA256']
        assert event.data['board_id'] == 'fixture'
        outcome = Activity.objects.get(event_type='signature.download_outcome', data__audit_id=str(event.pk))
        assert outcome.data == {'audit_id':str(event.pk), 'outcome':'unknown', 'delivery':'response_handoff'}
        with patch('dealroom_sign.exports.record', side_effect=RuntimeError('fixture audit unavailable')):
            assert post(export_body(req)).status_code == 503
        assert post(export_body(req, extra='unknown')).status_code == 400
        assert post(export_body(req, 'evidence_report')).status_code == 400


@pytest.mark.parametrize('kind', ['partial','audit','evidence_report','history_evidence'])
def test_agent_key_cannot_export_partial_or_audit(base, kind):
    req, _ = product(base); client, _ = agent(base, req)
    with patch('dealroom_sign.client.Documenso.request') as upstream, patch('dealroom_sign.storage.fileserver_client.upload_file') as upload:
        assert client.post(PREFIX+'/exports', export_body(req, kind), format='json').status_code == 403
        upstream.assert_not_called(); upload.assert_not_called()
    assert not models.RequestArtifact.objects.exists()
    # MCP advertises the same central operation and explicit protected-kind policy.
    mapping = json.loads((Path(__file__).resolve().parents[3]/'mcp-server/coneshare_mcp/dealroom_tools.json').resolve().read_text())
    entry = next((x for x in mapping if x['operation_id'] == EXPORT_OP), None)
    assert entry and kind in entry['human_only_kinds']
    # Execute the production MCP method with a framework-free shell: FastMCP is a
    # separate service dependency; the deny must happen before validation/transport.
    source = Path(__file__).resolve().parents[3]/'mcp-server/coneshare_mcp/dealroom.py'
    tree = ast.parse(source.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'RegistryTool')
    run = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'run')
    scope = {'ToolResult':object}
    exec(compile(ast.Module(body=[run], type_ignores=[]), str(source), 'exec'), scope)
    with pytest.raises(ValueError, match='403:'):
        asyncio.run(scope['run'](SimpleNamespace(endpoint=entry), {'body':export_body(req, kind)}))


@pytest.mark.parametrize('kind', ['original','final','certificate'])
def test_agent_can_export_scoped_original_final_certificate(base, kind):
    req, _ = product(base); client, scope = agent(base, req)
    if kind != 'original':
        base.work.state = 'done'; base.work.save()
        ExecutedArtifact.objects.create(workflow=base.work, item_id='item_fixture', kind='sealed_pdf' if kind == 'final' else kind, version=base.version, size=len(base.pdf), sha256=hashlib.sha256(base.pdf).hexdigest())
    with patch('dealroom_sign.exports.source_bytes', return_value=base.pdf):
        response = client.post(PREFIX+'/exports', export_body(req, kind), format='json')
        assert response.status_code == 200
        scope.rooms = []; scope.save()
        assert client.post(PREFIX+'/exports', export_body(req, kind), format='json').status_code == 403
        scope.rooms = [str(base.room.pk)]; scope.operations = []; scope.save()
        assert client.post(PREFIX+'/exports', export_body(req, kind), format='json').status_code == 403


def test_partial_stamped_final_bytes_unchanged(base):
    req, _ = product(base); client = remote(base)
    stamped = stamp_partial(base.pdf, str(req.pk), '2026-11-14T10:00:00Z')
    assert all('NOT FINAL' in page.extract_text() for page in PdfReader(io.BytesIO(stamped)).pages)
    with patch('dealroom_sign.exports.Documenso') as remote_class, patch('dealroom_sign.storage.fileserver_client.upload_file'):
        remote_class.return_value.__enter__.return_value = client
        response = post(export_body(req, 'partial'))
        assert response.status_code == 200
        assert all('NOT FINAL' in page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
        assert models.RequestArtifact.objects.get(kind='partial').sha256 == response['X-Content-SHA256']
        # A newly observed signature invalidates the unpinned derivative.
        base.work.signer_projection[0]['signingStatus'] = 'SIGNED'; base.work.save()
        client.get.side_effect = [client.get.return_value, {**client.get.return_value, 'status':'COMPLETED'}]
        assert post(export_body(req, 'partial')).status_code == 409
    base.work.state = 'done'; base.work.save()
    writer = PdfWriter()
    writer.clone_document_from_reader(PdfReader(io.BytesIO(base.pdf)))
    writer.add_metadata({'/Title':'Executed fixture'})
    sealed = io.BytesIO(); writer.write(sealed); sealed_bytes = sealed.getvalue()
    assert sealed_bytes != base.pdf
    sealed_version = DocumentVersion.objects.create(document=base.version.document, version_number=2,
        type='pdf', content_type='application/pdf', original_storage_key='sealed-fixture.pdf')
    artifact = ExecutedArtifact.objects.create(workflow=base.work, item_id='item_fixture',
        kind='sealed_pdf', version=sealed_version, size=len(sealed_bytes), sha256=hashlib.sha256(sealed_bytes).hexdigest())
    with patch('dealroom_sign.exports.source_bytes', return_value=sealed_bytes) as read, \
         patch('dealroom_sign.storage.fileserver_client.upload_file') as upload:
        final = post(export_body(req, 'final'))
        assert final.status_code == 200 and final.content == sealed_bytes
        assert hashlib.sha256(final.content).hexdigest() == artifact.sha256 == final['X-Content-SHA256']
        assert all('NOT FINAL' not in page.extract_text() for page in PdfReader(io.BytesIO(final.content)).pages)
        read.assert_called_once_with(sealed_version)
        upload.assert_not_called()


def test_import_is_idempotent_and_never_verifies_legacy_identity(base, tmp_path):
    assert hasattr(models, 'SignatureRequest'), 'Slice 1 import persistence is not implemented'
    manifest = {'board_id':'fixture','bindings':[{'login':base.user.email,'send_user_id':str(base.user.pk),'signer_email':base.user.email,'role':'reader','enabled':True}], 'requests':[{'workflow_id':str(base.work.pk),'creator_login':base.user.email,'task_ref':None}]}
    path = tmp_path/'import.json'; path.write_text(json.dumps(manifest))
    with patch('dealroom_sign.client.Documenso.request') as upstream:
        call_command('import_board_sign', manifest=str(path), fetch_audit=True)
        upstream.assert_not_called()
    assert not models.SignatureRequest.objects.exists()
    call_command('import_board_sign', manifest=str(path), apply=True)
    call_command('import_board_sign', manifest=str(path), apply=True)
    assert models.SignatureRequest.objects.count() == 1
    assert models.BoardStaffBinding.objects.count() == 1
    request = models.SignatureRequest.objects.get()
    assert request.source_context['identity'] == 'legacy_reported' and request.task_ref is None
    pages = []
    def respond(native_request):
        if native_request.url.path.endswith('/audit-log'):
            page = int(native_request.url.params['page']); pages.append(page)
            return httpx.Response(200, json={'data':[{'id':f'legacy-{page}',
                'type':'DOCUMENT_RECIPIENT_COMPLETED','data':{'recipientId':12}}], 'count':2})
        return httpx.Response(200, json={**remote(base).get.return_value, 'teamId':3})
    with patch('dealroom_sign.management.commands.import_board_sign.Documenso',
               side_effect=lambda credential: Documenso(credential, httpx.MockTransport(respond))):
        call_command('import_board_sign', manifest=str(path), apply=True, fetch_audit=True)
    assert pages == [1,2]
    request.refresh_from_db(); assert request.audit_complete
    assert get(PREFIX+f'/requests/{request.pk}').data['evidence'][0]['classification']['value'] != 'staff'


def test_product_registry_tool_parity():
    root = Path(__file__).resolve().parents[3]
    tools = {x['operation_id']:x for x in json.loads((root/'mcp-server/coneshare_mcp/dealroom_tools.json').read_text())}
    source = root/'mcp-server/coneshare_mcp/dealroom.py'
    register = next(node for node in ast.parse(source.read_text()).body if isinstance(node, ast.FunctionDef) and node.name == 'register')
    scope = {'json':json, 'Path':Path, '__file__':str(source), 'RegistryTool':lambda **kwargs: SimpleNamespace(**kwargs)}
    exec(compile(ast.Module(body=[register], type_ignores=[]), str(source), 'exec'), scope)
    mcp = Mock(); scope['register'](mcp)
    descriptions = {call.args[0].endpoint['operation_id']:call.args[0].description for call in mcp.add_tool.call_args_list}
    for cls in ['SignatureRequestListView','SignatureOverviewView','SignatureRequestDetailView','SignaturePageListView','SignaturePageView','SignatureExportView']:
        oid = f'dealroom_sign_{cls}_endpoint_' + ('post' if cls == 'SignatureExportView' else 'get')
        assert oid in registry(), f'Missing slice 1 registry operation: {oid}'
        assert oid in tools
        assert registry()[oid]['boundary'] == 'staff'
        assert registry()[oid]['widens_access'] is False
        if cls in ['SignaturePageListView','SignaturePageView']:
            assert registry()[oid]['human_only'] is True
            assert 'verified human board session' in descriptions[oid].lower()
            assert 'JWT' not in descriptions[oid]


def test_snapshot_crop_binds_native_item_recipient_and_page(base):
    req, _ = product(base)
    snap = models.RequestArtifact.objects.create(request=req, kind='partial', snapshot_id='b'*64,
        item_id='item_fixture', version=base.version, sha256='b'*64, size=100, source_sha256=base.work.source_sha256)
    snapshot_fields(base.work, snap.snapshot_id, 'item_fixture', remote(base).get.return_value)
    base.version.has_pages = True; base.version.render_status = 'ready'; base.version.save()
    DocumentPage.objects.create(document_version=base.version, page_number=2, storage_key='fixture/page2.jpg')
    output = io.BytesIO(); image = Image.new('RGB', (600,800), 'white'); image.save(output, format='JPEG'); image.close()
    path = PREFIX+f'/requests/{req.pk}/pages/2?kind=partial&snapshot_id={snap.snapshot_id}&field_id=7'
    with patch('dealroom_sign.storage.page_bytes', return_value=output.getvalue()):
        response = get(path)
        assert response.status_code == 200
        with Image.open(io.BytesIO(response.content)) as crop:
            assert crop.size == (180,64)
        assert get(path.replace('field_id=7','field_id=8')).status_code == 404
        assert get(path.replace(snap.snapshot_id,'changed')).status_code == 409
    response = get(PREFIX+f'/requests/{req.pk}/pages?kind=partial&snapshot_id={snap.snapshot_id}')
    assert response.data['signatures'][0]['recipient_id'] == 12
    assert response.data['signatures'][0]['url'].endswith('field_id=7')


def test_product_filter_cursor_and_no_later_slice_endpoints(base):
    req, _ = product(base)
    assert get(PREFIX+'/requests?board=fixture&q=missing').data['items'] == []
    assert get(PREFIX+'/requests?board=fixture&state=waiting').data['counts']['waiting'] == 1
    assert get(PREFIX+'/requests?board=fixture&direction=in').data['items'] == []
    assert get(PREFIX+'/overview?board=fixture').data['source_states'] == {'predictions':'not_enabled'}
    for suffix in ['/requests',f'/requests/{req.pk}/send',f'/requests/{req.pk}/void']:
        raw=b'{}'
        response=APIClient().generic('POST', PREFIX+suffix, raw, content_type='application/json', **headers('POST',PREFIX+suffix,raw))
        assert response.status_code in (403,404,405)
    assert post([]).status_code == 400
    with patch('dealroom_sign.exports.source_bytes', return_value=base.pdf+b'changed'):
        assert post(export_body(req)).status_code == 503


def test_product_request_revoked_room_and_binding_are_rechecked(base):
    req, binding = product(base)
    path=PREFIX+f'/requests/{req.pk}'
    assert get(path).status_code == 200
    base.settings.BOARD_SIGN_BOARDS = {'fixture':{'owner_ids':[str(base.user.pk)],'team_ids':[3],'room_ids':[]}}
    assert get(path).status_code == 404
    with patch('dealroom_sign.exports.source_bytes') as read:
        assert post(export_body(req)).status_code == 404
        read.assert_not_called()


def test_legacy_admin_reads_cannot_bypass_snapshot_boundary(base):
    req, _ = product(base)
    base.user.role = 'admin'; base.user.save()
    models.RequestArtifact.objects.create(request=req, kind='partial', snapshot_id='c'*64,
        item_id='item_fixture', version=base.version, sha256='c'*64, size=100, source_sha256=base.work.source_sha256)
    client, scope = agent(base, req)
    scope.operations = None; scope.rooms = None; scope.save()
    assert client.get(f'/api/v1/documents/{base.version.document_id}/').status_code == 403
    for kind in [[], {}, 12]:
        assert post(export_body(req, kind)).status_code == 400


def test_new_signature_invalidates_unpinned_partial_snapshot(base):
    req, _ = product(base)
    snap = models.RequestArtifact.objects.create(request=req,kind='partial',snapshot_id='d'*64,
        item_id='item_fixture',version=base.version,sha256='d'*64,size=100,source_sha256=base.work.source_sha256)
    snapshot_fields(base.work,snap.snapshot_id,'item_fixture',remote(base).get.return_value)
    assert existing_artifact(req,'partial').pk == snap.pk
    req.workflow.signer_projection[0]['signingStatus'] = 'SIGNED'
    assert existing_artifact(req,'partial') is None
    assert existing_artifact(req,'partial',snap.snapshot_id).pk == snap.pk


@pytest.mark.parametrize('task', [None, {'id':'card-1','title':'Review agreement'}])
def test_legacy_board_send_creates_product_request_and_import_is_idempotent(base, tmp_path, task):
    product(base)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(base.user).access_token))
    body = {'room_id':str(base.room.pk),'version_id':str(base.version.pk),
        'recipients':base.work.recipients,'idempotency_key':'board-send',
        'board_id':'fixture','task_ref':task}
    with patch('dealroom_sign.workflows.source_bytes', return_value=base.pdf):
        sent = client.post(PREFIX+'/envelopes/', body, format='json')
        assert sent.status_code == 201, sent.data
        row = models.SignatureRequest.objects.get(workflow_id=sent.data['id'])
        assert row.board_id == 'fixture' and row.task_ref == task
        assert row.source_context == {'identity':'legacy_reported','creator_login':None}
        assert client.post(PREFIX+'/envelopes/', body, format='json').data['id'] == sent.data['id']
        for changes in [{'task_ref':{'id':'different-card'}}, {'board_id':'different-board'},
                        {'creator_login':'unverified@example.test'}]:
            assert client.post(PREFIX+'/envelopes/', {**body, **changes}, format='json').status_code == 400
        assert models.SignatureRequest.objects.filter(workflow_id=sent.data['id']).count() == 1
    listing = get(PREFIX+'/requests?board=fixture').data['items']
    assert next(r for r in listing if r['id'] == str(row.pk))['task'] == task
    detail = get(PREFIX+f'/requests/{row.pk}')
    assert detail.status_code == 200 and detail.data['source_context']['identity'] == 'legacy_reported'
    manifest = {'board_id':'fixture','bindings':[{'login':base.user.email,'send_user_id':str(base.user.pk),
        'signer_email':base.user.email,'role':'manager','enabled':True}],
        'requests':[{'workflow_id':sent.data['id'],'creator_login':base.user.email,'task_ref':task}]}
    path = tmp_path/'import.json'; path.write_text(json.dumps(manifest))
    for _ in range(2):
        call_command('import_board_sign', manifest=str(path), apply=True)
    row.refresh_from_db()
    assert models.SignatureRequest.objects.filter(workflow_id=sent.data['id']).count() == 1
    assert row.source_context == {'identity':'legacy_reported','creator_login':None}
    operator = User.objects.create_user(username='operator@example.test', email='operator@example.test',
        organization=base.org, is_staff=True)
    manifest['bindings'] = [{'login':operator.email, 'send_user_id':str(operator.pk),
        'signer_email':operator.email, 'role':'reader', 'enabled':True}]
    manifest['requests'][0]['creator_login'] = operator.email
    path.write_text(json.dumps(manifest))
    call_command('import_board_sign', manifest=str(path), apply=True)
    row.refresh_from_db()
    assert row.creator_id == base.user.pk and row.source_context['creator_login'] is None


def test_legacy_board_send_request_failure_rolls_back_workflow(base):
    client = APIClient(); client.force_authenticate(base.user)
    body = {'room_id':str(base.room.pk),'version_id':str(base.version.pk),
        'recipients':base.work.recipients,'idempotency_key':'rollback-send',
        'board_id':'fixture','task_ref':None}
    with patch('dealroom_sign.workflows.source_bytes', return_value=base.pdf), \
         patch.object(models.SignatureRequest.objects, 'get_or_create', side_effect=RuntimeError('Fixture row write failed')):
        with pytest.raises(RuntimeError, match='Fixture row write failed'):
            client.post(PREFIX+'/envelopes/', body, format='json')
    assert not Workflow.objects.filter(idempotency_key='rollback-send').exists()


def test_overview_exposes_only_the_requested_boards_configured_rooms(base):
    product(base)
    base.settings.BOARD_SIGN_BOARDS['other'] = {'room_ids': ['other-room']}
    path = PREFIX+'/overview?board=fixture'
    assert get(path).data['room_ids'] == [str(base.room.pk)]
    assert get(PREFIX+'/overview?board=other').status_code == 403
    base.settings.BOARD_SIGN_BOARDS['fixture']['room_ids'] = []
    assert get(path).data['room_ids'] == []


def test_legacy_board_send_unconfigured_room_creates_no_rows(base):
    base.settings.BOARD_SIGN_BOARDS['fixture']['room_ids'] = []
    client = APIClient(); client.force_authenticate(base.user)
    body = {'room_id':str(base.room.pk), 'version_id':str(base.version.pk),
        'recipients':base.work.recipients, 'idempotency_key':'unconfigured-room',
        'board_id':'fixture', 'task_ref':None}
    before = Workflow.objects.count()
    with patch('dealroom_sign.workflows.source_bytes', return_value=base.pdf):
        response = client.post(PREFIX+'/envelopes/', body, format='json')
    assert response.status_code == 400
    assert 'Invalid owner/team/room mapping' in str(response.data)
    assert Workflow.objects.count() == before
    assert not models.SignatureRequest.objects.exists()


@pytest.mark.parametrize('metadata', [
    {'board_id':'fixture'},
    {'board_id':'fixture', 'task_ref':{'id':'card-1', 'title':'Agreement'}},
    {'task_ref':{'id':'card-1', 'title':'Agreement'}},
    {'task_ref':None},
])
@pytest.mark.parametrize('approval_enabled', [True, False])
def test_api_key_cannot_create_board_originated_envelopes(base, metadata, approval_enabled):
    base.settings.DEALROOM_ENABLED = approval_enabled
    raw, prefix, hashed = generate_raw_api_key()
    APIKey.objects.create(user=base.user, name='Fixture writer', tier='full_access',
        prefix=prefix, hashed_key=hashed)
    client = APIClient(); client.credentials(HTTP_AUTHORIZATION='Bearer '+raw)
    body = {'room_id':str(base.room.pk), 'version_id':str(base.version.pk),
        'recipients':base.work.recipients, 'idempotency_key':'key-board-send'}
    before = Workflow.objects.count()
    with patch('dealroom_sign.workflows.source_bytes', return_value=base.pdf):
        response = client.post(PREFIX+'/envelopes/', {**body, **metadata}, format='json')
        assert response.status_code in {400, 403}, response.data
        assert Workflow.objects.count() == before
        assert not models.SignatureRequest.objects.exists()
        assert not AccessApproval.objects.exists()
        # The existing non-board operation remains available to agent keys.
        assert client.post(PREFIX+'/envelopes/', body, format='json').status_code == (202 if approval_enabled else 201)
        assert not models.SignatureRequest.objects.exists()


def test_envelope_registry_documents_api_key_board_metadata_rejection():
    note = registry()['dealroom_sign_SigningEnvelopeViewSet_create_post']['reason']
    assert 'API keys' in note and 'board_id' in note and 'task_ref' in note


def test_legacy_replay_preserves_imported_operator_creator(base, tmp_path):
    client = APIClient(); client.force_authenticate(base.user)
    task = {'id':'card-1', 'title':'Agreement'}
    body = {'room_id':str(base.room.pk), 'version_id':str(base.version.pk),
        'recipients':base.work.recipients, 'idempotency_key':'import-before-replay',
        'board_id':'fixture', 'task_ref':task}
    with patch('dealroom_sign.workflows.source_bytes', return_value=base.pdf):
        sent = client.post(PREFIX+'/envelopes/', body, format='json')
    assert sent.status_code == 201
    models.SignatureRequest.objects.get(workflow_id=sent.data['id']).delete()
    operator = User.objects.create_user(username='operator@example.test', email='operator@example.test',
        organization=base.org, is_staff=True)
    manifest = {'board_id':'fixture', 'bindings':[{'login':operator.email,
        'send_user_id':str(operator.pk), 'signer_email':operator.email, 'role':'reader', 'enabled':True}],
        'requests':[{'workflow_id':sent.data['id'], 'creator_login':operator.email, 'task_ref':task}]}
    path = tmp_path/'import.json'; path.write_text(json.dumps(manifest))
    call_command('import_board_sign', manifest=str(path), apply=True)
    row = models.SignatureRequest.objects.get(workflow_id=sent.data['id'])
    response = client.post(PREFIX+'/envelopes/', body, format='json')
    assert response.status_code == 201, response.data
    assert response.data['id'] == sent.data['id']
    row.refresh_from_db()
    assert row.creator_id == operator.pk
    assert models.SignatureRequest.objects.count() == 1


@pytest.mark.parametrize('tier', ['read_only','read_write','full_access'])
def test_api_key_pages_denied_detail_redacted_and_binding_email_used(base, tier):
    req, binding = product(base)
    binding.signer_email = 'Signer@Example.test'; binding.save()
    raw, prefix, hashed = generate_raw_api_key()
    key = APIKey.objects.create(user=base.user, name='Unscoped fixture', prefix=prefix, hashed_key=hashed, tier=tier)
    assert not KeyScope.objects.filter(key=key).exists()
    client = APIClient(); client.credentials(HTTP_AUTHORIZATION='Bearer '+raw)
    with patch('dealroom_sign.client.Documenso.request') as upstream, \
         patch('dealroom_sign.exports.source_bytes') as read, \
         patch('dealroom_sign.storage.page_bytes') as page_read, \
         patch('dealroom_sign.storage.fileserver_client.upload_file') as upload:
        for suffix in ['/pages?kind=original','/pages/2?kind=partial&field_id=7']:
            assert client.get(PREFIX+f'/requests/{req.pk}'+suffix).status_code == 403
        detail = client.get(PREFIX+f'/requests/{req.pk}')
        assert detail.status_code == 200 and detail.data['evidence'] == []
        assert not {'partial','audit'} & {a['kind'] for a in detail.data['artifacts']}
        assert '/pages/' not in detail.content.decode()
        upstream.assert_not_called(); read.assert_not_called(); page_read.assert_not_called(); upload.assert_not_called()
        assert detail.data['needs_you'] is True
        assert detail.data['people'][0]['side'] == 'ours'
    binding.enabled = False; binding.save()
    models.BoardStaffBinding.objects.create(board_id='fixture',login='other@example.test',send_user=base.user,
        signer_email='other@example.test',role='reader')
    assert client.get(PREFIX+f'/requests/{req.pk}').data['needs_you'] is False


def test_board_needs_you_and_evidence_use_case_insensitive_binding_email(base):
    req, binding = product(base)
    binding.signer_email = 'Signer@Example.test'; binding.save()
    detail = get(PREFIX+f'/requests/{req.pk}').data
    assert detail['needs_you'] is True and detail['people'][0]['side'] == 'ours'
    assert detail['evidence'][0]['classification']['value'] == 'board_user'
    assert get(PREFIX+'/requests?board=fixture&state=needs_you').data['items'][0]['id'] == str(req.pk)
    binding.signer_email = 'other@example.test'; binding.save()
    models.BoardStaffBinding.objects.create(board_id='fixture',login='second@example.test',send_user=base.user,
        signer_email='Signer@Example.test',role='reader')
    assert get(PREFIX+f'/requests/{req.pk}').data['needs_you'] is False


def test_unpinned_partial_export_reuses_page_snapshot(base):
    req, _ = product(base)
    stamped = stamp_partial(base.pdf, str(req.pk), '2026-11-14T10:00:00Z')
    sha = hashlib.sha256(stamped).hexdigest()
    snap = models.RequestArtifact.objects.create(request=req, kind='partial', snapshot_id=sha,
        version=base.version, item_id='item_fixture', sha256=sha, size=len(stamped), source_sha256=base.work.source_sha256)
    snapshot_fields(base.work, sha, 'item_fixture', remote(base).get.return_value)
    with patch('dealroom_sign.exports.source_bytes', return_value=stamped), \
         patch('dealroom_sign.exports.Documenso') as upstream, \
         patch('dealroom_sign.storage.fileserver_client.upload_file') as upload:
        for _ in range(2):
            response = post(export_body(req, 'partial'))
            assert response.status_code == 200 and response.content == stamped
            assert response['X-Dealroom-Artifact-ID'] == str(snap.pk)
        upstream.assert_not_called(); upload.assert_not_called()
    assert models.RequestArtifact.objects.filter(request=req, kind='partial').count() == 1
