"""Aligned signature rules remain one column when their lengths differ."""
import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r15b import block


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('labelled', [False, True])
def test_aligned_rule_lengths_share_column(reverse, labelled):
    row = {'text': 'Name: Pat Smith', 'rect': [300, 312, 310, 322]}
    blocks = [block((72, 290), row, labelled=labelled),
              block((72, 320), row, y=500, labelled=labelled),
              block((330, 548), row, y=600, labelled=labelled)]
    if reverse:
        blocks.reverse()
    placement.prepare_blocks(blocks, {}, PAT)
    assert [b.scores for b in blocks] == ([[0], [6], [6]] if reverse else [[6], [6], [0]])
