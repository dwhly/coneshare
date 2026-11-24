"""Gate 3 recovery and approval regression cases; all storage is local/faked."""
import hashlib
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from datarooms.models import Dataroom, DataroomFolder, DataroomDocument, DataroomItemOrder
from documents.models import DocumentPage, DocumentVersion
from sharelinks.models import ShareLinkDataroomSetting
from dealroom import models, room_schemas
from dealroom.room_commands import execute
from dealroom.registry import registry
from dealroom.management.commands.dealroom_registry import inventory
from tests.dealroom.test_board_rooms import setup
from tests.dealroom.test_room_commands_s2 import (
    BASE, enable_s2, call, manifest, start, digest, continuation, complete, file_bytes,
)

pytestmark = pytest.mark.django_db


def writer(s):
    s.binding.role = 'writer'
    s.binding.room_capabilities = ['read', 'write']
    s.binding.save()


def batch(s, m, key='batch'):
    writer(s)
    row = models.BoardRoom.objects.get(room=s.room)
    return call(BASE+str(s.room.pk)+'/imports/', dict(expected_revision=row.revision,
        approved_manifest=m, manifest_sha256=digest(m), idempotency_key=key))


@pytest.mark.parametrize('creating', [False, True])
def test_render_failure_abandon_unlocks_and_new_review_succeeds(setup, creating):
    content = file_bytes('docx'); sha = hashlib.sha256(content).hexdigest()
    m = manifest([
        dict(client_item_id='folder', kind='folder', name='Reports', parent_id=None, position=4),
        dict(client_item_id='file', kind='file', name='Report.docx', parent_id='folder', position=0, sha256=sha, purpose='document'),
    ])
    if creating:
        response, original = start(setup, m)
    else:
        models.BoardRoom.objects.create(board_id='fixture', room=setup.room, build_state='ready')
        response = batch(setup, m)
    assert response.status_code == 201
    approved = response.json(); root = BASE+approved['id']+'/'
    f = call(root+'folders/', continuation(approved, 'folder', name='Reports', parent_id=None, position=4, client_item_id='folder'))
    with patch('documents.fileserver.fileserver_client.upload_file'):
        uploaded = call(root+'upload/', continuation(approved, 'upload', file=SimpleUploadedFile('Report.docx', content),
            folder_id=f.json()['id'], position='0', client_item_id='file', source_sha256=sha, purpose='document'), multipart=True)
    assert uploaded.status_code == 201, uploaded.content
    result = uploaded.json()
    DocumentVersion.objects.filter(pk=result['version_id']).update(render_status='failed')
    completion = complete(approved, m, [dict(client_item_id='file', version_id=result['version_id'], sha256=sha)], result['revision'])
    assert call(root+'complete/', completion).status_code == 409
    staff = APIClient(); staff.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(setup.user).access_token))
    assert staff.post(root+'folders/', {'name':'Staff'}, format='json').status_code == 409
    path = root+'imports/'+approved['import_id']+'/abandon/'
    body = dict(approval_key=approved['approval_key'], idempotency_key='abandon', expected_revision=result['revision'])
    assert call(path, body, via='service:assistant').status_code == 403
    assert call(path, {**body, 'approval_key':'different'}).status_code == 409
    assert call(path, {**body, 'expected_revision':1}).status_code == 409
    abandoned = call(path, body)
    assert abandoned.status_code == 200, abandoned.content
    assert call(path, body).json() == abandoned.json()
    assert not DataroomDocument.objects.filter(pk=result['id']).exists()
    assert not DataroomFolder.objects.filter(pk=f.json()['id']).exists()
    assert not DataroomItemOrder.objects.filter(dataroom_id=approved['id'], position=4).exists()
    assert models.RoomCommandReceipt.objects.filter(command_key='abandon', operation='abandon').exists()
    if creating:
        assert not Dataroom.objects.filter(pk=approved['id']).exists()
        assert call(BASE, original).status_code == 410
        fresh, _ = start(setup, m, key='review-2')
        assert fresh.status_code == 201, fresh.content
    else:
        assert DataroomDocument.objects.filter(pk=setup.item.pk).exists()
        assert staff.post(root+'folders/', {'name':'Staff'}, format='json').status_code == 201
        fresh = batch(setup, m, 'review-2')
        assert fresh.status_code == 201, fresh.content
    approved = fresh.json(); root = BASE+approved['id']+'/'
    f = call(root+'folders/', continuation(approved, 'folder-2', name='Reports', parent_id=None, position=4, client_item_id='folder'))
    assert f.status_code == 201
    with patch('documents.fileserver.fileserver_client.upload_file'):
        uploaded = call(root+'upload/', continuation(approved, 'upload-2', file=SimpleUploadedFile('Report.docx', content),
            folder_id=f.json()['id'], position='0', client_item_id='file', source_sha256=sha, purpose='document'), multipart=True)
    assert uploaded.status_code == 201
    result = uploaded.json()
    DocumentVersion.objects.filter(pk=result['version_id']).update(render_status='ready', has_pages=True, num_pages=1)
    completion = complete(approved, m, [dict(client_item_id='file', version_id=result['version_id'], sha256=sha)], result['revision'])
    assert call(root+'complete/', completion).status_code == 200
    assert ShareLinkDataroomSetting.objects.filter(dataroom_document_id=result['id'], is_visible=True).exists()


