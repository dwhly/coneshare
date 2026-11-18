"""The widened Date band never adopts a signer under another company's heading."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r32_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('axes,pages,people,allowed', review.captured('affiliate_sender'))
def test_affiliate_heading_does_not_own_widened_name(axes, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    model.assert_not_called()


@pytest.mark.parametrize('order', ['aff_first', 'hla_first', 'no_hla'])
@pytest.mark.parametrize('explicit', [False, True])
def test_exact_affiliate_reproduction_holds_in_worker(order, explicit):
    source = review.worker_case()
    pdf = source['doc']('HARBOR LIGHT ANALYTICS HOLDINGS, LLC', 30, 30, order)
    person = source['PAT_X' if explicit else 'PAT_D']
    model = Mock()
    result = placement.place(pdf, [person], model_client=model)
    assert result['status'] == 'needs_sender' and not result['fields'], result
    model.assert_not_called()
