"""A separate uncaptioned ruled stack also prevents Date-band expansion."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r31_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('caption', ['', 'Signature:'])
def test_unclaimed_ruled_stack_prevents_widening(caption):
    rows = [(162, 'HARBOR LIGHT ANALYTICS, INC.', False, 72),
            (200, 'By:', True, 72, 272), (230, 'Date:', True, 72, 272),
            (260, 'Name: Pat Smith', False, 72),
            (200, caption, True, 340, 540), (230, 'Date:', True, 340, 540)]
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf([
        list(review.rc.RECITALS['parsed']), rows]),
        [dict(name='Pat Smith', email=review.rc.PE)], model)
    assert result['status'] == 'needs_sender' and not result['fields'], result
    model.assert_not_called()
