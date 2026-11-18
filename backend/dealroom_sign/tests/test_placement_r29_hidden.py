"""An unmatched printed name cannot resolve a different company's line."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r29_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('axes,pages,people,allowed', review.captured('hidden'))
def test_exact_hidden_shapes(axes, pages, people, allowed):
    model = Mock()
    result = in_process(placement, review.pdf(pages), people, model)
    assert not review.rc.wrong_fields(result, allowed), (axes, result)
    assert model.call_count == (1 if axes['shape'] == 'own_page'
                                and axes['head'] == 'HARBOR LIGHT ANALYTICS, INC.' else 0)
