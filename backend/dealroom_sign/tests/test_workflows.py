import io
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest
from django.db import connection
from django.test import RequestFactory, override_settings
from django.utils import timezone
from pypdf import PdfWriter
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.models import Organization, User
from datarooms.models import Dataroom, DataroomDocument
from documents.models import Document, DocumentVersion
from dealroom_sign.client import Documenso, SignError
from dealroom_sign.models import ExecutedArtifact, NdaAcceptance, NdaPolicy, SignCredential, Workflow
from dealroom_sign.policy import artifact_allowed, check_nda
from dealroom_sign.validation import digest, validate_recipients
from dealroom_sign.webhooks import webhook
from dealroom_sign.workflows import adopt, command, execute, process, reconcile, validate_envelope

pytestmark = pytest.mark.django_db


@pytest.fixture
def pdf():
    out = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=600, height=800)
    writer.write(out)
    return out.getvalue()


@pytest.fixture
def recipients():
    return [{'email': 'member@example.test', 'name': 'Member', 'role': 'SIGNER', 'fields': [
        {'type': 'SIGNATURE', 'page': 1, 'positionX': 10, 'positionY': 70, 'width': 30, 'height': 10}]}]


@pytest.fixture
def fixture(pdf, recipients):
    org = Organization.objects.create(name='Test Organization')
    user = User.objects.create_user(username='owner@example.test', email='owner@example.test', password='test', organization=org)
    room = Dataroom.objects.create(organization=org, created_by=user, name='Test Room')
    doc = Document.objects.create(organization=org, created_by=user, name='Source.pdf', type='pdf', content_type='application/pdf')
    version = DocumentVersion.objects.create(document=doc, version_number=1, content_type='application/pdf', original_storage_key='fixture.pdf')
    DataroomDocument.objects.create(dataroom=room, document=doc)
    credential = SignCredential.objects.create(owner=user, team_id=3, token='api_private-test-token')
    with patch('dealroom_sign.workflows.source_bytes', return_value=pdf):
        work = command(owner=user, room=room, version=version, recipients=recipients, idempotency_key='test')
    return SimpleNamespace(org=org, user=user, room=room, version=version, work=work, credential=credential)


def envelope(work, status='PENDING'):
    return {'id': 'envelope_test', 'externalId': work.external_id, 'status': status,
            'completedAt': '2026-11-04T12:00:00Z' if status == 'COMPLETED' else None,
            'envelopeItems': [{'id': 'item_test'}], 'recipients': [
                {'id': 1, 'email': 'member@example.test', 'role': 'SIGNER', 'signingStatus': 'SIGNED' if status == 'COMPLETED' else 'NOT_SIGNED', 'token': 'private-recipient-token'}]}


def linked(fixture):
    work = fixture.work
    work.envelope_id = 'envelope_test'
    work.item_ids = ['item_test']
    work.state = 'awaiting_signature'
    work.save()
    return work


def test_credential_ciphertext_not_raw(fixture):
    with connection.cursor() as cursor:
        cursor.execute('SELECT token FROM dealroom_sign_signcredential')
        raw = bytes(cursor.fetchone()[0])
    assert b'api_private-test-token' not in raw
    assert SignCredential.objects.get(pk=fixture.credential.pk).token == 'api_private-test-token'


def test_idempotency_same_command_and_changed_inputs_rejected(fixture, pdf, recipients):
    with patch('dealroom_sign.workflows.source_bytes', return_value=pdf):
        again = command(owner=fixture.user, room=fixture.room, version=fixture.version, recipients=recipients, idempotency_key='test')
        assert again.pk == fixture.work.pk
        recipients[0]['email'] = 'different@example.test'
        with pytest.raises(ValidationError):
            command(owner=fixture.user, room=fixture.room, version=fixture.version, recipients=recipients, idempotency_key='test')


@pytest.mark.parametrize('field,value', [('positionX', -1), ('width', 101), ('page', 0), ('height', float('nan')), ('identifier', 1), ('type', 'UNKNOWN')])
def test_invalid_placement_rejected(pdf, recipients, field, value):
    recipients[0]['fields'][0][field] = value
    with pytest.raises(ValidationError):
        validate_recipients(recipients, pdf)


def test_no_default_signature_placement(pdf, recipients):
    recipients[0]['fields'] = []
    with pytest.raises(ValidationError):
        validate_recipients(recipients, pdf)


def test_nda_email_must_equal_verified_member(fixture, pdf, recipients):
    member = SimpleNamespace(pk='member', email='someoneelse@example.test')
    with patch('dealroom_sign.workflows.source_bytes', return_value=pdf), pytest.raises(ValidationError):
        command(owner=fixture.user, room=fixture.room, version=fixture.version, recipients=recipients, idempotency_key='nda', purpose='nda', member=member)


