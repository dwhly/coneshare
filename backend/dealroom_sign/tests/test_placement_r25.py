"""Unclaimed signing identities on another page require sender review."""
from itertools import product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r25_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process

Q3A = list(review.q3a())
Q3B = list(review.q3b())
WORKERS = list(product(('msa_supplier', 'nda_member', 'nda_caption', 'nda_named'), (False, True)))


@pytest.mark.parametrize('args,pages,people,allowed', Q3A, ids=[str(i) for i in range(len(Q3A))])
def test_q3a_cross_page_identity(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('args,pages,people,allowed', Q3B, ids=[str(i) for i in range(len(Q3B))])
def test_q3b_defined_roles(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('kind,both', WORKERS)
def test_cross_page_real_worker(kind, both):
    pages, people, allowed = review.worker_case(kind, both)
    pdf, model = review.rc.pages_pdf(pages), Mock()
    result = placement.place(pdf, people, model_client=model)
    assert not review.rc.wrong_fields(result, allowed), result
    assert result == in_process(placement, pdf, people, model)
    model.assert_not_called()


@pytest.mark.parametrize('other_signer', [False, True])
@pytest.mark.parametrize('target_name', [False, True])
@pytest.mark.parametrize('separate_page', [False, True])
def test_cross_page_guard_accounts_for_all_signers(other_signer, target_name, separate_page):
    other = (review.prior.company_block(None, 'BRIGHTWATER, INC.', 40, extra='none')
             + [(312, 'Name: Chris Jones', False, 40)])
    target = review.prior.company_block(None, review.prior.HLA, 320,
                                        extra='printed' if target_name else 'placeholders')
    pages = [other, target] if separate_page else [other + target]
    people = review.people('domain')
    if other_signer:
        people += [dict(name='Chris Jones', email='chris@example.test')]
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    expected = 'needs_sender' if separate_page and not other_signer and not target_name else 'placed'
    assert result['status'] == expected, result
    if expected == 'needs_sender':
        assert result['fields'] == []
    else:
        allowed = {review.rc.PE: (2 if separate_page else 1, 320, 300, 500),
                   'chris@example.test': (1, 40, 300, 220)}
        assert not review.rc.wrong_fields(result, allowed), result
    model.assert_not_called()


def test_cross_page_witness_does_not_claim_party_identity():
    witness = [(300, 'Witness:', True, 40, 220),
               (312, 'Name: Chris Jones', False, 40), (360, 'Date:', True, 40, 220)]
    pages = [witness, review.prior.company_block(None, review.prior.HLA, 320)]
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), review.people('domain'), model)
    assert result['status'] == 'placed', result
    assert not review.rc.wrong_fields(result, {review.rc.PE: (2, 320, 300, 500)}), result
    model.assert_not_called()
