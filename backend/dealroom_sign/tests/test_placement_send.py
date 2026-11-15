"""Automatic placement is resolved before a durable send can be queued."""
import hashlib
import json
from unittest.mock import Mock, patch

import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from dealroom_sign.client import Documenso, SignError
from dealroom_sign.models import ObservedSignEvent, Workflow
from dealroom_sign.requests import activity
from dealroom_sign.views import SigningEnvelopeViewSet, SigningSourceView
from dealroom_sign.workflows import command, execute, envelope_meta
from dealroom_sign.placement import place
from dealroom_sign.tests.test_placement_r2 import nearby_body_pdf, opaque_reply
from dealroom_sign.tests.test_placement import FIXTURES, LEE
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def placement_settings(settings, monkeypatch):
    settings.SIGN_RECIPIENT_ORIGIN = 'https://signer.example.test'
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


def send(fixture, name='harbor', signers=None, key='c2a', **kwargs):
    source = (FIXTURES / (name + '.pdf')).read_bytes()
    with patch('dealroom_sign.workflows.source_bytes', return_value=source):
        return command(owner=fixture.user, room=fixture.room, version=fixture.version,
                       recipients=signers or [{k: v for k, v in LEE[0].items() if k != "side"}], idempotency_key=key, **kwargs)


def api_send(fixture, name):
    fixture.user.is_staff = True
    fixture.user.save()
    body = {'room_id': str(fixture.room.pk), 'version_id': str(fixture.version.pk),
            'recipients': [{k: v for k, v in LEE[0].items() if k != 'side'}], 'idempotency_key': 'api-c2a', 'placement': 'auto'}
    request = APIRequestFactory().post('/api/v1/dealroom-sign/envelopes/', body, format='json')
    force_authenticate(request, user=fixture.user)
    with patch('dealroom_sign.workflows.source_bytes', return_value=(FIXTURES / (name + '.pdf')).read_bytes()):
        return SigningEnvelopeViewSet.as_view({'post': 'create'})(request)


def test_api_default_creates_signature_and_date(fixture):
    response = api_send(fixture, 'harbor')
    assert response.status_code == 201, response.data
    work = Workflow.objects.get(pk=response.data['id'])
    assert {f['type'] for f in work.recipients[0]['fields']} == {'SIGNATURE', 'DATE'}
    assert work.recipients[0]['fields'][0]['page'] == 2


@pytest.mark.parametrize('name', ['bare', 'unusual'])
def test_api_hold_is_typed_and_creates_no_workflow(fixture, name):
    before = Workflow.objects.count()
    response = api_send(fixture, name)
    assert response.status_code == 409, response.data
    assert response.data['status'] == 'needs_sender'
    assert response.data['reason']
    assert isinstance(response.data['suggestions'], list)
    assert Workflow.objects.count() == before


def test_placement_persists_workflow_and_history_evidence(fixture, settings):
    settings.BOARD_SIGN_BOARDS = {'board-c2a': {'owner_ids': [str(fixture.user.pk)], 'room_ids': [str(fixture.room.pk)], 'team_ids': [3]}}
    work = send(fixture, board_id='board-c2a')
    fact = ObservedSignEvent.objects.get(workflow=work, kind='placement.resolved')
    data = fact.payload['data']
    assert data['source_sha256'] == work.source_sha256
    assert data['placement']['status'] == 'placed'
    assert data['placement']['fields'][0]['evidence']['label_text']
    history = next(row for row in activity(work.signature_request) if row['kind'] == 'placement.resolved')
    assert history['placement'] == data['placement']
    assert history['source_sha256'] == work.source_sha256


def test_auto_retry_does_not_recompute_and_changed_hints_rejected(fixture):
    work = send(fixture)
    with patch('dealroom_sign.workflows.place', side_effect=AssertionError('recomputed')):
        assert send(fixture).pk == work.pk
    changed = [{k: v for k, v in dict(LEE[0], company='Different Co').items() if k != 'side'}]
    with pytest.raises(ValidationError, match='Idempotency'):
        send(fixture, signers=changed)


def test_native_gets_exact_source_and_evidence_fields(fixture):
    work = send(fixture)
    source = (FIXTURES / 'harbor.pdf').read_bytes()
    client = Mock()
    client.create.side_effect = SignError('stop_after_create_capture')
    with patch('dealroom_sign.workflows.source_bytes', return_value=source), pytest.raises(SignError, match='stop_after_create_capture'):
        execute(work, client)
    assert client.create.call_args.args[1] == source
    assert hashlib.sha256(source).hexdigest() == work.source_sha256
    assert client.create.call_args.args[0].recipients[0]['fields'][0]['positionY'] == pytest.approx((367.2 - 18) / 792 * 100)
    client.distribute.assert_not_called()


