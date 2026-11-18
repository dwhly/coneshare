"""Text-drawn signing rules also compete across pages in the widened band."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r32_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('own_first', [False, True])
def test_better_unclaimed_underscore_block_vetoes_expansion(own_first):
    role = [(162, 'RECIPIENT:', False, 72), (200, 'By:', True, 72, 272),
            (230, 'Date:', True, 72, 272), (260, 'Name: Pat Smith', False, 72)]
    own = [(162, 'HARBOR LIGHT ANALYTICS, INC.', False, 72),
           (200, 'By: _________________________', False, 72),
           (230, 'Date: _______________________', False, 72)]
    pages = [list(review.rc.RECITALS['parsed']), *([own, role] if own_first else [role, own])]
    person = dict(name='Pat Smith', email=review.rc.PE, company='Harbor Light Analytics, Inc.')
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf(pages), [person], model)
    assert result['status'] == 'needs_sender' and not result['fields'], result
    model.assert_not_called()
