"""Gate 3 r17 findings: crossing headings still compete with affiliates."""
from itertools import product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR, rows_pdf
from dealroom_sign.tests.test_placement_r14 import in_process
from dealroom_sign.tests.test_placement_r17 import signers, wrong_fields


LONG_HARBOR = 'HARBOR LIGHT ANALYTICS INTERNATIONAL, INC.'
AFFILIATES = [
    'HARBOR LIGHT GROUP, INC.',
    'HARBOR LIGHT VENTURES LLC',
    'HARBOR LIGHT ANALYTICS UK LTD',
    HARBOR,
    'HARBOR LIGHT HOLDINGS, LLC',
    'HARBOR LIGHT, LLC',
]
AFFILIATE_MATRIX = list(product(
    AFFILIATES, [150, 180, 200, 218], [130, 160, 200, 240],
    [40, 280], [LONG_HARBOR, HARBOR], [False, True], [False, True],
))


def affiliate_rows(affiliate=AFFILIATES[0], width=180, gap=160, affiliate_x=40,
                   heading=LONG_HARBOR, fleet_heading=True):
    rows = [(250, heading, False, 40), (290, 'By:', True, 40, 40 + width),
            (350, 'Date:', True, 40, 40 + width)]
    if fleet_heading:
        rows.append((250, FLEET, False, 280))
    rows += [(290, 'By:', True, 280, 280 + width),
             (350, 'Date:', True, 280, 280 + width),
             (250 + gap, affiliate, False, affiliate_x),
             (290 + gap, 'By:', True, affiliate_x, affiliate_x + width),
             (350 + gap, 'Date:', True, affiliate_x, affiliate_x + width)]
    allowed = {PAT[0]['email']: (40, 290, 40 + width),
               TWO[1]['email']: (280, 290, 280 + width)}
    return rows, allowed


@pytest.mark.parametrize('affiliate,width,gap,affiliate_x,heading,both,fleet_heading', AFFILIATE_MATRIX)
def test_crossing_company_cannot_leave_affiliate_as_only_match(
        affiliate, width, gap, affiliate_x, heading, both, fleet_heading):
    rows, allowed = affiliate_rows(affiliate, width, gap, affiliate_x, heading, fleet_heading)
    model = Mock()
    result = in_process(placement, rows_pdf(rows), signers(both), model)
    assert not wrong_fields(result, allowed), result
    if result['status'] == 'needs_sender':
        assert result['fields'] == []
    model.assert_not_called()


@pytest.mark.parametrize('both', [False, True])
def test_b1_affiliate_reproduction_real_worker_holds(both):
    rows, _ = affiliate_rows()
    model = Mock()
    pdf = rows_pdf(rows)
    result = placement.place(pdf, signers(both), model_client=model)
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    assert result == in_process(placement, pdf, signers(both), model)
    model.assert_not_called()


@pytest.mark.parametrize('heading,roles', [
    (HARBOR, {}),
    ('RECIPIENT:', {'recipient': HARBOR}),
    ('For and on behalf of ' + HARBOR, {}),
    ('RECIPIENT:', {'recipient': 'For and on behalf of ' + HARBOR}),
    (FLEET, {}),
])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('printed_name', [False, True])
def test_crossing_competitor_normalizes_identity_and_respects_printed_name(
        heading, roles, reverse, printed_name):
    def block(x, y, text, rect):
        row = {'text': text, 'rect': rect}
        label = {'text': 'By:', 'rect': [x, y - 10, x + 20, y]}
        line = placement.Line(1, x + 30, x + 180, y, 'drawn', label, 'SIGNATURE')
        return placement.Block(str((x, y)), line, [row], text, '', False, raw_labels=[row])

    crossing_x, neighbour_x = (280, 40) if reverse else (40, 280)
    rect = [200, 250, 460, 260] if reverse else [40, 250, 282, 260]
    crossing = block(crossing_x, 290, heading, rect)
    neighbour = block(neighbour_x, 290, FLEET, [neighbour_x, 250, neighbour_x + 80, 260])
    affiliate = block(40, 450, AFFILIATES[0], [40, 410, 200, 420])
    if printed_name:
        affiliate.raw_labels.append({'text': 'Name: Pat Smith', 'rect': [40, 462, 130, 472]})
    blocks = [crossing, neighbour, affiliate]
    assert placement.heading_crosses_gutter(crossing, blocks)
    # A matching printed name is independent evidence; a different company's
    # crossing heading is not a competitor for Pat's company.
    expected = 10 if printed_name else (4 if heading == FLEET else 0)
    assert placement.score(PAT[0], affiliate, roles, blocks) == expected


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('overhang', [0, 30, 60, 62])
@pytest.mark.parametrize('dy', [-30, -29, 0, 29, 30])
@pytest.mark.parametrize('same_page', [False, True])
def test_l1_heading_reaches_neighbour_column(reverse, overhang, dy, same_page):
    def block(x, y, page, labels):
        label = {'text': 'By:', 'rect': [x, y - 10, x + 20, y]}
        line = placement.Line(page, x + 30, x + 180, y, 'drawn', label, 'SIGNATURE')
        return placement.Block(str((x, y)), line, labels, HARBOR, '', False, raw_labels=labels)

    x, other_x = (280, 40) if reverse else (40, 280)
    rect = [280 - overhang, 250, 460, 260] if reverse else [40, 250, 220 + overhang, 260]
    heading = block(x, 290, 1, [{'text': HARBOR, 'rect': rect}])
    neighbour = block(other_x, 290 + dy, 1 if same_page else 2, [])
    # Touching the neighbour's boundary is not crossing into its column.
    expected = same_page and abs(dy) < 30 and overhang > 60
    assert placement.heading_crosses_gutter(heading, [heading, neighbour]) == expected


@pytest.mark.parametrize('heading,width', [(HARBOR, 150), (LONG_HARBOR, 180),
                                           (LONG_HARBOR, 200), (LONG_HARBOR, 218)])
@pytest.mark.parametrize('worker', [False, True])
def test_l1_overhang_short_of_neighbour_keeps_company_placement(heading, width, worker):
    rows = [(250, heading, False, 40), (290, 'By:', True, 40, 40 + width),
            (350, 'Date:', True, 40, 40 + width), (250, FLEET, False, 318),
            (290, 'By:', True, 318, 318 + width), (350, 'Date:', True, 318, 318 + width)]
    model = Mock()
    pdf = rows_pdf(rows)
    result = (placement.place(pdf, PAT, model_client=model) if worker
              else in_process(placement, pdf, PAT, model))
    assert result['status'] == 'placed', result
    assert {field['type'] for field in result['fields']} == {'SIGNATURE', 'DATE'}
    assert not wrong_fields(result, {PAT[0]['email']: (40, 290, 40 + width)}), result
    model.assert_not_called()
