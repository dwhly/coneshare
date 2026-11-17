"""Gate 3 r4: identity belongs to the complete, separate signature block."""
import io
import json
from unittest.mock import Mock

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import FIXTURES, LEE, TWO, assert_golden, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r2 import opaque_reply
from dealroom_sign.tests.test_placement_r3 import PAT, extent_pdf, title_body_pdf


def row_name_pdf(layout, *, name='Lee Harbor', company=True):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    if company:
        c.drawString(72, 490, 'HARBOR LIGHT ANALYTICS, INC.')
    if layout == 'left':
        c.drawString(72, 450, 'Name: ' + name)
        c.drawString(260, 450, 'Signature:')
        c.line(315, 448, 480, 448)
        c.drawString(260, 410, 'Date:')
        c.line(295, 408, 460, 408)
    else:
        c.drawString(72, 450, 'Signature:')
        c.line(130, 448, 290, 448)
        c.drawString(175 if layout == 'baseline' else 320,
                     438 if layout == 'baseline' else 450, 'Name: ' + name)
        if layout == 'grid':
            c.drawString(72, 426, 'Title:')
            c.line(110, 424, 290, 424)
            c.drawString(320, 426, 'Date:')
            c.line(350, 424, 510, 424)
        else:
            c.drawString(72, 400, 'Date:')
            c.line(110, 398, 290, 398)
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('layout', ['right', 'grid', 'left', 'baseline'])
@pytest.mark.parametrize('own_name', [False, True])
@pytest.mark.parametrize('company', [False, True])
def test_rule_row_name_controls_identity(layout, own_name, company):
    result = placement.place(row_name_pdf(layout, company=company), LEE if own_name else PAT)
    assert result['status'] == ('placed' if own_name else 'needs_sender'), result
    if own_name:
        assert all(f['confidence'] == 'high' for f in result['fields'])
    else:
        assert result['fields'] == []
        assert all(a['confidence'] != 'high' for a in result['assignments'])


def test_side_by_side_company_blocks_keep_their_own_names():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 9)
    for x, name, company in [(40, 'Lee Harbor', 'Harbor Light Analytics, Inc.'),
                              (330, 'Dan Whaley', 'Fleet Test Co.')]:
        c.drawString(x, 490, company)
        c.drawString(x, 450, 'Signature:')
        c.line(x + 50, 448, x + 235, 448)
        c.drawString(x, 430, 'Name: ' + name)
        c.drawString(x, 400, 'Date:')
        c.line(x + 30, 398, x + 235, 398)
    c.save()
    result = placement.place(out.getvalue(), TWO)
    assert result['status'] == 'placed', result
    assert all(a['confidence'] == 'high' for a in result['assignments'])


TITLES = ['General Counsel', 'Managing Director', 'President and CEO', 'CEO and Founder',
          'Managing Member', 'Founder', 'Secretary', 'Owner', 'Vice President, Sales',
          'Founder & CEO', 'Chief Operating Officer', 'Senior Vice President of Sales']
WORDING = ['By:', 'Name:', 'Title:', 'Its:', 'Authorized Signatory', 'Authorised Signatory',
           'DISCLOSING PARTY:', 'RECEIVING PARTY:', 'AGREED AND ACCEPTED:', 'IN WITNESS WHEREOF:',
           'Duly authorized', 'Duly authorised', 'Date: November 16, 2026', 'Date: 2026-11-16',
           'Limited Liability Company', 'Inc.', 'LLC', 'Ltd.']


def harbor_variant(*, title='COO', wording=None):
    # Replace text operands only: all golden rule coordinates stay untouched.
    writer = PdfWriter(clone_from=FIXTURES / 'harbor.pdf')
    page = writer.pages[1]
    data = page.get_contents().get_data()
    data = data.replace(b'Lee Harbor, COO', ('Lee Harbor, ' + title).encode())
    if len(title) > 25:
        # Keep the long title legible beside the existing date column.
        data = data.replace(b'(Name / title: Lee Harbor,', b'/F1 8 Tf (Name / title: Lee Harbor,')
        operand = (title + ') Tj').encode()
        data = data.replace(operand, operand + b' /F1 10.5 Tf')
    if wording:
        escaped = wording.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        data += f'\nBT /F1 10.5 Tf 1 0 0 1 72 390 Tm ({escaped}) Tj ET\n'.encode()
    stream = DecodedStreamObject()
    stream.set_data(data)
    page.replace_contents(stream)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.mark.parametrize('title', TITLES)
def test_golden_harbor_role_suffix_keeps_exact_boxes(title):
    assert_golden(placement.place(harbor_variant(title=title), LEE), 'harbor', LEE)


@pytest.mark.parametrize('wording', WORDING + ['Title: ' + t for t in TITLES] + ['Its: Managing Member'])
def test_golden_harbor_block_wording_keeps_exact_boxes(wording):
    assert_golden(placement.place(harbor_variant(wording=wording), LEE), 'harbor', LEE)


@pytest.mark.parametrize('own_name', [False, True])
def test_ascii_hyphen_role_preserves_printed_identity(own_name):
    result = placement.place(extent_pdf('format:Lee Harbor - COO'), LEE if own_name else PAT)
    assert result['status'] == ('placed' if own_name else 'needs_sender'), result
    if not own_name:
        assert result['fields'] == []


