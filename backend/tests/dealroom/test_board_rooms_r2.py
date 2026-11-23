"""Gate 3 and live-walk regressions, using real scoped responses."""
import base64
import json
import os
from datetime import datetime, timedelta, timezone as dt_timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from django.core.management import call_command, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Organization, User
from datarooms.models import Dataroom, DataroomDocument, DataroomFolder, DataroomItemOrder
from dealroom import models
from dealroom.staff_preview import _apply_watermark_to_image
from dealroom_sign.models import BoardStaffBinding, ExecutedArtifact, RequestArtifact, SignatureRequest, Workflow
from documents.models import Document, DocumentVersion, DocumentPage
from sharelinks.models import ShareLink, ViewSession, DataroomVisit, PageView
from sharelinks.amforge import footer_text
from tests.dealroom.test_board_rooms import setup, image_transport, adopt, get, headers, paths, PREFIX, ACTIONS, KEY

pytestmark = pytest.mark.django_db
GOLDEN = Path(__file__).with_name('golden')
CONTRACT = GOLDEN / 'board-rooms-v1.json'


def test_canonical_contract_and_summary(setup):
    adopt(setup)
    result = get(PREFIX).json()
    assert set(result) == {'results', 'next'}
    summary = result['results'][0]
    assert summary['document_count'] == 1 and summary['people_count'] == 0
    assert summary['last_activity'] is None
    folder = DataroomFolder.objects.create(dataroom=setup.room, name='01 Corporate')
    setup.item.folder = folder; setup.item.save()
    detail = get(paths(setup)['detail']).json()
    assert detail['folders'][0]['id'] == str(folder.pk)
    assert 'order' in detail['items'][0] and 'order' in detail['folders'][0]


@pytest.mark.parametrize('kind', ['snapshot', 'audit', 'signed', 'executed_folder'])
def test_detail_omits_protected_metadata(setup, kind):
    adopt(setup)
    if kind == 'executed_folder':
        top = DataroomFolder.objects.create(dataroom=setup.room, name='Executed')
        child = DataroomFolder.objects.create(dataroom=setup.room, name='Private evidence', parent=top)
        setup.item.folder = child; setup.item.save()
    else:
        work = Workflow.objects.create(owner=setup.user, room=setup.room, source_version=setup.version,
                                       external_id='fixture', idempotency_key='fixture')
        if kind == 'snapshot':
            req = SignatureRequest.objects.create(board_id='fixture', creator=setup.user, workflow=work)
            RequestArtifact.objects.create(request=req, version=setup.version, kind='partial', snapshot_id='a'*64, sha256='a'*64, size=10)
        else:
            ExecutedArtifact.objects.create(workflow=work, version=setup.version, kind=kind, item_id='fixture', sha256='a'*64, size=10)
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='document.uploaded', target_id=str(setup.doc.pk))
    response = get(paths(setup)['detail'])
    assert response.status_code == 200
    assert response.data['items'] == [] and response.data['folders'] == []
    assert str(setup.version.pk) not in response.content.decode()
    assert setup.doc.name not in response.content.decode()
    assert response.data['document_count'] == 0


