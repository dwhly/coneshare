"""Gate 3 r2 regressions: nullable actors, portable fixtures and excluded facts."""
import base64
import json
from io import BytesIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone
from PIL import Image

from core.models import Organization
from datarooms.models import Dataroom, DataroomDocument, DataroomFolder
from dealroom import models
from dealroom_sign.models import ExecutedArtifact, RequestArtifact, SignatureRequest, Workflow
from documents.models import Document
from sharelinks.models import DataroomVisit, PageView, ViewSession
from tests.dealroom import test_board_rooms_r2 as golden_tests
from tests.dealroom.test_board_rooms import setup, image_transport, adopt, get, paths

pytestmark = pytest.mark.django_db


def test_contract_is_vendored():
    assert golden_tests.CONTRACT == golden_tests.GOLDEN / 'board-rooms-v1.json'
    assert golden_tests.CONTRACT.is_file()


def test_page_golden_accepts_different_png_encoding(settings, image_transport, tmp_path, monkeypatch):
    """The same decoded image can use a different valid compression stream."""
    for source in golden_tests.GOLDEN.glob('*.json'):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    page_path = tmp_path / 'page.json'
    page = json.loads(page_path.read_text())
    original = base64.b64decode(page['body_base64'])
    with Image.open(BytesIO(original)) as image:
        encoded = BytesIO()
        image.save(encoded, format='PNG', compress_level=0)
    assert encoded.getvalue() != original
    page['body_base64'] = base64.b64encode(encoded.getvalue()).decode()
    page_path.write_text(json.dumps(page))
    contract = json.loads(golden_tests.CONTRACT.read_text())
    contract['examples']['page'] = page
    contract_path = tmp_path / 'board-rooms-v1.json'
    contract_path.write_text(json.dumps(contract))
    monkeypatch.setattr(golden_tests, 'GOLDEN', tmp_path)
    monkeypatch.setattr(golden_tests, 'CONTRACT', contract_path)
    golden_tests.test_real_serializer_golden_contract(settings, image_transport)


@pytest.mark.parametrize('kind,actor', [('', None), ('staff', None), ('member', None),
                                      ('operator', 'Operator'), ('agent', 'Agent key')])
def test_activity_actor_and_summary(setup, kind, actor):
    adopt(setup)
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk),
        event_type='board.room.adopted', actor_kind=kind, actor_id='unknown')
    detail = get(paths(setup)['detail']).json()
    assert detail['activity'][0]['actor'] == actor
    phrase = (actor + ' added' if actor else 'Added') + ' the room to the board'
    assert detail['last_activity']['phrase'] == phrase
    assert get(paths(setup)['list']).json()['results'][0]['last_activity']['phrase'] == phrase


def test_unknown_stored_visit_actor_is_null(setup):
    adopt(setup)
    ViewSession.objects.create(share_link=setup.link, viewer_email='')
    detail = get(paths(setup)['detail']).json()
    assert detail['activity'][0]['actor'] is None
    assert detail['last_activity']['phrase'] == 'Visited the room'


def protect(s, kind):
    if kind == 'executed_folder':
        folder = DataroomFolder.objects.create(dataroom=s.room, name='Executed')
        s.item.folder = DataroomFolder.objects.create(dataroom=s.room, name='Evidence', parent=folder)
        s.item.save()
        return
    work = Workflow.objects.create(owner=s.user, room=s.room, source_version=s.version,
                                   external_id='r3', idempotency_key='r3')
    if kind == 'snapshot':
        req = SignatureRequest.objects.create(board_id='fixture', creator=s.user, workflow=work)
        RequestArtifact.objects.create(request=req, version=s.version, kind='partial',
                                       snapshot_id='a'*64, sha256='a'*64, size=10)
    else:
        ExecutedArtifact.objects.create(workflow=work, version=s.version, kind=kind,
                                        item_id='r3', sha256='a'*64, size=10)


@pytest.mark.parametrize('kind', ['snapshot', 'audit', 'signed'])
@pytest.mark.parametrize('removal', ['unlinked', 'other_room'])
def test_removed_protected_activity_is_omitted(setup, kind, removal):
    adopt(setup)
    protect(setup, kind)
    if removal == 'unlinked':
        setup.item.delete()
    else:
        setup.item.dataroom = Dataroom.objects.create(organization=setup.org, created_by=setup.user, name='Other')
        setup.item.save()
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk),
        event_type='document.removed', target_id=str(setup.doc.pk))
    detail = get(paths(setup)['detail']).json()
    assert detail['activity'] == []
    assert detail['last_activity'] is None


@pytest.mark.parametrize('kind', ['snapshot', 'audit', 'signed', 'executed_folder'])
@pytest.mark.parametrize('field', ['pages', 'downloaded'])
def test_visit_excludes_protected_item_facts(setup, kind, field):
    adopt(setup)
    protect(setup, kind)
    session = ViewSession.objects.create(share_link=setup.link, viewer_email='priya@northwind.test')
    visit = DataroomVisit.objects.create(view_session=session, dataroom_document=setup.item, downloaded_at=timezone.now())
    PageView.objects.create(view_session=session, dataroom_visit=visit, page_number=91, duration_seconds=22)
    models.Activity.objects.create(organization=setup.org, room_id=str(setup.room.pk),
        event_type='document.downloaded', target_id=str(setup.doc.pk),
        data={'visit_id': str(visit.pk), 'page': 92})
    result = get(paths(setup)['visits']).json()['results'][0]
    assert result[field] is None
    assert result['activity'] == []
    doc = Document.objects.create(organization=setup.org, created_by=setup.user, name='Public.pdf')
    item = DataroomDocument.objects.create(dataroom=setup.room, document=doc)
    visible = DataroomVisit.objects.create(view_session=session, dataroom_document=item, downloaded_at=timezone.now())
    PageView.objects.create(view_session=session, dataroom_visit=visible, page_number=2, duration_seconds=7)
    result = get(paths(setup)['visits']).json()['results'][0]
    assert result['pages'] == [2] and result['downloaded'] is True


@pytest.mark.parametrize('format', ['BMP', 'TIFF'])
def test_staff_preview_rejects_other_raster_formats(setup, image_transport, format):
    adopt(setup)
    encoded = BytesIO()
    with Image.new('RGB', (32, 32), 'white') as image:
        image.save(encoded, format=format)
    image_transport.response.headers = {'Content-Length': str(len(encoded.getvalue()))}
    image_transport.response.iter_content.return_value = [encoded.getvalue()]
    assert get(paths(setup)['page']).status_code == 503
    assert not models.Activity.objects.filter(event_type='board.preview.issued').exists()
    image_transport.response.headers = {'Content-Length': str(len(image_transport.source))}
    image_transport.response.iter_content.return_value = [image_transport.source]
    assert get(paths(setup)['page']).status_code == 200


@pytest.mark.parametrize('invalid', ['disabled', 'other_org'])
def test_adoption_requires_enabled_same_org_binding(setup, invalid):
    if invalid == 'disabled':
        setup.binding.enabled = False
        setup.binding.save()
    else:
        setup.user.organization = Organization.objects.create(name='Other')
        setup.user.save()
    with pytest.raises(CommandError, match='binding'):
        call_command('adopt_board_room', board='fixture', room=str(setup.room.pk))
    assert not models.BoardRoom.objects.filter(room=setup.room).exists()
    call_command('adopt_board_room', board='fixture', room=str(setup.room.pk), force=True)
    assert models.BoardRoom.objects.filter(room=setup.room).exists()
