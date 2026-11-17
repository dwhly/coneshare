"""Gate 3 r5: confidence-removing identity walks and conservative annotation handling."""
import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, TextStringObject, DecodedStreamObject
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import EXPECTED, FIXTURES, LEE, TWO, model_answer, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT, extent_pdf
from dealroom_sign.tests.test_placement_r4 import harbor_variant


def distant_identity_pdf(distance=150, *, barrier=None, below=False, split=None):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    if split == 'above':
        c.drawString(72, 100, 'LEE HARBOR')
        c.drawString(72, 50, 'HARBOR LIGHT ANALYTICS, INC.')
        c.showPage()
        c.setFont('Helvetica', 10)
        y = 140
    else:
        y = 700 if split == 'below' else 400
        c.drawString(72, 792 - y + 40, 'HARBOR LIGHT ANALYTICS, INC.')
    c.drawString(72, 792 - y + 2, 'By:')
    c.line(100, 792 - y, 290, 792 - y)
    if below or split == 'below':
        c.drawString(320, 792 - y + 2, 'Date:')
        c.line(350, 792 - y, 510, 792 - y)
        c.drawString(72, 792 - y - 30, 'Title: COO')
    else:
        c.drawString(72, 792 - y - 38, 'Date:')
        c.line(110, 792 - y - 40, 290, 792 - y - 40)
    if split == 'below':
        c.showPage()
        c.setFont('Helvetica', 10)
        c.drawString(72, 750, 'Name: Lee Harbor')
    elif not split:
        name_y = y + distance if below else y - distance
        c.drawString(72, 792 - name_y - 8, 'LEE HARBOR')
        if barrier == 'prose':
            c.drawString(72, 792 - y + 135, 'The parties agree to the terms of this agreement.')
        elif barrier == 'rule':
            c.drawString(72, 792 - y + 112, 'Signature:')
            c.line(130, 792 - y + 110, 290, 792 - y + 110)
            c.drawString(72, 792 - y + 92, 'Date:')
            c.line(110, 792 - y + 90, 290, 792 - y + 90)
    c.save()
    return out.getvalue()


def assert_held(result):
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == []
    assert all(a['confidence'] != 'high' for a in result['assignments'])


@pytest.mark.parametrize('distance', [100, 150, 200])
def test_b1_far_heading_vetoes_company_only(distance):
    assert_held(placement.place(distant_identity_pdf(distance), PAT))


@pytest.mark.parametrize('distance', [150, 200])
def test_b1_far_caption_vetoes_company_only(distance):
    assert_held(placement.place(distant_identity_pdf(distance, below=True), PAT))


@pytest.mark.parametrize('barrier', ['prose', 'rule'])
def test_b1_walk_stops_at_prose_or_other_rule(barrier):
    result = placement.place(distant_identity_pdf(200, barrier=barrier), PAT)
    assert result['status'] == 'placed', result
    assert next(f for f in result['fields'] if f['type'] == 'SIGNATURE')['evidence']['line'][1] == 400


@pytest.mark.parametrize('split', ['above', 'below'])
def test_b1_walk_crosses_page_edge(split):
    assert_held(placement.place(distant_identity_pdf(split=split), PAT))


@pytest.mark.parametrize('kwargs', [{'distance': 100}, {'distance': 150}, {'distance': 200},
                                    {'below': True}, {'split': 'above'}, {'split': 'below'}])
def test_b1_distant_name_never_adds_confidence(kwargs):
    result = placement.place(distant_identity_pdf(**kwargs), LEE)
    assert result['status'] != 'placed'
    assert result['fields'] == []


@pytest.mark.parametrize('name', list(EXPECTED['fixtures']))
def test_b1_all_seven_goldens_exact(name):
    baseline = json.loads((Path(__file__).resolve().parents[3] /
                           'docs/implementation/c2a-r4/placements.json').read_text())[name]
    signers = EXPECTED['fixtures'][name]['signers']
    result = placement.place((FIXTURES / (name + '.pdf')).read_bytes(), signers,
                             model_client=model_answer if name == 'unusual' else None)
    assert result['status'] == baseline['status']
    keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
    assert [{k: f[k] for k in keys} for f in result['fields']] == [
        {k: f[k] for k in keys} for f in baseline['fields']]
    for signer in signers:
        assert placement.to_native_fields(result, signer['email']) == placement.to_native_fields(baseline, signer['email'])


