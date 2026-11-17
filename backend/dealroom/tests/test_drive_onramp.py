import json
import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from django.core import signing
from django.utils import timezone
from rest_framework.test import APIClient

from cloudfiles.providers.base import CloudProviderError
from cloudfiles.providers.drive_snapshot import DriveSnapshotProvider, folder_id
from cloudfiles.providers.google_drive import GoogleDriveProvider
from datarooms.models import Dataroom, DataroomFolder
from dealroom.drive import walk_tree, match_template, import_tree, check_updates, publish_update, room_state
from dealroom.models import Activity
from documents.models import DocumentVersion

FIXTURES = Path(__file__).parent / 'fixtures' / 'drive'
LINK = 'https://drive.google.com/drive/folders/harbor-light'


@pytest.fixture
def snapshot(tmp_path, settings):
    shutil.copytree(FIXTURES, tmp_path / 'drive')
    settings.DEALROOM_DRIVE_SNAPSHOT_DIR = str(tmp_path / 'drive')
    return DriveSnapshotProvider('harbor-light')


@pytest.fixture
def room(staff):
    response = staff.post('/api/v1/dealroom/rooms/', {'name': 'Harbor Light'}, format='json')
    assert response.status_code == 201, response.data
    return Dataroom.objects.get(pk=response.data['id'])


@pytest.fixture
def storage(monkeypatch):
    files = {}
    def put(key, file, **kwargs):
        files[key] = file.read()
        file.seek(0)
    monkeypatch.setattr('dealroom.uploads.fileserver_client.upload_file', put)
    monkeypatch.setattr('dealroom.uploads.fileserver_client.delete_file', lambda key: files.pop(key, None))
    monkeypatch.setattr('documents.tasks.generate_pdf_pages_task.delay', lambda *args: None)
    monkeypatch.setattr('documents.tasks.convert_office_to_pdf_task.delay', lambda *args: None)
    return files


def test_snapshot_tree_and_exports(snapshot):
    nodes = walk_tree(snapshot, snapshot.root_id)
    assert len(nodes) == 16
    assert next(n for n in nodes if n['id'] == 'model')['folder_path'] == 'Financials'
    data = snapshot.download_file('overview')
    assert data['name'] == 'Company overview.pdf'
    assert data['content'].read(4) == b'%PDF'
    data['content'].close()
    sheet = snapshot.download_file('model')
    assert sheet['name'].endswith('.xlsx') and sheet['content'].read(2) == b'PK'
    sheet['content'].close()


def test_series_a_match_is_deterministic_and_conservative(snapshot):
    nodes = walk_tree(snapshot, snapshot.root_id)
    review = match_template(nodes)
    assert len(review['matched']) == 10
    assert {f['id'] for f in review['unsure']} == {'notes', 'board'}
    assert {s['id'] for s in review['missing']} == {'team', 'ip'}
    assert review == match_template(nodes)
    duplicate = next(n for n in nodes if n['id'] == 'deck').copy()
    duplicate['id'] = 'other-deck'
    result = match_template(nodes + [duplicate])
    assert any(f['id'] == 'other-deck' for f in result['unsure'])


@pytest.mark.django_db
def test_tree_import_keeps_structure_metadata_and_real_versions(snapshot, room, owner, storage):
    nodes = walk_tree(snapshot, 'harbor-light')
    import_tree(room, owner, {'harbor-light': snapshot}, nodes)
    assert room.documents.count() == 12
    item = room.documents.get(document__name='Company overview.pdf')
    assert item.folder.name == '01 Company'
    assert room.documents.get(document__name='Customer list - top 10.xlsx').folder is None
    version = item.document.versions.get(is_primary=True)
    assert version.metadata['drive_source']['webViewLink'] == 'https://drive.google.com/file/d/overview/view'
    assert version.metadata['drive_source']['modifiedTime'] == '2026-11-17T09:00:00Z'
    assert storage[version.original_storage_key].startswith(b'%PDF')
    assert all(not s.allow_download and s.enable_watermark for s in room.roompolicy.entry_link.dataroom_settings.all())
    owner.refresh_from_db()
    assert owner.total_document_size == 0
    import_tree(room, owner, {'harbor-light': snapshot}, nodes)
    assert room.documents.count() == 12


