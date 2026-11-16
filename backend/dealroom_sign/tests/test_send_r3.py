"""r3 upload identity, History redaction, and missing-evidence quarantine."""
import hashlib
import json
from unittest.mock import Mock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory, force_authenticate

from documents.models import DocumentVersion
from dealroom.models import Activity
from dealroom.views import RoomViewSet
from dealroom_sign.models import ObservedSignEvent
from dealroom_sign.placement import place
from dealroom_sign.views import SigningSourceView
from dealroom_sign.requests import activity
from dealroom_sign.workflows import command, process
from dealroom_sign.tests.test_placement import FIXTURES, LEE
from dealroom_sign.tests.test_placement_r2 import opaque_reply
from dealroom_sign.tests.test_placement_r3 import title_body_pdf
from dealroom_sign.tests.test_placement_send import send, placement_settings  # noqa: F401
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients  # noqa: F401

pytestmark = pytest.mark.django_db


def test_upload_response_pins_version_hash_and_activity(fixture, pdf):
    fixture.version.is_primary = True
    fixture.version.save()
    fixture.user.is_staff = True
    fixture.user.save()
    request = APIRequestFactory().post('/upload/', {'file': SimpleUploadedFile('Fictional.pdf', pdf, 'application/pdf')})
    force_authenticate(request, user=fixture.user)
    with patch.object(RoomViewSet, 'get_object', return_value=fixture.room), \
         patch('dealroom.uploads.fileserver_client.upload_file'), \
         patch('dealroom.uploads.create_document_from_upload', return_value=fixture.version.document):
        response = RoomViewSet.as_view({'post': 'upload'})(request, pk=str(fixture.room.pk))
    assert response.status_code == 201, response.data
    assert response.data['version_id'] == str(fixture.version.pk)
    assert response.data['sha256'] == hashlib.sha256(pdf).hexdigest()
    fixture.version.refresh_from_db()
    assert fixture.version.metadata['source_sha256'] == response.data['sha256']
    fact = Activity.objects.get(event_type='document.uploaded')
    assert fact.data['version_id'] == response.data['version_id']
    assert fact.data['source_sha256'] == response.data['sha256']


def test_title_case_body_not_persisted_to_history(fixture, settings):
    settings.BOARD_SIGN_BOARDS = {'board-c2a': {'owner_ids': [str(fixture.user.pk)], 'room_ids': [str(fixture.room.pk)], 'team_ids': [3]}}
    secret = 'Project Falcon Acquisition Terms'
    model = Mock(side_effect=opaque_reply)
    with patch('dealroom_sign.workflows.source_bytes', return_value=title_body_pdf(secret, extra_block=True)), \
         patch('dealroom_sign.workflows.place', side_effect=lambda pdf, signers: place(pdf, signers, model_client=model)):
        work = command(owner=fixture.user, room=fixture.room, version=fixture.version,
                       recipients=[{k:v for k,v in LEE[0].items() if k != 'side'}],
                       idempotency_key='r3-private', board_id='board-c2a', placement='auto')
    assert secret not in json.dumps(model.call_args.args[0])
    assert secret not in json.dumps(activity(work.signature_request), default=str)
    assert secret not in json.dumps(list(ObservedSignEvent.objects.filter(workflow=work).values_list('payload', flat=True)))


def test_missing_auto_evidence_is_quarantined_before_remote_write(fixture):
    work = send(fixture)
    ObservedSignEvent.objects.filter(workflow=work, kind='placement.resolved').delete()
    client = Mock()
    with patch('dealroom_sign.workflows.Documenso') as constructor:
        constructor.return_value.__enter__.return_value = client
        process(work.pk)
    work.refresh_from_db()
    assert work.state == 'quarantined'
    assert work.last_error == 'placement_evidence_missing'
    client.create.assert_not_called()
    client.distribute.assert_not_called()


def test_two_same_named_uploads_create_distinct_workflows_with_exact_source_hash(fixture):
    fixture.user.is_staff = True
    fixture.user.save()
    source = (FIXTURES / 'harbor.pdf').read_bytes()
    expected = hashlib.sha256(source).hexdigest()
    uploaded, workflows = [], []
    with patch.object(RoomViewSet, 'get_object', return_value=fixture.room), \
         patch('dealroom.uploads.fileserver_client.upload_file'), \
         patch('documents.services.validate_file_content_type_and_extension'), \
         patch('documents.services._route_document_for_processing'), \
         patch('dealroom_sign.workflows.source_bytes', return_value=source):
        for i in range(2):
            request = APIRequestFactory().post('/upload/', {'file': SimpleUploadedFile('Offer (Nov 15 1430).pdf', source, 'application/pdf')})
            force_authenticate(request, user=fixture.user)
            response = RoomViewSet.as_view({'post': 'upload'})(request, pk=str(fixture.room.pk))
            assert response.status_code == 201, response.data
            uploaded.append(response.data)
            request = APIRequestFactory().get('/sources/', {'version_id': response.data['version_id']})
            force_authenticate(request, user=fixture.user)
            with patch('dealroom_sign.views.source_bytes', return_value=source):
                listing = SigningSourceView.as_view()(request, room_id=str(fixture.room.pk))
            assert listing.status_code == 200
            assert listing.data[0]['id'] == response.data['version_id']
            assert listing.data[0]['sha256'] == response.data['sha256'] == expected
            version = DocumentVersion.objects.get(pk=response.data['version_id'])
            work = command(owner=fixture.user, room=fixture.room, version=version,
                           recipients=[{k:v for k,v in LEE[0].items() if k != 'side'}],
                           idempotency_key=f'r3-card-{i}', placement='auto')
            assert str(work.source_version_id) == response.data['version_id']
            assert work.source_sha256 == expected
            workflows.append(work)
    assert workflows[0].pk != workflows[1].pk
    assert uploaded[0]['version_id'] != uploaded[1]['version_id']
    assert workflows[0].source_version.document.name != workflows[1].source_version.document.name
