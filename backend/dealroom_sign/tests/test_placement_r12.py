"""Gate 3 r11 B-1: retain absorbed identities across intervening hosts."""
import io

import pytest
from reportlab.pdfgen import canvas

from dealroom_sign.tests.test_placement import TWO, no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r8 import CAPTIONS
from dealroom_sign.tests.test_placement_r9 import FLEET, rows_pdf
from dealroom_sign.tests.test_placement_r10 import assert_stack_hold


SECOND_RULES = ['By:', 'Signature:', 'Signed:']
HEADINGS = ['RECIPIENT:', 'RECIPIENT', 'For and on behalf of the Recipient',
            'harbor light analytics, inc.']
NAMES = ['Name: Pat Smith', 'Pat Smith']
STACKS = {
    'by_by': [(270, 'By:'), (310, 'By:')],
    'by_signature_by': [(260, 'By:'), (285, 'Signature:'), (310, 'By:')],
    'signature_by': [(270, 'Signature:'), (310, 'By:')],
}
# The review's 270 total requires nine forms; baseline_10 is the additional
# baseline control alongside the eight explicitly named forms.
FORMS = ['below_12', 'below_24', 'baseline_10', 'baseline_13', 'baseline_16',
         'raised_16', 'raised_25', 'margin', 'indented']
SIGNERS = {'pat': PAT, 'dan_pat': [TWO[1], *PAT]}


def matrix1_pdf(second_rule, heading, caption, name):
    return rows_pdf([
        (240, FLEET, False), (270, 'By:', True), (310, second_rule, True),
        (340, heading, False), (370, caption, True), (382, name, False),
        (420, 'Date:', True),
    ])


def matrix2_pdf(stack, caption, form):
    rows = [(220, FLEET, False)]
    rows += [(y, text, True) for y, text in STACKS[stack]]
    rows += [(340, 'RECIPIENT:', False), (370, caption, True), (420, 'Date:', True)]
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    c.setFont('Helvetica', 10)
    for y, text, rule in rows:
        x = 150 if text == caption and form == 'indented' else 72
        c.drawString(x, 792 - y + (2 if rule else -8), text)
        if rule:
            c.line(x + 10 + c.stringWidth(text, 'Helvetica', 10), 792 - y, x + 218, 792 - y)
    size, x, name = 10, 300, 'Pat Smith'
    if form.startswith('baseline_'):
        size = int(form.split('_')[1])
        baseline = 368
    elif form.startswith('raised_'):
        baseline = 370 - int(form.split('_')[1]) + 0.793 * size
    else:
        x = 20 if form == 'margin' else 72
        dy = int(form.split('_')[1]) if form.startswith('below_') else 12
        baseline = 370 + dy + 8
        name = 'Name: ' + name
    c.setFont('Helvetica', size)
    c.drawString(x, 792 - baseline, name)
    c.save()
    return out.getvalue()


def same_band_right_pdf():
    # Both hosts have the same y: even a nearest-first stable sort picks the
    # left host, whose right edge excludes the name. Only the right block
    # contains BOTH the absorbed caption's label and the name.
    return rows_pdf([
        (250, FLEET, False), (290, 'By:', True), (290, 'By:', True, 330),
        (360, 'Authorised signatory:', True, 260),
        (372, 'Name: Pat Smith', False, 340), (400, 'Date:', True, 330),
    ])


@pytest.mark.parametrize('second_rule', SECOND_RULES)
@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('heading', HEADINGS)
@pytest.mark.parametrize('name', NAMES)
def test_matrix1_intervening_host_holds(name, heading, caption, second_rule):
    assert_stack_hold(matrix1_pdf(second_rule, heading, caption, name), PAT)


@pytest.mark.parametrize('stack', STACKS)
@pytest.mark.parametrize('caption', CAPTIONS)
@pytest.mark.parametrize('form', FORMS)
@pytest.mark.parametrize('signer_set', SIGNERS)
def test_matrix2_widened_stacks_hold(signer_set, form, caption, stack):
    assert_stack_hold(matrix2_pdf(stack, caption, form), SIGNERS[signer_set])


def test_same_band_right_host_retains_absorbed_identity():
    assert_stack_hold(same_band_right_pdf(), PAT)
