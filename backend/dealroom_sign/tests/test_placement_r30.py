"""Date-first signing blocks retain their own printed names across a blank row."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r30_review_cases as review
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('axes,pages,people,allowed', review.captured('date'))
def test_exact_date_first_matrix_has_no_wrong_placement(axes, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    model.assert_not_called()


@pytest.mark.parametrize('layout', ['side', 'stacked'])
@pytest.mark.parametrize('gap', [12, 20, 22, 24, 30])
def test_date_first_blank_row_real_worker(layout, gap):
    def block(head, company, x, who, y):
        return [(y - 50, head, False, x), (y - 38, company, False, x),
                (y, 'By:', True, x, x + 180),
                (y + 24, 'Date:', True, x, x + 180),
                (y + 24 + gap, 'Name: ' + who, False, x),
                (y + 36 + gap, 'Title: CEO', False, x)]

    fx, fy, hx, hy = (40, 300, 320, 300) if layout == 'side' else (72, 200, 72, 450)
    pages = [list(review.rc.RECITALS['parsed']),
             block('DISCLOSER:', 'FLEET TEST CO.', fx, 'Dan Whaley', fy)
             + block('RECIPIENT:', 'HARBOR LIGHT ANALYTICS, INC.', hx, 'Pat Smith', hy)]
    pdf = review.rc.pages_pdf(pages)
    people = [TWO[1], dict(name='Pat Smith', email=review.rc.PE)]
    model = Mock()
    result = placement.place(pdf, people, model_client=model)
    assert result == in_process(placement, pdf, people, model)
    assert result['status'] == 'placed', result
    assert len(result['fields']) == 4
    assert not review.rc.wrong_fields(result, {
        review.rc.PE: (2, hx, hy, hx + 180), review.rc.DE: (2, fx, fy, fx + 180)})
    model.assert_not_called()