def test_position_zero_on_populated_room_requires_review(setup):
    models.BoardRoom.objects.create(board_id='fixture', room=setup.room, build_state='ready')
    DataroomItemOrder.objects.create(dataroom=setup.room, dataroom_document=setup.item, item_type='document', position=0)
    m = manifest([dict(client_item_id='folder', kind='folder', name='Reports', parent_id=None, position=0)])
    response = batch(setup, m)
    assert response.status_code == 409
    assert 'Room changed; review again' in str(response.content)
    assert not models.BoardRoom.objects.get(room=setup.room).staged_import


@pytest.mark.parametrize('name', ['file.exe', 'file.zip', 'file', 'file.pdf.exe'])
def test_approval_extension_allowlist(setup, name):
    m = manifest([dict(client_item_id='f', kind='file', name=name, parent_id=None, position=0, sha256='a'*64, purpose='document')])
    response, _ = start(setup, m)
    assert response.status_code == 400
    assert not models.RoomCommandReceipt.objects.exists()


def test_adopted_room_cannot_widen_access(setup):
    call_command('adopt_board_room', board='fixture', room=str(setup.room.pk))
    m = manifest(); m['access']['download_ceiling'] = 'watermarked'
    assert batch(setup, m).status_code == 409


@pytest.mark.parametrize('draft', [123, True])
def test_draft_id_requires_json_string(setup, draft):
    response, _ = start(setup, draft=draft)
    assert response.status_code == 400


def test_nonreceipt_integrity_error_is_definite(setup):
    with patch('dealroom.room_import.start', side_effect=IntegrityError('order collision')):
        response, _ = start(setup)
    assert response.status_code == 409
    assert 'review again' in str(response.content)
    assert 'retry' not in str(response.content)


@pytest.mark.parametrize('body', [[], {'name':'Folder', 'room':'invalid'}, {'name':'Folder', 'dataroom':['invalid']}])
def test_legacy_malformed_room_returns_400(setup, body):
    staff = APIClient(); staff.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(setup.user).access_token))
    response = staff.post(BASE+str(setup.room.pk)+'/folders/', body, format='json')
    assert response.status_code == 400


def test_empty_item_receipts_do_not_collide(setup):
    values = dict(board_id='fixture', actor='staff@example.test', via='tailscale', operation='lifecycle', payload_sha256='a'*64, import_id='', client_item_id='')
    models.RoomCommandReceipt.objects.create(command_key='first', **values)
    models.RoomCommandReceipt.objects.create(command_key='second', **values)
    values.update(import_id='batch', client_item_id='file')
    models.RoomCommandReceipt.objects.create(command_key='step', **values)
    with pytest.raises(IntegrityError), transaction.atomic():
        models.RoomCommandReceipt.objects.create(command_key='duplicate-step', **values)


