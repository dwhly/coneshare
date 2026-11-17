"""Gate 3: printed identity is authoritative, and untrusted work is bounded."""
import io
import json
import time
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path
from unittest.mock import Mock

import pytest
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import FIXTURES, LEE, EXPECTED, no_network  # noqa: F401


def named_pdf(name, *, company='Harbor Light Analytics, Inc.'):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 480, company)
    c.drawString(72, 450, 'Signature:')
    c.line(140, 448, 310, 448)
    c.drawString(72, 430, 'Name / title: ' + name + ', COO')
    c.drawString(72, 400, 'Date:')
    c.line(112, 398, 260, 398)
    c.save()
    return out.getvalue()


@pytest.mark.parametrize('printed,name,email', [
    ('harbor', 'Pat Smith', 'pat@harborlight.fleet.test'),
    ('harbor', 'Other Person', 'person@ar.com'),
    ('Jordan Lee', 'Dan Lee', 'dan@gmail.com'),
    ('Joann Lee', 'Ann Lee', 'ann@gmail.com'),
    ('harbor', 'Pat Lee', 'pat@harborlight.fleet.test'),
])
def test_reviewer_wrong_signer_goldens(printed, name, email):
    pdf = (FIXTURES / 'harbor.pdf').read_bytes() if printed == 'harbor' else named_pdf(printed)
    result = placement.place(pdf, [{'name': name, 'email': email}])
    assert result['status'] == 'needs_sender', result
    assert result['fields'] == []


@pytest.mark.parametrize('fixture', list(EXPECTED['fixtures']))
@pytest.mark.parametrize('other_name', ['Pat Smith', 'Pat Lee', 'Ann Lee', 'Dan Lee', 'Lee', 'Harbor'])
def test_unnamed_signer_never_takes_named_block(fixture, other_name):
    pdf = (FIXTURES / (fixture + '.pdf')).read_bytes()
    result = placement.place(pdf, [{'name': other_name, 'email': 'pat@harborlight.fleet.test',
                                   'company': 'Harbor Light Analytics, Inc.', 'title': 'COO'}])
    blocks, _, _ = placement.extract(pdf)
    for field in result['fields']:
        if field['type'] == 'SIGNATURE':
            # Role-only blanks remain valid; any printed person must match completely.
            block = next(b for b in blocks if [b.line.x0, b.line.y, b.line.x1] == field['evidence']['line'])
            assert not any(name in block.identity for name in ('Lee Harbor', 'Dan Whaley', 'Jordan Reyes')), result


def test_role_definition_is_anchored_to_company():
    _, _, roles = placement.extract((FIXTURES / 'roles.pdf').read_bytes())
    assert roles == {'discloser': 'Fleet Test Co.', 'recipient': 'Harbor Light Analytics, Inc.'}


@pytest.mark.parametrize('hint', ['ar', 'ey', 'co'])
def test_short_company_and_domain_are_not_identity(hint):
    block = placement.Block('b0', placement.Line(1, 72, 300, 400, 'drawn'), [],
                            'Harbor Light Analytics, Inc.', 'Harbor Light Analytics, Inc.', False)
    assert placement.score({'name': 'Pat Smith', 'email': 'pat@' + hint + '.com', 'company': hint}, block, {}) == 0


def test_total_deadline_includes_model(monkeypatch):
    monkeypatch.setenv('PLACEMENT_TOTAL_SECONDS', '0.4')
    def slow_model(payload):
        time.sleep(1)
        return {'assignments': []}
    started = time.monotonic()
    result = placement.place((FIXTURES / 'unusual.pdf').read_bytes(), LEE, model_client=slow_model)
    assert time.monotonic() - started < 0.8
    assert result['status'] == 'needs_sender'
    assert result['reason'] == 'Placement took too long'
    assert result['reason_code'] == 'placement_timeout'
    assert result['fields'] == []


