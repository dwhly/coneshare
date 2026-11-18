"""Hidden signing stacks retain ambiguity without fixed Name/Date vocabulary."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r28_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('axes,pages,people,allowed', review.captured('variants'))
def test_exact_700_variants(axes, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    model.assert_not_called()


@pytest.mark.parametrize('axes,pages,people,allowed', review.workers())
def test_five_real_worker_shapes(axes, pages, people, allowed):
    model = Mock()
    pdf = review.rc.pages_pdf(pages)
    result = placement.place(pdf, people, model_client=model)
    assert result == in_process(placement, pdf, people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    model.assert_not_called()


@pytest.mark.parametrize('axes,pages,people,allowed', list(review.extended()))
def test_person_row_and_labelled_rule(axes, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    model.assert_not_called()


def test_date_rule_without_label_rect():
    signature = placement.Line(1, 100, 290, 370, 'drawn')
    signature.label = {'text': 'Executed by:', 'rect': [72, 360, 95, 369]}
    date = placement.Line(1, 100, 290, 420, 'drawn', semantic='DATE')
    date.label = {'text': 'Date:'}
    name = {'text': 'Name: Pat Smith', 'rect': [72, 374, 160, 384]}
    assert placement.unclaimed_signing_peers([signature, date], [name], []) == [[['pat', 'smith']]]
