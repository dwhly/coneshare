"""S1a board adoption, scoped reads and identified preview contracts."""
import io
import json
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.urls import resolve
from django.utils import timezone
from PIL import Image, ImageChops
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.authentication import generate_raw_api_key
from core.models import APIKey, Organization, User
from datarooms.models import Dataroom, DataroomDocument, DataroomFolder, DataroomItemOrder
from dealroom import models
from dealroom.registry import registry
from dealroom_sign.board_auth import signature
from dealroom_sign.models import BoardStaffBinding, ExecutedArtifact, RequestArtifact, SignatureRequest, Workflow
from documents.models import Document, DocumentPage, DocumentVersion
from sharelinks.models import ShareLink, ShareLinkAccessGrant, ViewSession, DataroomVisit, PageView

pytestmark = pytest.mark.django_db
PREFIX = '/api/v1/dealroom/board/rooms/'
KEY = 'board-room-fixture-key'
ACTIONS = ['list', 'detail', 'visits', 'pages', 'page']


def headers(path, via='tailscale', board='fixture', login='staff@example.test', method='GET'):
    context = json.dumps({'board': board, 'login': login, 'via': via}, sort_keys=True, separators=(',', ':'))
    stamp = str(int(time.time()))
    return {'HTTP_X_BOARD_CONTEXT': context, 'HTTP_X_BOARD_TIMESTAMP': stamp,
            'HTTP_X_BOARD_SIGNATURE': signature(KEY, method, path, b'', stamp, context)}


def get(path, **context):
    return APIClient().get(path, **headers(path, **context))


@pytest.fixture
def setup(settings):
    settings.BOARD_SIGN_PROXY_KEY = KEY
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.PDF_PREVIEW_ENGINE = 'server_pages'
    settings.ENABLE_OFFICE_PREVIEW = True
    org = Organization.objects.create(name='Board fixture')
    user = User.objects.create_user(username='staff@example.test', email='staff@example.test',
                                   organization=org, is_staff=True, role='admin')
    binding = BoardStaffBinding.objects.create(board_id='fixture', login=user.email,
                                               send_user=user, signer_email=user.email, role='reader')
    room = Dataroom.objects.create(organization=org, created_by=user, name='Board room')
    link = ShareLink.objects.create(dataroom=room, created_by=user, slug='board-fixture')
    models.RoomPolicy.objects.create(room=room, entry_link=link)
    doc = Document.objects.create(organization=org, created_by=user, name='Report.pdf', type='pdf', content_type='application/pdf')
    version = DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True,
        type='pdf', content_type='application/pdf', has_pages=True, num_pages=1,
        render_status='ready', original_storage_key='private/original.pdf')
    item = DataroomDocument.objects.create(dataroom=room, document=doc)
    DocumentPage.objects.create(document_version=version, page_number=1, storage_key='private/page.png')
    with patch('requests.sessions.Session.send', side_effect=AssertionError('Unexpected network')):
        yield SimpleNamespace(org=org, user=user, binding=binding, room=room, link=link, doc=doc, version=version, item=item)


def adopt(s):
    assert hasattr(models, 'BoardRoom'), 'S1a BoardRoom adoption is not implemented'
    s.binding.room_capabilities = ['read']
    s.binding.save()
    return models.BoardRoom.objects.create(board_id='fixture', room=s.room, build_state='ready')


def paths(s):
    detail = PREFIX + str(s.room.pk) + '/'
    pages = detail + f'documents/{s.item.pk}/pages/'
    query = f'?version_id={s.version.pk}'
    return dict(list=PREFIX, detail=detail, visits=detail+'visits/', pages=pages+query, page=pages+'1/'+query)


@pytest.fixture
def image_transport():
    out = io.BytesIO()
    with Image.new('RGB', (800, 1000), 'white') as source:
        source.save(out, format='PNG')
    response = Mock(status_code=200, headers={'Content-Length': str(len(out.getvalue()))})
    response.iter_content.return_value = [out.getvalue()]
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    with patch('documents.fileserver.fileserver_client.generate_download_url', return_value='http://core:8080/private/token') as url, \
         patch('requests.get', return_value=response) as fetch:
        yield SimpleNamespace(source=out.getvalue(), url=url, fetch=fetch, response=response)