def test_activity_phrases_actors_targets_and_stored_visits(setup, image_transport):
    adopt(setup)
    setup.user.name = 'Maya Chen'; setup.user.save()
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='document.uploaded',
        actor_kind='staff', actor_id=str(setup.user.pk), target_id=str(setup.doc.pk))
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='new.unknown')
    session = ViewSession.objects.create(share_link=setup.link, viewer_email='priya@northwind.test', city='Seattle',
        user_agent='Mozilla/5.0 (Macintosh) Version/17.5 Safari/605.1', duration_seconds=840, downloaded_at=timezone.now())
    blank = ViewSession.objects.create(share_link=setup.link, viewer_email='pat@harborlight.test')
    visit = DataroomVisit.objects.create(view_session=session, dataroom_document=setup.item)
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk), event_type='document.downloaded',
        actor_kind='member', actor_id='absent', target_id=str(setup.doc.pk), data={'visit_id': str(visit.pk)})
    assert get(paths(setup)['page']).status_code == 200
    assert models.Activity.objects.filter(event_type='board.preview.issued').exists()
    activity = get(paths(setup)['detail']).json()['activity']
    assert not {'board.preview.issued', 'new.unknown'} & {a['event_type'] for a in activity}
    upload = next(a for a in activity if a['event_type'] == 'document.uploaded')
    assert upload['actor'] == 'Maya Chen' and upload['phrase'] == 'uploaded' and upload['document'] == 'Report.pdf' and upload['at']
    download = next(a for a in activity if a['event_type'] == 'document.downloaded')
    assert download['actor'] == session.viewer_email and download['view_session_id'] == str(session.pk)
    assert {a['view_session_id'] for a in activity if a['event_type'] == 'room.visited'} == {str(session.pk), str(blank.pk)}
    visits = get(paths(setup)['visits']).json()['results']
    priya = next(v for v in visits if v['id'] == str(session.pk))
    assert (priya['city'], priya['browser'], priya['device'], priya['duration_seconds'], priya['downloaded']) == ('Seattle', 'Safari', 'Desktop', 840, True)
    assert next(v for v in visits if v['id'] == str(blank.pk))['duration_seconds'] is None


def test_image_only_accept_and_foreign_version(setup, image_transport):
    adopt(setup)
    for path, status in [(paths(setup)['page'], 200), (paths(setup)['page'].replace(str(setup.version.pk), '00000000000000000000000999'), 404)]:
        response = APIClient().get(path, HTTP_ACCEPT='image/png,image/jpeg,image/webp', **headers(path))
        assert response.status_code == status
        if status == 200: assert response['Content-Type'] == 'image/png'


def test_staff_footer_omits_missing_identity_fields(setup, image_transport):
    adopt(setup)
    setup.user.first_name = None; setup.user.last_name = None; setup.user.save()
    with patch('dealroom.staff_preview._apply_watermark_to_image', wraps=_apply_watermark_to_image) as stamp:
        assert get(paths(setup)['page']).status_code == 200
    identity = stamp.call_args.kwargs['identity']
    assert identity['name'] == setup.binding.login
    text = footer_text(identity)
    assert 'None' not in text and '· ·' not in text and 'UTC' in text
    assert text.count(setup.binding.login) == 1


def test_render_enqueue_after_commit(setup, django_capture_on_commit_callbacks):
    adopt(setup)
    setup.version.render_status = 'not_generated'; setup.version.has_pages = False; setup.version.save()
    renderer = Mock()
    renderer.get_effective_render_status.return_value = 'queued'
    with patch('dealroom.board_rooms.get_renderer', return_value=renderer):
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert get(paths(setup)['pages']).status_code == 200
            renderer.enqueue_render_task.assert_not_called()
        assert len(callbacks) == 1
        renderer.enqueue_render_task.assert_called_once()


def test_render_slot_timeout_returns_unavailable(setup, image_transport):
    adopt(setup)
    with patch('dealroom.board_rooms.hooks.RENDER_SEMAPHORE') as slot:
        slot.acquire.return_value = False
        assert get(paths(setup)['page']).status_code == 503
        assert slot.acquire.call_args.kwargs.get('timeout', 0) > 0
        slot.release.assert_not_called()
    image_transport.url.assert_not_called()


def test_adoption_unknown_board_requires_force(setup):
    with pytest.raises(CommandError, match='binding'):
        call_command('adopt_board_room', board='unconfigured', room=str(setup.room.pk))
    call_command('adopt_board_room', board='unconfigured', room=str(setup.room.pk), force=True)
    assert models.BoardRoom.objects.get(room=setup.room).board_id == 'unconfigured'


@pytest.mark.parametrize('action', ACTIONS)
@pytest.mark.parametrize('method', ['HEAD', 'OPTIONS'])
def test_other_methods_denied(setup, image_transport, action, method):
    adopt(setup)
    path = paths(setup)[action]
    assert APIClient().generic(method, path, **headers(path, method=method)).status_code in (403, 405)
    image_transport.url.assert_not_called()


