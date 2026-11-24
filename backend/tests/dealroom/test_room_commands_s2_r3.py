"""Abandoned upload rows must release the staging storage references."""
import hashlib
import os
import time
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from dealroom import models
from documents.models import Document, DocumentPage, DocumentVersion
from tests.dealroom.test_board_rooms import setup
from tests.dealroom.test_room_commands_s2 import (
    BASE, call, continuation, enable_s2, file_bytes, manifest, start,
)
from tests.dealroom.test_room_commands_s2_r2 import batch

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('creating', [False, True])
def test_abandon_removes_staff_document_and_reaper_collects_upload(setup, tmp_path, creating):
    content = file_bytes('pdf')
    sha = hashlib.sha256(content).hexdigest()
    m = manifest([dict(client_item_id='file', kind='file', name='Report.pdf',
                       parent_id=None, position=4, sha256=sha, purpose='document')])
    if creating:
        response, _ = start(setup, m)
    else:
        models.BoardRoom.objects.create(board_id='fixture', room=setup.room, build_state='ready')
        response = batch(setup, m)
    assert response.status_code == 201
    approved = response.json()
    root = BASE+approved['id']+'/'
    with patch('documents.fileserver.fileserver_client.upload_file'):
        uploaded = call(root+'upload/', continuation(approved, 'upload',
            file=SimpleUploadedFile('Report.pdf', content), folder_id='', position='4',
            client_item_id='file', source_sha256=sha, purpose='document'), multipart=True)
    assert uploaded.status_code == 201, uploaded.content
    result = uploaded.json()
    doc = Document.objects.get(pk=result['document_id'])
    version = DocumentVersion.objects.get(pk=result['version_id'])
    key = version.original_storage_key or version.storage_key
    path = tmp_path/key
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    os.utime(path, (time.time()-90000,)*2)
    DocumentPage.objects.create(document_version=version, page_number=1, storage_key=key)
    call_command('reap_board_staging', storage_root=str(tmp_path), apply=True)
    assert path.exists()
    staff = APIClient()
    staff.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(setup.user).access_token))
    document_url = '/api/v1/documents/'+str(doc.pk)+'/'
    assert staff.get(document_url).status_code == 200
    body = dict(approval_key=approved['approval_key'], idempotency_key='abandon',
                expected_revision=result['revision'])
    response = call(root+'imports/'+approved['import_id']+'/abandon/', body)
    assert response.status_code == 200, response.content
    assert staff.get(document_url).status_code == 404
    assert not Document.objects.filter(pk=doc.pk).exists()
    assert not DocumentVersion.objects.filter(pk=version.pk).exists()
    assert not DocumentPage.objects.filter(document_version_id=version.pk).exists()
    assert Document.objects.filter(pk=setup.doc.pk).exists()
    assert path.exists()  # Storage collection occurs only after the DB commit.
    call_command('reap_board_staging', storage_root=str(tmp_path), apply=True)
    assert not path.exists()
    assert call(root+'imports/'+approved['import_id']+'/abandon/', body).json() == response.json()


def test_adopted_room_accepts_matching_download_ceiling(setup):
    call_command('adopt_board_room', board='fixture', room=str(setup.room.pk))
    m = manifest()
    assert m['access']['download_ceiling'] == 'none'
    response = batch(setup, m)
    assert response.status_code == 201, response.content