@pytest.mark.parametrize('via,enabled', [('service:assistant', True), ('tailscale', False)])
def test_execute_rechecks_human_and_switch(setup, settings, via, enabled):
    writer(setup); settings.BOARD_ROOM_WRITES_ENABLED = enabled
    request = SimpleNamespace(data={}, FILES={}, board_binding=setup.binding, user=setup.user,
                              board_context={'login':setup.user.email, 'via':via})
    with pytest.raises(PermissionDenied):
        execute(request, 'create')


def test_abandon_inventory_schema_and_contract():
    name = 'dealroom_RoomViewSet_abandon_post'
    assert name in inventory()
    assert registry()[name]['tier'] == 'read_write'
    assert registry()[name]['boundary'] == 'staff'
    assert registry()[name]['human_only'] is True
    assert inventory() == registry()
    tools = json.loads((Path(__file__).resolve().parents[3]/'mcp-server/coneshare_mcp/dealroom_tools.json').read_text())
    tool = next(t for t in tools if t['operation_id'] == name)
    assert tool['human_only'] is True
    assert tool['parameters']['properties']['body'] == room_schemas.ABANDON
    assert set(tool['path_params']) == {'id', 'import_id'}
    contract = json.loads((Path(__file__).parent/'golden/board-rooms-v1.json').read_text())
    assert set(room_schemas.ABANDON['required']) == set(contract['commands']['operations']['abandon']['required'])


def test_upload_hashes_incrementally(setup):
    writer(setup)
    file = SimpleUploadedFile('file.pdf', b'abc')
    file.chunks = lambda: iter([b'a', b'b', b'c'])
    request = SimpleNamespace(data={'file':file, 'position':'0', 'idempotency_key':'hash'}, FILES={'file':file},
        board_binding=setup.binding, user=setup.user, board_context={'login':setup.user.email, 'via':'tailscale'})
    real_hash = hashlib.sha256
    streamed = []
    def hasher(data=b''):
        assert data != b'abc', 'Upload body must be hashed incrementally'
        obj = real_hash(data)
        class Hash:
            def update(self, chunk):
                streamed.append(chunk); obj.update(chunk)
            def hexdigest(self):
                return obj.hexdigest()
        return Hash()
    with patch('dealroom.room_commands.hashlib.sha256', side_effect=hasher), patch('dealroom.room_import.start', return_value={}):
        execute(request, 'create')
    assert streamed == [b'a', b'b', b'c']


@pytest.mark.parametrize('reference', ['document', 'page'])
def test_reaper_preserves_all_storage_references(setup, tmp_path, reference):
    key = f'{setup.org.pk}/board-import/{setup.room.pk}/'+('a'*64)+'/'+('b'*64)
    path = tmp_path/key; path.parent.mkdir(parents=True); path.write_bytes(b'referenced')
    os.utime(path, (time.time()-90000,)*2)
    if reference == 'document':
        setup.doc.storage_key = key; setup.doc.save()
    else:
        DocumentPage.objects.filter(document_version=setup.version).update(storage_key=key)
    call_command('reap_board_staging', storage_root=str(tmp_path), apply=True)
    assert path.exists()


def test_cancel_after_lost_completion_retains_published_room(setup):
    response, _ = start(setup); approved = response.json()
    done = call(BASE+approved['id']+'/complete/', complete(approved, manifest()))
    assert done.status_code == 200
    path = BASE+approved['id']+'/imports/'+approved['import_id']+'/abandon/'
    body = dict(approval_key=approved['approval_key'], idempotency_key='cancel-completed', expected_revision=done.json()['revision'])
    cancelled = call(path, body)
    assert cancelled.status_code == 200
    assert cancelled.json()['abandoned'] is False
    assert cancelled.json()['build_state'] == 'ready'
    assert Dataroom.objects.filter(pk=approved['id']).exists()
    assert call(path, body).json() == cancelled.json()