@pytest.mark.parametrize('wording', ['Title: General Counsel', 'Its: Managing Member', 'Duly authorized'])
def test_unnamed_company_block_accounts_for_roles(wording):
    assert placement.place(extent_pdf('format:' + wording), PAT)['status'] == 'placed'


def test_title_person_remains_unresolved_and_holds():
    result = placement.place(extent_pdf('format:Title: Lee Harbor'), PAT)
    assert result['status'] == 'needs_sender'
    assert result['fields'] == []


def stacked_pdf(layout, gap=110):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    for y, name in [(400, 'DAN WHALEY'), (400 + gap, 'LEE HARBOR')]:
        if layout == 'headings':
            c.drawString(72, 792 - y + 20, name)
        c.drawString(72, 792 - y + 2, 'Signature:')
        c.line(130, 792 - y, 290, 792 - y)
        if layout == 'captions':
            c.drawString(72, 792 - y - 18, name)
            c.drawString(320, 792 - y + 2, 'Date:')
            c.line(350, 792 - y, 510, 792 - y)
        else:
            c.drawString(72, 792 - y - 38, 'Date:')
            c.line(110, 792 - y - 40, 290, 792 - y - 40)
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('layout', ['headings', 'captions'])
@pytest.mark.parametrize('gap', [80, 110])
def test_stacked_individual_blocks_place_without_neighbour_veto(layout, gap):
    result = placement.place(stacked_pdf(layout, gap), TWO)
    assert result['status'] == 'placed', result
    for field in result['fields']:
        assert field['confidence'] == 'high'
        if field['type'] == 'SIGNATURE':
            y = 400 + gap if field['signer'] == LEE[0]['email'] else 400
            assert field['evidence']['line'][1] == y


@pytest.mark.parametrize('layout', ['headings', 'captions'])
def test_stacked_individual_blocks_do_not_accept_company_only(layout):
    result = placement.place(stacked_pdf(layout), PAT)
    assert result['status'] == 'needs_sender'
    assert result['fields'] == []


def company_body_pdf():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 590, 'Project Falcon Acquisition Of Acme Corp.')
    c.drawString(72, 570, 'Lee Harbor')
    c.drawString(72, 550, 'Hand of the covenanting party:')
    c.line(245, 548, 465, 548)
    c.drawString(72, 510, 'Date:')
    c.line(112, 508, 265, 508)
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('layout', ['held', 'unselected', 'selected'])
def test_company_word_body_is_absent_from_model_and_result(layout, caplog):
    text = 'Project Falcon Acquisition Of Acme Corp.'
    model = Mock(side_effect=opaque_reply)
    pdf = company_body_pdf() if layout == 'selected' else title_body_pdf(text, extra_block=layout == 'unselected')
    result = placement.place(pdf, LEE, model_client=model)
    assert text not in json.dumps(result)
    assert text not in json.dumps([call.args for call in model.call_args_list])
    assert text not in caplog.text
    if layout != 'held':
        assert result['status'] == 'placed', result
        assert model.call_count == 1


@pytest.mark.parametrize('company', ['Acme Holdings, Inc.', 'Acme Global Services LLC', 'Acme Partners Ltd.'])
def test_leading_domain_token_can_omit_only_generic_company_words(company):
    assert placement.similarity('acme', company) == 1


@pytest.mark.parametrize('domain,company', [('light', 'Harbor Light Analytics, Inc.'),
    ('harbor', 'Harbor Light Analytics, Inc.'), ('acme', 'Acme Falcon Holdings LLC')])
def test_single_domain_token_cannot_omit_distinctive_company_words(domain, company):
    assert placement.similarity(domain, company) == 0


def test_name_in_gap_between_party_columns_makes_both_uncertain():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 9)
    for x, name, company in [(40, 'Lee Harbor', 'Harbor Light Analytics, Inc.'),
                              (380, 'Dan Whaley', 'Fleet Test Co.')]:
        c.drawString(x, 490, company)
        c.drawString(x, 450, 'Signature:')
        c.line(x + 50, 448, x + 200, 448)
        c.drawString(x, 430, 'Name: ' + name)
        c.drawString(x, 400, 'Date:')
        c.line(x + 30, 398, x + 200, 398)
    c.drawString(270, 450, 'Name: Pat Smith')
    c.save()
    result = placement.place(out.getvalue(), TWO)
    assert result['status'] == 'needs_sender'
    assert result['fields'] == []
    assert all(a['confidence'] != 'high' for a in result['assignments'])


def test_equidistant_row_between_stacked_rules_is_not_discarded():
    writer = PdfWriter(clone_from=io.BytesIO(stacked_pdf('headings', 100)))
    overlay = io.BytesIO()
    c = canvas.Canvas(overlay, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 792 - 453, 'Pat Smith')  # text centre is midway between 400 and 500
    c.save()
    writer.pages[0].merge_page(PdfReader(overlay).pages[0])
    out = io.BytesIO()
    writer.write(out)
    result = placement.place(out.getvalue(), TWO)
    assert result['status'] == 'needs_sender'
    assert result['fields'] == []
    assert all(a['confidence'] != 'high' for a in result['assignments'])
