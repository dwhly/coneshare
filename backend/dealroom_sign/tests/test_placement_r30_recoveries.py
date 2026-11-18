"""The 686 reviewer regressions recover exactly their prior correct placement."""
import json
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r30_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


EXPECTED = json.loads((review.FIXTURES / 'date-first-recoveries.json').read_text())
RECOVERIES = [(index, *cell, EXPECTED[str(index)])
              for index, cell in enumerate(review.captured('date')) if str(index) in EXPECTED]
assert len(RECOVERIES) == 686


@pytest.mark.parametrize('index,axes,pages,people,allowed,expected', RECOVERIES)
def test_every_r29_date_first_regression_recovers(index, axes, pages, people, allowed, expected):
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    assert {k: v for k, v in result.items() if k != 'analysis_version'} == {
        k: v for k, v in expected.items() if k != 'analysis_version'}, (index, axes, result)
    model.assert_not_called()
