"""Gate 3 r16: witness columns and merged three-party company headings."""
from itertools import permutations, product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR, rows_pdf
from dealroom_sign.tests.test_placement_r14 import in_process


HEADINGS = [HARBOR, 'Harbor Light', 'RECIPIENT:', None]
CAPTIONS = ['Witness:', 'Witness', 'WITNESS:', 'Attest:', 'ATTEST:', 'Attestation:']
A2 = list(product(CAPTIONS, [0, 40, 60, 80, 100], HEADINGS, [False, True], [False, True]))
SWEEP = list(product(['Witness:', 'Attest:'], range(0, 121, 10), [12, 24, 40],
                     [False, True], HEADINGS, [False, True], [False, True]))
F = list(product(permutations(range(3)), [0, 20, 40, 60, 80, 100],
                 [False, True], [False, True], [False, True]))
F_GAPS = list(product([8, 16, 22, 28, 34, 40], [False, True],
                      permutations(range(3)), [0, 20, 40, 60, 80, 100], [False, True]))


def signers(both):
    return [TWO[1], *PAT] if both else PAT


def witness_rows(caption='Witness:', dy=60, gap=12, own_name=False,
                 heading='RECIPIENT:', reverse=False):
    ours, theirs = (330, 72) if reverse else (72, 330)
    rows = [(250, FLEET, False, ours), (290, 'By:', True, ours, ours + 218),
            (350, 'Date:', True, ours, ours + 218)]
    if own_name:
        rows.append((302, 'Name: Dan Whaley', False, ours))
    if heading:
        rows.append((250 + dy, heading, False, theirs))
    rows += [(290 + dy, caption, True, theirs, theirs + 218),
             (290 + dy + gap, 'Name: Pat Smith', False, theirs),
             (350 + dy, 'Date:', True, theirs, theirs + 218)]
    return rows


def three_party_rows(order=(0, 1, 2), dy=60, short=False, own_name=False, gap=22):
    # 160 pt rules; the long Harbor heading is 159 pt wide. At gap <=22
    # its row merges with the third company when both share a baseline.
    companies = [FLEET, 'HARBOR, INC.' if short else HARBOR, 'NORTHWIND TRADERS LLC']
    rows, allowed = [], {}
    for column, party in enumerate(order):
        x = 40 + column * (160 + gap)
        y = 290 + (dy if party == 0 else 0)
        rows += [(y - 40, companies[party], False, x), (y, 'By:', True, x, x + 160)]
        if party == 1 or (party == 0 and own_name):
            rows.append((y + 12, 'Name: ' + ('Pat Smith' if party == 1 else 'Dan Whaley'), False, x))
        rows.append((y + 60, 'Date:', True, x, x + 160))
        if party < 2:
            allowed[(PAT[0] if party == 1 else TWO[1])['email']] = (x, y, x + 160)
    return rows, allowed


def wrong_fields(result, allowed):
    """Every emitted field must be on its signer's own signature/date rule."""
    wrong = []
    for field in result['fields']:
        x, y, end = allowed.get(field['signer'], (-1000, -1000, -1000))
        line = field['evidence']['line']
        expected_y = y if field['type'] == 'SIGNATURE' else y + 60
        if not (x < line[0] < end and line[1] == expected_y and line[2] == end):
            wrong.append(field)
    return wrong


def check_witness(rows, both, worker=False):
    model = Mock()
    pdf = rows_pdf(rows)
    result = (placement.place(pdf, signers(both), model_client=model) if worker
              else in_process(placement, pdf, signers(both), model))
    # Pat is printed under a witness/attestation rule, so neither party can
    # complete a placement for this signer set.
    assert result['fields'] == [], result
    assert result['status'] == 'needs_sender', result


@pytest.mark.parametrize('caption,dy,heading,reverse,both', A2)
def test_a2_witness_column_keeps_its_name(caption, dy, heading, reverse, both):
    check_witness(witness_rows(caption, dy, heading=heading, reverse=reverse), both)


@pytest.mark.parametrize('caption,dy,gap,own_name,heading,reverse,both', SWEEP)
def test_wider_witness_sweep(caption, dy, gap, own_name, heading, reverse, both):
    check_witness(witness_rows(caption, dy, gap, own_name, heading, reverse), both)


@pytest.mark.parametrize('order,dy,short,own_name,both', F)
def test_f_three_parties(order, dy, short, own_name, both):
    rows, allowed = three_party_rows(order, dy, short, own_name)
    result = in_process(placement, rows_pdf(rows), signers(both), Mock())
    assert not wrong_fields(result, allowed), result
    if result['status'] == 'needs_sender':
        assert result['fields'] == []


@pytest.mark.parametrize('gap,short,order,dy,both', F_GAPS)
def test_f_heading_gaps(gap, short, order, dy, both):
    rows, allowed = three_party_rows(order, dy, short, gap=gap)
    result = in_process(placement, rows_pdf(rows), signers(both), Mock())
    assert not wrong_fields(result, allowed), result
    if result['status'] == 'needs_sender':
        assert result['fields'] == []


@pytest.mark.parametrize('both', [False, True])
def test_b1_review_reproduction_real_worker(both):
    check_witness(witness_rows(), both, worker=True)


@pytest.mark.parametrize('both', [False, True])
def test_b2_review_reproduction_real_worker(both):
    rows, allowed = three_party_rows()
    model = Mock()
    result = placement.place(rows_pdf(rows), signers(both), model_client=model)
    assert not wrong_fields(result, allowed), result
    assert (result['status'], result['fields']) == ('needs_sender', [])
    model.assert_not_called()


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('heading', [HARBOR, HARBOR + ' NORTHWIND TRADERS LLC'])
def test_crossing_heading_supplies_no_company_score_to_either_column(heading, reverse):
    row = {'text': heading, 'rect': [72, 260, 480, 270]}
    blocks = []
    for x, end in [(72, 290), (330, 548)]:
        label = {'text': 'By:', 'rect': [x, 280, x + 20, 290]}
        line = placement.Line(1, x + 30, end, 290, 'drawn', label, 'SIGNATURE')
        blocks.append(placement.Block(str(x), line, [row], heading, '', False, raw_labels=[row]))
    if reverse:
        blocks.reverse()
    placement.prepare_blocks(blocks, {}, PAT)
    assert [block.scores for block in blocks] == [[0], [0]]
