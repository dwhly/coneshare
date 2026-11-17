"""Gate 3 r14 B-1: printed names cannot identify another column's block."""
from itertools import product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import FLEET, rows_pdf
from dealroom_sign.tests.test_placement_r14 import columns, fixed_rows, in_process


HEADINGS = ['Harbor Light', 'HARBOR LIGHT', 'Harbor Partners',
            'Harbor Light Group', 'Northwind Traders']
SECOND_ROWS = ['Witness: Jane Roe', 'Jane Roe', 'Name: Jane Roe',
               'Attn: Jane Roe', 'By: Jane Roe', 'P. Smith']
M1 = list(product(['left', 'right'], range(300, 451, 10), HEADINGS,
                  [False, True], [False, True]))
M2 = list(product(['left', 'right'], range(40, 121, 10), [12, 24, 40, 60],
                  SECOND_ROWS, ['RECIPIENT:', 'RECIPIENT', None], [False, True]))


def m1_reproduction_pdf():
    # Verbatim review A, including drawing order and explicit rule endpoints.
    A = [(250, 'Harbor Light', False, 72), (290, 'By:', True, 72, 290),
         (302, 'Name: Pat Smith', False, 82), (316, 'Title: CEO', False, 82), (330, 'Date:', True, 72),
         (310, FLEET, False, 330), (350, 'By:', True, 330, 548), (410, 'Date:', True, 330)]
    return rows_pdf(A)


def m2_reproduction_pdf():
    # Verbatim review B.
    B = [(250, FLEET, False, 72), (290, 'By:', True, 72, 290), (390, 'Date:', True, 72),
         (310, 'RECIPIENT:', False, 330), (350, 'By:', True, 330, 548),
         (390, 'Name: Pat Smith', False, 340), (416, 'Witness: Jane Roe', False, 340), (450, 'Date:', True, 330)]
    return rows_pdf(B)


def m2_rows(our_side, dy, gap, second_row, heading):
    ours, theirs = columns(our_side)
    their_y = 290 + dy
    rows = [(250, FLEET, False, ours), (290, 'By:', True, ours),
            (390, 'Date:', True, ours), (their_y, 'By:', True, theirs),
            (their_y + gap, 'Name: Pat Smith', False, theirs + 10),
            (their_y + gap + 26, second_row, False, theirs + 10),
            (their_y + 100, 'Date:', True, theirs)]
    if heading:
        rows.insert(3, (their_y - 40, heading, False, theirs))
    return rows, (ours, 290)


def wrong_pat_fields(result, our_line):
    """Every confidence and field type is forbidden on our signature rule."""
    x, y = our_line
    return [field for field in result['fields']
            if field['signer'] == PAT[0]['email']
            and x < field['evidence']['line'][0] < x + 218
            and field['evidence']['line'][1] == y]


def check_pdf(pdf, our_line, both, *, real_worker=False):
    model = Mock()
    signers = [TWO[1], *PAT] if both else PAT
    result = (placement.place(pdf, signers, model_client=model) if real_worker
              else in_process(placement, pdf, signers, model))
    model.assert_not_called()
    assert not wrong_pat_fields(result, our_line), result
    assert result['status'] in {'placed', 'needs_sender'}, result
    if result['status'] == 'needs_sender':
        assert result['fields'] == []


@pytest.mark.parametrize('both', [False, True], ids=['PAT', 'DAN+PAT'])
@pytest.mark.parametrize('mechanism', ['M1', 'M2'])
def test_review_reproduction_real_worker(mechanism, both):
    pdf, line = ((m1_reproduction_pdf(), (330, 350)) if mechanism == 'M1'
                 else (m2_reproduction_pdf(), (72, 290)))
    check_pdf(pdf, line, both, real_worker=True)


@pytest.mark.parametrize('our_side,our_y,heading,title,both', M1)
def test_m1_suffixless_heading(our_side, our_y, heading, title, both):
    rows, line = fixed_rows(our_side, our_y, heading, title)
    check_pdf(rows_pdf(rows), line, both)


@pytest.mark.parametrize('our_side,dy,gap,second_row,heading,both', M2)
def test_m2_second_printed_name(our_side, dy, gap, second_row, heading, both):
    rows, line = m2_rows(our_side, dy, gap, second_row, heading)
    check_pdf(rows_pdf(rows), line, both)