def test_nda_distribution_none(fixture):
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={'success': True})
    with Documenso(fixture.credential, httpx.MockTransport(respond)) as client:
        client.distribute('envelope_test', nda=True)
    import json
    assert json.loads(requests[0].content)['meta']['distributionMethod'] == 'NONE'


def test_remote_errors_do_not_expose_tokens(fixture):
    transport = httpx.MockTransport(lambda r: httpx.Response(500, text='api_private-test-token private-recipient-token'))
    with Documenso(fixture.credential, transport) as client, pytest.raises(SignError) as exc:
        client.get('envelope_test')
    assert str(exc.value) == 'sign_http_500'


def test_lost_create_response_never_recreated(fixture):
    work = fixture.work
    work.state = 'creating'
    work.save()
    client = Mock()
    client.find.return_value = []
    with pytest.raises(SignError, match='create_outcome_uncertain'):
        execute(work, client)
    client.create.assert_not_called()


def test_multiple_external_id_matches_quarantined(fixture):
    work = fixture.work
    work.state = 'uncertain'
    client = Mock()
    client.find.return_value = [{'id': 'one'}, {'id': 'two'}]
    with pytest.raises(SignError, match='duplicate_external_id'):
        execute(work, client)
    client.distribute.assert_not_called()


def test_ambiguous_distribution_never_resent(fixture):
    work = linked(fixture)
    work.state = 'distributing'
    client = Mock()
    client.get.return_value = envelope(work, 'DRAFT')
    with pytest.raises(SignError, match='distribution_outcome_uncertain'):
        execute(work, client)
    client.distribute.assert_not_called()


def test_rebound_signer_quarantines_before_acceptance(fixture):
    work = linked(fixture)
    env = envelope(work, 'COMPLETED')
    env['recipients'][0]['email'] = 'changed@example.test'
    with pytest.raises(SignError, match='signer_identity_changed'):
        reconcile(work, Mock(), env)
    assert not NdaAcceptance.objects.exists()
    assert not ExecutedArtifact.objects.exists()


def test_partial_signer_cannot_complete(fixture, pdf):
    work = linked(fixture)
    env = envelope(work, 'COMPLETED')
    env['recipients'][0]['signingStatus'] = 'NOT_SIGNED'
    client = Mock()
    client.audit.return_value = [{'id': 'audit-complete', 'type': 'DOCUMENT_COMPLETED'}]
    client.pdf.return_value = pdf
    with pytest.raises(SignError, match='completion_evidence_incomplete'):
        reconcile(work, client, env)
    assert not NdaAcceptance.objects.exists()


def test_source_hash_checked_before_adoption(fixture, pdf):
    client = Mock()
    client.get.return_value = envelope(fixture.work)
    client.pdf.return_value = pdf + b'changed'
    with pytest.raises(SignError, match='source_hash_changed'):
        adopt(fixture.work, client, 'envelope_test')


def test_duplicate_completion_files_once_and_accepts_atomically(fixture, pdf):
    work = linked(fixture)
    work.purpose, work.member_id, work.member_email, work.policy_revision = 'nda', 'member', 'member@example.test', 'revision'
    work.save()
    client = Mock()
    client.audit.return_value = [{'id': 'audit-complete', 'type': 'DOCUMENT_COMPLETED'}]
    client.pdf.return_value = client.signed_item.return_value = client.certificate.return_value = client.audit_pdf.return_value = pdf
    with patch('dealroom_sign.workflows.verify_seal', return_value={'signature_valid': True, 'trusted': False}), \
         patch('dealroom_sign.storage.fileserver_client.upload_file'), patch('dealroom_sign.workflows.record_fact'):
        reconcile(work, client, envelope(work, 'COMPLETED'))
        reconcile(work, client, envelope(work, 'COMPLETED'))
    assert ExecutedArtifact.objects.count() == 3
    assert NdaAcceptance.objects.count() == 1
    assert DataroomDocument.objects.count() == 4
    assert artifact_allowed(ExecutedArtifact.objects.first().version.document_id, SimpleNamespace(pk='other', email='other@example.test')) is False


def test_certificate_failure_keeps_gate_closed(fixture, pdf):
    work = linked(fixture)
    client = Mock()
    client.audit.return_value = [{'id': 'audit-complete', 'type': 'DOCUMENT_COMPLETED'}]
    client.pdf.return_value = client.signed_item.return_value = pdf
    client.certificate.side_effect = SignError('sign_http_503')
    with patch('dealroom_sign.workflows.verify_seal', return_value={}), patch('dealroom_sign.storage.fileserver_client.upload_file'), pytest.raises(SignError):
        reconcile(work, client, envelope(work, 'COMPLETED'))
    assert not ExecutedArtifact.objects.exists()
    assert not NdaAcceptance.objects.exists()


