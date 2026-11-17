import json

import pytest
from rest_framework.test import APIClient

from dealroom.onramp import personal_url
from sharelinks.models import ShareLinkAccessGrant
from dealroom.activity import record
from dealroom.drive import import_details, room_state
from dealroom.tests.test_drive_onramp import LINK, room, snapshot, storage  # noqa: F401


@pytest.mark.django_db
def test_outline_names_missing_slots_and_counts_only_unanswered_requests(staff, room, owner):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    staff.patch(f'{base}/outline/', {'template': 'series_a'}, format='json')
    question = record('room.request', organization=room.organization, actor=owner,
                      room_id=room.pk, data={'kind': 'question', 'firm': 'northwind.test', 'text': 'Timing?'})
    data = staff.get(f'{base}/outline/').data
    assert {'Team bios', 'IP assignment agreements'} <= {s['name'] for s in data['missing_slots']}
    assert data['needs_you_count'] == 1
    staff.post(f'{base}/answer/', {'id': str(question.pk), 'text': 'Next week.'}, format='json')
    assert staff.get(f'{base}/outline/').data['needs_you_count'] == 0


@pytest.mark.django_db
def test_review_exclude_and_move_are_applied_before_downloading(staff, room, snapshot, storage):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    review = staff.post(f'{base}/drive-review/', {'links': [LINK]}, format='json').data
    result = staff.post(f'{base}/drive-import/', {'ticket': review['ticket'], 'excluded': ['notes'],
                        'destinations': {'overview': 'financials'}}, format='json')
    assert result.status_code == 201, result.data
    assert len(result.data['imported']) == 11
    assert not room.documents.filter(document__name__startswith='Notes for investors').exists()
    assert room.documents.get(document__name='Company overview.pdf').folder.name == 'Financials'


@pytest.mark.django_db
@pytest.mark.parametrize('patch', [{'excluded': ['unknown']}, {'destinations': {'overview': 'outside'}},
                                   {'destinations': {'outside': 'financials'}}, {'excluded': 'notes'}])
def test_review_rejects_choices_outside_signed_tree(staff, room, snapshot, storage, patch):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    review = staff.post(f'{base}/drive-review/', {'links': [LINK]}, format='json').data
    result = staff.post(f'{base}/drive-import/', {'ticket': review['ticket'], **patch}, format='json')
    assert result.status_code == 400, result.data
    assert room.documents.count() == 0


@pytest.mark.django_db
def test_review_explains_exports_and_skips_unsupported_files(staff, room, snapshot, storage):
    path = snapshot.directory / 'manifest.json'
    data = json.loads(path.read_text())
    base_node = next(n for n in data['nodes'] if n['id'] == 'overview')
    for id, mime, size in [('shortcut', 'application/vnd.google-apps.shortcut', 0),
                           ('form', 'application/vnd.google-apps.form', 0),
                           ('large', 'application/pdf', 51 * 1024 * 1024)]:
        data['nodes'].append({**base_node, 'id': id, 'name': id + '.pdf', 'mimeType': mime, 'size': size})
    data['nodes'].append({**base_node, 'id': 'unavailable', 'path': None})
    path.write_text(json.dumps(data))
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    review = staff.post(f'{base}/drive-review/', {'links': [LINK]}, format='json').data
    files = {n['id']: n for n in review['nodes'] if n['type'] == 'file'}
    assert files['overview']['import_description'] == 'Google Doc, saved as a PDF copy'
    assert files['overview']['final_name'] == 'Company overview.pdf'
    assert files['model']['final_type'] == 'xlsx'
    assert files['deck']['import_description'] == 'PDF, added as is'
    assert {n['id'] for n in review['skipped']} == {'shortcut', 'form', 'large', 'unavailable'}
    assert all(n['skip_reason'] for n in review['skipped'])
    result = staff.post(f'{base}/drive-import/', {'ticket': review['ticket']}, format='json')
    assert result.status_code == 201, result.data
    assert len(result.data['imported']) == 12


@pytest.mark.django_db
def test_drive_check_time_persists_without_publishing(staff, room, snapshot, storage):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    review = staff.post(f'{base}/drive-review/', {'links': [LINK]}, format='json').data
    staff.post(f'{base}/drive-import/', {'ticket': review['ticket']}, format='json')
    checked = staff.get(f'{base}/drive-updates/').data
    assert checked['checked_at']
    assert staff.get(f'{base}/outline/').data['drive_checked_at'] == checked['checked_at']
    assert len(room_state(room)['drive_roots']) == 1