@pytest.mark.parametrize('action', ACTIONS)
@pytest.mark.parametrize('via', ['tailscale', 'cloudflare'])
def test_scoped_human_reads(setup, image_transport, action, via):
    adopt(setup)
    response = get(paths(setup)[action], via=via)
    assert response.status_code == 200
    assert response['Cache-Control'] == 'private, no-store'
    assert 'private/' not in str(dict(response.items()))
    if action != 'page':
        assert not any(value in response.content.decode() for value in ['private/', 'http://core', 'original_storage_key', 'token'])


@pytest.mark.parametrize('action', ACTIONS)
@pytest.mark.parametrize('denial', ['board', 'org', 'missing_read', 'disabled', 'inactive_user', 'non_staff', 'service:worker', 'dev', 'jwt', 'api_key', 'recipient'])
def test_permission_matrix(setup, image_transport, action, denial):
    row = adopt(setup)
    path = paths(setup)[action]
    assert get(path).status_code == 200
    context = {}
    client = APIClient()
    if denial == 'board':
        row.board_id = 'other'; row.save()
    elif denial == 'org':
        setup.room.organization = Organization.objects.create(name='Other'); setup.room.save()
    elif denial == 'missing_read':
        setup.binding.room_capabilities = ['write']; setup.binding.save()
    elif denial == 'disabled':
        setup.binding.enabled = False; setup.binding.save()
    elif denial in ('inactive_user', 'non_staff'):
        setattr(setup.user, 'is_active' if denial == 'inactive_user' else 'is_staff', False); setup.user.save()
    elif denial in ('service:worker', 'dev'):
        context['via'] = denial
    elif denial == 'jwt':
        client.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(setup.user).access_token))
    elif denial == 'api_key':
        raw, prefix, hashed = generate_raw_api_key()
        APIKey.objects.create(user=setup.user, name='Fixture', prefix=prefix, hashed_key=hashed, tier='full_access')
        client.credentials(HTTP_AUTHORIZATION='Bearer '+raw)
    elif denial == 'recipient':
        session = client.session; session['dealroom_member'] = {'room_id': str(setup.room.pk), 'member_id': 'fixture'}; session.save()
    response = client.get(path) if denial in ('jwt', 'api_key', 'recipient') else get(path, **context)
    if denial in ('board', 'org') and action == 'list':
        assert response.status_code == 200 and response.data['results'] == []
    else:
        assert response.status_code == (404 if denial in ('board', 'org') else 403)


def test_detail_explicit_ids_order_people_nda_and_archived(setup):
    adopt(setup)
    folder = DataroomFolder.objects.create(dataroom=setup.room, name='Financials')
    setup.item.folder = folder; setup.item.save()
    DataroomItemOrder.objects.create(dataroom=setup.room, item_type='document', dataroom_document=setup.item, parent_folder=folder, position=3)
    grant = ShareLinkAccessGrant.objects.create(share_link=setup.link, email='person@example.test')
    models.RoomPolicy.objects.filter(room=setup.room).update(status='archived')
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='room.updated', data={'token': 'secret', 'url': 'http://private'})
    result = get(paths(setup)['detail']).data
    assert result['id'] == str(setup.room.pk) and result['archived'] is True
    assert result['build_state'] == 'ready' and result['revision'] == 1
    assert result['folders'][0]['id'] == str(folder.pk)
    item = result['items'][0]
    assert (item['item_id'], item['document_id'], item['version_id']) == tuple(str(v.pk) for v in [setup.item, setup.doc, setup.version])
    assert item['order'] == 3 and item['folder_id'] == str(folder.pk)
    assert result['grants'][0]['id'] == str(grant.pk)
    assert result['people'][0]['email'] == grant.email
    assert result['nda']['enabled'] is False
    assert result['activity'][0]['event_type'] == 'room.updated'
    assert 'secret' not in json.dumps(result, default=str) and 'http://private' not in json.dumps(result, default=str)


