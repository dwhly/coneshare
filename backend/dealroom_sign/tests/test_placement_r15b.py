"""Printed identity belongs to the uniquely nearest horizontal column."""
import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT


def block(column, row, *, page=1, y=300, labelled=True):
    left, right = column
    label = {'text': 'By:', 'rect': [left, y - 10, left + 20, y]} if labelled else {}
    line = placement.Line(page, left + 30 if labelled else left, right, y,
                          'drawn', label, 'SIGNATURE')
    return placement.Block(str((page, y, left)), line, [row], '', '', False,
                           raw_labels=[row])


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('row_edges,expected', [
    ((300, 310), [6, 0]),       # 10 pt outside our rule, but 20 pt from theirs.
    ((302, 312), [6, 0]),       # No fixed outdent tolerance.
    ((304, 314), [0, 0]),       # Distance difference exactly 2 pt.
    ((304.1, 314.1), [0, 0]),
    ((305, 315), [0, 0]),       # Equal edge distances.
    ((306, 316), [0, 0]),       # Opposite 2 pt boundary.
    ((306.1, 316.1), [0, 6]),
    ((310, 320), [0, 6]),
    ((280, 340), [0, 0]),       # Overlaps both columns.
    ((280, 329), [0, 0]),       # Overlap versus a 1 pt gap still ties.
    ((280, 327), [6, 0]),
    ((20, 60), [6, 0]),        # Outdented to the left of all columns.
])
def test_nearest_column_and_two_point_ties(row_edges, expected, reverse):
    row = {'text': 'Name: Pat Smith', 'rect': [row_edges[0], 312, row_edges[1], 322]}
    blocks = [block((72, 290), row), block((330, 548), row, y=400)]
    if reverse:
        blocks.reverse()
        expected = expected[::-1]
    placement.prepare_blocks(blocks, {}, PAT)
    assert [b.scores[0] for b in blocks] == expected


@pytest.mark.parametrize('labelled', [False, True])
def test_same_column_stacked_blocks_and_other_page_do_not_tie(labelled):
    row = {'text': 'Name: Pat Smith', 'rect': [300, 312, 310, 322]}
    blocks = [block((72, 290), row, labelled=labelled),
              block((72, 290), row, y=500, labelled=labelled),
              block((300, 520), row, page=2, labelled=labelled)]
    placement.prepare_blocks(blocks, {}, PAT)
    assert [b.scores for b in blocks] == [[6], [6], [6]]


def test_label_is_part_of_the_column_even_before_rule_start():
    row = {'text': 'Name: Pat Smith', 'rect': [73, 312, 90, 322]}
    blocks = [block((72, 290), row), block((0, 60), row, y=500)]
    placement.prepare_blocks(blocks, {}, PAT)
    assert [b.scores for b in blocks] == [[6], [0]]
