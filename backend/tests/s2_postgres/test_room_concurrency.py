"""Run on an isolated PostgreSQL test database with run-postgres-tests.sh."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from django.db import close_old_connections, connection
from dealroom.models import BoardRoom
from dealroom import models
from tests.dealroom.test_room_commands_s2 import setup, enable_s2, manifest, digest, call, BASE

pytestmark=pytest.mark.django_db(transaction=True)


def test_same_key_concurrent_create_never_duplicates_or_500(setup):
    assert connection.vendor=='postgresql', 'This locking acceptance test requires PostgreSQL'
    setup.binding.role='writer';setup.binding.room_capabilities=['write'];setup.binding.save()
    m=manifest();body={'name':m['name'],'board_draft_id':'concurrent','draft_revision':1,
        'approved_manifest':m,'manifest_sha256':digest(m),'idempotency_key':'concurrent'}
    barrier=Barrier(2)
    def send():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            result=call(BASE,body)
            return result.status_code,result.json()
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:send(),range(2)))
    assert all(status in (201,409) for status,_ in results),results
    successes=[result for status,result in results if status==201]
    assert successes and all(result==successes[0] for result in successes)
    assert BoardRoom.objects.filter(draft_id='concurrent').count()==1
    assert models.RoomCommandReceipt.objects.filter(command_key='concurrent').count()==1
    assert call(BASE,body).json()==successes[0]


def test_same_key_concurrent_upload_has_one_item_version(setup):
    import hashlib
    from unittest.mock import patch
    from django.core.files.uploadedfile import SimpleUploadedFile
    from datarooms.models import DataroomDocument
    from documents.models import DocumentVersion
    from documents.renderers.base import BasePreviewRenderer
    from tests.dealroom.test_room_commands_s2 import file_bytes, start, continuation
    assert connection.vendor=='postgresql', 'This locking acceptance test requires PostgreSQL'
    content=file_bytes('pdf'); sha=hashlib.sha256(content).hexdigest()
    m=manifest([{'client_item_id':'file','kind':'file','name':'Report.pdf','parent_id':None,'position':0,'sha256':sha,'purpose':'document'}])
    r,_=start(setup,m); assert r.status_code==201
    result=r.json();barrier=Barrier(2)
    def send():
        close_old_connections()
        try:
            body=continuation(result,'concurrent-upload',file=SimpleUploadedFile('Report.pdf',content),folder_id='',position='0',
                              client_item_id='file',source_sha256=sha,purpose='document')
            barrier.wait(timeout=10)
            response=call(BASE+result['id']+'/upload/',body,multipart=True)
            return response.status_code,response.json()
        finally:
            close_old_connections()
    with patch('documents.fileserver.fileserver_client.upload_file'), patch.object(BasePreviewRenderer,'enqueue_render_task'):
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:send(),range(2)))
    assert responses[0][0]==responses[1][0]==201,responses
    assert responses[0][1]==responses[1][1]
    assert DataroomDocument.objects.filter(dataroom_id=result['id']).count()==1
    assert DocumentVersion.objects.filter(document_id=responses[0][1]['document_id']).count()==1


def test_receipt_migration_is_reversible_on_empty_isolated_database():
    from django.db.migrations.executor import MigrationExecutor
    assert connection.vendor=='postgresql'
    executor=MigrationExecutor(connection)
    leaves=executor.loader.graph.leaf_nodes()
    executor.migrate([('dealroom','0005_boardroom')])
    assert 'dealroom_roomcommandreceipt' not in connection.introspection.table_names()
    MigrationExecutor(connection).migrate(leaves)
    assert 'dealroom_roomcommandreceipt' in connection.introspection.table_names()