def annotation_pdf(kind='Widget', value='Lee Harbor', *, parent=None, appearance=None, other_page=False):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 490, 'HARBOR LIGHT ANALYTICS, INC.')
    c.drawString(72, 450, 'By:')
    c.line(100, 448, 290, 448)
    c.drawString(72, 425, 'Name:')
    c.drawString(72, 390, 'Date:')
    c.line(110, 388, 290, 388)
    if other_page:
        c.showPage()
        c.setFont('Helvetica', 10)
    if kind == 'Widget':
        c.acroForm.textfield(name='name', x=110, y=418, width=180, height=20, value=value)
    elif kind == 'Link':
        c.linkURL('https://example.test', (110, 418, 290, 438))
    c.showPage()
    c.save()
    writer = PdfWriter(clone_from=io.BytesIO(out.getvalue()))
    page = writer.pages[-1]
    if kind not in {'Widget', 'Link'}:
        page[NameObject('/Annots')] = ArrayObject([writer._add_object(DictionaryObject({
            NameObject('/Subtype'): NameObject('/' + kind),
            NameObject('/Contents'): TextStringObject('Lee Harbor'),
        }))])
    annotation = page['/Annots'][0].get_object()
    if parent is not None:
        grandparent = DictionaryObject({NameObject('/V'): TextStringObject(parent)})
        annotation[NameObject('/Parent')] = writer._add_object(DictionaryObject({
            NameObject('/Parent'): writer._add_object(grandparent)}))
    if appearance is not None:
        stream = DecodedStreamObject()
        stream.set_data(appearance)
        annotation[NameObject('/AP')] = DictionaryObject({NameObject('/N'): writer._add_object(stream)})
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize('kwargs', [
    {}, {'other_page': True}, {'value': '', 'parent': 'Lee Harbor'},
    {'value': '', 'appearance': b'BT (Lee Harbor) Tj ET'},
    {'value': '', 'appearance': b'/X1 Do'},
    {'kind': 'FreeText'}, {'kind': 'Stamp'}, {'kind': 'Ink'},
    {'kind': 'Text', 'appearance': b'BT (Lee Harbor) Tj ET'},
    {'kind': 'Link', 'appearance': b'BT (Lee Harbor) Tj ET'},
])
def test_b2_annotations_hold_entire_document(kwargs, caplog):
    model = Mock()
    result = placement.place(annotation_pdf(**kwargs), PAT, model_client=model)
    assert_held(result)
    assert result['reason_code'] == 'form_fields'
    assert result['reason'] == 'Form fields or annotations require placement review. Nothing was sent.'
    assert 'Lee Harbor' not in json.dumps(result) + caplog.text
    model.assert_not_called()


@pytest.mark.parametrize('kwargs', [{'value': ''}, {'value': '', 'parent': ''}, {'kind': 'Link'}])
def test_b2_proven_empty_widget_and_plain_link_keep_placement(kwargs):
    result = placement.place(annotation_pdf(**kwargs), PAT)
    assert result['status'] == 'placed', result


def exact_harbor(result):
    baseline = json.loads((Path(__file__).resolve().parents[3] /
                           'docs/implementation/c2a-r4/placements.json').read_text())['harbor']
    assert result['status'] == 'placed', result
    assert placement.to_native_fields(result, LEE[0]['email']) == placement.to_native_fields(baseline, LEE[0]['email'])
    keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
    assert [{k: f[k] for k in keys} for f in result['fields']] == [
        {k: f[k] for k in keys} for f in baseline['fields']]


NEW_TITLES = ['Co-Founder', 'CEO & Co-Founder', 'Vice-President', 'Chairman', 'Chair',
              'Attorney', 'Consultant', 'Chief of Staff', 'Account Executive', 'Sole Proprietor']


