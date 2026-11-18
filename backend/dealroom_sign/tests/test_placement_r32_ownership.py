"""Exact company ownership and better cross-page headings constrain expansion."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r32_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('heading,company,expected', [
    ('HARBOR LIGHT ANALYTICS, LLC', 'Harbor Light Analytics, Inc.', 'placed'),
    ('Harbor Light Analytics', 'HARBOR LIGHT ANALYTICS, INC.', 'placed'),
    ('HARBORLIGHT ANALYTICS, INC.', 'Harbor Light Analytics, Inc.', 'needs_sender'),
    ('HARBOR LIGHT ANALYTICS HOLDINGS, LLC', 'Harbor Light Analytics, Inc.', 'needs_sender'),
    ('HARBORLIGHT, LLC', '', 'needs_sender'),
    ('HARBOR LIGHT ANALYTICS, INC.', '', 'needs_sender'),
    ('HARBOR LIGHT ANALYTICS, INC.', 'Harbor of Light Analytics, Inc.', 'needs_sender'),
    ('HARBOR LIGHT ANALYTICS 2, INC.', 'Harbor Light Analytics 3, Inc.', 'needs_sender'),
])
def test_exact_normalized_company_without_recital(heading, company, expected):
    rows = [(162, heading, False, 72), (200, 'By:', True, 72, 272),
            (230, 'Date:', True, 72, 272), (260, 'Name: Pat Smith', False, 72)]
    person = dict(name='Pat Smith', email=review.rc.PE, company=company)
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf([[], rows]), [person], model)
    assert result['status'] == expected, result
    if expected == 'placed':
        assert not review.rc.wrong_fields(result, {review.rc.PE: (2, 72, 200, 272)})
    else:
        assert not result['fields']
    model.assert_not_called()


@pytest.mark.parametrize('own_first', [False, True])
@pytest.mark.parametrize('explicit', [False, True])
def test_better_unclaimed_company_heading_on_any_page_vetoes_role_expansion(own_first, explicit):
    role = [(162, 'RECIPIENT:', False, 72), (200, 'By:', True, 72, 272),
            (230, 'Date:', True, 72, 272), (260, 'Name: Pat Smith', False, 72)]
    own = [(162, 'HARBOR LIGHT ANALYTICS, INC.', False, 72),
           (200, 'By:', True, 72, 272), (230, 'Date:', True, 72, 272)]
    pages = [list(review.rc.RECITALS['parsed']), *([own, role] if own_first else [role, own])]
    person = dict(name='Pat Smith', email=review.rc.PE)
    if explicit:
        person['company'] = 'Harbor Light Analytics, Inc.'
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), [person], model)
    assert result['status'] == 'needs_sender' and not result['fields'], result
    model.assert_not_called()