def test_visits_use_only_stored_session_and_visit_ids_and_nulls(setup):
    adopt(setup)
    blank = ViewSession.objects.create(share_link=setup.link)
    visit = ViewSession.objects.create(share_link=setup.link, viewer_email='person@example.test', ip_address='192.0.2.1',
        city='London', country='GB', user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        duration_seconds=42, latitude=51, longitude=-1)
    dv = DataroomVisit.objects.create(view_session=visit, dataroom_document=setup.item)
    PageView.objects.create(view_session=visit, dataroom_visit=dv, page_number=1, duration_seconds=42)
    joined = models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='document.downloaded', data={'view_session_id': str(visit.pk)})
    via_visit = models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='document.viewed', data={'visit_id': str(dv.pk), 'page': 2})
    unjoined = models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='document.downloaded', data={'email': visit.viewer_email})
    results = get(paths(setup)['visits']).data['results']
    empty = next(r for r in results if r['id'] == str(blank.pk))
    for field in ['email', 'ip', 'city', 'country', 'browser', 'device', 'duration_seconds', 'pages', 'downloaded']:
        assert empty[field] is None, field
    card = next(r for r in results if r['id'] == str(visit.pk))
    assert card['email'] == visit.viewer_email and card['ip'] == '192.0.2.1'
    assert card['browser'] == 'Chrome' and card['device'] == 'Desktop'
    assert card['duration_seconds'] == 42 and card['pages'] == [1, 2] and card['downloaded'] is True
    assert {e['id'] for e in card['activity']} == {str(joined.pk), str(via_visit.pk)}
    assert str(unjoined.pk) not in json.dumps(results, default=str)
    assert not {'latitude', 'longitude', 'user_agent', 'share_link', 'url'} & card.keys()


@pytest.mark.parametrize('kind', ['list', 'visits'])
def test_pagination_cursor_is_scoped(setup, kind):
    adopt(setup)
    other = Dataroom.objects.create(organization=setup.org, created_by=setup.user, name='Other')
    models.BoardRoom.objects.create(board_id='other', room=other, build_state='ready')
    link = ShareLink.objects.create(dataroom=other, created_by=setup.user)
    foreign = ViewSession.objects.create(share_link=link)
    if kind == 'list':
        for index in range(51):
            room = Dataroom.objects.create(organization=setup.org, created_by=setup.user, name=f'Room {index}')
            models.BoardRoom.objects.create(board_id='fixture', room=room, build_state='ready')
        path, foreign_id = PREFIX, str(other.pk)
    else:
        for _ in range(52):
            ViewSession.objects.create(share_link=setup.link)
        path, foreign_id = paths(setup)['visits'], str(foreign.pk)
    first = get(path).data
    assert len(first['results']) == 50 and first['next']
    second = get(path+'?cursor='+first['next']).data
    assert len(second['results']) == 2 and second['next'] is None
    assert not {r['id'] for r in first['results']} & {r['id'] for r in second['results']}
    assert get(path+'?cursor='+foreign_id).status_code == 404


@pytest.mark.parametrize('kind', ['item', 'version', 'missing_version', 'other_document_org'])
@pytest.mark.parametrize('action', ['pages', 'page'])
def test_page_membership_before_storage(setup, action, kind):
    adopt(setup)
    path = paths(setup)[action]
    other = Document.objects.create(organization=setup.org, created_by=setup.user, name='Other.pdf')
    version = DocumentVersion.objects.create(document=other, version_number=1)
    if kind == 'item':
        other_room = Dataroom.objects.create(organization=setup.org, name='Other')
        item = DataroomDocument.objects.create(dataroom=other_room, document=setup.doc)
        path = path.replace(str(setup.item.pk), str(item.pk))
    elif kind == 'version':
        path = path.replace(str(setup.version.pk), str(version.pk))
    elif kind == 'missing_version':
        path = path.split('?')[0]
    else:
        setup.doc.organization = Organization.objects.create(name='Other'); setup.doc.save()
    with patch('documents.fileserver.fileserver_client.generate_download_url') as storage:
        assert get(path).status_code in (400, 404)
        storage.assert_not_called()


@pytest.mark.parametrize('kind', ['snapshot', 'audit', 'signed', 'executed_folder'])
@pytest.mark.parametrize('action', ['pages', 'page'])
def test_protected_documents_excluded(setup, action, kind):
    adopt(setup)
    if kind == 'executed_folder':
        top = DataroomFolder.objects.create(dataroom=setup.room, name='Executed')
        child = DataroomFolder.objects.create(dataroom=setup.room, name='Evidence', parent=top)
        setup.item.folder = child; setup.item.save()
    else:
        work = Workflow.objects.create(owner=setup.user, room=setup.room, source_version=setup.version,
                                       external_id='fixture', idempotency_key='fixture')
        if kind == 'snapshot':
            req = SignatureRequest.objects.create(board_id='fixture', creator=setup.user, workflow=work)
            RequestArtifact.objects.create(request=req, version=setup.version, kind='partial', snapshot_id='a'*64, sha256='a'*64, size=10)
        else:
            ExecutedArtifact.objects.create(workflow=work, version=setup.version, kind=kind, item_id='fixture', sha256='a'*64, size=10)
    with patch('documents.fileserver.fileserver_client.generate_download_url') as storage:
        assert get(paths(setup)[action]).status_code == 403
        storage.assert_not_called()


