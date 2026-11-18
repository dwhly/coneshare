"""Exact Gate 3 matrices and real-worker same-page regressions."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r26_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process

Q3C = review.captured('q3c')
WORKERS = list(review.worker_cases())


@pytest.mark.parametrize('args,pages,people,allowed', Q3C,
                         ids=[str(i) for i in range(len(Q3C))])
def test_q3c_exact_reviewer_matrix(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('args,pages,people,allowed', WORKERS,
                         ids=[f'{args[0]}-{args[1]}' for args, *_ in WORKERS])
def test_same_page_real_worker(args, pages, people, allowed):
    model = Mock()
    pdf = review.rc.pages_pdf(pages)
    result = placement.place(pdf, people, model_client=model)
    assert not review.rc.wrong_fields(result, allowed), (args, result)
    assert result == in_process(placement, pdf, people, model)
    model.assert_not_called()


def test_reviewer_inventory_is_complete():
    assert len(Q3C) == 2808
    assert sum(args['L'] == 'same_page3' for args, *_ in Q3C) == 468
    assert len(WORKERS) == 10
