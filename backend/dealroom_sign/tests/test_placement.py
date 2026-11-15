"""Placement goldens use independently measured PDF points, converted from native percentages."""
import io
import json
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from dealroom_sign import placement
from dealroom_sign.placement import assignment, place, validate_result

FIXTURES = Path(__file__).with_name('fixtures') / 'placement'
TWO = json.loads((FIXTURES / 's-two.json').read_text())
LEE = TWO[:1]
OFFER = json.loads((FIXTURES / 's-offer.json').read_text())
# Hand-measured page, x, y, width, height in points, independent of engine output.
EXPECTED = json.loads((FIXTURES / 'expected.json').read_text())
GOLDENS = {name: {int(k): v for k, v in data['boxes_by_signer_index'].items()}
           for name, data in EXPECTED['fixtures'].items()}



@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.delenv('PLACE_MODEL', raising=False)
    monkeypatch.setattr('httpx.Client.send', Mock(side_effect=AssertionError('Network forbidden in placement tests')))


def run(name, signers=None, **kwargs):
    return place((FIXTURES / (name + '.pdf')).read_bytes(), signers or (OFFER if name == 'offer' else LEE if name in {'harbor', 'unusual'} else TWO), **kwargs)


def assert_golden(result, name, signers):
    assert result['status'] == 'placed', result
    assert len(result['fields']) == sum(map(len, GOLDENS[name].values()))
    for index, boxes in GOLDENS[name].items():
        actual = [f for f in result['fields'] if f['signer'] == signers[index]['email']]
        for typ, page, *rect in boxes:
            field = next(f for f in actual if f['type'] == typ)
            assert field['page'] == page
            assert [field[k] * size / 100 for k, size in zip(('x', 'y', 'w', 'h'), (612, 792, 612, 792))] == pytest.approx(rect, abs=EXPECTED['tolerance_pt'])
            assert field['confidence'] in {'high', 'model-high'}
            assert field['evidence']['label_text']
            assert len(field['evidence']['line']) == 3


@pytest.mark.parametrize('name', ['nda', 'offer', 'roles', 'witness', 'harbor'])
def test_golden(name):
    assert_golden(run(name), name, OFFER if name == 'offer' else LEE if name == 'harbor' else TWO)


def test_bare_always_asks_even_with_model():
    model = Mock()
    result = run('bare', model_client=model)
    assert result['status'] == 'bare'
    assert result['fields'] == []
    model.assert_not_called()


def model_answer(payload):
    candidate = next(c for c in payload['candidates'] if 'Hand of the covenanting party:' in [l['text'] for l in c['labels']])
    return {'assignments': [{'signer': LEE[0]['email'], 'block_id': candidate['id'], 'confidence': 'high',
                              'evidence': 'Hand of the covenanting party:'}]}


def test_unusual_label_model_golden_and_minimal_payload():
    model = Mock(side_effect=model_answer)
    result = run('unusual', model_client=model)
    assert_golden(result, 'unusual', LEE)
    payload = model.call_args.args[0]
    assert 'PRIVATE BODY SENTINEL' not in json.dumps(payload)
    assert 'pdf' not in payload
    assert model.call_count == 1
    assert result['model']['outcome'] == 'resolved'


@pytest.mark.parametrize('failure', [TimeoutError('secret provider body'), ValueError('invalid JSON')])
def test_model_unavailable_visible(failure):
    result = run('unusual', model_client=Mock(side_effect=failure))
    assert result['status'] == 'needs_sender'
    assert 'unavailable' in result['reason'].lower()
    assert 'secret' not in json.dumps(result)


def test_no_key_does_not_call_provider():
    result = run('unusual')
    assert result['status'] == 'needs_sender'
    assert result['model']['outcome'] == 'unavailable'
    assert 'Placement review comes next; nothing was sent.' in result['reason']


@pytest.mark.parametrize('change', ['invented', 'low', 'missing', 'extra', 'no_evidence', 'bool_id'])
def test_invalid_model_assignments_ask(change):
    def reply(payload):
        result = model_answer(payload)
        row = result['assignments'][0]
        if change == 'invented': row['block_id'] = 'b999'
        if change == 'low': row['confidence'] = 'low'
        if change == 'missing': result['assignments'] = []
        if change == 'extra': row['rect'] = [1, 2, 3, 4]
        if change == 'no_evidence': row['evidence'] = 'an invented label'
        if change == 'bool_id': row['block_id'] = True
        return result
    result = run('unusual', model_client=reply)
    assert result['status'] == 'needs_sender'


def test_rules_success_never_calls_model():
    model = Mock()
    assert run('harbor', model_client=model)['status'] == 'placed'
    model.assert_not_called()


def test_two_signers_cannot_take_one_line():
    signers = [*LEE, dict(LEE[0], email='another@harborlight.fleet.test')]
    assert run('harbor', signers)['status'] == 'needs_sender'


def test_duplicate_signers_rejected():
    assert run('harbor', LEE * 2)['status'] == 'needs_sender'


def test_unknown_signer_is_not_assigned_from_generic_signature_cue():
    assert run('offer', [{'name': 'Other Person', 'email': 'other@gmail.com'}])['status'] == 'needs_sender'


