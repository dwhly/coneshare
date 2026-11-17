"""Round-three visitor behavior, using fictional identities and real PDF geometry."""
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pdfplumber
import pytest
from PIL import Image, ImageChops
from django.core.management import call_command, CommandError
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

from datarooms.models import Dataroom, DataroomItemOrder
from dealroom.onramp import personal_url
from dealroom.drive import import_tree, walk_tree
from dealroom.watermarks import effective_style
from dealroom_sign.models import ExecutedArtifact, NdaAcceptance, NdaPolicy, SignCredential, Workflow
from dealroom_sign.validation import digest
from dealroom_sign.workflows import envelope_meta, reset_nda
from dealroom_sign.recipient_proxy import terminal
from documents.models import Document, DocumentVersion
from sharelinks.models import ShareLinkAccessGrant, ShareLinkDataroomSetting, Viewer
from sharelinks.views import _apply_watermark_to_image, _generate_watermarked_pdf
from dealroom.tests.test_drive_onramp import room, snapshot, storage

HARBOR = Path(__file__).resolve().parents[2] / 'dealroom_sign/tests/fixtures/placement/harbor.pdf'
DEMO = Path(__file__).parent / 'fixtures/drive/harbor-light/nda.pdf'


def version_for(room, pdf, name="Mutual NDA.pdf"):
    doc = Document.objects.create(organization=room.organization, created_by=room.created_by,
        name=name, content_type='application/pdf', type='pdf')
    version = DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True,
        content_type='application/pdf', original_storage_key='fictional/nda.pdf',
        file_size=len(pdf), metadata={'source_sha256': digest(pdf)})
    room.documents.create(document=doc, name=doc.name)
    return version


def visitor(room, email='lee@harborlight.fleet.test', name='Lee Harbor'):
    member = Viewer.objects.create(organization=room.organization, email=email, name=name)
    link = room.roompolicy.entry_link
    grant = ShareLinkAccessGrant.objects.create(share_link=link, email=email,
        created_by=room.created_by, download_ceiling='none')
    client = APIClient()
    assert client.post(f'/api/v1/dealroom/recipient/{link.slug}/personal/',
        {'token': personal_url(room, grant).split('#personal=')[1]}, format='json').status_code == 200
    return client, member


@pytest.mark.django_db
def test_runtime_nda_uses_real_counterparty_line_even_with_old_policy_fields(room, monkeypatch, settings):
    settings.SIGN_RECIPIENT_ORIGIN = "https://sign.test"
    pdf = HARBOR.read_bytes()
    version = version_for(room, pdf)
    policy = NdaPolicy.objects.create(room=room, source_version=version, source_sha256=digest(pdf),
        fields=[{'type': 'SIGNATURE', 'page': 2, 'positionX': 10, 'positionY': 70, 'width': 30, 'height': 10}])
    client, member = visitor(room)
    SignCredential.objects.create(owner=room.created_by, team_id=1, token='api_fictional')
    monkeypatch.setattr('dealroom_sign.workflows.source_bytes', lambda v: pdf)
    response = client.post(f'/api/v1/dealroom-sign/nda/{room.pk}/')
    assert response.status_code == 201, response.data
    work = Workflow.objects.get(room=room)
    field = next(f for f in work.recipients[0]['fields'] if f['type'] == 'SIGNATURE')
    with pdfplumber.open(BytesIO(pdf)) as document:
        page = document.pages[1]
        caption = next(w for w in page.extract_words() if w['text'] == 'Lee')
        line = max((l for l in page.lines if l['top'] < caption['top']), key=lambda l: l['top'])
        assert field['page'] == 2
        assert line['top'] - 35 <= field['positionY'] * page.height / 100 <= line['top']
        assert abs((field['positionY'] + field['height']) * page.height / 100 - line['top']) < 4
    assert work.observedsignevent_set.filter(kind='placement.resolved').exists()
    assert envelope_meta(work)['redirectUrl'].endswith('/s/return/' + str(work.pk))


@pytest.mark.django_db
def test_runtime_uncertain_nda_holds_without_creating_workflow(room, monkeypatch):
    pdf = HARBOR.read_bytes()
    version = version_for(room, pdf)
    NdaPolicy.objects.create(room=room, source_version=version, source_sha256=digest(pdf), fields=[])
    client, _ = visitor(room, 'different@northwind.test', 'Different Visitor')
    SignCredential.objects.create(owner=room.created_by, team_id=1, token='api_fictional')
    monkeypatch.setattr('dealroom_sign.workflows.source_bytes', lambda v: pdf)
    response = client.post(f'/api/v1/dealroom-sign/nda/{room.pk}/')
    assert response.status_code == 409
    assert response.data['status'] == 'needs_sender'
    assert not Workflow.objects.filter(room=room).exists()


