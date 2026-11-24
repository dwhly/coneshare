"""S2 receipt, visibility and continuation boundaries; no network services."""
import hashlib
import json
import time
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from dealroom import models
from dealroom_sign.board_auth import signature
from datarooms.models import Dataroom, DataroomItemOrder
from sharelinks.models import ShareLinkDataroomSetting, ShareLinkAccessGrant
from tests.dealroom.test_board_rooms import setup, KEY

pytestmark = pytest.mark.django_db
BASE = '/api/v1/dealroom/rooms/'

@pytest.fixture(autouse=True)
def enable_s2(settings):
    settings.BOARD_ROOM_WRITES_ENABLED = True


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def call(path, body, via='tailscale', method='POST', multipart=False):
    from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
    raw = encode_multipart(BOUNDARY, body) if multipart else json.dumps(body).encode()
    context = json.dumps({'board': 'fixture', 'login': 'staff@example.test', 'via': via}, sort_keys=True, separators=(',', ':'))
    stamp = str(int(time.time()))
    return APIClient().generic(method, path, raw, content_type=MULTIPART_CONTENT if multipart else 'application/json',
        HTTP_X_BOARD_CONTEXT=context, HTTP_X_BOARD_TIMESTAMP=stamp,
        HTTP_X_BOARD_SIGNATURE=signature(KEY, method, path, raw, stamp, context))

def manifest(items=None, nda=False):
    return {'name': 'Private review', 'items': items or [], 'nda': {'enabled': nda},
            'access': {'download_ceiling': 'none', 'expires_at': None}, 'intended_emails': []}

def start(s, m=None, key='create-1', draft='draft-1'):
    s.binding.role = 'writer'; s.binding.room_capabilities = ['read', 'write']; s.binding.save()
    m = m or manifest()
    body = {'name': m['name'], 'board_draft_id': draft, 'draft_revision': 1, 'approved_manifest': m,
            'manifest_sha256': digest(m), 'idempotency_key': key}
    return call(BASE, body), body

def continuation(result, key, **values):
    return {'approval_key': result['approval_key'], 'import_id': result['import_id'], 'idempotency_key': key, **values}

def complete(result, m, items=None, revision=None):
    return continuation(result, result['approval_key']+':complete', expected_revision=revision or result['revision'],
        manifest_sha256=digest(m), items=items or [], nda_revision=None, access=m['access'])

def test_create_receipt_response_loss_conflict_and_tombstone(setup):
    r, body = start(setup); assert r.status_code == 201, r.content
    first = r.json(); assert first['build_state'] == 'building'
    assert call(BASE, body).json() == first
    assert call(BASE, {**body, 'name':'Different'}).status_code == 409
    assert models.BoardRoom.objects.filter(draft_id='draft-1').count() == 1
    assert not ShareLinkAccessGrant.objects.filter(share_link__dataroom_id=first['id']).exists()
    # Delete policy first because the canonical link is protected by it.
    models.RoomPolicy.objects.filter(room_id=first['id']).delete()
    Dataroom.objects.filter(pk=first['id']).delete()
    assert call(BASE, body).status_code == 410
    assert not models.BoardRoom.objects.filter(draft_id='draft-1').exists()

@pytest.mark.parametrize('via', ['service:worker', 'agent', 'dev', ''])
@pytest.mark.parametrize('operation', ['create', 'folders', 'upload', 'complete', 'imports'])
def test_every_board_write_requires_human(setup, via, operation):
    setup.binding.role='writer'; setup.binding.room_capabilities=['write']; setup.binding.save()
    path = BASE if operation=='create' else BASE+str(setup.room.pk)+'/'+operation+'/'
    assert call(path, {}, via=via).status_code == 403

def test_empty_private_room_complete_and_stale_replay(setup):
    m=manifest(); r,_=start(setup,m); assert r.status_code==201
    initial=r.json(); path=BASE+initial['id']+'/complete/'; body=complete(initial,m)
    first=call(path,body); assert first.status_code==200, first.content
    assert first.json()['build_state']=='ready'
    assert call(path,body).json()==first.json()
    assert call(path,{**body,'idempotency_key':'other','expected_revision':1}).status_code==409

def test_nda_on_never_completes_without_policy(setup):
    m=manifest(nda=True); r,_=start(setup,m); assert r.status_code==201
    response=call(BASE+r.json()['id']+'/complete/',complete(r.json(),m))
    assert response.status_code==409
    assert 'NDA comes next' in str(response.content)
    assert models.BoardRoom.objects.get(room_id=r.json()['id']).build_state=='building'

