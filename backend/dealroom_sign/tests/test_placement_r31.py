"""An expanded Date band requires ownership of the adopted printed name."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r31_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('axes,pages,people,allowed',
                         review.captured('plain') + review.captured('swap'))
def test_exact_close_date_band_matrix(axes, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    model.assert_not_called()


@pytest.mark.parametrize('axes,pages,people', review.workers())
def test_exact_close_date_band_real_worker(axes, pages, people):
    pdf = review.rc.pages_pdf(pages)
    model = Mock()
    result = placement.place(pdf, people, model_client=model)
    assert result == in_process(placement, pdf, people, Mock())
    assert result['status'] == 'needs_sender' and not result['fields'], (axes, result)
    model.assert_not_called()
