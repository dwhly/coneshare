"""Room entry templates: sender confirmation and visitor-independent geometry."""
import json
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pdfplumber
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient

from datarooms.models import Dataroom
from dealroom.drive import room_state, save_state
from dealroom_sign.client import Documenso
from dealroom_sign.models import NdaPolicy, SignCredential, Workflow
from dealroom_sign.validation import digest
from sharelinks.models import ViewerOrganisation
from dealroom.tests.test_drive_onramp import room, snapshot, storage
from dealroom.tests.test_room_round3 import version_for, visitor

PDF = Path(__file__).parent / 'fixtures/Investor NDA (fictional).pdf'
FIELDS = [dict(type=t, page=1, positionX=22, positionY=y, width=55, height=3, identifier=0)
          for t, y in [('SIGNATURE', 64), ('NAME', 70), ('TEXT', 76), ('DATE', 82)]]


@pytest.fixture
def source(room, monkeypatch):
    pdf = PDF.read_bytes()
    v = version_for(room, pdf, 'Investor NDA (fictional).pdf')
    monkeypatch.setattr('dealroom_sign.views.source_bytes', lambda v: pdf)
    monkeypatch.setattr('dealroom_sign.workflows.source_bytes', lambda v: pdf)
    return v


def select(staff, room, version):
    response = staff.put(f'/api/v1/dealroom-sign/nda-policy/{room.pk}/',
        {'version_id': str(version.pk), 'enabled': True}, format='json')
    assert response.status_code == 200, response.data
    return response.data


def confirm(staff, room, version, fields=FIELDS):
    selected = select(staff, room, version)
    response = staff.put(f'/api/v1/dealroom-sign/nda-policy/{room.pk}/',
        {'version_id': str(version.pk), 'revision': selected['revision'], 'fields': fields,
         'confirm': True, 'enabled': True}, format='json')
    assert response.status_code == 200, response.data
    return response.data


@pytest.mark.django_db
def test_suggestions_follow_blank_recipient_rule_and_do_not_confirm(room, staff, source, monkeypatch):
    from dealroom_sign import nda_template
    monkeypatch.setattr(nda_template, 'source_bytes', lambda v: PDF.read_bytes())
    selected = select(staff, room, source)
    response = staff.get(f'/api/v1/dealroom/rooms/{room.pk}/entry-nda/')
    assert response.status_code == 200, response.data
    fields = response.data['suggestions']
    assert {f['type'] for f in fields} == {'SIGNATURE', 'NAME', 'TEXT', 'DATE'}
    with pdfplumber.open(PDF) as doc:
        page = doc.pages[0]
        label = next(w for w in page.extract_words() if w['text'] == 'Signature:')
        line = next(l for l in page.lines if abs(l['top'] - label['bottom']) < 5)
        sig = next(f for f in fields if f['type'] == 'SIGNATURE')
        assert sig['page'] == 1
        assert line['top'] - 30 < sig['positionY'] * page.height / 100 < line['top']
        assert abs((sig['positionY'] + sig['height']) * page.height / 100 - line['top']) < 2
        assert sig['positionX'] * page.width / 100 >= line['x0'] - 1
    assert not selected['confirmed']
    assert NdaPolicy.objects.get(room=room).fields == []


@pytest.mark.django_db
def test_confirmed_geometry_used_for_every_visitor_with_editable_identity(room, staff, source, monkeypatch):
    data = confirm(staff, room, source)
    assert data['confirmed'] and NdaPolicy.objects.get(room=room).fields == FIELDS
    SignCredential.objects.create(owner=room.created_by, token='fictional', team_id=1)
    placement = Mock(side_effect=AssertionError('Per-visitor placement must not run'))
    monkeypatch.setattr('dealroom_sign.workflows.place', placement)
    for name, email, firm in [('Maya Chen', 'maya@northwind.test', 'Northwind'), ('Alex Lee', 'alex@southwind.test', 'Southwind')]:
        client, member = visitor(room, email, name)
        member.refresh_from_db()
        member.recipient_org = ViewerOrganisation.objects.create(organization=room.organization, name=firm)
        member.save()
        response = client.post(f'/api/v1/dealroom-sign/nda/{room.pk}/')
        assert response.status_code == 201, response.data
        work = Workflow.objects.get(member_id=str(member.pk))
        recipient = work.recipients[0]
        assert recipient['name'] == name
        assert [{k: f[k] for k in FIELDS[0]} for f in recipient['fields']] == FIELDS
        company = next(f for f in recipient['fields'] if f['type'] == 'TEXT')
        assert company['fieldMeta']['text'] == firm and company['fieldMeta']['readOnly'] is False
        # Exercise the real envelope payload builder, including editable company defaults.
        transport = Mock()
        transport.request.return_value.json.return_value = {'id': 'fictional-envelope'}
        Documenso.create(transport, work, PDF.read_bytes())
        payload = json.loads(transport.request.call_args.kwargs['data']['payload'])
        assert payload['recipients'][0]['name'] == name
        assert payload['recipients'][0]['fields'] == recipient['fields']
    placement.assert_not_called()