def test_folder_tree_order_empty_and_stored_manifest(setup):
    items=[{'client_item_id':'parent','kind':'folder','name':'Parent','parent_id':None,'position':0},
           {'client_item_id':'empty','kind':'folder','name':'Empty','parent_id':'parent','position':2}]
    m=manifest(items); r,_=start(setup,m); assert r.status_code==201
    result=r.json(); path=BASE+result['id']+'/folders/'
    bad=continuation(result,'bad',name='Other',parent_id=None,position=0,client_item_id='parent')
    assert call(path,bad).status_code==409
    assert call(path,{**bad,'approved_manifest':manifest()}).status_code==400
    good={**bad,'name':'Parent','idempotency_key':'parent-step'}
    parent=call(path,good); assert parent.status_code==201, parent.content
    assert call(path,good).json()==parent.json()
    child=call(path,continuation(result,'empty-step',name='Empty',parent_id=parent.json()['id'],position=2,client_item_id='empty'))
    assert child.status_code==201
    assert DataroomItemOrder.objects.filter(dataroom_id=result['id']).count()==2
    assert not ShareLinkDataroomSetting.objects.filter(share_link__dataroom_id=result['id'],is_visible=True).exists()
    done=call(BASE+result['id']+'/complete/',complete(result,m,revision=child.json()['revision']))
    assert done.status_code==200, done.content
    assert ShareLinkDataroomSetting.objects.filter(share_link__dataroom_id=result['id'],is_visible=True).count()==2

def test_building_recipient_and_legacy_jwt_closed_ready_staff_works(setup):
    row=models.BoardRoom.objects.create(board_id='fixture',room=setup.room,build_state='building')
    from dealroom.policy import select_grant
    from rest_framework.exceptions import PermissionDenied
    ShareLinkAccessGrant.objects.create(share_link=setup.link,email='reader@example.test',created_by=setup.user)
    with pytest.raises(PermissionDenied,match='unavailable'):
        select_grant(setup.link,'reader@example.test')
    c=APIClient(); c.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(setup.user).access_token))
    for suffix,body in [('folders/',{'name':'Hidden'}),('policy/',{'status':'active'})]:
        method=c.patch if suffix=='policy/' else c.post
        assert method(BASE+str(setup.room.pk)+'/'+suffix,body,format='json').status_code==409
    row.build_state='ready'; row.save()
    assert c.post(BASE+str(setup.room.pk)+'/folders/',{'name':'Staff'},format='json').status_code==201

def test_legacy_doc_message(setup):
    from dealroom.uploads import upload
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError,match='save as .docx'):
        upload(setup.room,setup.user,SimpleUploadedFile('old.doc',b'legacy'))

def test_contract_operations():
    from pathlib import Path
    contract=json.loads((Path(__file__).parent/'golden/board-rooms-v1.json').read_text())
    assert set(contract['commands']['operations'])=={'create','folders','upload','imports','complete','abandon'}


def file_bytes(kind):
    import io
    if kind=='pdf':
        from pypdf import PdfWriter
        out=io.BytesIO(); writer=PdfWriter(); writer.add_blank_page(width=100,height=100); writer.write(out)
        return out.getvalue()
    import zipfile
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as package:
        package.writestr('[Content_Types].xml','<Types/>')
        package.writestr('word/document.xml','<document>Original Office bytes</document>')
    return out.getvalue()


@pytest.mark.parametrize('kind',['pdf','docx'])
def test_upload_replay_pinned_bytes_readiness_and_hash_check(setup,kind,django_capture_on_commit_callbacks):
    from unittest.mock import patch
    from datarooms.models import DataroomDocument
    from documents.models import DocumentVersion
    from documents.renderers.base import BasePreviewRenderer
    content=file_bytes(kind); sha=hashlib.sha256(content).hexdigest(); name='Report.'+kind
    m=manifest([{'client_item_id':'file','kind':'file','name':name,'parent_id':None,'position':0,'sha256':sha,'purpose':'document'}])
    r,_=start(setup,m); assert r.status_code==201
    initial=r.json(); path=BASE+initial['id']+'/upload/'
    def body(**changes):
        return continuation(initial,'upload-1',file=SimpleUploadedFile(name,content),folder_id='',position='0',
                            client_item_id='file',source_sha256=sha,purpose='document',**changes)
    with patch('documents.fileserver.fileserver_client.upload_file') as storage, patch.object(BasePreviewRenderer,'enqueue_render_task') as enqueue:
        with django_capture_on_commit_callbacks(execute=True):
            first=call(path,body(),multipart=True)
        assert first.status_code==201, first.content
        result=first.json(); assert enqueue.call_count==1
        assert call(path,body(),multipart=True).json()==result
        assert storage.call_count==1
        assert result['sha256']==sha
        version=DocumentVersion.objects.get(pk=result['version_id'])
        assert version.content_type.endswith('document') if kind=='docx' else version.content_type=='application/pdf'
        assert DataroomDocument.objects.filter(dataroom_id=initial['id']).count()==1
        assert DocumentVersion.objects.filter(document_id=result['document_id']).count()==1
        assert not ShareLinkDataroomSetting.objects.filter(dataroom_document_id=result['id'],is_visible=True).exists()
        completion=complete(initial,m,[{'client_item_id':'file','version_id':result['version_id'],'sha256':sha}],result['revision'])
        assert call(BASE+initial['id']+'/complete/',completion).status_code==409
        version.has_pages=True; version.num_pages=1; version.render_status='ready'; version.save()
        version.metadata={'source_sha256':'0'*64}; version.save()
        assert call(BASE+initial['id']+'/complete/',completion).status_code==409
        version.metadata={'source_sha256':sha}; version.num_pages=501; version.save()
        assert call(BASE+initial['id']+'/complete/',completion).status_code==409
        version.num_pages=1; version.save()
        done=call(BASE+initial['id']+'/complete/',completion)
        assert done.status_code==200, done.content
        assert call(BASE+initial['id']+'/complete/',completion).json()==done.json()
        assert ShareLinkDataroomSetting.objects.filter(dataroom_document_id=result['id'],is_visible=True).exists()