def test_many_hairlines_are_bounded(tmp_path):
    # Supervise the old implementation too, so a red run cannot occupy a worker indefinitely.
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    for i in range(100_000):
        c.line(72, 100 + i * .005, 300, 100 + i * .005)
    c.save()
    pdf = tmp_path / 'many-lines.pdf'
    pdf.write_bytes(out.getvalue())
    program = "from pathlib import Path; import json; from dealroom_sign.placement import place; print(json.dumps(place(Path(__import__('sys').argv[1]).read_bytes(), [{'name':'Lee Harbor','email':'lee@example.test'}])))"
    started = time.monotonic()
    try:
        run = subprocess.run([sys.executable, '-c', program, str(pdf)], capture_output=True, text=True, timeout=4)
    except subprocess.TimeoutExpired:
        pytest.fail('100,000 hairlines exceeded the four-second wall-clock budget')
    assert time.monotonic() - started < 4
    result = json.loads(run.stdout)
    assert result['status'] == 'needs_sender'
    assert result['reason_code'] in {'parse_limit', 'placement_timeout'}


@pytest.mark.parametrize('resource', ['edges', 'chars', 'words'])
def test_page_caps_precede_deduplication(monkeypatch, resource):
    page = Mock()
    page.rotation = 0
    page.cropbox = page.mediabox = page.bbox = (0, 0, 612, 792)
    page.width, page.height, page.page_number = 612, 792, 1
    page.edges = [{}] * (5001 if resource == 'edges' else 0)
    page.chars = [{}] * (20001 if resource == 'chars' else 0)
    page.extract_words.return_value = [{}] * (4001 if resource == 'words' else 0)
    doc = Mock(pages=[page])
    doc.__enter__ = Mock(return_value=doc)
    doc.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(placement.pdfplumber, 'open', Mock(return_value=doc))
    with pytest.raises(ValueError, match='parse_limit'):
        placement.extract(b'fixture')


@pytest.mark.parametrize('failure,outcome', [(TimeoutError('private'), 'timeout'), (ValueError('private'), 'invalid_reply'), (RuntimeError('private'), 'error')])
def test_distinct_model_failure_outcomes(failure, outcome):
    result = placement.place((FIXTURES / 'unusual.pdf').read_bytes(), LEE, model_client=Mock(side_effect=failure))
    assert result['model']['outcome'] == outcome
    assert result['reason_code'] == 'model_' + outcome
    assert 'private' not in json.dumps(result)


def test_not_configured_and_fixed_parse_reason():
    result = placement.place((FIXTURES / 'unusual.pdf').read_bytes(), LEE)
    assert result['model']['outcome'] == 'not_configured'
    assert result['reason_code'] == 'model_not_configured'
    invalid = placement.place(b'%PDF invalid private bytes', LEE)
    assert invalid['reason_code'] == 'unreadable_pdf'
    assert 'private' not in json.dumps(invalid)


def nearby_body_pdf():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 390, 'Lee Harbor, Harbor Light Analytics')
    c.drawString(72, 370, 'PRIVATE NEARBY SENTINEL: the special terms remain confidential.')
    c.drawString(72, 350, 'Hand of the covenanting party:')
    c.line(245, 348, 465, 348)
    c.drawString(72, 310, 'Date:')
    c.line(112, 308, 265, 308)
    c.save()
    return out.getvalue()


def opaque_reply(payload):
    return {'assignments': [{'signer': payload['signers'][0]['id'], 'block_id': payload['candidates'][0]['id'],
                            'confidence': 'high', 'evidence': 'Hand of the covenanting party:'}]}


def test_nearby_body_is_redacted_and_model_identity_is_minimal():
    model = Mock(side_effect=opaque_reply)
    result = placement.place(nearby_body_pdf(), [dict(LEE[0], company='Harbor Light Analytics', title='COO')], model_client=model)
    assert model.call_count == 1
    payload = model.call_args.args[0]
    assert 'PRIVATE NEARBY SENTINEL' not in json.dumps(payload)
    assert '@' not in json.dumps(payload)
    assert set(payload['signers'][0]) == {'id', 'name'}
    assert result['status'] == 'placed'
    assert 'PRIVATE NEARBY SENTINEL' not in json.dumps(result)
    assert all(len(label['text']) <= 120 for f in result['fields'] for label in f['evidence']['labels'])


