"""Printed names cannot supply identity across columns or party boundaries."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r29_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


H1 = ([('conformed', *row) for row in review.captured('hidden')
       if row[0]['shape'] == 'conformed_s']
      + [(family, *row) for family in ('no_rule', 'geometry', 'ruleless_name')
         for row in review.captured(family)])


@pytest.mark.parametrize('family,axes,pages,people,allowed', H1)
def test_exact_h1_matrices(family, axes, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (family, axes, result)
    model.assert_not_called()


@pytest.mark.parametrize('axes,pages,people,allowed', review.workers())
def test_ruleless_real_worker(axes, pages, people, allowed):
    model = Mock()
    pdf = review.pdf(pages)
    result = placement.place(pdf, people, model_client=model)
    assert result == in_process(placement, pdf, people, model)
    assert result['status'] == 'needs_sender', (axes, result)
    assert result['fields'] == []
    model.assert_not_called()
