"""Thirty-six HLA + NORTHWIND probes with neutral signer placeholders."""
from itertools import product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r21_review_cases as rc
from dealroom_sign.tests.placement_r22_review_cases import HLA, NW
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process
from dealroom_sign.tests.test_placement_r17 import signers


PROBES = list(product(('same', 'guarantor', 'split'), ('RECIPIENT:', 'Recipient'),
                      ('none', 'placeholders', 'underscores'), (False, True)))


@pytest.mark.parametrize('layout,heading,extra,both', PROBES)
def test_conflicting_recitals_hold_all_signature_layouts(layout, heading, extra, both):
    pages, allowed = rc.layout_pages(layout, 'none', heading, extra, 'group')
    allowed = {k: (p + 1, x, y, end) for k, (p, x, y, end) in allowed.items()}
    model = Mock()
    result = in_process(placement, rc.pages_pdf([HLA, NW, *pages[1:]]), signers(both), model)
    assert not rc.wrong_fields(result, allowed), result
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()
