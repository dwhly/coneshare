"""A shared domain token does not override the signer's mapped company."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r31_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('name,email,heading', [
    ('Pat Smith', review.rc.PE, 'HARBOR LIGHT GROUP, INC.'),
    ('Dan Whaley', review.rc.DE, 'FLEET HOLDINGS, LLC'),
])
def test_recital_party_prevents_adoption_by_affiliate(name, email, heading):
    rows = [(162, heading, False, 72), (200, 'By:', True, 72, 272),
            (230, 'Date:', True, 72, 272), (260, 'Name: ' + name, False, 72)]
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf([
        list(review.rc.RECITALS['parsed']), rows]), [dict(name=name, email=email)], model)
    assert result['status'] == 'needs_sender' and not result['fields'], result
    model.assert_not_called()
