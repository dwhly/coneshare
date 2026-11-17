"""Gate 3 r10 B-1/M-1: absorbed identities belong to their subordinating host."""
import io
from unittest.mock import Mock

import pytest
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r8 import CAPTIONS
from dealroom_sign.tests.test_placement_r9 import (
    FLEET, HARBOR, HEADINGS, heading_rows, rows_pdf,
)
from dealroom_sign.tests.test_placement_r10 import assert_signature_control, assert_stack_hold


FORMS = (
    [f'baseline_{size}_{prefix}' for size in (13, 14, 16, 18) for prefix in ('plain', 'name')]
    + [f'raised_{dy}' for dy in (13, 16, 19, 22, 25, 28)]
    + ['indented_12', 'indented_24', 'margin']
)
CROSS_CAPTIONS = ['Initials:', 'Fax:', 'Authorised signatory:', 'Firma:']
CROSS_LAYOUTS = ['stacked_both', 'stacked_pat', 'side_below', 'side_above']


def host_extent_pdf(layout, heading, caption, form):
    rows = [row for row in heading_rows(layout, heading, caption) if row[1] != 'Name: Pat Smith']
    rule_y = 360 if layout == 'C12' else 375
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    for y, text, rule in rows:
        if text == 'Date:' and layout == 'C12':
            y = 420
        x = 150 if text == caption and form.startswith('indented_') else 72
        c.drawString(x, 792 - y + (2 if rule else -8), text)
        if rule:
            c.line(x + 10 + c.stringWidth(text, 'Helvetica', 10), 792 - y, x + 218, 792 - y)
    name, size, x = 'Pat Smith', 10, 300
    if form.startswith('baseline_'):
        _, size, prefix = form.split('_')
        size = int(size)
        if prefix == 'name':
            name = 'Name: ' + name
        baseline = rule_y - 2
    elif form.startswith('raised_'):
        # Helvetica's top is 0.793 * font size above the baseline: exact dy.
        baseline = rule_y - int(form.split('_')[1]) + 0.793 * size
    else:
        x = 20 if form == 'margin' else 72
        dy = 12 if form == 'margin' else int(form.split('_')[1])
        baseline = rule_y + dy + 8
    c.setFont('Helvetica', size)
    c.drawString(x, 792 - baseline, name)
    c.save()
    return out.getvalue()


def cross_host_pdf(layout, caption):
    rows = [(160, FLEET, False), (200, 'By:', True),
            (230, caption, True), (260, 'Date:', True)]
    if layout.startswith('stacked_'):
        rows += [(340, HARBOR, False), (370, 'By:', True),
                 (382, 'Name: Pat Smith', False), (410, 'Date:', True)]
    else:
        rows += [(160, HARBOR, False, 330), (200, 'By:', True, 330),
                 (260, 'Date:', True, 330)]
        if layout == 'side_below':
            rows += [(212, 'Title:', False, 330), (244, 'Name: Pat Smith', False, 330)]
        else:
            rows += [(212, 'Name: Pat Smith', False, 330)]
    return rows_pdf(rows)


def assert_cross_host_placement(layout, caption):
    signers = PAT if layout == 'stacked_pat' else [TWO[1], *PAT]
    model = Mock()
    result = placement.place(cross_host_pdf(layout, caption), signers, model_client=model)
    assert result['status'] == 'placed', result
    pat_y = (370, 410) if layout.startswith('stacked_') else (200, 260)
    expected = {(PAT[0]['email'], 'SIGNATURE', pat_y[0], 'high'),
                (PAT[0]['email'], 'DATE', pat_y[1], 'high')}
    if layout != 'stacked_pat':
        expected |= {(TWO[1]['email'], 'SIGNATURE', 200, 'high'),
                     (TWO[1]['email'], 'DATE', 260, 'high')}
    assert {(f['signer'], f['type'], f['evidence']['line'][1], f['confidence'])
            for f in result['fields']} == expected
    assert len(result['fields']) == len(expected)
    for field in result['fields']:
        right_column = layout.startswith('side_') and field['signer'] == PAT[0]['email']
        assert field['evidence']['line'][0] > 330 if right_column else field['evidence']['line'][0] < 150
    model.assert_not_called()
    return result


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('layout', ['C12', 'C13'])
@pytest.mark.parametrize('form', FORMS)
def test_b1_identity_inside_subordinating_host_holds(form, layout, heading, caption):
    assert_stack_hold(host_extent_pdf(layout, heading, caption, form), PAT)


@pytest.mark.parametrize('caption', CROSS_CAPTIONS)
@pytest.mark.parametrize('layout', CROSS_LAYOUTS)
def test_m1_other_host_keeps_its_own_identity(layout, caption):
    assert_cross_host_placement(layout, caption)


@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('layout', ['C12', 'C13'])
@pytest.mark.parametrize('form', FORMS)
def test_signature_host_extent_controls_unchanged(form, layout, heading):
    source = host_extent_pdf(layout, heading, 'Signature:', form)
    # On r10, raised/large names tie both hosts; an indented signature lacks
    # its Date companion. Only C12's margin form places among these new forms.
    if layout == 'C12' and form == 'margin':
        assert_signature_control(source, layout)
    else:
        assert_stack_hold(source, PAT)


def test_subordinating_rule_without_block_keeps_identity_veto():
    source = rows_pdf([
        (290, 'Witness:', True), (300, 'By:', True, 330),
        (360, 'Firma:', True, 260), (372, 'Name: Pat Smith', False, 280),
    ])
    blocks, _, roles = placement.extract(source)
    assert [block.line.y for block in blocks] == [300]
    assert blocks[0].uncertain_identity
    placement.prepare_blocks(blocks, roles, PAT)
    assert blocks[0].scores == [0]
    assert_stack_hold(source, PAT)