@pytest.mark.parametrize('revoke', ['binding', 'capability', 'assignment'])
def test_revocation_between_page_list_and_fetch(setup, image_transport, revoke):
    row = adopt(setup)
    assert get(paths(setup)['pages']).status_code == 200
    if revoke == 'binding':
        setup.binding.enabled = False; setup.binding.save()
    elif revoke == 'capability':
        setup.binding.room_capabilities = []; setup.binding.save()
    else:
        row.delete()
    assert get(paths(setup)['page']).status_code == (404 if revoke == 'assignment' else 403)
    image_transport.url.assert_not_called()


@pytest.mark.parametrize('filetype', ['pdf', 'docx'])
def test_pages_are_stamped_with_staff_copy_and_not_recipient_visits(setup, image_transport, filetype):
    adopt(setup)
    if filetype == 'docx':
        setup.doc.name = 'Report.docx'; setup.doc.type = 'document'; setup.doc.save()
        setup.version.type = 'document'; setup.version.save()
    assert get(paths(setup)['pages']).data == {'status': 'ready', 'page_count': 1}
    with patch('dealroom.staff_preview._apply_watermark_to_image', wraps=__import__('sharelinks.views', fromlist=['_apply_watermark_to_image'])._apply_watermark_to_image) as stamp:
        response = get(paths(setup)['page'])
    assert response.status_code == 200 and response['Content-Type'] == 'image/png'
    assert response['X-Content-Type-Options'] == 'nosniff' and response['Referrer-Policy'] == 'no-referrer'
    copy_id = response['X-Dealroom-Copy-ID']
    identity = stamp.call_args.kwargs['identity']
    assert identity['email'] == setup.binding.login and identity['copy_id'] == copy_id
    with Image.open(io.BytesIO(response.content)) as actual, Image.open(io.BytesIO(image_transport.source)) as source:
        assert ImageChops.difference(actual.convert('RGB'), source.convert('RGB')).getbbox()
    image_transport.url.assert_called_once_with('private/page.png', is_internal=True)
    assert image_transport.fetch.call_args.kwargs['allow_redirects'] is False
    assert not ViewSession.objects.exists() and not DataroomVisit.objects.exists()
    fact = models.Activity.objects.get(event_type='board.preview.issued')
    assert fact.actor_id == str(setup.user.pk) and fact.data['copy_id'] == copy_id
    assert fact.data['binding_id'] == str(setup.binding.pk)


@pytest.mark.parametrize('state,expected', [('queued', 'processing'), ('processing', 'processing'), ('failed', 'failed'), ('not_applicable', 'failed')])
def test_missing_render_never_falls_back_to_original(setup, state, expected):
    adopt(setup)
    setup.version.has_pages = False; setup.version.render_status = state; setup.version.save()
    with patch('documents.fileserver.fileserver_client.generate_download_url') as storage:
        assert get(paths(setup)['pages']).data == {'status': expected, 'page_count': None}
        assert get(paths(setup)['page']).status_code == 409
        storage.assert_not_called()


@pytest.mark.parametrize('failure', ['fetch', 'watermark', 'oversize', 'invalid_image'])
def test_semaphore_released_on_render_error(setup, image_transport, failure):
    adopt(setup)
    from dealroom import hooks
    if failure == 'fetch':
        image_transport.fetch.side_effect = RuntimeError('private/token')
    elif failure == 'oversize':
        image_transport.response.headers['Content-Length'] = str(100 * 1024 * 1024)
    elif failure == 'invalid_image':
        image_transport.response.iter_content.return_value = [b'not an image']
    with patch('dealroom.staff_preview._apply_watermark_to_image', side_effect=RuntimeError('private/token')) if failure == 'watermark' else patch('dealroom.staff_preview.uuid.uuid4', wraps=__import__('uuid').uuid4):
        response = get(paths(setup)['page'])
    assert response.status_code == 503 and b'private/token' not in response.content
    assert hooks.RENDER_SEMAPHORE.acquire(blocking=False)
    hooks.RENDER_SEMAPHORE.release()
    assert not models.Activity.objects.filter(event_type='board.preview.issued').exists()


