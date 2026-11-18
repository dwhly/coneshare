"""Separate Name rows require overlap even immediately beside a rule column."""
from itertools import product
from unittest.mock import Mock

import pytest
from reportlab.pdfbase.pdfmetrics import stringWidth

from dealroom_sign import placement
from dealroom_sign.tests import placement_r29_review_cases as review
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process


@pytest.mark.parametrize('side,gap,caption,explicit', list(product(
    ('left', 'right'), (1, 10, 24), ('By:', 'Signature:'), (False, True))))
def test_separate_name_row_outside_column_holds(side, gap, caption, explicit):
    text = 'Name: Pat Smith'
    column = 340 if side == 'left' else 72
    end = column + 218
    x = column - gap - stringWidth(text, 'Helvetica', 10) if side == 'left' else end + gap
    rows = [(240, 'FLEET TEST CO.', False, column),
            (270, caption, True, column, end), (310, 'Date:', True, column, end),
            (282, text, False, x)]
    signer = dict(name='Pat Smith', email=review.rc.PE)
    if explicit:
        signer['company'] = 'Harbor Light Analytics, Inc.'
    model = Mock()
    result = in_process(placement, review.rc.pages_pdf([rows]), [signer], model)
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == []
    model.assert_not_called()