def test_add_batch_keeps_published_content_and_locks_legacy(setup):
    from dealroom.policy import select_grant
    from unittest.mock import patch
    row=models.BoardRoom.objects.create(board_id='fixture',room=setup.room,build_state='ready')
    setup.binding.role='writer'; setup.binding.room_capabilities=['read','write']; setup.binding.save()
    ShareLinkAccessGrant.objects.create(share_link=setup.link,email='reader@example.test',created_by=setup.user)
    m=manifest([{'client_item_id':'empty','kind':'folder','name':'Empty','parent_id':None,'position':4}])
    body={'expected_revision':1,'approved_manifest':m,'manifest_sha256':digest(m),'idempotency_key':'batch-1'}
    path=BASE+str(setup.room.pk)+'/'
    batch=call(path+'imports/',body); assert batch.status_code==201,batch.content
    assert call(path+'imports/',body).json()==batch.json()
    assert select_grant(setup.link,'reader@example.test')[0].room==setup.room
    c=APIClient();c.credentials(HTTP_AUTHORIZATION='Bearer '+str(RefreshToken.for_user(setup.user).access_token))
    assert c.post(path+'folders/',{'name':'Unapproved'},format='json').status_code==409
    for prefix,pk,change in [('grants',ShareLinkAccessGrant.objects.last().pk,{'download_ceiling':'watermarked'}),
                              ('share-links',setup.link.pk,{'name':'Changed'}),
                              ('file-policies',ShareLinkDataroomSetting.objects.get(dataroom_document=setup.item,share_link=setup.link).pk,{'is_visible':True})]:
        assert c.patch('/api/v1/dealroom/'+prefix+'/'+str(pk)+'/',change,format='json').status_code==409
    result=batch.json()
    folder=call(path+'folders/',continuation(result,'batch-folder',name='Empty',parent_id=None,position=4,client_item_id='empty'))
    assert folder.status_code==201,folder.content
    assert ShareLinkDataroomSetting.objects.get(dataroom_document=setup.item,share_link=setup.link).is_visible
    assert not ShareLinkDataroomSetting.objects.get(dataroom_folder_id=folder.json()['id'],share_link=setup.link).is_visible
    assert call(path+'complete/',complete(result,m,revision=folder.json()['revision'])).status_code==200
    assert c.post(path+'folders/',{'name':'Allowed'},format='json').status_code==201


@pytest.mark.parametrize('change',[{'approval_key':'missing'},{'import_id':'wrong'},{'name':'Other'},{'position':8},{'parent_id':'other'}])
def test_continuation_is_exactly_approved(setup,change):
    m=manifest([{'client_item_id':'folder','kind':'folder','name':'Folder','parent_id':None,'position':0}])
    r,_=start(setup,m); assert r.status_code==201
    body=continuation(r.json(),'folder-step',name='Folder',parent_id=None,position=0,client_item_id='folder')
    assert call(BASE+r.json()['id']+'/folders/',{**body,**change}).status_code==409
    assert DataroomItemOrder.objects.filter(dataroom_id=r.json()['id']).count()==0


@pytest.mark.parametrize('role,capabilities',[('reader',['write']),('writer',[]),('manager',['read'])])
def test_write_capability_and_role_required(setup,role,capabilities):
    setup.binding.role=role;setup.binding.room_capabilities=capabilities;setup.binding.save()
    assert call(BASE,{}).status_code==403