@pytest.mark.parametrize('action', ACTIONS)
def test_json_format_suffix_keeps_scope(setup, image_transport, action):
    row = adopt(setup)
    path = paths(setup)[action]
    base, sep, query = path.partition('?')
    path = base.rstrip('/') + '.json' + (sep + query if sep else '')
    assert get(path).status_code == 200
    row.board_id = 'other'; row.save()
    response = get(path)
    assert response.status_code == (200 if action == 'list' else 404)
    if action == 'list': assert response.json()['results'] == []


@pytest.mark.parametrize('kind', ['pk', 'item_id', 'version_id', 'cursor', 'visit_cursor'])
def test_malformed_identifiers_return_404(setup, kind):
    adopt(setup)
    path = paths(setup)['page']
    if kind == 'pk': path = paths(setup)['detail'].replace(str(setup.room.pk), 'not-a-ulid')
    elif kind == 'item_id': path = path.replace(str(setup.item.pk), 'not-a-ulid')
    elif kind == 'version_id': path = path.replace(str(setup.version.pk), 'not-a-ulid')
    else: path = (PREFIX if kind == 'cursor' else paths(setup)['visits']) + '?cursor=not-a-ulid'
    assert get(path).status_code == 404


def test_archived_detail_retains_removed_document(setup):
    adopt(setup)
    models.RoomPolicy.objects.filter(room=setup.room).update(status='archived')
    setup.doc.deleted_at = timezone.now(); setup.doc.save()
    detail = get(paths(setup)['detail']).json()
    assert detail['archived'] is True and detail['items'][0]['lifecycle'] == 'removed'
    assert get(paths(setup)['page']).status_code == 403