@pytest.mark.django_db
def test_preverification_brand_and_sender_never_include_room_name(staff, room, owner):
    owner.name = 'Dan Whaley'
    owner.save(update_fields=['name'])
    room.created_by = owner
    room.save(update_fields=['created_by'])
    client = APIClient()
    data = client.get(f'/api/v1/dealroom/recipient/{room.roompolicy.entry_link.slug}/challenge/').data
    assert data['sender_name'] == 'Dan Whaley'
    assert data['brand']['name'] and data['brand']['logo']
    assert room.name not in json.dumps(data)
    assert 'dealroom_member' not in client.session


@pytest.mark.django_db
def test_invitation_preview_uses_current_owner_without_redeeming(room, owner):
    grant = ShareLinkAccessGrant.objects.create(share_link=room.roompolicy.entry_link, email='maya@northwind.test')
    owner.name = 'Dan Whaley'
    owner.save(update_fields=['name'])
    token = personal_url(room, grant, owner).split('#personal=')[1]
    client = APIClient()
    url = f'/api/v1/dealroom/recipient/{room.roompolicy.entry_link.slug}/challenge/'
    response = client.get(url, HTTP_X_ROOM_INVITATION=token)
    assert response.data['sender_name'] == 'Dan Whaley'
    assert room.name not in json.dumps(response.data)
    assert 'dealroom_member' not in client.session
    grant.delete()
    assert client.get(url, HTTP_X_ROOM_INVITATION=token).data['sender_name'] == ''


@pytest.mark.parametrize('mime,extension,description', [
    ('application/vnd.google-apps.document', 'pdf', 'Google Doc, saved as a PDF copy'),
    ('application/vnd.google-apps.spreadsheet', 'xlsx', 'Google Sheet, saved as an Excel file copy'),
    ('application/vnd.google-apps.presentation', 'pptx', 'Google Slides, saved as a PowerPoint file copy'),
])
def test_export_wording_names_source_and_final_type(mime, extension, description):
    result = import_details({'name': 'Plan', 'mimeType': mime})
    assert result['final_type'] == extension
    assert result['final_name'] == f'Plan.{extension}'
    assert result['import_description'] == description


@pytest.mark.django_db
def test_repeat_review_lists_existing_files_as_skipped(staff, room, snapshot, storage):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    data = staff.post(f'{base}/drive-review/', {'links': [LINK]}, format='json').data
    staff.post(f'{base}/drive-import/', {'ticket': data['ticket']}, format='json')
    data = staff.post(f'{base}/drive-review/', {'links': [LINK]}, format='json').data
    assert not any(n['type'] == 'file' for n in data['nodes'])
    assert len(data['skipped']) == 12
    assert all(n['skip_reason'].startswith('Already in this room') for n in data['skipped'])


@pytest.mark.django_db
def test_visitors_never_receive_checklist_slots_or_empty_folders(staff, room, snapshot, storage):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    review = staff.post(f'{base}/drive-review/', {'links': [LINK], 'template': 'series_a'}, format='json').data
    choices = {file['id']: file['slot'] for file in review['matched']}
    staff.post(f'{base}/drive-import/', {'ticket': review['ticket'], 'choices': choices}, format='json')
    staff.patch(f'{base}/outline/', {'require_nda': False}, format='json')
    grant = ShareLinkAccessGrant.objects.create(share_link=room.roompolicy.entry_link, email='maya@northwind.test')
    client = APIClient()
    slug = room.roompolicy.entry_link.slug
    client.post(f'/api/v1/dealroom/recipient/{slug}/personal/',
                {'token': personal_url(room, grant).split('#personal=')[1]}, format='json')
    result = client.get(f'/api/v1/dealroom/recipient/{slug}/room/')
    assert result.status_code == 200, result.data
    assert not {'slots', 'missing_slots', 'slot_definitions'} & result.data.keys()
    assert 'Team bios' not in json.dumps(result.data)
    assert 'IP assignment agreements' not in json.dumps(result.data)
    assert not any(folder['name'] == '08 Team' for folder in result.data['folders'])