@pytest.mark.django_db
def test_seed_uses_real_placement_and_populates_folders(snapshot, owner, storage):
    call_command('seed_room_onramp', owner=owner.email, stdout=StringIO())
    room = Dataroom.objects.get(name='Harbor Light Analytics · Series A')
    assert room.folders.filter(dataroomdocument__isnull=False).exists()
    field = next(f for f in NdaPolicy.objects.get(room=room).fields if f['type'] == 'SIGNATURE')
    with pdfplumber.open(DEMO) as document:
        page = document.pages[1]
        caption = next(w for w in page.extract_words() if w['text'] == 'Maya')
        line = max((l for l in page.lines if l['top'] < caption['top']), key=lambda l: l['top'])
        assert field['page'] == 2
        assert line['top'] - 35 <= field['positionY'] * page.height / 100 <= line['top']


@pytest.mark.django_db
def test_seed_reports_unattributable_nda(snapshot, owner, storage, monkeypatch):
    monkeypatch.setattr('dealroom_sign.placement.place', lambda *a, **k: {
        'status': 'needs_sender', 'fields': [], 'reason': 'No attributable signature cues.'})
    with pytest.raises(CommandError, match='NDA placement.*No attributable'):
        call_command('seed_room_onramp', owner=owner.email, stdout=StringIO())
    assert not NdaPolicy.objects.exists()


@pytest.fixture
def signed(room, monkeypatch):
    pdf = HARBOR.read_bytes()
    version = version_for(room, pdf)
    policy = NdaPolicy.objects.create(room=room, source_version=version, source_sha256=digest(pdf))
    client, member = visitor(room)
    work = Workflow.objects.create(owner=room.created_by, room=room, purpose='nda',
        member_id=str(member.pk), member_email=member.email, policy_revision=str(policy.revision),
        source_version=version, source_sha256=digest(pdf), external_id='fictional:nda',
        idempotency_key='fictional:nda', state='awaiting_seal',
        signer_projection=[{'email': member.email, 'signingStatus': 'SIGNED', 'signedAt': '2026-11-17T12:00:00Z'}])
    return SimpleNamespace(room=room, client=client, member=member, work=work, pdf=pdf,
        base=f'/api/v1/dealroom/recipient/{room.roompolicy.entry_link.slug}')


def complete(signed):
    work = signed.work
    work.state = 'done'; work.completed_at = timezone.now(); work.save()
    NdaAcceptance.objects.create(room=work.room, member_id=work.member_id, member_email=work.member_email,
        workflow=work, policy_revision=work.policy_revision)
    version = version_for(work.room, signed.pdf, name="Executed NDA.pdf")
    ExecutedArtifact.objects.create(workflow=work, version=version, kind='sealed_pdf',
        item_id='fictional', sha256=digest(signed.pdf), size=len(signed.pdf))


@pytest.mark.django_db
def test_confirmation_preparing_then_downloads_exact_own_pdf_even_after_closure(signed, monkeypatch):
    url = signed.base + '/signed-nda/'
    response = signed.client.get(url)
    assert response.status_code == 200, response.data
    assert response.data['signed'] and response.data['download_url'] is None
    assert signed.client.get(url + 'download/').status_code == 409
    complete(signed)
    monkeypatch.setattr('dealroom.nda.source_bytes', lambda version: signed.pdf)
    response = signed.client.get(url)
    assert response.data['email'] == signed.member.email
    assert response.data['signed_at'] and response.data['can_enter']
    room_data = signed.client.get(signed.base + '/room/').data
    assert room_data['signed_nda']['download_url'] == url + 'download/'
    assert len(room_data['files']) == 1  # Host NDA only, executed copy is separate.
    signed.room.roompolicy.status = 'archived'; signed.room.roompolicy.save()
    download = signed.client.get(url + 'download/')
    assert download.status_code == 200
    assert b''.join(download.streaming_content) == signed.pdf
    assert 'attachment;' in download['Content-Disposition']
    assert download['Cache-Control'] == 'private, no-store'


