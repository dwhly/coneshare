"""Role-description disagreement and cross-page company competition must hold."""
from itertools import product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r24_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process

RECITALS = list(review.cases.matrix(review.ATTACK | review.BOUNDARY))
CROSS_PAGE = list(review.cross_page_matrix())
VETO = list(review.veto_matrix())


@pytest.mark.parametrize('args,pages,people,allowed', RECITALS,
                         ids=[str(i) for i in range(len(RECITALS))])
def test_recital_geometry(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('args,pages,people,allowed', CROSS_PAGE,
                         ids=[str(i) for i in range(len(CROSS_PAGE))])
def test_cross_page_geometry(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('args,pages,people,allowed', VETO,
                         ids=[str(i) for i in range(len(VETO))])
def test_alias_veto_geometry(args, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('kind,both', product(('b1', 'b2'), (False, True)))
def test_recital_real_worker(kind, both):
    pages, people, allowed = review.worker_case(kind, both)
    model = Mock()
    pdf = review.rc.pages_pdf(pages)
    result = placement.place(pdf, people, model_client=model)
    assert not review.rc.wrong_fields(result, allowed), result
    assert result == in_process(placement, pdf, people, model)
    model.assert_not_called()


def test_cross_page_real_worker():
    pages, people, allowed = review.h1_worker_case()
    model = Mock()
    pdf = review.rc.pages_pdf(pages)
    result = placement.place(pdf, people, model_client=model)
    assert not review.rc.wrong_fields(result, allowed), result
    assert result == in_process(placement, pdf, people, model)
    model.assert_not_called()


def test_uncaptioned_cross_page_real_worker():
    pages, people, allowed = review.h1_uncaptioned_worker_case()
    model = Mock()
    pdf = review.rc.pages_pdf(pages)
    result = placement.place(pdf, people, model_client=model)
    assert not review.rc.wrong_fields(result, allowed), result
    assert result == in_process(placement, pdf, people, model)
    model.assert_not_called()
