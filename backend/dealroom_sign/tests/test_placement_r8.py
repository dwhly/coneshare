"""Gate 3 r8: preserve unusual hosts and separate company identities."""
import io
from unittest.mock import Mock

import pytest
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT


CAPTIONS = ['Authorised signatory:', 'Signatory:', 'Executed by:', 'Firma:', 'Unterschrift:']
LAYOUTS = ['C4', 'C8', 'C10', 'C12', 'C13']
HOST_Y = {'C4': 380, 'C7': 400, 'C8': 290, 'C10': 380, 'C12': 360, 'C13': 375}
NEIGHBOUR_Y = {'C4': 440, 'C7': 340, 'C8': 370, 'C10': 440, 'C12': 300, 'C13': 300}


def layout_pdf(layout, caption='Authorised signatory:'):
    """Review C layouts; y denotes row tops or rules, in top-down PDF points."""
    fleet, harbor = 'FLEET TEST CO.', 'HARBOR LIGHT ANALYTICS, INC.'
    rows = {
        'C4': [(300, fleet), (380, caption, True), (392, 'Name: Dan Whaley'),
               (440, 'Witness:', True), (452, 'Name:'), (470, 'Date:', True)],
        'C7': [(300, fleet), (340, 'Witness:', True), (352, 'Name:'),
               (400, caption, True), (412, 'Name: Dan Whaley'), (430, 'Date:', True)],
        'C8': [(250, harbor), (290, caption, True), (302, 'Name: Pat Smith'),
               (316, 'Title: Director'), (340, fleet), (370, 'By:', True),
               (382, 'Name:'), (400, 'Date:', True)],
        'C10': [(300, fleet), (380, caption, True), (392, 'Name: Dan Whaley'),
                (440, 'By:', True), (452, 'Name:'), (470, 'Date:', True)],
        'C12': [(260, fleet), (300, 'By:', True), (330, harbor),
                (360, caption, True), (372, 'Name: Pat Smith'), (395, 'Date:', True)],
        'C13': [(260, fleet), (300, 'By:', True), (320, 'Date:', True),
                (345, harbor), (375, caption, True), (387, 'Name: Pat Smith')],
        'only': [(360, harbor), (400, caption, True), (430, 'Date:', True),
                 (442, 'Name: Pat Smith')],
    }[layout]
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    for y, text, *rule in rows:
        c.drawString(72, 792 - y + (2 if rule else -8), text)
        if rule:
            x = 82 + c.stringWidth(text, 'Helvetica', 10)
            c.line(x, 792 - y, 290, 792 - y)
    c.save()
    return out.getvalue()


def layout_signers(layout):
    return [TWO[1]] if layout in {'C4', 'C7', 'C10'} else PAT


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('layout', LAYOUTS)
def test_b1_unusual_host_never_places_on_neighbour(layout, caption):
    source = layout_pdf(layout, caption)
    result = placement.place(source, layout_signers(layout))
    assert result['status'] == 'needs_sender', result
    assert result['reason_code'] in {'ambiguous_identity', 'model_not_configured'}
    assert result['fields'] == []
    blocks, _, _ = placement.extract(source)
    assert HOST_Y[layout] in [b.line.y for b in blocks]


@pytest.mark.parametrize('layout', LAYOUTS)
def test_b1_signature_controls_keep_previous_outcome(layout):
    result = placement.place(layout_pdf(layout, 'Signature:'), layout_signers(layout))
    if layout == 'C12':
        assert result['status'] == 'placed', result
        assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
            ('SIGNATURE', 360, 'high'), ('DATE', 395, 'high'),
        }
    else:
        assert result['status'] == 'needs_sender', result
        assert result['fields'] == []


@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('layout', ['C8', 'C12', 'C13'])
def test_second_company_holds_without_subordinate_rule(monkeypatch, layout, caption):
    # Recreate r7 classification while leaving the independent identity check on.
    monkeypatch.setattr(placement, 'subordinate_caption', lambda *args: True, raising=False)
    source = layout_pdf(layout, caption)
    blocks, sizes, roles = placement.extract(source)
    assert [b.line.y for b in blocks] == [NEIGHBOUR_Y[layout]]
    assert blocks[0].uncertain_identity
    placement.prepare_blocks(blocks, roles, PAT)
    assert blocks[0].scores == [0]
    monkeypatch.setattr(placement, 'bounded_extract', lambda *args: (blocks, sizes, roles))
    model = Mock()
    result = placement.place(source, PAT, model_client=model)
    assert result['status'] == 'needs_sender', result
    assert result['reason_code'] == 'ambiguous_identity'
    assert result['fields'] == []
    model.assert_not_called()