@pytest.mark.django_db
def test_signed_copy_is_bound_to_verified_visitor(signed, monkeypatch):
    complete(signed)
    other, _ = visitor(signed.room, 'other@harborlight.fleet.test', 'Other Visitor')
    url = signed.base + '/signed-nda/'
    assert other.get(url).data['download_url'] is None
    assert other.get(url + 'download/').status_code in (403, 404)
    assert APIClient().get(url + 'download/').status_code in (401, 403)
    session = signed.client.session
    proof = session['dealroom_member']; proof['email'] = 'other@harborlight.fleet.test'
    session['dealroom_member'] = proof; session.save()
    assert signed.client.get(url + 'download/').status_code == 403


@pytest.mark.django_db
def test_signed_return_redirects_to_confirmation_while_sealing(signed, monkeypatch, settings):
    monkeypatch.setattr('dealroom_sign.recipient_proxy.access_state', lambda access: 'signed')
    settings.SITE_DOMAIN = 'https://dealroom.test'
    access = SimpleNamespace(workflow=signed.work)
    response = terminal(RequestFactory().get('/s/return/example'), access, {})
    assert response.status_code == 303
    assert response["Location"] == f'https://dealroom.test/view/{signed.room.roompolicy.entry_link.slug}?nda=complete'


@pytest.mark.django_db
def test_workspace_watermark_default_room_override_and_validation(staff, room, owner):
    url = '/api/v1/dealroom/workspace-settings/'
    assert staff.get(url).data['watermark_style'] == 'diagonal'
    assert staff.patch(url, {'watermark_style': 'edge'}, format='json').status_code == 200
    assert effective_style(room.roompolicy.entry_link) == 'edge'
    second = staff.post('/api/v1/dealroom/rooms/', {'name': 'Another room'}, format='json')
    second = Dataroom.objects.get(pk=second.data['id'])
    assert effective_style(second.roompolicy.entry_link) == 'edge'
    outline = f'/api/v1/dealroom/rooms/{room.pk}/outline/'
    assert staff.patch(outline, {'watermark_style': 'diagonal'}, format='json').status_code == 200
    assert effective_style(room.roompolicy.entry_link) == 'diagonal'
    assert effective_style(second.roompolicy.entry_link) == 'edge'
    assert staff.patch(outline, {'watermark_style': None}, format='json').status_code == 200
    assert effective_style(room.roompolicy.entry_link) == 'edge'
    assert staff.patch(url, {'watermark_style': 'sideways'}, format='json').status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize('style', ['diagonal', 'edge'])
def test_styles_render_on_page_image_and_downloaded_pdf(style, room, monkeypatch, settings):
    settings.WATERMARK_FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    identity = {'name': 'Maya Chen', 'email': 'maya@northwind.test', 'organisation': 'Northwind',
        'copy_id': 'CP-FICTIONAL', 'watermark_style': style}
    image = Image.new('RGBA', (612, 792), 'white')
    rendered = _apply_watermark_to_image(image, 'Maya Chen · Northwind · Copy CP-FICTIONAL', identity)
    difference = ImageChops.difference(image.convert('RGB'), rendered.convert('RGB'))
    box = difference.getbbox()
    assert box and (box[1] > 740 if style == 'edge' else box[1] < 400)
    pdf = HARBOR.read_bytes()
    version = version_for(room, pdf)
    response = Mock(content=pdf)
    monkeypatch.setattr('sharelinks.views.requests.get', lambda *a, **k: response)
    monkeypatch.setattr('sharelinks.views.fileserver_client.generate_download_url', lambda *a, **k: 'http://files.test/nda')
    output = _generate_watermarked_pdf(version.document, version, 'Maya Chen · Copy CP-FICTIONAL',
        RequestFactory().get('/'), identity['email'], identity=identity)
    with pdfplumber.open(output) as document:
        chars = [c for c in document.pages[0].chars if c['text'] == 'M']
        if style == 'edge':
            assert any(c['top'] > 740 and c['upright'] for c in chars)
            assert all(c['upright'] for c in document.pages[0].chars)
        else:
            assert any(not c['upright'] or abs(c['matrix'][1]) > .1 for c in chars)


@pytest.mark.django_db
def test_visitor_folders_follow_sender_order_with_note(room, snapshot, storage, staff):
    import_tree(room, room.created_by, {'harbor-light': snapshot}, walk_tree(snapshot, 'harbor-light'), '', {})
    folders = list(room.folders.filter(parent=None).order_by('-name'))
    for position, folder in enumerate(folders):
        DataroomItemOrder.objects.update_or_create(folder=folder, defaults={
            'dataroom': room, 'item_type': 'folder', 'position': position})
    staff.patch(f'/api/v1/dealroom/rooms/{room.pk}/outline/', {'note': 'Start with the model. — Dan'}, format='json')
    client, _ = visitor(room)
    data = client.get(f'/api/v1/dealroom/recipient/{room.roompolicy.entry_link.slug}/room/').data
    assert [f['id'] for f in data['folders'] if not f['parent_id']] == [str(f.pk) for f in folders]
    assert data['note'] == 'Start with the model. — Dan'


