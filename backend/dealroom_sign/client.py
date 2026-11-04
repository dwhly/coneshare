"""Bounded v2 envelope transport. No response bodies/tokens in errors or logs."""
import json
import re

import httpx
from django.conf import settings


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
        self.http = httpx.Client(
            base_url=settings.SIGN_INTERNAL_URL.rstrip('/') + '/api/v2/',
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
        return self.request('GET', f'envelope/{identifier(envelope_id)}').json()

    def find(self, external_id):
        # externalId is correlation, NOT an upstream uniqueness guarantee.
        matches = []
        page = 1
        while True:
            data = self.request('GET', 'envelope', params={'page': page, 'perPage': 100}).json()
            rows = data.get('data', [])
            matches.extend(row for row in rows if row.get('externalId') == external_id)
            if page * 100 >= data.get('count', len(rows)):
                return matches
            page += 1
            if page > 100:
                raise SignError('discovery_limit_requires_operator')

    def create(self, workflow, pdf):
        payload = {'title': workflow.title, 'type': 'DOCUMENT', 'externalId': workflow.external_id,
                   'recipients': workflow.recipients, 'meta': {'distributionMethod': 'NONE'}}
        return self.request('POST', 'envelope/create', data={'payload': json.dumps(payload)},
                            files={'files': ('document.pdf', pdf, 'application/pdf')}).json()['id']

    def distribute(self, envelope_id, *, nda=False, redirect_url=''):
        meta = {'distributionMethod': 'NONE' if nda else 'EMAIL'}
        if redirect_url:
            meta['redirectUrl'] = redirect_url
        return self.request('POST', 'envelope/distribute', json={'envelopeId': envelope_id, 'meta': meta}).json()

    def pdf(self, path, **kwargs):
        response = self.request('GET', path, **kwargs)
        if len(response.content) > 50 * 1024 * 1024 or not response.content.startswith(b'%PDF-'):
            raise SignError('invalid_evidence_pdf')
        return response.content

    def signed_item(self, item_id):
        return self.pdf(f'envelope/item/{identifier(item_id)}/download', params={'version': 'signed'})

    def certificate(self, envelope_id):
        return self.pdf(f'envelope/{identifier(envelope_id)}/certificate/download')

    def audit(self, envelope_id):
        return self.request('GET', f'envelope/{identifier(envelope_id)}/audit-log').json()

    def audit_pdf(self, envelope_id):
        return self.pdf(f'envelope/{identifier(envelope_id)}/audit-log/download')
