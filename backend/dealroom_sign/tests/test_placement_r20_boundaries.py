"""The unnamed-party guard respects page, witness and explicit-identity scope."""
import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement_r3 import PAT


def block(x, y, heading, *, page=1, caption='By:', name=None):
    label = {'text': caption, 'rect': [x, y - 10, x + 20, y]}
    line = placement.Line(page, x + 30, x + 180, y, 'drawn', label, 'SIGNATURE')
    rows = ([{'text': heading, 'rect': [x, y - 40, x + 150, y - 30]}]
            if heading else [])
    if name:
        rows.append({'text': 'Name: ' + name, 'rect': [x, y + 2, x + 100, y + 12]})
    return placement.Block(str((page, x, y)), line, rows, heading, '', False, raw_labels=rows)


@pytest.mark.parametrize('heading,roles,expected', [
    ('', {}, 0), ('RECIPIENT:', {}, 0), ('COMPANY:', {}, 0),
    ('For and on behalf of COMPANY', {}, 0),
    ('RECIPIENT:', {'recipient': 'For and on behalf of COMPANY'}, 0),
    ('RECIPIENT:', {'recipient': 'NORTHWIND TRADERS LLC'}, 4),
    ('NORTHWIND TRADERS LLC', {}, 4),
    ('Chris Jones', {}, 4),
])
def test_heading_is_normalized_before_identifying_other_party(heading, roles, expected):
    target = block(40, 450, 'HARBOR LIGHT GROUP, INC.')
    other = block(40, 290, heading)
    fleet = block(280, 290, 'FLEET TEST CO.')
    assert placement.score(PAT[0], target, roles, [target, other, fleet]) == expected


@pytest.mark.parametrize('control', ['two_parties', 'different_page', 'witness',
                                    'printed_other', 'explicit_company', 'printed_signer'])
def test_independent_evidence_and_party_count_controls(control):
    target = block(40, 450, 'HARBOR LIGHT GROUP, INC.',
                   name='Pat Smith' if control == 'printed_signer' else None)
    other = block(40, 290, '', page=2 if control == 'different_page' else 1,
                  caption='Witness:' if control == 'witness' else 'By:',
                  name='Chris Jones' if control == 'printed_other' else None)
    blocks = [target, other]
    if control != 'two_parties':
        blocks.append(block(280, 290, 'FLEET TEST CO.'))
    signer = dict(PAT[0])
    if control == 'explicit_company':
        signer['company'] = 'HARBOR LIGHT GROUP, INC.'
    assert placement.score(signer, target, {}, blocks) == (
        0 if control == 'different_page' else (10 if control == 'printed_signer' else 4))