def test_real_serializer_golden_contract(settings, image_transport):
    """Regenerate only with UPDATE_BOARD_GOLDEN=1; no hand-authored route payloads."""
    settings.BOARD_SIGN_PROXY_KEY = KEY
    settings.PDF_PREVIEW_ENGINE = 'server_pages'
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    fixed = datetime(2026, 11, 20, 12, 0, tzinfo=dt_timezone.utc)
    uid = lambda number: f'{number:026d}'
    with patch('django.utils.timezone.now', return_value=fixed):
        org = Organization.objects.create(id=uid(1), name='Northwind')
        user = User.objects.create_user(id=uid(2), username='staff@example.test', email='staff@example.test',
            name='Maya Chen', organization=org, is_staff=True, role='admin')
        BoardStaffBinding.objects.create(board_id='fixture', login=user.email, send_user=user, signer_email=user.email,
            role='reader', room_capabilities=['read'])
        older = Dataroom.objects.create(id=uid(9), organization=org, created_by=user, name='Lighthouse diligence')
        room = Dataroom.objects.create(id=uid(10), organization=org, created_by=user, name='Northwind diligence')
        for r in (older, room): models.BoardRoom.objects.create(board_id='fixture', room=r, build_state='ready')
        link = ShareLink.objects.create(id=uid(11), dataroom=room, created_by=user, slug='northwind-golden', require_nda=True)
        models.RoomPolicy.objects.create(room=room, entry_link=link)
        folder = DataroomFolder.objects.create(id=uid(20), dataroom=room, name='01 Corporate')
        empty = DataroomFolder.objects.create(id=uid(21), dataroom=room, name='Empty', parent=folder)
        DataroomItemOrder.objects.create(dataroom=room, item_type='folder', folder=folder, position=1)
        DataroomItemOrder.objects.create(dataroom=room, item_type='folder', folder=empty, parent_folder=folder, position=1)
        for number, name, parent in [(30, 'Report.docx', folder), (31, 'Overview.pdf', None)]:
            doc = Document.objects.create(id=uid(number), organization=org, created_by=user, name=name, type='pdf', content_type='application/pdf')
            version = DocumentVersion.objects.create(id=uid(number+10), document=doc, version_number=1, is_primary=True,
                type='pdf', content_type='application/pdf', has_pages=True, num_pages=2, render_status='ready')
            item = DataroomDocument.objects.create(id=uid(number+20), dataroom=room, document=doc, folder=parent)
            DataroomItemOrder.objects.create(dataroom=room, item_type='document', dataroom_document=item, parent_folder=parent, position=0)
            DocumentPage.objects.create(document_version=version, page_number=1, storage_key='private/page.png')
        session = ViewSession.objects.create(id=uid(60), share_link=link, viewer_email='priya@northwind.test',
            ip_address='203.0.113.24', city='Seattle', country='United States', duration_seconds=840,
            user_agent='Mozilla/5.0 (Macintosh) Version/17.5 Safari/605.1', downloaded_at=fixed)
        blank = ViewSession.objects.create(id=uid(61), share_link=link, viewer_email='pat@harborlight.test')
        ViewSession.objects.filter(pk__in=[session.pk, blank.pk]).update(viewed_at=fixed)
        models.Activity.objects.create(id='00000000-0000-0000-0000-000000000070', organization=org,
            room_id=str(room.pk), event_type='document.uploaded', actor_kind='staff', actor_id=str(user.pk), target_id=uid(30))
        models.Activity.objects.create(id='00000000-0000-0000-0000-000000000071', organization=org,
            room_id=str(room.pk), event_type='document.downloaded', actor_kind='member', actor_id='', target_id=uid(30),
            data={'view_session_id': str(session.pk)})
        adoption = models.Activity.objects.create(id='00000000-0000-0000-0000-000000000072', organization=org,
            room_id=str(room.pk), event_type='board.room.adopted', actor_kind='', actor_id='')
        models.Activity.objects.filter(pk=adoption.pk).update(created_at=fixed + timedelta(seconds=1))
        detail_path = PREFIX + str(room.pk) + '/'
        pages_path = detail_path + f'documents/{uid(50)}/pages/'
        with patch('dealroom.board_rooms.PAGE_SIZE', 1):
            examples = {'list': get(PREFIX).json(), 'detail': get(detail_path).json(),
                        'visits': get(detail_path+'visits/').json(),
                        'pages': get(pages_path+f'?version_id={uid(40)}').json()}
            assert 'results' in examples['list']
            examples['list-next'] = get(PREFIX+'?cursor='+examples['list']['next']).json()
            examples['visits-next'] = get(detail_path+'visits/?cursor='+examples['visits']['next']).json()
        with patch('dealroom.staff_preview.uuid.uuid4') as uuid4:
            uuid4.return_value.hex = 'f'*32
            # Leave the audit model's captured UUID default untouched.
            response = get(pages_path+f'1/?version_id={uid(40)}')
        assert response.status_code == 200
        examples['page'] = {'status': response.status_code, 'content_type': response['Content-Type'],
                            'body_base64': base64.b64encode(response.content).decode()}
    if os.environ.get('UPDATE_BOARD_GOLDEN') == '1':
        GOLDEN.mkdir(exist_ok=True)
        for name, value in examples.items():
            (GOLDEN / (name+'.json')).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    for name, value in examples.items():
        assert_example(name, json.loads((GOLDEN / (name+'.json')).read_text()), value)
    contract = json.loads(CONTRACT.read_text())
    assert set(contract['examples']) == set(examples)
    for name, value in examples.items():
        assert_example(name, contract['examples'][name], value)


def assert_example(name, expected, actual):
    if name != 'page':
        assert expected == actual, name
        return
    assert set(expected) == set(actual) == {'status', 'content_type', 'body_base64'}
    assert expected['status'] == actual['status'] == 200
    assert expected['content_type'] == actual['content_type'] == 'image/png'
    dimensions = []
    for value in (expected, actual):
        content = base64.b64decode(value['body_base64'], validate=True)
        assert content.startswith(b'\x89PNG\r\n\x1a\n')
        with Image.open(BytesIO(content), formats=['PNG']) as image:
            image.load()
            dimensions.append(image.size)
    assert dimensions[0] == dimensions[1]