def test_conflicting_sealed_bytes_never_overwrite(fixture, pdf):
    from dealroom_sign.storage import stage
    work = linked(fixture)
    ExecutedArtifact.objects.create(workflow=work, item_id='item_test', kind='sealed_pdf', sha256='old', size=3, version=fixture.version)
    with pytest.raises(SignError, match='sealed_bytes_conflict'):
        stage(work, 'item_test', 'sealed_pdf', pdf)


def test_gate_requires_current_policy_and_current_identity(fixture):
    policy = NdaPolicy.objects.create(room=fixture.room, source_version=fixture.version, source_sha256=fixture.work.source_sha256)
    member = SimpleNamespace(pk='member', email='member@example.test')
    with pytest.raises(PermissionDenied):
        check_nda(fixture.room, member)
    NdaAcceptance.objects.create(room=fixture.room, member_id='member', member_email=member.email, policy_revision=str(policy.revision), workflow=fixture.work)
    check_nda(fixture.room, member)
    member.email = 'rebound@example.test'
    with pytest.raises(PermissionDenied):
        check_nda(fixture.room, member)


def test_lease_blocks_concurrent_workers(fixture):
    fixture.work.lease_until = timezone.now() + timedelta(minutes=1)
    fixture.work.save()
    with patch('dealroom_sign.workflows.execute') as run:
        process(fixture.work.pk)
    run.assert_not_called()


@pytest.mark.parametrize('secret,code', [('', 403), ('wrong', 403), ('unit-test-secret', 202)])
def test_webhook_hint_auth_and_no_payload_trust(secret, code):
    req = RequestFactory().post('/hook', {'payload': {'envelopeId': 'envelope_test', 'status': 'COMPLETED'}}, content_type='application/json', HTTP_X_DOCUMENSO_SECRET=secret)
    with patch('dealroom_sign.webhooks.reconcile_envelope.delay') as enqueue:
        result = webhook(req)
    assert result.status_code == code
    if code == 202:
        enqueue.assert_called_once_with('envelope_test')
    assert not NdaAcceptance.objects.exists()


def test_webhook_enqueue_failure_retryable():
    req = RequestFactory().post('/hook', {'payload': {'envelopeId': 'envelope_test'}}, content_type='application/json', HTTP_X_DOCUMENSO_SECRET='unit-test-secret')
    with patch('dealroom_sign.webhooks.reconcile_envelope.delay', side_effect=RuntimeError):
        assert webhook(req).status_code == 503

@pytest.fixture
def agent_client(fixture):
    from core.models import APIKey
    from core.authentication import generate_raw_api_key
    from rest_framework.test import APIClient
    fixture.user.is_staff = True
    fixture.user.role = 'admin'
    fixture.user.save()
    raw, prefix, hashed = generate_raw_api_key()
    key = APIKey.objects.create(user=fixture.user, name='Integration test agent', prefix=prefix, hashed_key=hashed, tier='read_write')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + raw)
    return client, key


def test_agent_send_has_no_effect_before_human_approval(fixture, recipients, agent_client):
    from dealroom.models import AccessApproval
    client, key = agent_client
    response = client.post('/api/v1/dealroom-sign/envelopes/', {'room_id': str(fixture.room.pk), 'version_id': str(fixture.version.pk), 'recipients': recipients, 'idempotency_key': 'agent-new'}, format='json')
    assert response.status_code == 202
    assert response.data['status'] == 'pending_approval'
    assert AccessApproval.objects.filter(agent_key=key).count() == 1
    assert Workflow.objects.count() == 1


@pytest.mark.parametrize('change', [{'enabled': False}, {'version_id': 'changed'}, {'fields': []}])
def test_nda_gate_edits_require_approval(fixture, agent_client, change):
    client, _ = agent_client
    response = client.put(f'/api/v1/dealroom-sign/nda-policy/{fixture.room.pk}/', change, format='json')
    assert response.status_code == 202
    assert not NdaPolicy.objects.exists()


def test_agent_never_configures_raw_sign_credential(fixture, agent_client):
    client, _ = agent_client
    response = client.put('/api/v1/dealroom-sign/credentials/', {'token': 'api_replacement', 'team_id': 99}, format='json')
    assert response.status_code == 403
    fixture.credential.refresh_from_db()
    assert fixture.credential.token == 'api_private-test-token'


def test_status_projection_never_exposes_signing_token(fixture, agent_client):
    client, _ = agent_client
    fixture.work.signing_token = 'private-recipient-token'
    fixture.work.save()
    response = client.get(f'/api/v1/dealroom-sign/envelopes/{fixture.work.pk}/')
    assert response.status_code == 200
    assert 'private-recipient-token' not in str(response.data)
    assert 'api_private-test-token' not in str(response.data)