@pytest.mark.parametrize('evidence', ['none', 'grant', 'revoked_grant', 'activity', 'session'])
def test_adoption_seed_idempotence_and_undo(setup, evidence):
    assert hasattr(models, 'BoardRoom'), 'S1a BoardRoom adoption is not implemented'
    if evidence in ('grant', 'revoked_grant'):
        ShareLinkAccessGrant.objects.create(share_link=setup.link, email='person@example.test', revoked_at=timezone.now() if evidence == 'revoked_grant' else None)
    elif evidence == 'activity':
        models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='invitation.sent')
    elif evidence == 'session':
        ViewSession.objects.create(share_link=setup.link)
    for _ in range(2):
        call_command('adopt_board_room', board='fixture', room=str(setup.room.pk))
    row = models.BoardRoom.objects.get(room=setup.room)
    assert row.build_state == 'ready' and row.draft_id is None and row.creator_binding_id is None
    assert row.manifest_sha256 == '' and row.revision == 1
    assert (row.ever_invited_at is None) == (evidence == 'none')
    assert models.Activity.objects.filter(event_type='board.room.adopted').count() == 1
    with pytest.raises(CommandError):
        call_command('adopt_board_room', board='other', room=str(setup.room.pk))
    with pytest.raises(CommandError):
        call_command('adopt_board_room', board='other', room=str(setup.room.pk), undo=True)
    call_command('adopt_board_room', board='fixture', room=str(setup.room.pk), undo=True)
    assert not models.BoardRoom.objects.exists()
    assert Dataroom.objects.filter(pk=setup.room.pk).exists() and setup.room.documents.count() == 1
    assert ShareLink.objects.filter(pk=setup.link.pk).exists()
    assert models.Activity.objects.filter(event_type='board.room.unadopted').count() == 1


def test_null_drafts_multiple_non_null_unique_and_one_room(setup):
    first = adopt(setup)
    room = Dataroom.objects.create(organization=setup.org, name='Second')
    second = models.BoardRoom.objects.create(board_id='fixture', room=room)
    assert first.draft_id is None and second.draft_id is None
    first.draft_id = 'draft'; first.save()
    with pytest.raises(IntegrityError), transaction.atomic():
        second.draft_id = 'draft'; second.save()
    with pytest.raises(IntegrityError), transaction.atomic():
        models.BoardRoom.objects.create(board_id='other', room=setup.room)


def test_capabilities_default_and_validation(setup):
    assert 'room_capabilities' in {field.name for field in BoardStaffBinding._meta.fields}
    assert setup.binding.room_capabilities == []
    for invalid in [['admin'], {'read': True}, 'read', {}, '']:
        setup.binding.room_capabilities = invalid
        with pytest.raises(ValidationError):
            setup.binding.full_clean()
    for valid in [[], ['read'], ['write'], ['read', 'write']]:
        setup.binding.room_capabilities = valid
        setup.binding.full_clean()


def test_only_five_read_operations_and_legacy_boundaries(setup):
    adopt(setup)
    entries = registry()
    expected = {f'dealroom_BoardRoomReadViewSet_{action}_get' for action in ['list', 'retrieve', 'visits', 'pages', 'page']}
    assert {oid for oid in entries if 'BoardRoomReadViewSet' in oid} == expected
    for oid in expected:
        assert {k: entries[oid][k] for k in ['boundary', 'tier', 'human_only', 'widens_access']} == dict(boundary='staff', tier='read_only', human_only=True, widens_access=False)
    for oid, entry in entries.items():
        if oid.startswith(('analytics_', 'cloudfiles_')) or oid in ['documents_DocumentPreviewDataView_endpoint_get', 'documents_DocumentDownloadView_endpoint_get']:
            assert entry['boundary'] == 'denied'
    for oid in ['datarooms_DataroomViewSet_view_sessions_get', 'documents_DocumentViewSet_view_sessions_get']:
        assert entries[oid]['boundary'] == 'staff' and entries[oid]['human_only'] is False
    from dealroom_sign.board_auth import BoardProxyAuthentication
    assert resolve(PREFIX).func.cls.authentication_classes == [BoardProxyAuthentication]
    assert not hasattr(resolve(PREFIX).func.cls, 'create')
    assert get(PREFIX+'adopt/').status_code == 404
    for oid in ['documents_DocumentPreviewDataView_endpoint_get', 'documents_DocumentDownloadView_endpoint_get', 'analytics_DashboardSummaryView_endpoint_get']:
        path = entries[oid]['path'].replace('{document_id}', str(setup.doc.pk)).replace('{id}', str(setup.doc.pk))
        client = APIClient(); client.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(setup.user).access_token))
        assert client.get(path).status_code == 403
