"""Party identity excludes witness lines and ambiguous same-band gutters."""
import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r15b import block


@pytest.mark.parametrize('role', ['Witness:', 'Attest:', 'Attestation:'])
@pytest.mark.parametrize('reverse', [False, True])
def test_witness_column_never_owns_party_name(role, reverse):
    row = {'text': 'Name: Pat Smith', 'rect': [350, 312, 400, 322]}
    party = block((72, 290), row)
    witness = block((330, 548), row)
    witness.line.label['text'] = role
    witness.line.semantic = ''
    blocks = [party, witness]
    if reverse:
        blocks.reverse()
    placement.prepare_blocks(blocks, {}, PAT)
    assert party.scores == [6]
    assert witness.scores == [0]


@pytest.mark.parametrize('dy,expected', [(0, 0), (29, 0), (30, 6), (100, 6)])
@pytest.mark.parametrize('reverse', [False, True])
def test_gutter_scores_only_when_columns_are_staggered(dy, expected, reverse):
    row = {'text': 'Name: Pat Smith', 'rect': [300, 312, 310, 322]}
    left = block((72, 290), row)
    right = block((330, 548), row, y=300 + dy)
    blocks = [left, right]
    if reverse:
        blocks.reverse()
    placement.prepare_blocks(blocks, {}, PAT)
    assert left.scores == [expected]
    assert right.scores == [0]


@pytest.mark.parametrize('edges', [(304, 314), (305, 315), (306, 316), (280, 340)])
def test_tied_name_cannot_fall_back_to_company_score(edges):
    row = {'text': 'Name: Pat Smith', 'rect': [edges[0], 312, edges[1], 322]}
    blocks = [block((72, 290), row), block((330, 548), row, y=400)]
    blocks[0].heading = 'Harbor Light Analytics, Inc.'
    placement.prepare_blocks(blocks, {}, PAT)
    assert [b.scores for b in blocks] == [[0], [0]]


@pytest.mark.parametrize('edges', [(300, 350), (270, 320)])
@pytest.mark.parametrize('reverse', [False, True])
def test_name_crossing_gutter_cannot_identify_either_party(edges, reverse):
    row = {'text': 'Name: Pat Smith', 'rect': [edges[0], 312, edges[1], 322]}
    blocks = [block((72, 290), row), block((330, 548), row)]
    if reverse:
        blocks.reverse()
    placement.prepare_blocks(blocks, {}, PAT)
    assert [b.scores for b in blocks] == [[0], [0]]