@pytest.mark.parametrize('case',['size','pages','office','rate'])
def test_agent_nda_preparation_bounds(setup,case):
    import io
    from pypdf import PdfWriter
    from django.core.cache import cache
    setup.binding.room_capabilities=['read'];setup.binding.save();cache.clear()
    body={'file':SimpleUploadedFile('nda.pdf',file_bytes('pdf'))}
    if case=='size':body['file']=SimpleUploadedFile('nda.pdf',b'%PDF-'+b'x'*(15*1024*1024))
    if case=='pages':
        writer=PdfWriter();out=io.BytesIO()
        for _ in range(51):writer.add_blank_page(width=100,height=100)
        writer.write(out);body['file']=SimpleUploadedFile('nda.pdf',out.getvalue())
    if case=='office':body['file']=SimpleUploadedFile('nda.docx',b'not-an-office-container')
    if case=='rate':cache.set('room-nda-placement:'+str(setup.binding.pk),10,60)
    result=call('/api/v1/dealroom-sign/nda-placement/',body,via='service:assistant',multipart=True)
    assert result.status_code==({'size':413,'pages':400,'office':400,'rate':429}[case]),result.content


def test_command_contract_has_typed_mcp_bodies():
    from pathlib import Path
    contract=json.loads((Path(__file__).parent/'golden/board-rooms-v1.json').read_text())['commands']
    from dealroom.room_schemas import IMPORTS, COMPLETE
    for name,schema in [('imports',IMPORTS),('complete',COMPLETE)]:
        assert set(schema['required'])==set(contract['operations'][name]['required'])
        assert set(schema['required'])==set(schema['properties'])


def test_recipient_sees_approved_empty_folders_only_after_completion(setup):
    from django.utils import timezone
    from sharelinks.models import Viewer
    m=manifest([{'client_item_id':'root','kind':'folder','name':'Outer','parent_id':None,'position':0},
                {'client_item_id':'child','kind':'folder','name':'Empty','parent_id':'root','position':1}])
    r,_=start(setup,m);result=r.json();room=Dataroom.objects.get(pk=result['id']);link=room.roompolicy.entry_link
    member=Viewer.objects.create(organization=setup.org,email='reader@example.test',verified_at=timezone.now())
    ShareLinkAccessGrant.objects.create(share_link=link,email=member.email,created_by=setup.user)
    c=APIClient();session=c.session;now=timezone.now().timestamp()
    session['dealroom_member']={'room_id':str(room.pk),'member_id':str(member.pk),'email':member.email,'expires':now+3600,'last_seen':now};session.save()
    url='/api/v1/dealroom/recipient/'+link.slug+'/room/'
    assert c.get(url).status_code==403
    parent=call(BASE+str(room.pk)+'/folders/',continuation(result,'root',name='Outer',parent_id=None,position=0,client_item_id='root')).json()
    child=call(BASE+str(room.pk)+'/folders/',continuation(result,'child',name='Empty',parent_id=parent['id'],position=1,client_item_id='child')).json()
    assert c.get(url).status_code==403
    assert call(BASE+str(room.pk)+'/complete/',complete(result,m,revision=child['revision'])).status_code==200
    view=c.get(url);assert view.status_code==200,view.content
    assert {f['name']:f['parent_id'] for f in view.json()['folders']}=={'Outer':None,'Empty':parent['id']}
    assert {f['name']:f['order'] for f in view.json()['folders']}=={'Outer':0,'Empty':1}
    assert view.json()['files']==[]


def test_rollout_switch_blocks_writes_not_receipt_retention(setup,settings):
    response,body=start(setup);assert response.status_code==201
    settings.BOARD_ROOM_WRITES_ENABLED=False
    assert call(BASE,body).status_code==403
    assert models.RoomCommandReceipt.objects.filter(command_key=body['idempotency_key']).exists()


def test_create_replay_rechecks_room_assignment_scope(setup):
    r,body=start(setup);assert r.status_code==201
    models.BoardRoom.objects.filter(room_id=r.json()['id']).delete()
    assert call(BASE,body).status_code==404


def test_staging_reaper_preserves_referenced_and_active_bytes(setup,tmp_path):
    import os
    from django.core.management import call_command
    folder=tmp_path/str(setup.org.pk)/'board-import'/str(setup.room.pk)/('a'*64)
    folder.mkdir(parents=True)
    published=folder/('b'*64);orphan=folder/('c'*64)
    for file in (published,orphan):
        file.write_bytes(b'fixture');os.utime(file,(time.time()-90000,)*2)
    setup.version.original_storage_key=published.relative_to(tmp_path).as_posix();setup.version.save()
    row=models.BoardRoom.objects.create(board_id='fixture',room=setup.room,build_state='ready',staged_import='active')
    call_command('reap_board_staging',storage_root=str(tmp_path),apply=True)
    assert published.exists() and orphan.exists()
    row.staged_import='';row.save()
    call_command('reap_board_staging',storage_root=str(tmp_path))
    assert published.exists() and orphan.exists()
    call_command('reap_board_staging',storage_root=str(tmp_path),apply=True)
    assert published.exists() and not orphan.exists()
