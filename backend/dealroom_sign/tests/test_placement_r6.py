"""Gate 3 r6: preserve block ownership and account for ordinary PDF wording."""
import io

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import FIXTURES, LEE, TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r4 import harbor_variant
from dealroom_sign.tests.test_placement_r5 import assert_held, exact_harbor


def contact_rule_pdf(label, name):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 432, 'HARBOR LIGHT ANALYTICS, INC.')
    for offset, caption in [(0, 'By'), (30, 'Date'), (60, label)]:
        c.drawString(72, 394 - offset, caption + ':')
        x = 82 + c.stringWidth(caption + ':', 'Helvetica', 10)
        c.line(x, 392 - offset, 290, 392 - offset)
    c.drawString(72, 312, 'Name: ' + name)
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('label', ['Email', 'E-mail', 'Address', 'Phone', 'Tel', 'Company'])
@pytest.mark.parametrize('name,signers,placed', [
    ('Lee Harbor', PAT, False), ('Lee Harbor', LEE, True), ('Pat Smith', PAT, True),
])
def test_h2_contact_rule_preserves_typed_identity(label, name, signers, placed):
    result = placement.place(contact_rule_pdf(label, name), signers)
    if not placed:
        assert_held(result)
        return
    assert result['status'] == 'placed', result
    assert {f['type'] for f in result['fields']} == {'SIGNATURE', 'DATE'}
    for field in result['fields']:
        assert field['confidence'] == 'high'
        assert field['evidence']['line'][1] == (400 if field['type'] == 'SIGNATURE' else 430)


def stacked_caption_pdf(gap, *, other_name=False):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    for y, company, name in [
        (400, 'FLEET TEST CO.', 'Dan Whaley'),
        (400 + gap, 'HARBOR LIGHT ANALYTICS, INC.', 'Lee Harbor' if other_name else ''),
    ]:
        c.drawString(72, 792 - y + 30, company)
        c.drawString(72, 792 - y + 2, 'By:')
        c.line(100, 792 - y, 290, 792 - y)
        c.drawString(320, 792 - y + 2, 'Date:')
        c.line(350, 792 - y, 510, 792 - y)
        c.drawString(72, 792 - y - 20, 'Name: ' + name)
        c.drawString(72, 792 - y - 40, 'Title: CEO' if name else 'Title:')
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('gap', [110, 140])
@pytest.mark.parametrize('other_name', [False, True])
def test_h1_previous_caption_stays_with_its_host(gap, other_name):
    result = placement.place(stacked_caption_pdf(gap, other_name=other_name), [TWO[1], PAT[0]])
    if other_name:
        assert result['status'] == 'needs_sender', result
        assert result['fields'] == []
        assert result['assignments'][1]['confidence'] == 'low'
        return
    assert result['status'] == 'placed', result
    assert len(result['fields']) == 4
    for field in result['fields']:
        assert field['confidence'] == 'high'
        assert field['evidence']['line'][1] == (400 + gap if field['signer'] == PAT[0]['email'] else 400)


def running_text_pdf(header='Mutual Non-Disclosure Agreement', *, drift=0, repeated=True, footer=None):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    if footer is None:
        c.drawString(72, 750, header.format(page=1) if repeated else 'Agreement terms follow.')
        c.drawString(72, 500, 'The parties agree to the terms of this agreement.')
        c.showPage()
        c.setFont('Helvetica', 10)
        c.drawString(72, 750 + drift, header.format(page=2))
    y = 600 if footer else 220
    c.drawString(72, 792 - y + 40, 'HARBOR LIGHT ANALYTICS, INC.')
    c.drawString(72, 792 - y + 2, 'By:')
    c.line(100, 792 - y, 290, 792 - y)
    c.drawString(320, 792 - y + 2, 'Date:')
    c.line(350, 792 - y, 510, 792 - y)
    if footer:
        c.drawString(260, 792 - y - 148, footer)
        c.showPage()
        c.setFont('Helvetica', 10)
        c.drawString(72, 750, 'Name: Lee Harbor')
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('header', [
    'Mutual Non-Disclosure Agreement', 'Execution Version {page}', 'Mutual NDA – Signature Page',
])
@pytest.mark.parametrize('drift', [0, 2, -2])
def test_m1_repeated_running_header_is_neutral(header, drift):
    result = placement.place(running_text_pdf(header, drift=drift), PAT)
    assert result['status'] == 'placed', result
    assert len(result['fields']) == 2
    assert all(f['page'] == 2 and f['evidence']['line'][1] == 220 for f in result['fields'])


@pytest.mark.parametrize('kwargs', [{'repeated': False}, {'drift': 3}])
def test_m1_nonrepeated_header_retains_identity_veto(kwargs):
    assert_held(placement.place(running_text_pdf(**kwargs), PAT))


@pytest.mark.parametrize('footer', ['Page 1 of 2', '1', '- 1 -', '1 / 2'])
def test_m1_page_number_does_not_hide_next_page_name(footer):
    assert_held(placement.place(running_text_pdf(footer=footer), PAT))


@pytest.mark.parametrize('suffix', ['LIMITED', 'LLP', 'LP', 'INCORPORATED', 'PTY', 'AG', 'SA', 'BV', 'NV', 'PBC'])
def test_m2_behalf_company_suffix_keeps_exact_golden(suffix):
    wording = 'Signed for and on behalf of ACME WIDGETS ' + suffix
    exact_harbor(placement.place(harbor_variant(wording=wording), [dict(LEE[0], company='Acme Widgets')]))


@pytest.mark.parametrize('person', ['the Director', 'The Director', 'Managing Director'])
def test_m2_behalf_role_is_not_a_person(person):
    wording = 'Signed by ' + person + ' for and on behalf of HARBOR LIGHT ANALYTICS LIMITED'
    exact_harbor(placement.place(harbor_variant(wording=wording), LEE))


def test_m3_comma_witness_paragraph_keeps_exact_golden():
    writer = PdfWriter(clone_from=FIXTURES / 'harbor.pdf')
    blocks, _, _ = placement.extract((FIXTURES / 'harbor.pdf').read_bytes())
    sig = max((b.line for b in blocks if b.line.page == 2), key=lambda line: line.y)
    stream = DecodedStreamObject()
    stream.set_data(writer.pages[1].get_contents().get_data().replace(b'(Harbor Light Analytics, Inc.)', b'()'))
    writer.pages[1].replace_contents(stream)
    overlay = io.BytesIO()
    c = canvas.Canvas(overlay, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 792 - sig.y + 82, 'IN WITNESS WHEREOF, the parties hereto have executed this Agreement as of the')
    c.drawString(72, 792 - sig.y + 52, 'Effective Date.')
    c.save()
    writer.pages[1].merge_page(PdfReader(overlay).pages[0])
    out = io.BytesIO()
    writer.write(out)
    exact_harbor(placement.place(out.getvalue(), LEE))


@pytest.mark.parametrize('caption', ['Title', 'Its'])
def test_n1_title_person_before_comma_still_vetoes(caption):
    assert_held(placement.place(harbor_variant(wording=caption + ': Dan Whaley, CEO'), LEE))


@pytest.mark.parametrize('name', ['DAN WHALEY.', 'Dan Whaley.'])
def test_n2_period_name_still_vetoes_named_block(name):
    assert_held(placement.place(harbor_variant(wording=name), LEE))
