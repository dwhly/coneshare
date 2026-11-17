"""Company-only assignments require unambiguous page-level identity."""
from itertools import product
from unittest.mock import Mock

import pytest
from reportlab.pdfbase.pdfmetrics import stringWidth

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR, rows_pdf
from dealroom_sign.tests.test_placement_r14 import in_process
from dealroom_sign.tests.test_placement_r17 import signers, wrong_fields


VETO_LINES = ['Name: Patricia Smith', '(Corporate Seal)', 'Notary Public',
              'Address: 100 Harbor Way, Boston MA', 'Patricia Smith',
              'Name: P. Smith', 'Name: Chris Jones']
AFFILIATES = ['HARBOR LIGHT GROUP, INC.', 'HARBOR LIGHT VENTURES LLC',
              'HARBOR LIGHT ANALYTICS UK LTD', 'HARBOR LIGHT HOLDINGS, LLC',
              'HARBOR LIGHT, LLC']
VETO_MATRIX = list(product(VETO_LINES, AFFILIATES, [40, 280], [False, True]))


def veto_rows(extra, affiliate, affiliate_x):
    rows = [(250, HARBOR, False, 40), (290, 'By:', True, 40, 220),
            (302, extra, False, 40), (350, 'Date:', True, 40, 220),
            (250, FLEET, False, 280), (290, 'By:', True, 280, 460),
            (350, 'Date:', True, 280, 460),
            (410, affiliate, False, affiliate_x),
            (450, 'By:', True, affiliate_x, affiliate_x + 180),
            (510, 'Date:', True, affiliate_x, affiliate_x + 180)]
    allowed = {PAT[0]['email']: (40, 290, 220), TWO[1]['email']: (280, 290, 460)}
    return rows, allowed


@pytest.mark.parametrize('extra,affiliate,affiliate_x,both', VETO_MATRIX)
def test_vetoed_company_still_competes(extra, affiliate, affiliate_x, both):
    rows, allowed = veto_rows(extra, affiliate, affiliate_x)
    model = Mock()
    result = in_process(placement, rows_pdf(rows), signers(both), model)
    assert not wrong_fields(result, allowed), result
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()


@pytest.mark.parametrize('both', [False, True])
@pytest.mark.parametrize('gap', [-12, -2, 0, 2])
@pytest.mark.parametrize('worker', [False, True])
def test_colliding_heading_row_is_unresolved(both, gap, worker):
    fleet = 'FLEET TEST CO. INTERNATIONAL HOLDINGS'
    harbor_x = 40 + stringWidth(fleet, 'Helvetica', 10) + gap
    rows = [(250, fleet, False, 40), (250, HARBOR, False, harbor_x),
            (290, 'By:', True, 40, 160), (350, 'Date:', True, 40, 160),
            (290, 'By:', True, 280, 400), (350, 'Date:', True, 280, 400),
            (410, AFFILIATES[0], False, 40), (450, 'By:', True, 40, 220),
            (510, 'Date:', True, 40, 220)]
    model = Mock()
    pdf = rows_pdf(rows)
    result = (placement.place(pdf, signers(both), model_client=model) if worker
              else in_process(placement, pdf, signers(both), model))
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()


@pytest.mark.parametrize('heading,roles', [
    (HARBOR, {}),
    ('RECIPIENT:', {'recipient': HARBOR}),
    ('For and on behalf of ' + HARBOR, {}),
    ('RECIPIENT:', {'recipient': 'For and on behalf of ' + HARBOR}),
])
@pytest.mark.parametrize('reason', ['uncertain', 'company_veto', 'name', 'prose', 'ordinary'])
@pytest.mark.parametrize('same_page', [False, True])
def test_company_competition_uses_identity_before_vetoes(heading, roles, reason, same_page):
    def block(x, y, page, text):
        row = {'text': text, 'rect': [x, y - 40, x + 150, y - 30]}
        label = {'text': 'By:', 'rect': [x, y - 10, x + 20, y]}
        line = placement.Line(page, x + 30, x + 180, y, 'drawn', label, 'SIGNATURE')
        return placement.Block(str((x, y)), line, [row], text, '', False, raw_labels=[row])

    other = block(40, 290, 1 if same_page else 2, heading)
    target = block(40, 450, 1, AFFILIATES[0])
    other.uncertain_identity = reason == 'uncertain'
    other.company_only_blocked = reason == 'company_veto'
    if reason in {'name', 'prose'}:
        text = 'Name: Patricia Smith' if reason == 'name' else 'Address: 100 Harbor Way, Boston MA'
        other.raw_labels.append({'text': text, 'rect': [40, 302, 180, 312]})
    assert placement.score(PAT[0], target, roles, [other, target]) == (0 if same_page else 4)


@pytest.mark.parametrize('separator', [' / ', ' - ', ': '])
@pytest.mark.parametrize('affiliate', [False, True])
def test_shared_heading_remains_identity_without_heading_attribution(separator, affiliate):
    heading = 'FLEET TEST CO. INTERNATIONAL HOLDINGS' + separator + HARBOR
    rows = [(250, heading, False, 40), (290, 'By:', True, 40, 160),
            (350, 'Date:', True, 40, 160), (290, 'By:', True, 280, 400),
            (350, 'Date:', True, 280, 400)]
    if affiliate:
        rows += [(410, AFFILIATES[0], False, 40), (450, 'By:', True, 40, 220),
                 (510, 'Date:', True, 40, 220)]
    model = Mock()
    result = in_process(placement, rows_pdf(rows), PAT, model)
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()


@pytest.mark.parametrize('gap', [-2, 0, 2])
@pytest.mark.parametrize('both', [False, True])
def test_colliding_mapped_roles_are_unresolved(gap, both):
    second = 40 + stringWidth('DISCLOSER:', 'Helvetica', 10) + gap
    rows = [(100, 'between FLEET TEST CO. ("Discloser") and HARBOR LIGHT ANALYTICS, INC. ("Recipient")', False, 40),
            (250, 'DISCLOSER:', False, 40), (250, 'RECIPIENT:', False, second),
            (290, 'By:', True, 40, 120), (350, 'Date:', True, 40, 120),
            (290, 'By:', True, 130, 210), (350, 'Date:', True, 130, 210),
            (450, AFFILIATES[0], False, 40), (490, 'By:', True, 40, 220),
            (550, 'Date:', True, 40, 220)]
    model = Mock()
    result = in_process(placement, rows_pdf(rows), signers(both), model)
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()
