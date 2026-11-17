"""Gate 3 r8 B-1/H-1: an absorbed caption identity must hold placement."""
import io
from unittest.mock import Mock

import pytest
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r8 import CAPTIONS


FLEET = 'FLEET TEST CO.'
HARBOR = 'HARBOR LIGHT ANALYTICS, INC.'
HEADINGS = [
    HARBOR + ', a Delaware corporation',
    HARBOR + ' (the "Recipient")',
    'RECIPIENT',
    'RECIPIENT:',
    'For and on behalf of the Recipient',
    'harbor light analytics, inc.',
]
BETWEEN = ['Title: Director', 'Title:', 'Name:', None]
PARTIES = [(HARBOR, 'Pat Smith', PAT), (FLEET, 'Dan Whaley', [TWO[1]])]


def rows_pdf(rows):
    """Rows are (top/rule y, text, rule?, optional x, optional rule end)."""
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    for y, text, rule, *position in rows:
        x = position[0] if position else 72
        end = position[1] if len(position) > 1 else x + 218
        c.drawString(x, 792 - y + (2 if rule else -8), text)
        if rule:
            start = x + 10 + c.stringWidth(text, 'Helvetica', 10)
            c.line(start, 792 - y, end, 792 - y)
    c.save()
    return out.getvalue()


def heading_rows(layout, heading, caption):
    if layout == 'C12':
        return [(260, FLEET, False), (300, 'By:', True), (330, heading, False),
                (360, caption, True), (372, 'Name: Pat Smith', False), (395, 'Date:', True)]
    assert layout == 'C13'
    return [(260, FLEET, False), (300, 'By:', True), (320, 'Date:', True),
            (345, heading, False), (375, caption, True), (387, 'Name: Pat Smith', False)]


def heading_pdf(layout, heading, caption):
    return rows_pdf(heading_rows(layout, heading, caption))


def behalf_right_pdf(caption):
    # Same caption-row baseline, beyond the rule's x=290 endpoint.
    rows = [(260, FLEET, False), (300, 'By:', True), (360, caption, True),
            (350, 'For and on behalf of ' + HARBOR, False, 300),
            (372, 'Name: Pat Smith', False), (395, 'Date:', True)]
    return rows_pdf(rows)


def stack_pdf(company, name, between, caption):
    rows = [(250, company, False), (290, 'By:', True)]
    if between is not None:
        rows.append((302, between, False))
    rows.extend([(360, caption, True), (372, 'Name: ' + name, False), (395, 'Date:', True)])
    return rows_pdf(rows)


def assert_identity_hold(source, signers):
    # Exercise the real worker and prove that a model cannot override the veto.
    model = Mock()
    result = placement.place(source, signers, model_client=model)
    assert result['status'] == 'needs_sender', result
    assert result['reason_code'] == 'ambiguous_identity', result
    assert result['fields'] == []
    model.assert_not_called()
    blocks, _, roles = placement.extract(source)
    assert len(blocks) == 1
    assert blocks[0].uncertain_identity
    placement.prepare_blocks(blocks, roles, signers)
    assert blocks[0].scores == [0]
    return result


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('layout', ['C12', 'C13'])
def test_b1_heading_variants_hold(layout, heading, caption):
    assert_identity_hold(heading_pdf(layout, heading, caption), PAT)


@pytest.mark.parametrize('caption', CAPTIONS)
def test_b1_same_row_right_behalf_holds(caption):
    assert_identity_hold(behalf_right_pdf(caption), PAT)


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('between', BETWEEN)
@pytest.mark.parametrize('company,name,signers', PARTIES)
def test_h1_stacked_signers_hold(company, name, signers, between, caption):
    assert_identity_hold(stack_pdf(company, name, between, caption), signers)


@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('layout', ['C12', 'C13'])
def test_b1_signature_controls_keep_previous_outcome(layout, heading):
    result = placement.place(heading_pdf(layout, heading, 'Signature:'), PAT)
    if layout == 'C12':
        assert result['status'] == 'placed', result
        assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
            ('SIGNATURE', 360, 'high'), ('DATE', 395, 'high'),
        }
    else:
        assert result['status'] == 'needs_sender', result
        assert result['fields'] == []


@pytest.mark.parametrize('dy,dx,uncertain', [
    (-0.1, 0, False), (0, 0, True), (21.9, 0, True), (22, 0, False),
    (12, -35, False), (12, -34.9, True), (12, 34.9, True), (12, 35, False),
])
def test_caption_identity_slot_edges(monkeypatch, dy, dx, uncertain):
    # Set exact extracted-row edges to avoid PDF font rounding at strict bounds.
    original = placement.text_rows

    def exact_name_position(words):
        rows = original(words)
        name = next(row for row in rows if row['text'] == 'Name: Pat Smith')
        x, top, right, bottom = name['rect']
        name['rect'] = [72 + dx, 360 + dy, 72 + dx + right - x, 360 + dy + bottom - top]
        return rows

    monkeypatch.setattr(placement, 'text_rows', exact_name_position)
    blocks, _, _ = placement.extract(stack_pdf(HARBOR, 'Pat Smith', None, 'Firma:'))
    host = next(block for block in blocks if block.line.y == 290)
    assert host.uncertain_identity is uncertain


def test_absorbed_identity_vetoes_every_overlapping_host():
    source = rows_pdf([
        (250, HARBOR, False), (290, 'By:', True), (300, 'By:', True, 330),
        (360, 'Firma:', True, 260), (372, 'Name: Pat Smith', False, 280),
    ])
    blocks, _, roles = placement.extract(source)
    assert [block.line.y for block in blocks] == [290, 300]
    assert all(block.uncertain_identity for block in blocks)
    placement.prepare_blocks(blocks, roles, PAT)
    assert [block.scores for block in blocks] == [[0], [0]]
    result = placement.place(source, PAT)
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == []
