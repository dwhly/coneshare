"""A named role must have an unambiguous block before domain-only placement."""
import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement_r20_boundaries import block
from dealroom_sign.tests.test_placement_r3 import PAT


@pytest.mark.parametrize('heading', ['RECIPIENT:', 'THE RECIPIENT'])
@pytest.mark.parametrize('page', [1, 2])
@pytest.mark.parametrize('peer_name,expected', [(None, 0), ('Chris Jones', 4)])
def test_duplicate_named_role_requires_independent_identity(heading, page, peer_name, expected):
    target = block(40, 450, 'HARBOR LIGHT GROUP, INC.')
    other = block(40, 290, heading)
    peer = block(280, 290, 'NORTHWIND TRADERS LLC', page=page, name=peer_name)
    roles = {heading.rstrip(': ').lower(): 'NORTHWIND TRADERS LLC'}
    assert placement.score(PAT[0], target, roles, [target, other, peer]) == expected