@pytest.mark.parametrize('title', NEW_TITLES)
@pytest.mark.parametrize('caption', ['Title:', 'Its:', 'suffix'])
def test_h1_title_wording_keeps_exact_golden(title, caption):
    pdf = harbor_variant(title=title) if caption == 'suffix' else harbor_variant(wording=caption + ' ' + title)
    exact_harbor(placement.place(pdf, LEE))


@pytest.mark.parametrize('prefix', ['Signed ', 'Signed by LEE HARBOR ', '', 'by LEE HARBOR '])
def test_h1_behalf_wording_keeps_exact_golden(prefix):
    wording = prefix + 'for and on behalf of HARBOR LIGHT ANALYTICS LIMITED'
    exact_harbor(placement.place(harbor_variant(wording=wording), LEE))


def test_h1_behalf_other_person_vetoes_named_signer():
    pdf = harbor_variant(wording='Signed by DAN WHALEY for and on behalf of HARBOR LIGHT ANALYTICS LIMITED')
    assert_held(placement.place(pdf, LEE))


@pytest.mark.parametrize('named', [False, True])
def test_h1_wrapped_sentence_is_not_a_name_but_blocks_company_only(named):
    pdf = harbor_variant(wording='Effective Date.') if named else extent_pdf('format:Effective Date.')
    result = placement.place(pdf, LEE if named else PAT)
    if named:
        exact_harbor(result)
    else:
        assert_held(result)


@pytest.mark.parametrize('wording,placed', [('Title: Lee Harbor', False), ('Title: Co-Founder', True),
                                          ('Title: unfamiliar occupation', False)])
def test_h1_company_only_title_rules_stay_strict(wording, placed):
    result = placement.place(extent_pdf('format:' + wording), PAT)
    if placed:
        assert result['status'] == 'placed', result
    else:
        assert_held(result)


@pytest.mark.parametrize('wording,placed', [('Title: Lee Harbor', False), ('Its: Pat Smith', False),
    ('Title: unfamiliar occupation', True), ('Title: Chief of Partnerships', True)])
def test_h1_positive_name_title_remainder_predicate(wording, placed):
    result = placement.place(harbor_variant(wording=wording), LEE)
    if placed:
        exact_harbor(result)
    else:
        assert_held(result)


CAPTIONS = ['Name and Title:', 'Name & Title:', 'Name (print):', 'Name (printed):', 'Name of Signatory:',
            'Name and Title: Lee Harbor, CEO', 'Name (printed): Lee Harbor',
            'Name: ________ Title: ________']


@pytest.mark.parametrize('wording', CAPTIONS)
def test_m1_compound_name_caption_keeps_exact_golden(wording):
    result = placement.place(harbor_variant(wording=wording), LEE)
    if '________' in wording:
        # This variant adds an actual blank Name rule. Preserve its existing
        # companion behavior and require the original signature/date to be exact.
        names = [f for f in result['fields'] if f['type'] == 'NAME']
        assert len(names) == 1
        assert names[0]['confidence'] == 'high'
        result = dict(result, fields=[f for f in result['fields'] if f['type'] != 'NAME'])
    exact_harbor(result)


def test_m1_compound_caption_keeps_mismatched_person_veto():
    assert_held(placement.place(extent_pdf('format:Name and Title: Lee Harbor, CEO'), PAT))


def headings_side_pdf(gap):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    for y, name in [(400, 'DAN WHALEY'), (400 + gap, 'LEE HARBOR')]:
        c.drawString(72, 792 - y + 20, name)
        c.drawString(72, 792 - y + 2, 'Signature:')
        c.line(130, 792 - y, 290, 792 - y)
        c.drawString(320, 792 - y + 2, 'Date:')
        c.line(350, 792 - y, 510, 792 - y)
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('gap', [80, 110])
@pytest.mark.parametrize('own_names', [True, False])
def test_m2_stacked_headings_with_side_dates(gap, own_names):
    result = placement.place(headings_side_pdf(gap), TWO if own_names else PAT)
    if not own_names:
        assert_held(result)
        return
    assert result['status'] == 'placed', result
    assert len(result['fields']) == 4
    for field in result['fields']:
        y = 400 + gap if field['signer'] == LEE[0]['email'] else 400
        assert field['evidence']['line'][1] == y
        assert field['confidence'] == 'high'