def test_invalid_pdf_fails_closed():
    assert place(b'%PDF-invalid', LEE)['status'] == 'needs_sender'


def test_missing_date_line_asks():
    stream = io.BytesIO()
    c = canvas.Canvas(stream)
    c.drawString(72, 400, 'Lee Harbor')
    c.drawString(72, 370, 'Signature:')
    c.line(130, 368, 300, 368)
    c.save()
    assert place(stream.getvalue(), LEE)['status'] == 'needs_sender'


@pytest.mark.parametrize('rotation', [90, 180, 270])
def test_rotated_pages_fail_closed_without_moving_fields(rotation):
    reader = PdfReader(io.BytesIO((FIXTURES / 'harbor.pdf').read_bytes()))
    reader.pages[1].rotate(rotation)
    out = io.BytesIO()
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.write(out)
    # Until normalized prepare is available, rotated sources must be reviewed.
    result = place(out.getvalue(), LEE)
    assert result['status'] == 'needs_sender'
    assert 'rotation' in result['reason'].lower()


def test_cropbox_requires_review():
    reader = PdfReader(io.BytesIO((FIXTURES / 'harbor.pdf').read_bytes()))
    reader.pages[1].cropbox.lower_left = (20, 30)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    out = io.BytesIO()
    writer.write(out)
    assert place(out.getvalue(), LEE)['status'] == 'needs_sender'


def test_runtime_pins_licenses_and_ci():
    root = Path(__file__).resolve().parents[2]
    requirements = (root / 'requirements.txt').read_text()
    assert 'pdfplumber==0.11.9' in requirements
    assert 'pdfminer.six==20251230' in requirements
    assert 'pymupdf' not in requirements.lower()
    for name in ('pdfplumber', 'pdfminer.six'):
        assert 'Permission is hereby granted' in (root / 'dealroom_sign' / 'licenses' / (name + '.txt')).read_text()
    ci = (root.parent / '.github/workflows/build-ci.yml').read_text()
    assert 'dealroom_sign/tests/test_placement.py' in ci


def test_assignment_uses_actual_block_score_and_feasible_margin():
    # Greedy consumes block zero for signer zero and leaves signer one with zero.
    pairs, total = assignment([[10, 8], [9, 0]])
    assert pairs == {0: 1, 1: 0}
    assert total == 17
    assert total - assignment([[10, 8], [9, 0]], (0, 1))[1] == 7


@pytest.mark.parametrize('change', ['overlap', 'nonfinite', 'offpage', 'page', 'extra_signer', 'duplicate', 'low'])
def test_validate_rejects_unusable_fields(change):
    result = run('harbor')
    fields = result['fields']
    if change == 'overlap': fields[1].update({k: fields[0][k] for k in ('x', 'y', 'w', 'h')})
    if change == 'nonfinite': fields[0]['x'] = float('nan')
    if change == 'offpage': fields[0]['x'] = 99
    if change == 'page': fields[0]['page'] = 0
    if change == 'extra_signer': fields.append(dict(fields[0], signer='unrequested@example.test', page=3))
    if change == 'duplicate': fields.append(dict(fields[0], page=3))
    if change == 'low': fields[0]['confidence'] = 'low'
    assert not validate_result(result, LEE)


@pytest.mark.parametrize('mode', ['ok', 'missing_model', 'http_error', 'oversized', 'invalid_json'])
def test_configured_provider_uses_bounded_minimal_request(monkeypatch, mode):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fictional-provider-key')
    if mode != 'missing_model':
        monkeypatch.setenv('PLACE_MODEL', 'fixture/cheap-tier')
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    stream = Mock()
    stream.__enter__ = Mock(return_value=stream)
    stream.__exit__ = Mock(return_value=False)
    captured = {}

    def respond(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        payload = json.loads(kwargs['json']['messages'][1]['content'])
        body = json.dumps({'choices': [{'message': {'content': json.dumps(model_answer(payload))}}]}).encode()
        stream.iter_bytes.return_value = [b'x' * 32001 if mode == 'oversized' else b'invalid' if mode == 'invalid_json' else body]
        if mode == 'http_error':
            stream.raise_for_status.side_effect = httpx.HTTPError('private-provider-error')
        return stream

    client.stream.side_effect = respond
    factory = Mock(return_value=client)
    monkeypatch.setattr(placement.httpx, 'Client', factory)
    result = run('unusual')
    assert result['status'] == ('placed' if mode == 'ok' else 'needs_sender')
    if mode == 'missing_model':
        factory.assert_not_called()
    else:
        factory.assert_called_once_with(timeout=30, follow_redirects=False)
        assert captured['url'] == 'https://openrouter.ai/api/v1/chat/completions'
        assert captured['json']['model'] == 'fixture/cheap-tier'
        assert captured['json']['max_tokens'] == 2000
        assert 'PRIVATE BODY SENTINEL' not in json.dumps(captured)
    assert 'fictional-provider-key' not in json.dumps(result)
    assert 'private-provider-error' not in json.dumps(result)