@pytest.mark.django_db
def test_reset_nda_replaces_old_policy_coordinates_with_placement(signed, monkeypatch):
    policy = NdaPolicy.objects.get(room=signed.room)
    policy.fields = [{'type': 'SIGNATURE', 'page': 2, 'positionX': 10, 'positionY': 70, 'width': 30, 'height': 10}]
    policy.save()
    SignCredential.objects.create(owner=signed.room.created_by, team_id=1, token='api_fictional')
    remote = Mock()
    remote.find.return_value = []
    context = Mock()
    context.__enter__ = Mock(return_value=remote)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr('dealroom_sign.workflows.Documenso', lambda *a: context)
    monkeypatch.setattr('dealroom_sign.workflows.source_bytes', lambda v: signed.pdf)
    replacement = reset_nda(signed.work)
    field = next(f for f in replacement.recipients[0]['fields'] if f['type'] == 'SIGNATURE')
    assert field['page'] == 2 and 40 < field['positionY'] < 48
    assert replacement.observedsignevent_set.filter(kind='placement.resolved').exists()


@pytest.mark.django_db
@pytest.mark.parametrize('style', ['diagonal', 'edge'])
def test_workspace_style_reaches_real_viewer_and_pdf_download_endpoints(room, staff, monkeypatch, settings, style):
    settings.WATERMARK_FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    pdf = HARBOR.read_bytes()
    version = version_for(room, pdf)
    item = room.documents.get(document=version.document)
    link = room.roompolicy.entry_link
    client, _ = visitor(room)
    link.access_grants.update(download_ceiling='watermarked')
    ShareLinkDataroomSetting.objects.filter(share_link=link, dataroom_document=item).update(
        allow_download=True, download_ceiling='watermarked', enable_watermark=True)
    response = staff.patch('/api/v1/dealroom/workspace-settings/', {'watermark_style': style}, format='json')
    assert response.status_code == 200
    white = Image.new('RGB', (612, 792), 'white')
    buffer = BytesIO(); white.save(buffer, format='PNG')
    renderer = Mock()
    renderer.get_page_storage_key.return_value = 'page.png'
    monkeypatch.setattr('sharelinks.views.get_renderer', lambda v: renderer)
    monkeypatch.setattr('sharelinks.views.fileserver_client.generate_download_url', lambda key, **k: 'http://files.test/' + key)
    monkeypatch.setattr('sharelinks.views.requests.get', lambda url, **k: Mock(content=buffer.getvalue() if url.endswith('page.png') else pdf))
    response = client.get(f'/api/v1/links/{link.slug}/render-page/1/?dataroom_document_id={item.pk}')
    assert response.status_code == 200
    page = Image.open(BytesIO(response.content)).convert('RGB')
    difference = ImageChops.difference(white, page)
    box = difference.getbbox()
    assert box and (box[1] > 730 if style == 'edge' else box[1] < 400)
    response = client.get(f'/api/v1/links/{link.slug}/download-file/?dataroom_document_id={item.pk}')
    assert response.status_code == 200
    content = b''.join(response.streaming_content) if response.streaming else response.content
    with pdfplumber.open(BytesIO(content)) as document:
        chars = document.pages[0].chars
        assert 'Copy' in document.pages[0].extract_text()
        if style == 'edge':
            assert all(abs(c['matrix'][1]) < .01 for c in chars)
            assert any(c['text'] == 'L' and c['top'] > 740 for c in chars)
        else:
            assert any(abs(c['matrix'][1]) > .1 for c in chars)


@pytest.mark.django_db
def test_visitor_folders_without_order_rows_keep_sender_creation_order(room):
    folders = [room.folders.create(name=name, created_by=room.created_by) for name in ('Z Overview', 'A Detail')]
    for folder in folders:
        version = version_for(room, HARBOR.read_bytes(), name=folder.name + '.pdf')
        room.documents.filter(document=version.document).update(folder=folder)
    client, _ = visitor(room)
    data = client.get(f'/api/v1/dealroom/recipient/{room.roompolicy.entry_link.slug}/room/').data
    assert [f['id'] for f in data['folders']] == [str(f.pk) for f in folders]