@pytest.mark.parametrize('label', ['Email', 'Address', 'Phone', 'Company', 'Witness'])
@pytest.mark.parametrize('filled', [False, True])
def test_l1_empty_contact_labels_only_are_accounted(label, filled):
    result = placement.place(extent_pdf('format:' + label + ':' + (' Lee Harbor' if filled else '')), PAT)
    if filled:
        assert_held(result)
    else:
        assert result['status'] == 'placed', result


def test_l2_single_typed_row_signature_and_date():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 490, 'Lee Harbor')
    c.drawString(72, 450, 'Signature: ____________________ Date: ____________________')
    c.save()
    result = placement.place(out.getvalue(), LEE)
    assert result['status'] == 'placed', result
    assert {f['type'] for f in result['fields']} == {'SIGNATURE', 'DATE'}


@pytest.mark.parametrize('name', ['Cho Cao', 'Cao Coo', 'Coo Cho'])
def test_n1_mixed_case_role_shaped_names_veto_company_only(name):
    assert_held(placement.place(extent_pdf('format:' + name), PAT))


@pytest.mark.parametrize('role', ['CEO', 'COO', 'CFO', 'CHRO', 'VP', 'SVP', 'EVP'])
def test_n1_uppercase_role_abbreviations_remain_accounted(role):
    assert placement.place(extent_pdf('format:Title: ' + role), PAT)['status'] == 'placed'


def test_n2_partition_preserves_independent_uncertainty():
    # A boundary flag set by another pair must survive a later successful partition.
    def label(text, top):
        return {'text': text, 'rect': [72, top, 250, top + 10]}
    previous = placement.Block('p', placement.Line(1, 130, 290, 400, 'drawn', label('By:', 390)),
                               [], 'Dan Whaley', '', False)
    previous.extras['DATE'] = placement.Line(1, 110, 290, 440, 'drawn', label('Date:', 430))
    following = placement.Block('n', placement.Line(1, 130, 290, 510, 'drawn', label('By:', 500)),
                                [], 'Lee Harbor', '', False, uncertain_identity=True)
    texts = [label('Dan Whaley', 375), label('Lee Harbor', 485)]
    previous.raw_labels = following.raw_labels = texts.copy()
    placement.partition_stacked_blocks([previous, following], texts, {})
    assert following.uncertain_identity


@pytest.mark.parametrize('named', [False, True])
def test_h1_execution_clause_is_a_heading(named):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 9)
    clause = 'Signed ' + ('by LEE HARBOR ' if named else '') + 'for and on behalf of HARBOR LIGHT ANALYTICS LIMITED'
    c.drawString(72, 490, clause)
    c.drawString(72, 450, 'By:')
    c.line(100, 448, 290, 448)
    c.drawString(72, 410, 'Date:')
    c.line(110, 408, 290, 408)
    c.save()
    result = placement.place(out.getvalue(), LEE if named else PAT)
    assert result['status'] == 'placed', result
    blocks, _, _ = placement.extract(out.getvalue())
    assert blocks[0].heading == clause
    if named:
        assert_held(placement.place(out.getvalue(), PAT))


@pytest.mark.parametrize('name', ['Lee Harbor Jr.', 'Lee Harbor Sr.', 'Lee Harbor Esq.', 'Lee H.'])
def test_h1_sentence_rule_retains_name_suffixes_and_initials(name):
    assert placement.person_text(name) == name


