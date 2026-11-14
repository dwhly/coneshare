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

import httpx
import pytest
from django.core.management import call_command
from pypdf import PdfReader, PdfWriter
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.authentication import generate_raw_api_key
from core.models import APIKey, Organization, User
from datarooms.models import Dataroom, DataroomDocument
from dealroom.models import Activity, KeyScope
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
    assert hashlib.sha256(base.pdf).hexdigest() == base.work.source_sha256
    with patch('dealroom_sign.exports.Documenso') as remote_class, patch('dealroom_sign.storage.fileserver_client.upload_file'):
        remote_class.return_value.__enter__.return_value = client
        response = post(export_body(req, 'partial'))
        assert response.status_code == 200
        assert all('NOT FINAL' in page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
        assert models.RequestArtifact.objects.get(kind='partial').sha256 == response['X-Content-SHA256']
        client.get.side_effect = [client.get.return_value, {**client.get.return_value, 'status':'COMPLETED'}]
        assert post(export_body(req, 'partial')).status_code == 409


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
    for cls in ['SignatureRequestListView','SignatureOverviewView','SignatureRequestDetailView','SignaturePageListView','SignaturePageView','SignatureExportView']:
        oid = f'dealroom_sign_{cls}_endpoint_' + ('post' if cls == 'SignatureExportView' else 'get')
        assert oid in registry(), f'Missing slice 1 registry operation: {oid}'
        assert oid in tools
        assert registry()[oid]['boundary'] == 'staff'
        assert registry()[oid]['widens_access'] is False
        if cls in ['SignaturePageListView','SignaturePageView']:
            assert registry()[oid]['human_only'] is True


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