@pytest.mark.django_db
def test_provider_agnostic_import_with_nested_folder(room, owner, storage):
    class Provider:
        PROVIDER_NAME = 'ordinary_cloud'
        def list_files(self, path='/'):
            return {'root': [{'id': 'a', 'name': 'First', 'type': 'folder'}],
                    'a': [{'id': 'b', 'name': 'Second', 'type': 'folder'}],
                    'b': [{'id': 'file', 'name': 'Overview.pdf', 'type': 'file', 'mimeType': 'application/pdf',
                           'modifiedTime': '2026-11-17T09:00:00Z', 'webViewLink': 'https://drive.google.com/file/d/file/view'}]}[path]
        def download_file(self, file_id):
            content = (FIXTURES / 'harbor-light' / 'overview.pdf').read_bytes()
            return {'name': 'Overview.pdf', 'size': len(content), 'content': BytesIO(content), 'modifiedTime': '2026-11-17T09:00:00Z'}
    provider = Provider()
    import_tree(room, owner, {'root': provider}, walk_tree(provider, 'root'))
    assert room.documents.get().folder.parent.name == 'First'
    assert room.documents.get().folder.name == 'Second'


@pytest.mark.django_db
def test_check_does_not_publish_until_explicit_version_action(snapshot, room, owner, storage):
    import_tree(room, owner, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'))
    item = room.documents.get(document__name='Company overview.pdf')
    original = item.document.versions.get(is_primary=True)
    old_bytes = storage[original.original_storage_key]
    snapshot.nodes['overview']['modifiedTime'] = '2026-11-18T12:00:00Z'
    updates = check_updates(room, {'harbor-light': snapshot})
    assert len(updates) == 1
    original.refresh_from_db()
    assert original.is_primary and item.document.versions.count() == 1
    assert storage[original.original_storage_key] == old_bytes
    new = publish_update(room, owner, snapshot, updates[0])
    original.refresh_from_db()
    assert not original.is_primary and new.is_primary and new.version_number == 2
    assert check_updates(room, {'harbor-light': snapshot}) == []
    with pytest.raises(Exception, match='already updated'):
        publish_update(room, owner, snapshot, updates[0])


@pytest.mark.django_db
def test_api_review_confirmation_and_tenant_scope(snapshot, room, staff, storage, owner):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    response = staff.post(f'{base}/drive-review/', {'links': [LINK, LINK], 'template': 'series_a'}, format='json')
    assert response.status_code == 200, response.data
    assert room.documents.count() == 0
    choices = {f['id']: f['slot'] for f in response.data['matched']}
    result = staff.post(f'{base}/drive-import/', {'ticket': response.data['ticket'], 'choices': choices}, format='json')
    assert result.status_code == 201, result.data
    assert len(result.data['imported']) == 12
    assert room.documents.get(document__name='Financial model FY26-FY29.xlsx').folder.name == '02 Financials'
    assert len(room_state(room)['slots']) == 10
    other = staff.post('/api/v1/dealroom/rooms/', {'name': 'Other'}, format='json').data['id']
    result = staff.post(f'/api/v1/dealroom/rooms/{other}/drive-import/', {'ticket': response.data['ticket']}, format='json')
    assert result.status_code == 400
    from core.models import Organization
    foreign = Dataroom.objects.create(organization=Organization.objects.create(name='Other tenant'), name='Private')
    assert staff.get(f'/api/v1/dealroom/rooms/{foreign.pk}/outline/').status_code == 404


@pytest.mark.parametrize('url', ['https://example.com/drive/folders/x', 'https://drive.google.com/drive/folders/../private', 'file:///tmp/example'])
def test_only_drive_folder_links(url):
    with pytest.raises(CloudProviderError):
        folder_id(url)


def test_snapshot_disabled_and_path_boundary(snapshot, settings):
    settings.DEALROOM_DRIVE_SNAPSHOT_DIR = ''
    with pytest.raises(CloudProviderError, match='not configured'):
        DriveSnapshotProvider('harbor-light')
    snapshot.nodes['overview']['path'] = '../outside.pdf'
    with pytest.raises(CloudProviderError, match='inside'):
        snapshot.download_file('overview')


def test_google_provider_paginates_and_exposes_metadata():
    provider = object.__new__(GoogleDriveProvider)
    client = Mock()
    client.files().list().execute.side_effect = [
        {'files': [{'id': 'one', 'name': 'One', 'mimeType': 'application/pdf', 'modifiedTime': 'today', 'webViewLink': 'https://drive.google.com/file/d/one/view'}], 'nextPageToken': 'next'},
        {'files': [{'id': 'two', 'name': 'Two', 'mimeType': 'application/pdf', 'modifiedTime': 'today'}]},
    ]
    provider._get_client = lambda: client
    rows = provider.list_files('folder')
    assert [r['id'] for r in rows] == ['one', 'two']
    assert rows[0]['modifiedTime'] == 'today'
    assert client.files().list.call_args.kwargs['pageToken'] == 'next'


@pytest.mark.django_db
def test_personal_invitation_requires_post_and_respects_revocation(staff, room, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=False):
        result = staff.post(f'/api/v1/dealroom/rooms/{room.pk}/invite/', {'emails': ['maya@northwind.test'], 'notes': {'northwind.test': 'Start with the model.'}}, format='json')
    assert result.status_code == 201, result.data
    url = result.data['invitations'][0]['url']
    token = url.split('#personal=')[1]
    slug = room.roompolicy.entry_link.slug
    client = APIClient()
    assert client.get(f'/api/v1/dealroom/recipient/{slug}/personal/').status_code in (403, 405)
    assert 'dealroom_member' not in client.session
    entered = client.post(f'/api/v1/dealroom/recipient/{slug}/personal/', {'token': token}, format='json')
    assert entered.status_code == 200, entered.data
    data = client.get(f'/api/v1/dealroom/recipient/{slug}/room/').data
    assert data['note'] == 'Start with the model.'
    room.roompolicy.entry_link.access_grants.update(revoked_at=timezone.now())
    assert client.get(f'/api/v1/dealroom/recipient/{slug}/room/').status_code == 403
    assert client.post(f'/api/v1/dealroom/recipient/{slug}/personal/', {'token': token}, format='json').status_code == 403


@pytest.mark.django_db
def test_nda_setup_required_for_new_checklist(staff, room):
    from dealroom.onramp import personal_url
    from sharelinks.models import ShareLinkAccessGrant
    staff.patch(f'/api/v1/dealroom/rooms/{room.pk}/outline/', {'template': 'series_a'}, format='json')
    grant = ShareLinkAccessGrant.objects.create(share_link=room.roompolicy.entry_link, email='maya@northwind.test')
    client = APIClient()
    slug = room.roompolicy.entry_link.slug
    client.post(f'/api/v1/dealroom/recipient/{slug}/personal/', {'token': personal_url(room, grant).split('#personal=')[1]}, format='json')
    result = client.get(f'/api/v1/dealroom/recipient/{slug}/room/')
    assert result.status_code == 403 and result.data['code'] == 'nda_not_configured'

@pytest.mark.django_db
def test_distinct_same_name_folders_are_preserved(snapshot, room, owner, storage):
    # Same-name siblings are legal in Drive; never merge them by display name.
    snapshot.nodes['other-company'] = {**snapshot.nodes['company'], 'id': 'other-company'}
    snapshot.nodes['notes']['parents'] = ['other-company']
    import_tree(room, owner, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'))
    assert room.folders.filter(name='01 Company').count() == 2
    assert room.documents.get(document__name='Notes for investors - draft.pdf').folder_id != room.documents.get(document__name='Company overview.pdf').folder_id


@pytest.mark.django_db
def test_failed_publish_preserves_primary(snapshot, room, owner, storage):
    from rest_framework.exceptions import ValidationError
    import_tree(room, owner, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'))
    item = room.documents.get(document__name='Company overview.pdf')
    original = item.document.versions.get(is_primary=True)
    snapshot.nodes['overview']['modifiedTime'] = '2026-11-18T12:00:00Z'
    update = check_updates(room, {'harbor-light': snapshot})[0]
    (snapshot.directory / 'overview.pdf').write_bytes(b'incomplete export')
    with pytest.raises(ValidationError):
        publish_update(room, owner, snapshot, update)
    original.refresh_from_db()
    assert original.is_primary and item.document.versions.count() == 1


@pytest.mark.django_db
def test_copy_requests_keep_downloads_off_and_answers_private(snapshot, room, staff, owner, storage):
    from dealroom.onramp import personal_url
    from sharelinks.models import ShareLinkAccessGrant
    import_tree(room, owner, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'))
    item = room.documents.first()
    slug = room.roompolicy.entry_link.slug
    def recipient(email):
        grant = ShareLinkAccessGrant.objects.create(share_link=room.roompolicy.entry_link, email=email)
        client = APIClient()
        client.post(f'/api/v1/dealroom/recipient/{slug}/personal/', {'token': personal_url(room, grant).split('#personal=')[1]}, format='json')
        return client
    maya = recipient('maya@northwind.test')
    other = recipient('leo@harbor.test')
    result = maya.post(f'/api/v1/dealroom/recipient/{slug}/requests/', {'kind': 'copy', 'item_id': str(item.pk), 'page': 1, 'text': 'May I have a PDF?'}, format='json')
    assert result.status_code == 201, result.data
    assert len(staff.get(f'/api/v1/dealroom/rooms/{room.pk}/outline/').data['needs_you']) == 1
    reply = staff.post(f'/api/v1/dealroom/rooms/{room.pk}/answer/', {'id': result.data['id'], 'text': 'Let us discuss this tomorrow.'}, format='json')
    assert reply.status_code == 200
    data = maya.get(f'/api/v1/dealroom/recipient/{slug}/room/').data
    assert data['answers'][0]['text'] == 'Let us discuss this tomorrow.'
    assert all(f['download_level'] == 'none' for f in data['files'])
    assert other.get(f'/api/v1/dealroom/recipient/{slug}/room/').data['answers'] == []
    assert not staff.get(f'/api/v1/dealroom/rooms/{room.pk}/outline/').data['needs_you']


@pytest.mark.django_db
def test_personal_entry_checks_csrf_and_sign_return_uses_same_room(room, owner, client):
    from dealroom.onramp import personal_url
    from sharelinks.models import ShareLinkAccessGrant
    grant = ShareLinkAccessGrant.objects.create(share_link=room.roompolicy.entry_link, email='maya@northwind.test')
    slug = room.roompolicy.entry_link.slug
    browser = APIClient(enforce_csrf_checks=True)
    result = browser.post(f'/api/v1/dealroom/recipient/{slug}/personal/', {'token': personal_url(room, grant).split('#personal=')[1]}, format='json')
    assert result.status_code == 403
    assert client.get(f'/signing/room/{slug}').url == f'/view/{slug}'
    assert client.get(f'/signing/nda/{room.pk}').url == f'/view/{slug}'


def test_public_mailboxes_are_separate_firms():
    from dealroom.onramp import firm_key
    assert firm_key('maya@gmail.com') == 'maya@gmail.com'
    assert firm_key('leo@gmail.com') == 'leo@gmail.com'
    assert firm_key('maya@northwind.test') == 'northwind.test'

@pytest.mark.django_db
def test_office_snapshots_queue_server_page_previews(snapshot, room, owner, storage, monkeypatch, django_capture_on_commit_callbacks):
    office, pdf = Mock(), Mock()
    monkeypatch.setattr('documents.tasks.convert_office_to_pdf_task.delay', office)
    monkeypatch.setattr('documents.tasks.generate_pdf_pages_task.delay', pdf)
    with django_capture_on_commit_callbacks(execute=True):
        import_tree(room, owner, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'))
    assert office.call_count == 4
    assert pdf.call_count == 8
    assert room.documents.get(document__name='Pitch deck.pdf').document.versions.get(is_primary=True).num_pages == 6

@pytest.mark.django_db
def test_outline_move_updates_actual_visitor_folder(snapshot, room, staff, owner, storage):
    import_tree(room, owner, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'))
    item = room.documents.get(document__name='Notes for investors - draft.pdf')
    result = staff.patch(f'/api/v1/dealroom/rooms/{room.pk}/outline/', {'slots': {'overview': str(item.pk)}}, format='json')
    assert result.status_code == 200, result.data
    item.refresh_from_db()
    assert item.folder.name == '01 Company'

@pytest.mark.parametrize('mime,extension,exported', [
    ('application/vnd.google-apps.document', '.pdf', 'application/pdf'),
    ('application/vnd.google-apps.spreadsheet', '.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    ('application/vnd.google-apps.presentation', '.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
])
def test_workspace_export_mapping(snapshot, mime, extension, exported):
    snapshot.nodes['overview'].update(name='Snapshot', mimeType=mime, exportedMimeType=exported)
    data = snapshot.download_file('overview')
    try:
        assert data['name'] == 'Snapshot' + extension
        assert data['content_type'] == exported
    finally:
        data['content'].close()

@pytest.mark.django_db
def test_snapshot_update_api_reads_new_manifest_then_publishes(snapshot, room, staff, storage):
    base = f'/api/v1/dealroom/rooms/{room.pk}'
    review = staff.post(f'{base}/drive-review/', {'links': [LINK]}, format='json').data
    assert staff.post(f'{base}/drive-import/', {'ticket': review['ticket']}, format='json').status_code == 201
    path = snapshot.directory / 'manifest.json'
    data = json.loads(path.read_text())
    next(n for n in data['nodes'] if n['id'] == 'overview')['modifiedTime'] = '2026-11-20T10:00:00Z'
    path.write_text(json.dumps(data))
    response = staff.get(f'{base}/drive-updates/')
    assert response.status_code == 200, response.data
    update = response.data['updates'][0]
    item = room.documents.get(pk=update['item_id'])
    assert item.document.versions.count() == 1
    published = staff.post(f'{base}/drive-updates/', {'item_id': update['item_id'], 'modifiedTime': update['modifiedTime']}, format='json')
    assert published.status_code == 200, published.data
    assert item.document.versions.count() == 2
    assert staff.get(f'{base}/drive-updates/').data['updates'] == []


@pytest.mark.django_db
def test_demo_seed_is_repeatable_and_nda_stays_enabled(snapshot, owner, storage):
    from django.core.management import call_command
    from dealroom_sign.models import NdaPolicy
    from io import StringIO
    out = StringIO()
    for _ in range(2):
        call_command('seed_room_onramp', owner=owner.email, stdout=out)
    room = Dataroom.objects.get(name='Harbor Light Analytics · Series A')
    assert room.documents.count() == 12
    assert room_state(room)['require_nda'] is True
    assert NdaPolicy.objects.get(room=room).enabled
    assert 'Visitor: /view/' in out.getvalue()
    assert room.roompolicy.entry_link.access_grants.count() == 1
