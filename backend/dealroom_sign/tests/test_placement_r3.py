"""Gate 3 r3: decisions use the whole raw block; emitted evidence is minimal."""
import io
import json
import random
from unittest.mock import Mock

import pdfplumber
import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import EXPECTED, FIXTURES, LEE, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r2 import opaque_reply

PAT = [{'name': 'Pat Smith', 'email': 'pat@harborlight.fleet.test'}]


def extent_pdf(layout, name='Lee Harbor'):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 490 if layout.startswith('format:') else 478, 'HARBOR LIGHT ANALYTICS, INC.')
    if layout == 'heading':
        c.drawString(72, 498, name)
    elif layout.startswith('format:'):
        c.drawString(72, 468, layout.split(':', 1)[1].replace('Lee Harbor', name))
    label = {'by': 'By: ' + name, 'signed': 'SIGNED by ' + name.upper()}.get(layout, 'Signature:')
    c.drawString(72, 450, label + ' __________________________')
    if layout.startswith('below:'):
        gap, extra = layout.split(':')[1:]
        c.drawString(72, 448 - float(gap) - 8, 'Name: ' + name + ('__________' if extra == 'rule' else ''))
        c.drawString(72, 365, 'Title: COO')
    c.drawString(72, 340, 'Date: __________________________')
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('layout', ['by', 'signed', 'heading', 'format:Lee Harbor – COO',
    'format:Lee Harbor (COO)', 'format:Lee Harbor / COO', 'format:LEE HARBOR / COO',
    'below:22:text', 'below:26:text', 'below:45:text', 'below:26:rule', 'below:65:rule'])
def test_other_person_in_whole_raw_extent_never_gets_high(layout):
    pdf = extent_pdf(layout)
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        assert 'lee harbor' in doc.pages[0].extract_text().lower()
    result = placement.place(pdf, PAT)
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == [], result
    assert all(a['confidence'] != 'high' for a in result['assignments']), result


@pytest.mark.parametrize('fixture', list(EXPECTED['fixtures']))
def test_inserted_raw_person_vetoes_across_fixtures(fixture):
    original = (FIXTURES / (fixture + '.pdf')).read_bytes()
    blocks, _, _ = placement.extract(original)
    # Use independently measured boxes when a fixture has no detected hosts (bare).
    targets = [(b.line.page, b.line.x1 - 80, b.line.y, b.line.x0) for b in blocks]
    if not targets:
        targets = [(1, 72, 450, 72)]
    rng = random.Random(613)
    for page, x, y, rule_x in targets:
        with pdfplumber.open(io.BytesIO(original)) as doc:
            words = doc.pages[page - 1].extract_words()
        # Randomize within open space so the injected PDF text remains legible.
        above = [n for n in range(-65, -15) if not any(w['x0'] < x + 75 and w['x1'] > x
                 and w['top'] < y + n + 12 and w['bottom'] > y + n - 3 for w in words)]
        below = [n for n in range(24, 85) if not any(w['x0'] < x + 75 and w['x1'] > x
                 and w['top'] < y + n + 12 and w['bottom'] > y + n - 3 for w in words)]
        for name_x, offset in ((x, rng.choice(above)), (x, rng.choice(below)),
                               (x + 110, -8)):
            stream = io.BytesIO()
            c = canvas.Canvas(stream, pagesize=(612, 792))
            c.setFont('Helvetica', 8)
            # x + 110 is line.x1 + 30: a caption beside the rule's own row.
            c.drawString(name_x, 792 - y - offset - 8, 'Name: Lee Harbor')
            c.save()
            reader = PdfReader(io.BytesIO(original))
            reader.pages[page - 1].merge_page(PdfReader(stream).pages[0])
            writer = PdfWriter()
            writer.append_pages_from_reader(reader)
            output = io.BytesIO()
            writer.write(output)
            pdf = output.getvalue()
            with pdfplumber.open(io.BytesIO(pdf)) as doc:
                assert 'Lee Harbor' in doc.pages[page - 1].extract_text()
            result = placement.place(pdf, PAT)
            for f in result['fields']:
                assert not (f['type'] == 'SIGNATURE' and f['page'] == page
                            and abs(f['evidence']['line'][0] - rule_x) < 3
                            and abs(f['evidence']['line'][1] - y) < 3
                            and f['confidence'] == 'high'), result