@pytest.mark.parametrize('state', ['absent_value', 'missing_reference', 'parent_cycle', 'parent_appearance', 'appearance_states'])
def test_b2_unproven_empty_widget_holds(state):
    writer = PdfWriter(clone_from=io.BytesIO(annotation_pdf(value='')))
    annotation = writer.pages[0]['/Annots'][0].get_object()
    if state == 'absent_value':
        del annotation['/V']
    elif state == 'missing_reference':
        annotation[NameObject('/V')] = IndirectObject(999999, 0, writer)
    elif state == 'parent_cycle':
        annotation[NameObject('/Parent')] = writer.pages[0]['/Annots'][0]
    elif state == 'parent_appearance':
        stream = DecodedStreamObject()
        stream.set_data(b'BT (Lee Harbor) Tj ET')
        annotation[NameObject('/Parent')] = writer._add_object(DictionaryObject({
            NameObject('/V'): TextStringObject(''),
            NameObject('/AP'): DictionaryObject({NameObject('/N'): writer._add_object(stream)})}))
    else:
        annotation[NameObject('/AP')] = DictionaryObject({NameObject('/N'): DictionaryObject()})
    out = io.BytesIO()
    writer.write(out)
    result = placement.place(out.getvalue(), PAT)
    assert_held(result)
    assert result['reason_code'] == 'form_fields'


def test_b1_named_block_does_not_use_distant_veto():
    writer = PdfWriter(clone_from=io.BytesIO(distant_identity_pdf()))
    overlay = io.BytesIO()
    c = canvas.Canvas(overlay, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 792 - 420, 'Name: Pat Smith')
    c.save()
    writer.pages[0].merge_page(PdfReader(overlay).pages[0])
    out = io.BytesIO()
    writer.write(out)
    result = placement.place(out.getvalue(), PAT)
    assert result['status'] == 'placed', result
    assert 'Lee Harbor' not in json.dumps(result)


def test_b1_veto_respects_neighbour_column_band():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 9)
    c.drawString(380, 590, 'Lee Harbor')
    for x, company in [(40, 'HARBOR LIGHT ANALYTICS, INC.'), (380, 'FLEET TEST CO.')]:
        c.drawString(x, 430, company)
        c.drawString(x, 394, 'By:')
        c.line(x + 30, 392, x + 160, 392)
        c.drawString(x, 354, 'Date:')
        c.line(x + 30, 352, x + 160, 352)
    c.save()
    result = placement.place(out.getvalue(), PAT)
    assert result['status'] == 'placed', result
    assert next(f for f in result['fields'] if f['type'] == 'SIGNATURE')['evidence']['line'][0] == 70


def test_h1_wrapped_witness_paragraph_keeps_exact_golden():
    writer = PdfWriter(clone_from=FIXTURES / 'harbor.pdf')
    blocks, _, _ = placement.extract((FIXTURES / 'harbor.pdf').read_bytes())
    sig = max((b.line for b in blocks if b.line.page == 2), key=lambda line: line.y)
    # Make room for the witness paragraph; the printed Name caption and all
    # signature/date geometry stay untouched.
    stream = DecodedStreamObject()
    stream.set_data(writer.pages[1].get_contents().get_data().replace(b'(Harbor Light Analytics, Inc.)', b'()'))
    writer.pages[1].replace_contents(stream)
    overlay = io.BytesIO()
    c = canvas.Canvas(overlay, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 792 - sig.y + 82, 'IN WITNESS WHEREOF the parties executed this Agreement as of the')
    c.drawString(72, 792 - sig.y + 52, 'Effective Date.')
    c.save()
    writer.pages[1].merge_page(PdfReader(overlay).pages[0])
    out = io.BytesIO()
    writer.write(out)
    exact_harbor(placement.place(out.getvalue(), LEE))


def test_b1_cross_page_walk_includes_row_at_page_top():
    writer = PdfWriter(clone_from=io.BytesIO(distant_identity_pdf(split='below')))
    writer.pages[1].add_transformation((1, 0, 0, 1, 0, 34.07))
    out = io.BytesIO()
    writer.write(out)
    with placement.pdfplumber.open(io.BytesIO(out.getvalue())) as doc:
        assert doc.pages[1].extract_words()[0]['top'] == pytest.approx(0, abs=1e-8)
    assert_held(placement.place(out.getvalue(), PAT))
