"""Party names containing conjunctions retain their own signature geometry."""
from itertools import product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r23_review_cases as cases
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process

Q2 = list(cases.matrix())
WORKERS = list(product(('b1', 'b2'), (False, True), (False, True),
                       ('same', 'guarantor', 'split'),
                       ('RECIPIENT:', 'THE RECIPIENT', 'Recipient')))
EXTRA_RECITALS = {
    'johnson_short': [cases.PREFIX + 'Johnson and Johnson ("Recipient").'],
    'johnson_address': [cases.PREFIX + 'Johnson and Johnson, ' + cases.ADDRESS + ' ("Recipient").'],
    'procter_short': [cases.PREFIX + 'Procter and Gamble Co. ("Recipient").'],
    'procter_address': [cases.PREFIX + 'Procter and Gamble Co., ' + cases.ADDRESS + ' ("Recipient").'],
    'group_repeat': [cases.FIRST + ' Harbor Light Group, Inc. ("Recipient").'],
    'holdings_repeat': [cases.FIRST + ' Harbor Light Holdings, Inc. ("Recipient").'],
    'light_repeat': [cases.FIRST + ' Harbor Light, Inc. ("Recipient").'],
}
EXTRA = list(cases.matrix(EXTRA_RECITALS))


@pytest.mark.parametrize('args,pages,people,allowed', Q2, ids=[str(i) for i in range(len(Q2))])
def test_review_q2_geometry(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, cases.rc.pages_pdf(pages), people, model)
    assert not cases.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('kind,both,explicit,layout,heading', WORKERS)
def test_review_real_worker(kind, both, explicit, layout, heading):
    pages, people, allowed = cases.worker_case(kind, both, explicit, layout, heading)
    model = Mock()
    pdf = cases.rc.pages_pdf(pages)
    result = placement.place(pdf, people, model_client=model)
    assert not cases.rc.wrong_fields(result, allowed), result
    assert result == in_process(placement, pdf, people, model)
    model.assert_not_called()


@pytest.mark.parametrize('args,pages,people,allowed', EXTRA, ids=[str(i) for i in range(len(EXTRA))])
def test_additional_conjunction_and_repeat_controls(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, cases.rc.pages_pdf(pages), people, model)
    assert not cases.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('key,company', [
    ('b1_inc_address', 'Smith and Jones, Inc.'),
    ('b1_co_address', 'Smith and Jones Co.'),
    ('b1_llc_hereinafter', 'Smith and Jones LLC'),
    ('b1_three', 'Smith and Jones, Inc.'),
    ('b2_lazy_tail', 'Recipient'),
    ('research_center', cases.HLA),
])
def test_description_role_mapping(key, company):
    rows = cases.recital_rows(cases.RECITALS[key][0], True)
    _, _, roles = placement.extract(cases.rc.pages_pdf([rows]))
    assert roles['recipient'] == company, roles
