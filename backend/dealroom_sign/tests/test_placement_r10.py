"""Gate 3 r9 B-1/M-1: absorbed identities extend beyond the caption slot."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import (
    EXPECTED, FIXTURES, LEE, assert_golden, model_answer, no_network,  # noqa: F401
)
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r8 import CAPTIONS
from dealroom_sign.tests.test_placement_r9 import (
    HARBOR, HEADINGS, PARTIES, assert_identity_hold, heading_rows, rows_pdf,
)


VARIANTS = ['title_then_name', 'tab_gap', 'indented', 'caption_row_right']
CONTACTS = ['Fax', 'Mobile', 'Contact', 'Attention', 'Notice Address', 'Initials', 'Sign']
EXEMPT_CONTACTS = ['Email', 'E-mail', 'Address', 'Phone', 'Tel', 'Company']
MATCHING_SIGNERS = [('Lee Harbor', LEE), ('Pat Smith', PAT)]
DY_VALUES = [22, 24, 26, 28, 30, 34]
ROOT = Path(__file__).resolve().parents[3]


def name_rows(rule_y, name, variant):
    if variant == 'title_then_name':
        return [(rule_y + 12, 'Title:', False), (rule_y + 24, 'Name: ' + name, False)]
    if variant == 'tab_gap':
        # A Word-style tab is two text runs, not a literal PDF tab glyph.
        return [(rule_y + 12, 'Name:', False), (rule_y + 12, name, False, 150)]
    if variant == 'indented':
        return [(rule_y + 12, 'Name: ' + name, False, 110)]
    assert variant == 'caption_row_right'
    # Match the caption baseline, beyond the rule's x=290 endpoint.
    return [(rule_y - 10, name, False, 300)]


def out_of_slot_pdf(layout, heading, caption, variant=None, dy=None):
    rows = [row for row in heading_rows(layout, heading, caption) if row[1] != 'Name: Pat Smith']
    rule_y = 360 if layout == 'C12' else 375
    # Leave room for the Title-before-Name form and the complete dy sweep.
    rows = [(420, text, rule) if text == 'Date:' and layout == 'C12' else (y, text, rule)
            for y, text, rule in rows]
    rows.extend(name_rows(rule_y, 'Pat Smith', variant) if variant is not None
                else [(rule_y + dy, 'Name: Pat Smith', False)])
    return rows_pdf(rows)


def stack_out_of_slot_pdf(company, name, caption, variant):
    return rows_pdf([(250, company, False), (290, 'By:', True),
                     (360, caption, True), (395, 'Date:', True)] + name_rows(360, name, variant))


def contact_out_of_slot_pdf(label, name, variant):
    return rows_pdf([(360, HARBOR, False), (400, 'By:', True), (430, 'Date:', True),
                     (460, label + ':', True)] + name_rows(460, name, variant))


def assert_signature_control(source, layout):
    model = Mock()
    result = placement.place(source, PAT, model_client=model)
    model.assert_not_called()
    if layout == 'C12':
        assert result['status'] == 'placed', result
        assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
            ('SIGNATURE', 360, 'high'), ('DATE', 420, 'high'),
        }
        assert len(result['fields']) == 2
    else:
        assert result['status'] == 'needs_sender', result
        assert result['reason_code'] == 'ambiguous_identity', result
        assert result['fields'] == []
    return result


def assert_stack_hold(source, signers):
    model = Mock()
    result = placement.place(source, signers, model_client=model)
    assert result['status'] == 'needs_sender', result
    assert result['reason_code'] == 'ambiguous_identity', result
    assert result['fields'] == []
    model.assert_not_called()
    return result


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('layout', ['C12', 'C13'])
@pytest.mark.parametrize('variant', VARIANTS)
def test_b1_out_of_slot_identity_holds(variant, layout, heading, caption):
    assert_identity_hold(out_of_slot_pdf(layout, heading, caption, variant), PAT)


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('layout', ['C12', 'C13'])
@pytest.mark.parametrize('dy', DY_VALUES)
def test_b1_name_below_caption_holds(dy, layout, caption):
    assert_identity_hold(out_of_slot_pdf(layout, 'RECIPIENT:', caption, dy=dy), PAT)


@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('layout', ['C12', 'C13'])
@pytest.mark.parametrize('variant', VARIANTS)
def test_signature_out_of_slot_controls_unchanged(variant, layout, heading):
    assert_signature_control(out_of_slot_pdf(layout, heading, 'Signature:', variant), layout)


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('company,name,signers', PARTIES)
@pytest.mark.parametrize('variant', VARIANTS)
def test_h1_out_of_slot_stacks_still_hold(variant, company, name, signers, caption):
    assert_stack_hold(stack_out_of_slot_pdf(company, name, caption, variant), signers)


@pytest.mark.parametrize('label', CONTACTS)
@pytest.mark.parametrize('name,signers', MATCHING_SIGNERS)
@pytest.mark.parametrize('variant', VARIANTS)
def test_m1_non_exempt_contact_out_of_slot_holds(variant, name, signers, label):
    assert_identity_hold(contact_out_of_slot_pdf(label, name, variant), signers)


@pytest.mark.parametrize('label', EXEMPT_CONTACTS)
@pytest.mark.parametrize('name,signers', MATCHING_SIGNERS)
@pytest.mark.parametrize('variant', VARIANTS)
def test_six_contact_captions_remain_exempt(variant, name, signers, label):
    model = Mock()
    result = placement.place(contact_out_of_slot_pdf(label, name, variant), signers, model_client=model)
    assert result['status'] == 'placed', result
    assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
        ('SIGNATURE', 400, 'high'), ('DATE', 430, 'high'),
    }
    assert len(result['fields']) == 2
    model.assert_not_called()


@pytest.mark.parametrize('name', EXPECTED['fixtures'])
def test_seven_goldens_exact(name):
    golden = EXPECTED['fixtures'][name]
    source = (FIXTURES / (name + '.pdf')).read_bytes()
    model = Mock(side_effect=model_answer)
    result = placement.place(source, golden['signers'], model_client=model)
    if name == 'bare':
        assert result['status'] == 'bare' and result['fields'] == []
    else:
        assert_golden(result, name, golden['signers'])
    assert model.call_count == (1 if name == 'unusual' else 0)
    keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
    for revision in ('c2a-r4', 'c2a-r5'):
        previous = json.loads((ROOT / 'docs/implementation' / revision / 'placements.json').read_text())[name]
        assert result['status'] == previous['status']
        assert [{key: f[key] for key in keys} for f in result['fields']] == [
            {key: f[key] for key in keys} for f in previous['fields']
        ]
        for signer in golden['signers']:
            assert placement.to_native_fields(result, signer['email']) == placement.to_native_fields(
                previous, signer['email'])
