"""Abandon preserves independently referenced uploads and rejects stale revisions cleanly."""
import hashlib
import os
import time
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from datarooms.models import Dataroom, DataroomDocument
from dealroom import models
from documents.models import Document, DocumentVersion
from filerequests.models import FileRequest, UploadedFile
from sharelinks.models import QnAThread, ShareLink
from tests.dealroom.test_board_rooms import setup
from tests.dealroom.test_room_commands_s2 import (
    BASE, call, continuation, enable_s2, file_bytes, manifest, start,
)
from tests.dealroom.test_room_commands_s2_r2 import batch

pytestmark = pytest.mark.django_db


def staged(s, creating):
    content = file_bytes('pdf')
    sha = hashlib.sha256(content).hexdigest()
    m = manifest([dict(client_item_id='file', kind='file', name='Report.pdf',
                       parent_id=None, position=4, sha256=sha, purpose='document')])
    if creating:
        response, _ = start(s, m)
    else:
        models.BoardRoom.objects.create(board_id='fixture', room=s.room, build_state='ready')
        response = batch(s, m)
    assert response.status_code == 201
    approved = response.json()
    root = BASE + approved['id'] + '/'
    with patch('documents.fileserver.fileserver_client.upload_file'):
        uploaded = call(root + 'upload/', continuation(approved, 'upload',
            file=SimpleUploadedFile('Report.pdf', content), folder_id='', position='4',
            client_item_id='file', source_sha256=sha, purpose='document'), multipart=True)
    assert uploaded.status_code == 201, uploaded.content
    result = uploaded.json()
    body = dict(approval_key=approved['approval_key'], idempotency_key='abandon',
                expected_revision=result['revision'])
    return root + 'imports/' + approved['import_id'] + '/abandon/', body, result, content


@pytest.mark.parametrize('creating', [False, True])
@pytest.mark.parametrize('reference', ['share_link', 'second_room', 'qna', 'file_request', 'version'])
def test_abandon_keeps_independently_referenced_document(setup, tmp_path, creating, reference):
    path, body, result, content = staged(setup, creating)
    doc = Document.objects.get(pk=result['document_id'])
    version = DocumentVersion.objects.get(pk=result['version_id'])
    if reference == 'share_link':
        related = ShareLink.objects.create(document=doc, created_by=setup.user)
    elif reference == 'second_room':
        other = Dataroom.objects.create(organization=setup.org, created_by=setup.user, name='Other')
        related = DataroomDocument.objects.create(dataroom=other, document=doc)
    elif reference == 'qna':
        related = QnAThread.objects.create(organization=setup.org, share_link=setup.link,
                                          document=doc, subject='Report question')
    elif reference == 'file_request':
        request = FileRequest.objects.create(folder=doc.folder, created_by=setup.user, name='Reports')
        related = UploadedFile.objects.create(file_request=request, document=doc,
            uploader_name='Example', uploader_email='example@example.test')
    else:
        related = DocumentVersion.objects.create(document=doc, version_number=2,
            storage_key='custom/later.pdf')
    key = version.original_storage_key or version.storage_key
    stored = tmp_path / key
    stored.parent.mkdir(parents=True)
    stored.write_bytes(content)
    os.utime(stored, (time.time() - 90000,) * 2)
    response = call(path, body)
    assert response.status_code == 200, response.content
    assert Document.objects.filter(pk=doc.pk).exists()
    assert DocumentVersion.objects.filter(pk=version.pk).exists()
    assert type(related).objects.filter(pk=related.pk).exists()
    assert not DataroomDocument.objects.filter(pk=result['id']).exists()
    call_command('reap_board_staging', storage_root=str(tmp_path), apply=True)
    assert stored.exists()
    assert call(path, body).json() == response.json()


@pytest.mark.parametrize('creating', [False, True])
def test_abandon_stale_revision_writes_no_receipt_and_same_key_accepts_new_body(setup, creating):
    path, body, result, _ = staged(setup, creating)
    before = models.RoomCommandReceipt.objects.count()
    stale = {**body, 'expected_revision': body['expected_revision'] - 1}
    assert call(path, stale).status_code == 409
    assert models.RoomCommandReceipt.objects.count() == before
    assert not models.RoomCommandReceipt.objects.filter(command_key=body['idempotency_key']).exists()
    assert DataroomDocument.objects.filter(pk=result['id']).exists()
    response = call(path, body)
    assert response.status_code == 200, response.content
    assert models.RoomCommandReceipt.objects.filter(command_key=body['idempotency_key'], operation='abandon').count() == 1
    assert call(path, body).json() == response.json()