@pytest.mark.django_db
def test_unconfirmed_share_blocked_and_file_change_clears_confirmation(room, staff, source):
    select(staff, room, source)
    invite = f'/api/v1/dealroom/rooms/{room.pk}/invite/'
    response = staff.post(invite, {'emails': ['maya@northwind.test']}, format='json')
    assert response.status_code == 409, response.data
    assert response.data['action'] == 'Place the NDA fields'
    assert room.roompolicy.entry_link.access_grants.count() == 0
    confirm(staff, room, source)
    assert staff.post(invite, {'emails': ['maya@northwind.test']}, format='json').status_code == 201
    other = version_for(room, PDF.read_bytes(), 'Replacement.pdf')
    result = select(staff, room, other)
    assert not result['confirmed'] and result['fields'] == []
    assert staff.post(invite, {'emails': ['alex@southwind.test']}, format='json').status_code == 409


@pytest.mark.django_db
def test_upload_entry_nda_is_separate_from_room_content(room, staff, storage, monkeypatch):
    from dealroom_sign import nda_template
    monkeypatch.setattr(nda_template, 'source_bytes', lambda v: PDF.read_bytes())
    response = staff.post(f'/api/v1/dealroom/rooms/{room.pk}/entry-nda/',
        {'file': SimpleUploadedFile(PDF.name, PDF.read_bytes(), content_type='application/pdf')}, format='multipart')
    assert response.status_code == 201, response.data
    assert not room.documents.exists()
    policy = NdaPolicy.objects.get(room=room)
    assert policy.source_version.document.name == PDF.name
    assert not response.data['confirmed']
    assert APIClient().get(f'/api/v1/dealroom/rooms/{room.pk}/entry-nda/').status_code in (401, 403)


@pytest.mark.django_db
def test_seed_confirms_entry_fixture_and_preserves_company_nda(snapshot, owner, storage, monkeypatch):
    monkeypatch.setattr('dealroom_sign.placement.place', lambda *a, **k: {
        'status': 'needs_sender', 'fields': [], 'reason': 'Unknown visitor'})
    out = StringIO()
    for _ in range(2):
        call_command('seed_room_onramp', owner=owner.email, stdout=out)
    room = Dataroom.objects.get(name='Harbor Light Analytics · Series A')
    policy = NdaPolicy.objects.get(room=room)
    assert policy.source_version.document.name == PDF.name
    assert policy.source_sha256 == digest(PDF.read_bytes())
    assert len(policy.fields) == 4 and 'confirmed 4 fields on page 1' in out.getvalue()
    mutual = room.documents.get(document__name__icontains='Mutual NDA')
    assert mutual.folder.name.endswith('Legal')
    assert mutual.document_id != policy.source_version.document_id
    assert room.documents.count() == 12


@pytest.mark.django_db
def test_confirmation_rejects_stale_source_and_outside_page_fields(room, staff, source):
    selected = select(staff, room, source)
    url = f'/api/v1/dealroom-sign/nda-policy/{room.pk}/'
    payload = {'version_id': str(source.pk), 'revision': selected['revision'], 'confirm': True, 'fields': FIELDS}
    outside = [dict(FIELDS[0], positionX=99)]
    assert staff.put(url, dict(payload, fields=outside), format='json').status_code == 400
    other = version_for(room, PDF.read_bytes(), 'New NDA.pdf')
    select(staff, room, other)
    assert staff.put(url, payload, format='json').status_code == 400
    assert NdaPolicy.objects.get(room=room).source_version_id == other.pk


