"""Ownership and same-page alternatives constrain the expanded Date band."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r31_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('heading,peer,recital', [
    ('', None, 'parsed'),
    ('RECIPIENT:', None, 'none'),
    ('FLEET TEST CO.', None, 'parsed'),
    ('DISCLOSER:', None, 'parsed'),
    ('HARBOR LIGHT ANALYTICS, INC.', '', 'parsed'),
    ('HARBOR LIGHT ANALYTICS, INC.', 'RECIPIENT:', 'parsed'),
    ('HARBOR LIGHT ANALYTICS, INC.', 'HARBOR LIGHT ANALYTICS, INC.', 'parsed'),
])
@pytest.mark.parametrize('explicit', [False, True])
def test_widening_requires_own_party_and_no_unclaimed_alternative(heading, peer, recital, explicit):
    rows = [(162, heading, False, 72), (200, 'By:', True, 72, 272),
            (230, 'Date:', True, 72, 272), (260, 'Name: Pat Smith', False, 72)]
    if peer is not None:
        rows += [(162, peer, False, 340), (200, 'By:', True, 340, 540),
                 (230, 'Date:', True, 340, 540)]
    person = dict(name='Pat Smith', email=review.rc.PE)
    if explicit:
        person['company'] = 'Harbor Light Analytics, Inc.'
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf([
        list(review.rc.RECITALS[recital]), rows]), [person], model)
    assert result['status'] == 'needs_sender' and not result['fields'], result
    model.assert_not_called()


@pytest.mark.parametrize('heading', ['HARBOR LIGHT ANALYTICS, INC.', 'RECIPIENT:'])
@pytest.mark.parametrize('explicit', [False, True])
def test_own_company_or_mapped_role_preserves_recovery(heading, explicit):
    rows = [(162, heading, False, 72), (200, 'By:', True, 72, 272),
            (230, 'Date:', True, 72, 272), (260, 'Name: Pat Smith', False, 72)]
    person = dict(name='Pat Smith', email=review.rc.PE)
    if explicit:
        person['company'] = 'Harbor Light Analytics, Inc.'
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf([
        list(review.rc.RECITALS['parsed']), rows]), [person], model)
    assert result['status'] == 'placed', result
    assert not review.rc.wrong_fields(result, {review.rc.PE: (2, 72, 200, 272)})
    model.assert_not_called()
