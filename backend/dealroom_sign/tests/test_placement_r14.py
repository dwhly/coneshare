"""Gate 3 r13 B-1: staggered columns cannot lend their printed identity."""
import io
from itertools import product
from unittest.mock import Mock, patch

import pytest
from pypdf import PdfReader, PdfWriter

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR, rows_pdf
from dealroom_sign.tests.test_placement_r13 import assert_pat_placement, short_rule_pdf


HEADINGS = [HARBOR, 'RECIPIENT:', None]
GRID = list(product(
    ['left', 'right'], ['ours', 'theirs'], [0, 20, 40, 60, 80, 100],
    [12, 24, 40, 60], ['none', 'blank', 'dan'], HEADINGS, [False, True], [False, True],
))
FIXED = list(product(['left', 'right'], range(300, 441, 10), HEADINGS,
                     [False, True], [False, True]))


def columns(our_side):
    return (72, 330) if our_side == 'left' else (330, 72)


def grid_rows(our_side, lower, dy, gap, own_name, heading, title):
    ours, theirs = columns(our_side)
    our_y, their_y = (290 + dy, 290) if lower == 'ours' else (290, 290 + dy)
    rows = [
        (our_y - 40, FLEET, False, ours), (our_y, 'By:', True, ours),
        (our_y + 100, 'Date:', True, ours), (their_y, 'By:', True, theirs),
        (their_y + gap, 'Name: Pat Smith', False, theirs + 10),
        (their_y + 100, 'Date:', True, theirs),
    ]
    if heading:
        rows.append((their_y - 40, heading, False, theirs))
    if title:
        rows.append((their_y + gap + 14, 'Title: CEO', False, theirs + 10))
    if own_name == 'blank':
        rows.append((our_y + gap, 'Name:', True, ours))
    elif own_name == 'dan':
        rows.append((our_y + gap, 'Name: Dan Whaley', False, ours + 10))
    return rows, (ours, our_y)


def fixed_rows(our_side='right', our_y=350, heading=HARBOR, title=True):
    ours, theirs = columns(our_side)
    rows = [(290, 'By:', True, theirs), (302, 'Name: Pat Smith', False, theirs + 10),
            (330, 'Date:', True, theirs), (our_y - 40, FLEET, False, ours),
            (our_y, 'By:', True, ours), (our_y + 60, 'Date:', True, ours)]
    if heading:
        rows.append((250, heading, False, theirs))
    if title:
        rows.append((316, 'Title: CEO', False, theirs + 10))
    return rows, (ours, our_y)


def reproduction_pdf():
    # Verbatim review reproduction, including drawing order and rule endpoints.
    return rows_pdf([
        (250, HARBOR, False, 72), (290, 'By:', True, 72, 290),
        (302, 'Name: Pat Smith', False, 82), (316, 'Title: CEO', False, 82),
        (330, 'Date:', True, 72), (310, FLEET, False, 330),
        (350, 'By:', True, 330, 548), (410, 'Date:', True, 330),
    ])


def in_process(module, pdf, signers, model):
    """Use the review's extraction path for the large geometry matrices."""
    def bounded(source, deadline, signers):
        blocks, sizes, roles = module.extract(source, deadline=deadline)
        module.prepare_blocks(blocks, roles, signers)
        return blocks, sizes, roles

    with patch.object(module, 'bounded_extract', bounded):
        return module.place(pdf, signers, model_client=model)


def wrong_pat_fields(result, our_line):
    x, y = our_line
    return [field for field in result['fields']
            if field['signer'] == PAT[0]['email'] and field['type'] == 'SIGNATURE'
            and field['confidence'] in {'high', 'model-high'}
            and x < field['evidence']['line'][0] < x + 218
            and field['evidence']['line'][1] == y]


def assert_no_borrowed_name(rows, our_line, both):
    model = Mock()
    result = in_process(placement, rows_pdf(rows), [TWO[1], *PAT] if both else PAT, model)
    assert not wrong_pat_fields(result, our_line), result
    assert result['status'] in {'placed', 'needs_sender'}, result
    if result['status'] == 'needs_sender':
        assert result['fields'] == []
    model.assert_not_called()


def test_b1_review_reproduction_real_worker_holds():
    model = Mock()
    result = placement.place(reproduction_pdf(), PAT, model_client=model)
    assert (result['status'], result['reason_code'], result['fields']) == (
        'needs_sender', 'ambiguous_identity', []), result
    model.assert_not_called()


@pytest.mark.parametrize('our_side,lower,dy,gap,own_name,heading,title,both', GRID)
def test_two_column_grid_no_pat_on_our_line(our_side, lower, dy, gap, own_name, heading, title, both):
    rows, our_line = grid_rows(our_side, lower, dy, gap, own_name, heading, title)
    assert_no_borrowed_name(rows, our_line, both)


@pytest.mark.parametrize('our_side,our_y,heading,title,both', FIXED)
def test_fixed_geometry_sweep_no_pat_on_our_line(our_side, our_y, heading, title, both):
    rows, our_line = fixed_rows(our_side, our_y, heading, title)
    assert_no_borrowed_name(rows, our_line, both)


@pytest.mark.parametrize('our_side', ['left', 'right'])
def test_staggered_without_mixed_heading_stays_placed(our_side):
    rows, _ = fixed_rows(our_side)
    rows = [row for row in rows if row[1] != FLEET]
    # The counterparty's unambiguous HARBOR block must still win over the
    # other block sharing its name. A blanket shared-name veto would fail.
    assert_pat_placement(rows_pdf(rows), 290, 330, right_column=our_side == 'left')


@pytest.mark.parametrize('caption_x', [150, 200])
def test_l1_printed_name_in_our_column_remains_authoritative(caption_x):
    assert_pat_placement(short_rule_pdf(caption_x), 290, 400, right_column=True)


@pytest.mark.parametrize('separate_page', [False, True])
def test_separate_printing_of_same_name_is_not_vetoed(separate_page):
    mixed, _ = fixed_rows()
    independent = [(510, HARBOR, False), (550, 'By:', True),
                   (562, 'Name: Pat Smith', False, 82), (610, 'Date:', True)]
    if separate_page:
        writer = PdfWriter()
        for rows in [mixed, independent]:
            writer.append_pages_from_reader(PdfReader(io.BytesIO(rows_pdf(rows))))
        stream = io.BytesIO()
        writer.write(stream)
        source = stream.getvalue()
    else:
        source = rows_pdf(mixed + independent)
    result = assert_pat_placement(source, 550, 610)
    assert {field['page'] for field in result['fields']} == {2 if separate_page else 1}