@pytest.mark.django_db
def test_required_room_without_policy_cannot_share(room, staff):
    state = room_state(room); state['require_nda'] = True
    save_state(room, room.created_by, state)
    response = staff.post(f'/api/v1/dealroom/rooms/{room.pk}/invite/', {'emails': ['maya@northwind.test']}, format='json')
    assert response.status_code == 409
    assert staff.get(f'/api/v1/dealroom/rooms/{room.pk}/outline/').data['share_blocked']


@pytest.mark.django_db
def test_preview_is_pinned_private_and_requires_owner(room, staff, source, monkeypatch):
    from dealroom_sign import nda_template
    monkeypatch.setattr(nda_template, 'source_bytes', lambda v: PDF.read_bytes())
    data = select(staff, room, source)
    url = data['pdf_url']
    response = staff.get(url)
    assert response.status_code == 200
    assert b''.join(response.streaming_content) == PDF.read_bytes()
    assert response['Cache-Control'] == 'private, no-store'
    assert APIClient().get(url).status_code in (401, 403)
    other = version_for(room, PDF.read_bytes(), 'Replacement.pdf')
    select(staff, room, other)
    assert staff.get(url).status_code == 400


def test_blank_rule_fallback_does_not_suggest_signed_company_block():
    from dealroom_sign.nda_template import suggestions
    company = Path(__file__).resolve().parents[2] / 'dealroom_sign/tests/fixtures/placement/harbor.pdf'
    assert suggestions(company.read_bytes()) == []


@pytest.mark.django_db
def test_cannot_select_another_rooms_entry_source(room, staff, storage, monkeypatch):
    from dealroom_sign import nda_template
    monkeypatch.setattr(nda_template, 'source_bytes', lambda v: PDF.read_bytes())
    uploaded = staff.post(f'/api/v1/dealroom/rooms/{room.pk}/entry-nda/',
        {'file': SimpleUploadedFile(PDF.name, PDF.read_bytes(), content_type='application/pdf')}, format='multipart')
    assert uploaded.status_code == 201
    other = staff.post('/api/v1/dealroom/rooms/', {'name': 'Another room'}, format='json').data['id']
    response = staff.put(f'/api/v1/dealroom-sign/nda-policy/{other}/',
        {'version_id': uploaded.data['source_version_id']}, format='json')
    assert response.status_code == 400
    assert not NdaPolicy.objects.filter(room_id=other).exists()


@pytest.mark.django_db
def test_invalid_entry_upload_preserves_confirmed_source(room, staff, source, storage):
    data = confirm(staff, room, source)
    response = staff.post(f'/api/v1/dealroom/rooms/{room.pk}/entry-nda/',
        {'file': SimpleUploadedFile('Invalid.pdf', b'not a pdf', content_type='application/pdf')}, format='multipart')
    assert response.status_code == 400
    policy = staff.get(f'/api/v1/dealroom-sign/nda-policy/{room.pk}/').data
    assert policy['confirmed'] and policy['revision'] == data['revision']


@pytest.mark.django_db
def test_unconfirmed_reset_does_not_cancel_the_existing_envelope(room, source, monkeypatch):
    from dealroom_sign.nda_template import NdaNotPlaced
    from dealroom_sign.workflows import reset_nda
    policy = NdaPolicy.objects.create(room=room, source_version=source, source_sha256=digest(PDF.read_bytes()))
    _, member = visitor(room, 'maya@northwind.test', 'Maya Chen')
    work = Workflow.objects.create(room=room, owner=room.created_by, purpose='nda', source_version=source,
        source_sha256=policy.source_sha256, policy_revision=str(policy.revision), state='failed',
        member_id=str(member.pk), member_email=member.email, external_id='fictional:reset', idempotency_key='reset')
    SignCredential.objects.create(owner=room.created_by, token='fictional', team_id=1)
    remote = Mock(); remote.find.return_value = []
    context = Mock(); context.__enter__ = Mock(return_value=remote); context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr('dealroom_sign.workflows.Documenso', lambda *args: context)
    with pytest.raises(NdaNotPlaced):
        reset_nda(work)
    remote.find.assert_not_called()
