"""A vetoed own-name stack does not add an independent third party."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r21_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


IDENTITIES = [
    ('Pat Smith', 'pat@harborlight.example', 'HARBOR LIGHT ANALYTICS, INC.'),
    ('Alex Chen', 'alex@northwindsystems.example', 'NORTHWIND SYSTEMS, LLC.'),
    ('Morgan Reed', 'morgan@cedargrove.example', 'CEDAR GROVE SOFTWARE, INC.'),
]


@pytest.mark.parametrize('name,email,company', IDENTITIES)
@pytest.mark.parametrize('heading_kind', ['role', 'company'])
@pytest.mark.parametrize('own_name', [False, True])
@pytest.mark.parametrize('extra_page', [False, True])
def test_separate_company_with_vetoed_stack(name, email, company, heading_kind,
                                           own_name, extra_page):
    printed = name if own_name else 'Chris Jones'
    heading = 'RECIPIENT:' if heading_kind == 'role' else company.lower()
    pages = [[
        (240, 'ACME INDUSTRIES, LLC.', False, 72),
        (270, 'By:', True, 72), (310, 'By:', True, 72),
        (340, heading, False, 72), (370, 'Firma:', True, 72),
        (382, 'Name: ' + printed, False, 72), (420, 'Date:', True, 72),
        (520, company, False, 72), (560, 'By:', True, 72),
        (600, 'Date:', True, 72),
    ]]
    if extra_page:
        pages.append([(300, 'By:', True, 72), (360, 'Date:', True, 72)])
    pdf = review.pages_pdf(pages)
    people = [dict(name=name, email=email)]
    model = Mock()
    result = placement.place(pdf, people, model_client=model)
    assert result == in_process(placement, pdf, people, model)
    if own_name and not extra_page:
        assert result['status'] == 'placed', result
        assert {(f['signer'], f['type'], f['evidence']['line'][1]) for f in result['fields']} == {
            (email, 'SIGNATURE', 560), (email, 'DATE', 600),
        }
        assert result['assignments'][0]['score'] == 4
        assert result['assignments'][0]['margin'] == 4
    else:
        assert result['status'] == 'needs_sender', result
        assert not result['fields']
    model.assert_not_called()