@pytest.mark.parametrize('text', ['Pat Smith', 'Alex Rowan Vale', 'unaccounted private words'])
def test_company_only_requires_every_raw_line_accounted_for(text):
    assert placement.place(extent_pdf('format:' + text), LEE)['fields'] == []


def test_matching_printed_name_can_resolve_label_prefix():
    assert placement.place(extent_pdf('by'), LEE)['status'] == 'placed'


def title_body_pdf(text, *, extra_block=False):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    def block(y, heading):
        c.drawString(72, y + 42, 'Harbor Light Analytics, Inc.')
        c.drawString(72, y + 22, heading)
        c.drawString(72, y, 'Hand of the covenanting party:')
        c.line(245, y - 2, 465, y - 2)
        c.drawString(72, y - 40, 'Date:')
        c.line(112, y - 42, 265, y - 42)
    block(550, 'Lee Harbor' if extra_block else text)
    if extra_block:
        block(300, text)
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('text', ['Project Falcon Acquisition Terms', 'Strictly Private And Confidential',
                                 'Purchase Price Remains Confidential'])
@pytest.mark.parametrize('extra_block', [False, True])
def test_title_case_body_never_leaves_local_evidence(text, extra_block):
    model = Mock(side_effect=opaque_reply)
    result = placement.place(title_body_pdf(text, extra_block=extra_block), LEE, model_client=model)
    assert text not in json.dumps(result)
    assert text not in json.dumps([call.args for call in model.call_args_list])
    if extra_block:
        assert result['status'] == 'placed', result
        assert model.call_count == 1
    else:
        assert result['fields'] == []


@pytest.mark.parametrize('domain,company', [('light', 'Harbor Light Analytics'), ('ventures', 'Acme Ventures LLC'),
    ('capital', 'Acme Capital LLC'), ('partners', 'Acme Partners LLC'), ('group', 'Acme Group LLC'),
    ('holdings', 'Acme Holdings LLC'), ('global', 'Acme Global LLC')])
def test_single_company_word_is_not_domain_identity(domain, company):
    assert placement.similarity(domain, company) == 0


def test_compound_domain_and_full_company_still_match():
    assert placement.similarity('harborlight', 'Harbor Light Analytics, Inc.') == 1
    assert placement.similarity('Acme', 'Acme LLC') == 1


@pytest.mark.parametrize('unknown', ['Pat Smith?', 'By: unreadable [name]', 'SIGNED by unreadable [name]'])
def test_matched_name_does_not_override_unresolved_person_like_line(unknown):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 510, 'Lee Harbor')
    c.drawString(72, 488, unknown)
    c.drawString(72, 450, 'Signature: __________________________')
    c.drawString(72, 400, 'Date: __________________________')
    c.save()
    result = placement.place(out.getvalue(), LEE)
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == []


def test_company_only_requires_one_signer_even_if_other_signer_has_named_block():
    pdf = title_body_pdf('Harbor Light Analytics, Inc.', extra_block=True)
    signers = LEE + PAT
    def confirm_all(payload):
        return {'assignments': [
            {'signer': s['id'], 'block_id': payload['candidates'][i]['id'],
             'confidence': 'high', 'evidence': 'Hand of the covenanting party:'}
            for i, s in enumerate(payload['signers'])]}
    model = Mock(side_effect=confirm_all)
    result = placement.place(pdf, signers, model_client=model)
    assert result['fields'] == []
    assert result['status'] == 'needs_sender'


@pytest.mark.parametrize('line', ['Lee Harbor, Pat Smith', 'Lee Harbor / Pat Smith', 'Lee Harbor (Pat Smith)'])
def test_second_person_in_same_raw_line_also_vetoes(line):
    result = placement.place(extent_pdf('format:' + line), LEE)
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == []


@pytest.mark.parametrize('label', ['COO', 'Title: COO', 'Harbor Light Analytics, Inc.', 'Signature:'])
def test_fixed_role_company_and_field_labels_remain_available(label):
    assert placement.safe_label({'text': label}, {})['text'] == label
