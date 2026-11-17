"""Gate 3 r12: an absorbed caption includes both its label and its rule."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r8 import CAPTIONS
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR, rows_pdf
from dealroom_sign.tests.test_placement_r10 import assert_stack_hold
from dealroom_sign.tests.test_placement_r12 import HEADINGS


SHORT_CAPTIONS = ['Firma:', 'Fax:', 'Sign:', 'Initials:', 'Signatory:', 'Unterschrift:']
TOP_VARIANTS = ['left_only', 'fleet_right', 'recipient_between']


def same_band_rows(caption, caption_x, right_x, dy, top, name='Name: Pat Smith'):
    rows = [(250, FLEET, False), (290, 'By:', True), (290 + dy, 'By:', True, right_x)]
    if top == 'fleet_right':
        rows.append((250, FLEET, False, right_x))
    elif top == 'recipient_between':
        rows.append((335, 'RECIPIENT:', False))
    else:
        assert top == 'left_only'
    return rows + [(360, caption, True, caption_x), (372, name, False, right_x + 10),
                   (400, 'Date:', True, right_x)]


def reproduction_pdf():
    return rows_pdf([
        (250, FLEET, False), (250, FLEET, False, 330),
        (290, 'By:', True), (290, 'By:', True, 330),
        (335, 'RECIPIENT:', False), (360, 'Firma:', True, 260),
        (372, 'Name: Pat Smith', False, 340), (400, 'Date:', True, 330),
    ])


def short_rule_pdf(caption_x):
    # L-1: the label AND rule stop before the right block's left edge (290).
    # Pat's printed name is exclusively under the FLEET-headed right column.
    rows = same_band_rows('Firma:', caption_x, 330, 0, 'fleet_right')
    rows = [(360, 'Firma:', True, caption_x, 285) if row[1] == 'Firma:' else row
            for row in rows]
    return rows_pdf(rows + [(335, 'RECIPIENT:', False)])


def own_company_pdf(caption, heading):
    # L-2: Matrix 1 followed by a separate line for Pat's own company.
    return rows_pdf([
        (240, FLEET, False), (270, 'By:', True), (310, 'By:', True),
        (340, heading, False), (370, caption, True), (382, 'Name: Pat Smith', False),
        (420, 'Date:', True), (520, HARBOR, False), (560, 'By:', True),
        (600, 'Date:', True),
    ])


def assert_pat_placement(source, signature_y, date_y, right_column=False):
    model = Mock()
    result = placement.place(source, PAT, model_client=model)
    assert result['status'] == 'placed', result
    assert len(result['fields']) == 2
    assert {(field['signer'], field['type'], field['evidence']['line'][1], field['confidence'])
            for field in result['fields']} == {
                (PAT[0]['email'], 'SIGNATURE', signature_y, 'high'),
                (PAT[0]['email'], 'DATE', date_y, 'high'),
            }
    for field in result['fields']:
        assert (field['evidence']['line'][0] > 330) == right_column
    model.assert_not_called()
    return result


def test_b1_review_reproduction_holds():
    assert_stack_hold(reproduction_pdf(), PAT)


@pytest.mark.parametrize('caption', [*CAPTIONS, 'Fax:', 'Sign:'])
@pytest.mark.parametrize('caption_x', [150, 200, 260])
@pytest.mark.parametrize('dy', [0, 20])
def test_same_band_caption_label_and_rule_hold(caption, caption_x, dy):
    source = rows_pdf(same_band_rows(caption, caption_x, 330, dy, 'fleet_right'))
    assert_stack_hold(source, PAT)


@pytest.mark.parametrize('caption', SHORT_CAPTIONS)
@pytest.mark.parametrize('caption_x', [200, 230, 260, 280])
@pytest.mark.parametrize('right_x', [300, 330, 360])
@pytest.mark.parametrize('dy', [0, 20])
@pytest.mark.parametrize('top', TOP_VARIANTS)
@pytest.mark.parametrize('name', ['Pat Smith', 'Name: Pat Smith'])
def test_b1_short_caption_sweep_holds(caption, caption_x, right_x, dy, top, name):
    source = rows_pdf(same_band_rows(caption, caption_x, right_x, dy, top, name))
    assert_stack_hold(source, PAT)


@pytest.mark.parametrize('caption_x', [150, 200])
def test_l1_name_outside_absorbed_rule_preserves_printed_name_policy(caption_x):
    assert_pat_placement(short_rule_pdf(caption_x), 290, 400, right_column=True)


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('both_signers', [False, True])
def test_l2_separate_own_company_line_preserves_scoring(caption, heading, both_signers):
    source = own_company_pdf(caption, heading)
    if both_signers:
        assert_stack_hold(source, [TWO[1], *PAT])
    else:
        result = assert_pat_placement(source, 560, 600)
        assert result['assignments'][0]['score'] == 4
        assert result['assignments'][0]['margin'] == 4