@pytest.mark.parametrize('gap', [23, 35, 55])
def test_caption_cannot_claim_next_block(gap):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 500, 'Signature:')
    c.line(140, 498, 310, 498)
    c.drawString(72, 498-gap-9, 'Lee Harbor')
    c.drawString(72, 498-gap-35, 'Signature:')
    c.line(140, 498-gap-37, 310, 498-gap-37)
    c.drawString(72, 498-gap-65, 'Date:')
    c.line(112, 498-gap-67, 265, 498-gap-67)
    c.save()
    assert placement.place(out.getvalue(), LEE)['status'] == 'needs_sender'


@pytest.mark.parametrize('label_x', [320, 180])
def test_date_cannot_be_borrowed_from_next_column(label_x):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 480, 'Lee Harbor')
    c.drawString(72, 450, 'Signature:')
    c.line(140, 448, 270, 448)
    c.drawString(label_x, 440, 'Date:')
    c.line(360, 438, 510, 438)
    c.save()
    assert placement.place(out.getvalue(), LEE)['status'] == 'needs_sender'


def test_native_signature_is_tight_and_bottom_anchored():
    result = placement.place((FIXTURES / 'harbor.pdf').read_bytes(), LEE)
    field = next(f for f in placement.to_native_fields(result, LEE[0]['email']) if f['type'] == 'SIGNATURE')
    assert field['height'] * 792 / 100 <= 18
    assert (field['positionY'] + field['height']) * 792 / 100 == pytest.approx(367.2, abs=.001)
    assert field['fieldMeta'] == {'type': 'signature', 'fontSize': 18}


def test_pdf_dependency_closure_is_pinned_and_licensed():
    root = Path(__file__).resolve().parents[2]
    requirements = (root / 'requirements.txt').read_text()
    for name in ['pypdfium2', 'cryptography', 'charset-normalizer', 'cffi', 'pycparser']:
        assert name + '==' + distribution(name).version in requirements
        notice = root / 'dealroom_sign' / 'licenses' / (name + '.txt')
        assert notice.exists() and len(notice.read_text()) > 200
    assert (root / 'dealroom_sign/licenses/pdfium-third-party.txt').stat().st_size > 10000


@pytest.mark.parametrize('printed', ['JORDAN LEE', 'jordan lee', "Jo O’Neil", 'Lee A. Harbor'])
def test_printed_name_variants_veto_company_match(printed):
    result = placement.place(named_pdf(printed), [{'name':'Pat Smith', 'email':'pat@harborlight.fleet.test'}])
    assert result['status'] == 'needs_sender'
    assert result['fields'] == []


def test_named_caption_is_not_dropped_when_it_is_long():
    name = 'Alexanderthefirst ' * 8 + 'Harbor'
    result = placement.place(named_pdf(name), [{'name':'Pat Smith', 'email':'pat@harborlight.fleet.test'}])
    assert result['status'] == 'needs_sender'
    assert result['fields'] == []


@pytest.mark.parametrize('name', ['jordan lee', 'Alexanderthefirst ' * 8 + 'Harbor'])
def test_unlabelled_unrecognized_caption_cannot_be_ignored(name):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 480, 'Harbor Light Analytics, Inc.')
    c.drawString(72, 450, 'Signature:')
    c.line(140, 448, 310, 448)
    c.drawString(72, 430, name)
    c.drawString(72, 400, 'Date:')
    c.line(112, 398, 260, 398)
    c.save()
    result = placement.place(out.getvalue(), [{'name':'Pat Smith', 'email':'pat@harborlight.fleet.test'}])
    assert result['status'] == 'needs_sender'
    assert result['fields'] == []


def test_heading_cannot_cross_a_previous_unlabelled_rule():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 480, 'Lee Harbor')
    c.line(72, 460, 270, 460)
    c.drawString(72, 425, 'Signature:')
    c.line(140, 423, 310, 423)
    c.drawString(72, 395, 'Date:')
    c.line(112, 393, 260, 393)
    c.save()
    assert placement.place(out.getvalue(), LEE)['status'] == 'needs_sender'


def test_date_in_close_right_column_with_unlabelled_signature_is_not_borrowed():
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.drawString(72, 480, 'Lee Harbor')
    c.drawString(72, 450, 'Signature:')
    c.line(140, 448, 280, 448)
    c.line(300, 470, 500, 470)
    c.drawString(300, 440, 'Date:')
    c.line(340, 438, 500, 438)
    c.save()
    assert placement.place(out.getvalue(), LEE)['status'] == 'needs_sender'