def test_scoped_key_cannot_query_other_room(fixture, agent_client):
    from dealroom.models import KeyScope
    client, key = agent_client
    KeyScope.objects.create(key=key, rooms=['some-other-room'])
    assert client.get(f'/api/v1/dealroom-sign/envelopes/{fixture.work.pk}/').status_code == 403


def test_recipient_cannot_use_staff_agent_as_email_proof(fixture, agent_client):
    from dealroom.models import RoomPolicy
    from sharelinks.models import ShareLink
    client, _ = agent_client
    link = ShareLink.objects.create(dataroom=fixture.room, created_by=fixture.user)
    RoomPolicy.objects.create(room=fixture.room, entry_link=link)
    response = client.get(f'/api/v1/dealroom-sign/nda/{fixture.room.pk}/')
    assert response.status_code in (401, 403)
    assert response['Referrer-Policy'] == 'no-referrer'


def test_revoke_after_signature_still_denies_access(fixture):
    from dealroom.models import RoomPolicy
    from dealroom.policy import evaluate
    from sharelinks.models import ShareLink, ShareLinkAccessGrant, Viewer
    link = ShareLink.objects.create(dataroom=fixture.room, created_by=fixture.user, restrict_to_grants=True)
    RoomPolicy.objects.create(room=fixture.room, entry_link=link)
    grant = ShareLinkAccessGrant.objects.create(share_link=link, email='member@example.test', created_by=fixture.user)
    member = Viewer.objects.create(organization=fixture.org, email=grant.email, verified_at=timezone.now())
    policy = NdaPolicy.objects.create(room=fixture.room, source_version=fixture.version, source_sha256=fixture.work.source_sha256)
    NdaAcceptance.objects.create(room=fixture.room, member_id=str(member.pk), member_email=member.email, policy_revision=str(policy.revision), workflow=fixture.work)
    now = timezone.now().timestamp()
    request = SimpleNamespace(session={'dealroom_member': {'room_id': str(fixture.room.pk), 'member_id': str(member.pk), 'email': member.email, 'expires': now+3600, 'last_seen': now}})
    assert evaluate(request, link).allowed
    grant.revoked_at = timezone.now(); grant.save()
    with pytest.raises(PermissionDenied):
        evaluate(request, link)


def test_every_served_glue_operation_has_a_tool_and_mutation_classification():
    import json
    from pathlib import Path
    from dealroom.registry import registry
    from dealroom_sign import __file__ as app_file
    mapping = json.loads(Path(app_file).with_name('tool_map.json').read_text())
    operations = {k:v for k,v in registry().items() if k.startswith('dealroom_sign_')}
    assert set(operations) == set(mapping)
    for operation in operations.values():
        if operation['method'] not in {'GET', 'HEAD', 'OPTIONS'}:
            assert operation['widens_access'] in {True, False, 'evaluate_change'}
    assert operations['dealroom_sign_SignCredentialView_endpoint_put']['human_only']


def test_recipient_allowlist_is_built_from_served_routes():
    import json
    from pathlib import Path
    from django.urls import resolve
    from dealroom_sign import __file__ as app_file
    manifest = json.loads(Path(app_file).with_name('recipient_routes.json').read_text())
    assert manifest['exposure_default'] == 'off'
    for route in manifest['served_routes']:
        path = route.get('target', route['path']).replace('{slug}', 'test').replace('{room_id}', 'test')
        match = resolve(path)
        assert match.func.__module__.startswith('dealroom_sign') or match.func.view_class.__module__.startswith('dealroom_sign')
    assert '/api/v1/dealroom-sign/webhook/' in manifest['private_only']


def test_same_item_replaced_in_sign_does_not_accept_new_source(fixture, pdf):
    work = linked(fixture)
    client = Mock()
    client.audit.return_value = [{'id': 'audit-complete', 'type': 'DOCUMENT_COMPLETED'}]
    client.pdf.return_value = pdf + b'changed source bytes'
    with pytest.raises(SignError, match='source_hash_changed'):
        reconcile(work, client, envelope(work, 'COMPLETED'))
    assert not NdaAcceptance.objects.exists()
    assert not ExecutedArtifact.objects.exists()


def test_sign_credential_team_binding_checked(fixture):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={'teamId': 999}))
    with Documenso(fixture.credential, transport) as client, pytest.raises(SignError, match='sign_team_mismatch'):
        client.get('envelope_test')


def test_audit_catchup_reads_all_pages(fixture):
    pages = []
    def respond(request):
        page = int(request.url.params['page'])
        pages.append(page)
        return httpx.Response(200, json={'data': [{'id': page}], 'count': 2})
    with Documenso(fixture.credential, httpx.MockTransport(respond)) as client:
        assert len(client.audit('envelope_test')['data']) == 2
    assert pages == [1, 2]
