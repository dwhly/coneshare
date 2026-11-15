import json
from types import SimpleNamespace

import httpx
import pytest

from dealroom_sign.client import Documenso, SignError

FLAGS = dict.fromkeys(('recipientSigningRequest', 'recipientRemoved', 'recipientSigned',
    'documentPending', 'documentCompleted', 'documentDeleted', 'ownerDocumentCompleted',
    'ownerRecipientExpired', 'ownerDocumentCreated'), False)
REMINDERS = {'sendAfter': {'disabled': True}, 'repeatEvery': {'disabled': True}}
EXPIRATION = {'unit': 'day', 'amount': 30}


@pytest.mark.parametrize('nda', [False, True])
def test_release_updates_reads_back_then_distributes_without_native_mail(nda):
    calls = []
    def handle(request):
        calls.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
        return httpx.Response(200, json={'id': 'env_test', 'externalId': 'correlation', 'teamId': 3, 'authOptions': {'globalAccessAuth': [], 'globalActionAuth': []}, 'documentMeta': {
            'distributionMethod': 'NONE', 'emailSettings': FLAGS, 'reminderSettings': REMINDERS, 'envelopeExpirationPeriod': EXPIRATION}})
    with Documenso(SimpleNamespace(enabled=True, team_id=3, token='test'), httpx.MockTransport(handle)) as client:
        client.distribute('env_test', external_id='correlation', redirect_url='https://recipient.test/s/return/r')
    assert [(m, p.rsplit('/', 1)[-1]) for m, p, _ in calls] == [
        ('POST', 'update'), ('POST', 'get'), ('POST', 'distribute'), ('GET', 'env_test')]
    assert calls[0][2] == {'envelopeId': 'env_test', 'data': {'globalAccessAuth': [], 'globalActionAuth': []},
        'meta': {'reminderSettings': REMINDERS, 'envelopeExpirationPeriod': EXPIRATION}}
    assert calls[2][2] == {'envelopeId': 'env_test', 'meta': {'distributionMethod': 'NONE',
        'emailSettings': FLAGS, 'redirectUrl': 'https://recipient.test/s/return/r'}}


@pytest.mark.parametrize('meta', [{}, {'reminderSettings': REMINDERS},
    {'reminderSettings': REMINDERS, 'envelopeExpirationPeriod': {'unit': 'day', 'amount': 31}},
    {'reminderSettings': {'sendAfter': {'disabled': True}, 'repeatEvery': {'unit': 'day', 'amount': 2}},
     'envelopeExpirationPeriod': EXPIRATION}])
def test_metadata_mismatch_never_distributes(meta):
    paths = []
    def handle(request):
        paths.append(request.url.path)
        return httpx.Response(200, json={'id': 'env_test', 'externalId': 'correlation', 'teamId': 3, 'documentMeta': meta})
    with Documenso(SimpleNamespace(enabled=True, team_id=3, token='test'), httpx.MockTransport(handle)) as client:
        with pytest.raises(SignError, match='release_settings_not_persisted'):
            client.distribute('env_test', external_id='correlation')
    assert not any(p.endswith('/distribute') for p in paths)


@pytest.mark.parametrize('field,value', [('id', None), ('id', 'other'), ('teamId', None),
    ('teamId', 4), ('externalId', None), ('externalId', 'other')])
def test_editor_readback_is_bound_to_envelope_team_and_correlation(field, value):
    paths = []
    def handle(request):
        paths.append(request.url.path)
        data = {'id': 'env_test', 'teamId': 3, 'externalId': 'correlation',
            'documentMeta': {'reminderSettings': REMINDERS, 'envelopeExpirationPeriod': EXPIRATION}}
        data[field] = value
        assert request.headers['Authorization'] == 'team-credential'
        if request.url.path.endswith('/editor/get'):
            assert json.loads(request.content) == {'envelopeId': 'env_test'}
        return httpx.Response(200, json=data)
    with Documenso(SimpleNamespace(enabled=True, team_id=3, token='team-credential'), httpx.MockTransport(handle)) as client:
        with pytest.raises(SignError, match='envelope_correlation_mismatch'):
            client.distribute('env_test', external_id='correlation')
    assert paths == ['/api/v2/envelope/update', '/api/deal/envelope/editor/get']
