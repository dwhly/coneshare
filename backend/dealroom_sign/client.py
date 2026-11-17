"""Bounded v2 envelope transport. No response bodies/tokens in errors or logs."""
import json
import re
import time

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


NATIVE_EMAIL_OFF = dict.fromkeys((
    'recipientSigningRequest', 'recipientRemoved', 'recipientSigned', 'documentPending',
    'documentCompleted', 'documentDeleted', 'ownerDocumentCompleted', 'ownerRecipientExpired',
    'ownerDocumentCreated',
), False)
NATIVE_REMINDERS_OFF = {'sendAfter': {'disabled': True}, 'repeatEvery': {'disabled': True}}
SIGNING_PERIOD = {'unit': 'day', 'amount': 30}


def pdf_filename(title):
    """The file name signers see when they download ("<title>.pdf", then "<title>_signed.pdf"), not "document.pdf"."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', ' ', title or '').strip().strip('.')
    name = re.sub(r'\s+', ' ', name)[:120].strip()
    if name.lower().endswith('.pdf'):
        name = name[:-4].rstrip()
    return (name or 'document') + '.pdf'


class SignError(Exception):
    def __init__(self, code, *, uncertain=False):
        self.code = code
        self.uncertain = uncertain
        super().__init__(code)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise SignError('invalid_sign_identifier')
    return value


class Documenso:
    def __init__(self, credential, transport=None):
        if not credential.enabled:
            raise SignError('sign_credential_disabled')
        self.base_url = settings.SIGN_INTERNAL_URL.strip().rstrip('/')
        if not self.base_url:
            raise ImproperlyConfigured('SIGN_INTERNAL_URL is required for Dealroom Sign')
        self.team_id = credential.team_id
        self.http = httpx.Client(
            base_url=self.base_url + '/api/v2/',
            headers={'Authorization': credential.token, 'Accept': 'application/json'},
            timeout=httpx.Timeout(10), follow_redirects=False, transport=transport,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.http.close()

    def request(self, method, path, **kwargs):
        try:
            response = self.http.request(method, path, **kwargs)
        except httpx.TransportError:
            raise SignError('sign_transport_error', uncertain=method != 'GET') from None
        if response.status_code >= 300:
            raise SignError(f'sign_http_{response.status_code}', uncertain=method != 'GET' and response.status_code >= 500)
        return response

    def get(self, envelope_id):
        envelope = self.request('GET', f'envelope/{identifier(envelope_id)}').json()
        if envelope.get('teamId') != self.team_id:
            raise SignError('sign_team_mismatch')
        return envelope

    def find(self, external_id):
        # externalId is correlation, NOT an upstream uniqueness guarantee.
        matches = []
        page = 1
        deadline = time.monotonic() + 40
        while True:
            data = self.request('GET', 'envelope', params={'page': page, 'perPage': 100}).json()
            rows = data.get('data', [])
            matches.extend(row for row in rows if row.get('externalId') == external_id)
            if page * 100 >= data.get('count', len(rows)):
                return matches
            page += 1
            if page > 100 or time.monotonic() > deadline:
                raise SignError('discovery_limit_requires_operator')

    def create(self, workflow, pdf, meta=None):
        payload = {'title': workflow.title, 'type': 'DOCUMENT', 'externalId': workflow.external_id,
                   'recipients': [{k: r[k] for k in ('name', 'email', 'role', 'signingOrder', 'fields') if k in r}
                                  for r in workflow.recipients], 'meta': {**(meta or {}), 'distributionMethod': 'NONE', 'emailSettings': NATIVE_EMAIL_OFF}}
        return self.request('POST', 'envelope/create', data={'payload': json.dumps(payload)},
                            files={'files': (pdf_filename(workflow.title), pdf, 'application/pdf')}).json()['id']

    def distribute(self, envelope_id, *, external_id, redirect_url='', before_distribute=None):
        # EDD §4.3 / r1b: distribute strips reminder/expiry settings; persist and verify first.
        self.request('POST', 'envelope/update', json={'envelopeId': envelope_id,
            'data': {'globalAccessAuth': [], 'globalActionAuth': []},
            'meta': {'reminderSettings': NATIVE_REMINDERS_OFF, 'envelopeExpirationPeriod': SIGNING_PERIOD}})
        envelope = self.request('POST', self.base_url +
            '/api/deal/envelope/editor/get', json={'envelopeId': identifier(envelope_id)}).json()
        if (not isinstance(envelope, dict) or envelope.get('id') != envelope_id or
                envelope.get('teamId') != self.team_id or not external_id or
                envelope.get('externalId') != external_id):
            raise SignError('envelope_correlation_mismatch')
        persisted = envelope.get('documentMeta') or {}
        auth = envelope.get('authOptions') or {}
        if (persisted.get('reminderSettings') != NATIVE_REMINDERS_OFF or
                persisted.get('envelopeExpirationPeriod') != SIGNING_PERIOD or
                auth.get('globalAccessAuth') != [] or auth.get('globalActionAuth') != []):
            raise SignError('release_settings_not_persisted')
        meta = {'distributionMethod': 'NONE', 'emailSettings': NATIVE_EMAIL_OFF, 'redirectUrl': redirect_url}
        if before_distribute:
            before_distribute()
        result = self.request('POST', 'envelope/distribute', json={'envelopeId': envelope_id, 'meta': meta}).json()
        self.verify_release(self.get(envelope_id))
        return result

    @staticmethod
    def verify_release(envelope):
        meta = envelope.get('documentMeta') or {}
        if (meta.get('distributionMethod') != 'NONE' or
                any(meta.get('emailSettings', {}).get(flag) is not False for flag in NATIVE_EMAIL_OFF)):
            raise SignError('release_mail_settings_mismatch', uncertain=True)

    def pdf(self, path, **kwargs):
        response = self.request('GET', path, **kwargs)
        if len(response.content) > 50 * 1024 * 1024 or not response.content.startswith(b'%PDF-'):
            raise SignError('invalid_evidence_pdf')
        return response.content

    def item_pdf(self, item_id, version):
        if version not in {'original', 'pending', 'signed'}:
            raise SignError('invalid_item_version')
        return self.pdf(f'envelope/item/{identifier(item_id)}/download', params={'version': version})

    def signed_item(self, item_id):
        return self.pdf(f'envelope/item/{identifier(item_id)}/download', params={'version': 'signed'})

    def certificate(self, envelope_id):
        return self.pdf(f'envelope/{identifier(envelope_id)}/certificate/download')

    def audit(self, envelope_id):
        rows = []
        deadline = time.monotonic() + 40
        for page in range(1, 101):
            data = self.request('GET', f'envelope/{identifier(envelope_id)}/audit-log', params={'page': page, 'perPage': 100}).json()
            rows.extend(data['data'])
            if len(rows) >= data['count']:
                return {'data': rows}
            if time.monotonic() > deadline:
                break
        raise SignError('audit_pagination_incomplete')

    def audit_pdf(self, envelope_id):
        return self.pdf(f'envelope/{identifier(envelope_id)}/audit-log/download')


    def cancel(self, envelope_id, external_id):
        try:
            envelope = self.get(envelope_id)
        except SignError as exc:
            if exc.code == 'sign_http_404':
                return  # already deleted draft on a previous reset attempt
            raise
        if envelope.get('externalId') != external_id:
            raise SignError('envelope_correlation_mismatch')
        status = envelope['status']
        if status == 'DRAFT':
            # Native cancellation accepts PENDING only; delete the unsent draft.
            self.request('POST', 'envelope/delete', json={'envelopeId': envelope_id})
        elif status == 'PENDING':
            self.request('POST', 'envelope/cancel', json={'envelopeId': envelope_id, 'reason': 'Staff reset of stuck NDA workflow'})
            if self.get(envelope_id)['status'] != 'CANCELLED':
                raise SignError('cancellation_not_confirmed')
        elif status not in {'CANCELLED', 'REJECTED', 'COMPLETED'}:
            raise SignError('unknown_sign_status')
        # COMPLETED cannot be cancelled natively and has no remaining signing
        # action. Preserve its evidence; reset only supersedes the local failed
        # workflow and never turns the old completion into an NDA acceptance.
