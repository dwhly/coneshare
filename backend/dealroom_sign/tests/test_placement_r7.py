"""Gate 3 r7: structural captions, margin-only running rows and hold wording."""
import io
import json
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import (
    EXPECTED, FIXTURES, LEE, TWO, assert_golden, model_answer, no_network,  # noqa: F401
)
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r4 import harbor_variant
from dealroom_sign.tests.test_placement_r5 import assert_held, exact_harbor
from dealroom_sign.tests.test_placement_r6 import contact_rule_pdf


@pytest.mark.parametrize('label', ['Fax', 'Mobile', 'Contact', 'Attention', 'Notice Address'])
@pytest.mark.parametrize('name,signers,placed', [
    # Gate 3 r8 B-1: manager-approved hold for names under subordinate captions.
    ('Lee Harbor', PAT, False), ('Lee Harbor', LEE, False), ('Pat Smith', PAT, False),
])
def test_h1_short_contact_caption_preserves_typed_identity(label, name, signers, placed):
    result = placement.place(contact_rule_pdf(label, name), signers)
    if not placed:
        assert_held(result)
        return
    assert result['status'] == 'placed', result
    assert len(result['fields']) == 2
    assert {f['type'] for f in result['fields']} == {'SIGNATURE', 'DATE'}
    for field in result['fields']:
        assert field['signer'] == signers[0]['email']
        assert field['confidence'] == 'high'
        assert field['evidence']['line'][1] == (400 if field['type'] == 'SIGNATURE' else 430)


def repeated_body_pdf(*, first_y=300, text='Lee Harbor'):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    c.drawString(72, 792 - first_y, text)
    c.showPage()
    c.setFont('Helvetica', 10)
    c.drawString(72, 492, text)
    c.drawString(72, 382, 'HARBOR LIGHT ANALYTICS, INC.')
    c.drawString(72, 344, 'By:')
    c.line(100, 342, 290, 342)
    c.drawString(320, 344, 'Date:')
    c.line(350, 342, 510, 342)
    c.drawString(72, 322, 'Name:')
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('first_y', [300, 500])
def test_l1_repeated_body_name_retains_identity_veto(first_y):
    assert_held(placement.place(repeated_body_pdf(first_y=first_y), PAT))


@pytest.mark.parametrize('text', ['Page 1 of 2', '1', '- 1 -', '1 / 2'])
def test_l1_page_number_is_neutral_in_body(text):
    result = placement.place(repeated_body_pdf(text=text), PAT)
    assert result['status'] == 'placed', result
    assert len(result['fields']) == 2
    assert all(f['page'] == 2 and f['evidence']['line'][1] == 450 for f in result['fields'])


@pytest.mark.parametrize('top,bottom,neutral', [
    (71.9, 81.9, True), (72, 82, False), (300, 310, False),
    (710, 720, False), (710.1, 720.1, True),
])
def test_l1_repeated_row_respects_strict_margin_edges(top, bottom, neutral):
    rows = [{'text': 'Lee Harbor', 'rect': [72, top, 130, bottom]} for _ in range(2)]
    pages = {page: ([row], [], 792) for page, row in enumerate(rows, 1)}
    assert placement.running_rows(pages) == ({id(row) for row in rows} if neutral else set())


@pytest.mark.parametrize('wording', [
    'Closing Date.', 'Execution Date.', 'Commencement Date.',
    'This Agreement.', 'Date Above.', 'Date Below.', 'Terms Hereof.',
])
def test_l2_prose_ending_keeps_exact_harbor_boxes(wording):
    exact_harbor(placement.place(harbor_variant(wording=wording), LEE))


@pytest.mark.parametrize('name', ['DAN WHALEY.', 'Dan Whaley.'])
def test_l2_period_name_still_holds(name):
    assert_held(placement.place(harbor_variant(wording=name), LEE))


@pytest.mark.parametrize('signers,subject,verb', [
    (PAT, 'Pat Smith', 'signs and dates'),
    ([TWO[1], PAT[0]], 'Dan Whaley, Pat Smith', 'sign and date'),
])
def test_n1_hold_reason_agrees_with_signer_count(signers, subject, verb):
    result = placement.place(contact_rule_pdf('Email', 'Lee Harbor'), signers)
    assert_held(result)
    assert result['reason'] == (
        f"Couldn't tell where {subject} {verb}. Placement review comes next; nothing was sent."
    )


def test_n1_one_missing_signer_keeps_singular_reason():
    result = placement.place(contact_rule_pdf('Email', 'Lee Harbor'), TWO)
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == []
    assert result['reason'] == (
        "Couldn't tell where Dan Whaley signs and dates. Placement review comes next; nothing was sent."
    )


@pytest.mark.parametrize('name', EXPECTED['fixtures'])
def test_seven_goldens_remain_exact_against_r4_and_r5(name):
    signers = EXPECTED['fixtures'][name]['signers']
    result = placement.place(
        (FIXTURES / (name + '.pdf')).read_bytes(), signers,
        model_client=model_answer if name == 'unusual' else None,
    )
    if name == 'bare':
        assert result['status'] == 'bare' and result['fields'] == []
    else:
        assert_golden(result, name, signers)
    evidence = Path(__file__).resolve().parents[3] / 'docs/implementation'
    keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
    actual = [{k: field[k] for k in keys} for field in result['fields']]
    for revision in ('c2a-r4', 'c2a-r5'):
        previous = json.loads((evidence / revision / 'placements.json').read_text())[name]
        assert result['status'] == previous['status']
        assert actual == [{k: field[k] for k in keys} for field in previous['fields']]
        for signer in signers:
            assert placement.to_native_fields(result, signer['email']) == placement.to_native_fields(
                previous, signer['email'],
            )