def confirming_model(payload):
    # Confirm the candidate containing the requested printed identity, just as
    # the r7 single Witness candidate did. Never invent candidate geometry.
    candidate = next(c for c in payload['candidates'] if any(
        row['text'] == 'Name: ' + payload['signers'][0]['name'] for row in c['labels']
    ))
    own_label = next(row['text'] for row in candidate['labels']
                     if abs(row['rect'][3] - candidate['line'][1]) < 3)
    return {'assignments': [{'signer': payload['signers'][0]['id'], 'block_id': candidate['id'],
                             'confidence': 'high', 'evidence': own_label}]}


@pytest.mark.parametrize('caption', CAPTIONS)
def test_m1_c7_keeps_400_candidate_and_never_places_on_witness(caption):
    model = Mock(side_effect=confirming_model)
    source = layout_pdf('C7', caption)
    result = placement.place(source, layout_signers('C7'), model_client=model)
    assert not any(f['type'] == 'SIGNATURE' and f['evidence']['line'][1] == 340
                   for f in result['fields']), result
    blocks, _, _ = placement.extract(source)
    assert {b.line.y for b in blocks} == {340, 400}
    assert model.call_count == 1
    assert {c['line'][1] for c in model.call_args.args[0]['candidates']} == {340, 400}
    assert result['status'] == 'placed', result
    assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
        ('SIGNATURE', 400, 'model-high'), ('DATE', 430, 'model-high'),
    }


def test_l1_only_authorised_signatory_uses_model_on_its_own_line():
    model = Mock(side_effect=confirming_model)
    result = placement.place(layout_pdf('only'), PAT, model_client=model)
    assert result['status'] == 'placed', result
    assert model.call_count == 1
    assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
        ('SIGNATURE', 400, 'model-high'), ('DATE', 430, 'model-high'),
    }


def test_n1_no_fixture_caption_constant():
    assert not hasattr(placement, 'MODEL_SIGNATURE_CAPTION')


@pytest.mark.parametrize('gap,column,host_text,semantic,expected', [
    (5, 72, 'By:', 'SIGNATURE', False),
    (5.1, 72, 'By:', 'SIGNATURE', True),
    (125, 72, 'By:', 'SIGNATURE', True),
    (125.1, 72, 'By:', 'SIGNATURE', False),
    (-30, 72, 'By:', 'SIGNATURE', False),
    (60, 320, 'By:', 'SIGNATURE', False),
    (60, 72, 'Date:', 'DATE', False),
    (60, 72, 'Witness:', '', True),
])
def test_subordinate_caption_host_band_and_distance(gap, column, host_text, semantic, expected):
    host = placement.Line(1, 110, 290, 400, 'drawn',
                          {'text': host_text, 'rect': [72, 390, 105, 400]}, semantic)
    caption = placement.Line(1, column + 110, column + 218, 400 + gap, 'drawn',
                             {'text': 'Firma:', 'rect': [column, 390 + gap, column + 100, 400 + gap]})
    assert placement.subordinate_caption(caption, [host, caption], [], {}) is expected


@pytest.mark.parametrize('heading', [
    'HARBOR LIGHT ANALYTICS, INC.',
    'Signed for and on behalf of HARBOR LIGHT ANALYTICS, INC.',
    'Name: Pat Smith',
    'Receiving Party:',
])
def test_subordinate_caption_cannot_cross_identity_heading(heading):
    host = placement.Line(1, 110, 290, 400, 'drawn',
                          {'text': 'By:', 'rect': [72, 390, 105, 400]}, 'SIGNATURE')
    caption = placement.Line(1, 180, 290, 460, 'drawn',
                             {'text': 'Firma:', 'rect': [72, 450, 175, 460]})
    row = {'text': heading, 'rect': [72, 420, 270, 430]}
    assert not placement.subordinate_caption(caption, [host, caption], [row],
                                             {'receiving party': 'HARBOR LIGHT ANALYTICS, INC.'})


@pytest.mark.parametrize('caption', ['Email:', 'E-mail:', 'Address:', 'Phone:', 'Tel:', 'Company:'])
def test_contact_vocabulary_is_other_without_preceding_host(caption):
    result = placement.place(layout_pdf('only', caption), PAT)
    assert result['status'] == 'bare', result
    assert result['fields'] == []