def test_changed_source_never_creates_or_distributes(fixture):
    work = send(fixture)
    client = Mock()
    with patch('dealroom_sign.workflows.source_bytes', return_value=b'%PDF-changed'), pytest.raises(SignError, match='source_hash_changed'):
        execute(work, client)
    client.create.assert_not_called()
    client.distribute.assert_not_called()


@pytest.mark.parametrize('change', ['fields', 'status', 'hash'])
def test_worker_checks_persisted_placement_before_any_remote_write(fixture, change):
    work = send(fixture)
    fact = ObservedSignEvent.objects.get(workflow=work, kind='placement.resolved')
    if change == 'fields':
        work.recipients[0]['fields'][0]['positionY'] = 78
        work.save()
    elif change == 'status':
        fact.payload['data']['placement']['status'] = 'needs_sender'
        fact.save()
    else:
        fact.payload['data']['source_sha256'] = '0' * 64
        fact.save()
    client = Mock()
    with pytest.raises(SignError, match='placement_evidence_changed'):
        execute(work, client)
    client.create.assert_not_called()
    client.distribute.assert_not_called()


def test_native_payload_omits_internal_signer_hints(fixture):
    work = send(fixture, signers=[{'name': 'Lee Harbor', 'email': LEE[0]['email'], 'company': 'Harbor Light Analytics', 'title': 'COO'}])
    with Documenso(fixture.credential) as client, patch.object(client, 'request') as request:
        request.return_value.json.return_value = {'id': 'new-envelope'}
        client.create(work, (FIXTURES / 'harbor.pdf').read_bytes())
    recipient = json.loads(request.call_args.kwargs['data']['payload'])['recipients'][0]
    assert set(recipient) == {'name', 'email', 'role', 'signingOrder', 'fields'}
    assert {f['type'] for f in recipient['fields']} == {'SIGNATURE', 'DATE'}


def test_r2_missing_auto_fact_stops_before_remote_write(fixture):
    work = send(fixture)
    ObservedSignEvent.objects.filter(workflow=work, kind='placement.resolved').delete()
    client = Mock()
    with pytest.raises(SignError, match='placement_evidence_missing'):
        execute(work, client)
    client.create.assert_not_called()
    client.distribute.assert_not_called()


def test_r2_date_only_envelope_and_native_metadata(fixture):
    work = send(fixture)
    assert envelope_meta(work)['dateFormat'] == 'yyyy-MM-dd'
    sig = next(f for f in work.recipients[0]['fields'] if f['type'] == 'SIGNATURE')
    date = next(f for f in work.recipients[0]['fields'] if f['type'] == 'DATE')
    assert sig['fieldMeta'] == {'type':'signature', 'fontSize':18}
    assert date['fieldMeta'] == {'type':'date', 'fontSize':10}


def test_r2_nearby_sentinel_reaches_neither_model_nor_history(fixture, settings):
    settings.BOARD_SIGN_BOARDS = {'board-c2a': {'owner_ids': [str(fixture.user.pk)], 'room_ids': [str(fixture.room.pk)], 'team_ids': [3]}}
    model = Mock(side_effect=opaque_reply)
    def resolve(pdf, signers):
        return place(pdf, signers, model_client=model)
    with patch('dealroom_sign.workflows.source_bytes', return_value=nearby_body_pdf()), patch('dealroom_sign.workflows.place', side_effect=resolve):
        work = command(owner=fixture.user, room=fixture.room, version=fixture.version,
                       recipients=[{k:v for k,v in LEE[0].items() if k != 'side'}],
                       idempotency_key='r2-private', board_id='board-c2a', placement='auto')
    assert 'PRIVATE NEARBY SENTINEL' not in json.dumps(model.call_args.args[0])
    assert 'PRIVATE NEARBY SENTINEL' not in json.dumps(activity(work.signature_request), default=str)
    assert 'PRIVATE NEARBY SENTINEL' not in json.dumps(list(ObservedSignEvent.objects.filter(workflow=work).values('payload')), default=str)


def test_r2_selected_source_hash_is_authorized_and_matches_bytes(fixture):
    fixture.user.is_staff = True
    fixture.user.save()
    source = (FIXTURES / 'harbor.pdf').read_bytes()
    for version_id, expected in [(str(fixture.version.pk), hashlib.sha256(source).hexdigest()), ('absent-version', None)]:
        request = APIRequestFactory().get('/sources/', {'version_id': version_id})
        force_authenticate(request, user=fixture.user)
        with patch('dealroom_sign.views.source_bytes', return_value=source) as read:
            response = SigningSourceView.as_view()(request, room_id=str(fixture.room.pk))
        if expected:
            assert response.data[0]['sha256'] == expected
            read.assert_called_once_with(fixture.version)
        else:
            assert response.data == []
            read.assert_not_called()
