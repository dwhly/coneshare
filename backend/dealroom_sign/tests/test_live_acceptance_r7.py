"""Live acceptance r7: the in-page PDF viewer's token file route.

On the preview, the signing page showed "Something went wrong while loading the document": Sign's viewer asks for
/api/files/token/<t>/envelope/<e>/envelopeItem/<i>/dataId/<d>/current/item.pdf, and Sign's route accepts only
version initial|current (apps/remix/server/api/files/routes/get-envelope-item-pdf-by-token.ts:18). The proxy
allowlisted original|pending|signed, the download route's versions, so it denied every viewer request.
"""
import json
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope

pytestmark = pytest.mark.django_db


class Passed(Exception):
    """record_fact runs only after the scope check accepts the request."""


def _forward(access, version, *, token=None, data_id='data_test', item='item_test', envelope_id=None):
    from dealroom_sign.counterparty import new_session, COOKIE
    from dealroom_sign.recipient_proxy import forward
    session, raw = new_session(access)
    env = envelope(access.workflow)
    env['envelopeItems'][0]['documentDataId'] = 'data_test'
    path = (f'/api/files/token/{token or access.native_token}/envelope/{envelope_id or access.workflow.envelope_id}'
            f'/envelopeItem/{item}/dataId/{data_id}/{version}/item.pdf')
    req = RequestFactory().get(path)
    req.COOKIES[COOKIE] = raw
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=env), \
         patch('dealroom_sign.recipient_proxy.record_fact', side_effect=Passed):
        return forward(req, session)


@pytest.mark.parametrize('version', ['current', 'initial'])
def test_viewer_pdf_versions_sign_serves_are_allowed(access, version):
    with pytest.raises(Passed):
        _forward(access, version)


@pytest.mark.parametrize('version', ['original', 'pending', 'signed', 'CURRENT', 'current2', 'latest'])
def test_viewer_pdf_other_versions_are_denied(access, version):
    from dealroom_sign.client import SignError
    with pytest.raises(SignError, match='recipient_scope_mismatch'):
        _forward(access, version)


@pytest.mark.parametrize('kw', [{'token': 'someoneElsesToken'}, {'data_id': 'other_data'}, {'item': 'other_item'},
                                {'envelope_id': 'envelope_other'}])
def test_viewer_pdf_stays_bound_to_this_signer_and_document(access, kw):
    from dealroom_sign.client import SignError
    with pytest.raises(SignError, match='recipient_scope_mismatch'):
        _forward(access, 'current', **kw)
