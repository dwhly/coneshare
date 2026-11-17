"""Document layouts transcribed from the r20 review's inline reproductions."""
import io
from itertools import product

from reportlab.pdfgen import canvas

from dealroom_sign.tests.test_placement import TWO
from dealroom_sign.tests.test_placement_r3 import PAT

PE, DE = PAT[0]['email'], TWO[1]['email']
HEADINGS = ('RECIPIENT:', 'THE RECIPIENT', 'COUNTERPARTY:', 'RECEIVING PARTY:',
            'THE COMPANY', 'COMPANY:', None, 'AGREED AND ACCEPTED:',
            '[RECIPIENT]', 'Recipient', 'HARBOR LIGHT ANALYTICS, INC.')
ROLE_WORDS = ('recipient', 'discloser', 'counterparty', 'company', 'party',
              'guarantor', 'purchaser', 'buyer', 'seller', 'licensor', 'licensee',
              'employer', 'employee')
RECITALS = {
    'none': [],
    'parsed': [(80, 'This Agreement is entered into between FLEET TEST CO. ("Discloser") and HARBOR LIGHT ANALYTICS, INC. ("Recipient").', False, 40)],
    'address': [(80, 'This Agreement is entered into between Fleet Test Co. ("Discloser") and Harbor Light Analytics, Inc.,', False, 40),
                (94, 'a Delaware corporation with offices at 100 Harbor Way, Boston MA ("Recipient").', False, 40)],
    'hereinafter': [(80, 'This Agreement is entered into between Fleet Test Co. ("Discloser") and Harbor Light Analytics, Inc.', False, 40),
                    (94, '(hereinafter "Recipient").', False, 40)],
}
EXTRAS = {
    'none': [],
    'placeholders': [(12, 'Name:'), (24, 'Title:')],
    'print': [(12, 'Print Name: ____')],
    'underscores': [(12, 'Name: ____'), (24, 'Title: ____')],
    'its': [(12, 'Its: Authorized Signatory')],
    'printed': [(12, 'Name: Pat Smith'), (24, 'Title: CEO')],
}


def pages_pdf(pages):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(612, 792))
    for rows in pages:
        c.setFont('Helvetica', 10)
        for y, text, rule, *pos in rows:
            x = pos[0]
            end = pos[1] if len(pos) > 1 else x + 218
            c.drawString(x, 792 - y + (2 if rule else -8), text)
            if rule:
                c.line(x + 10 + c.stringWidth(text, 'Helvetica', 10), 792 - y, end, 792 - y)
        c.showPage()
    c.save()
    return out.getvalue()


def block(heading, x, y=300, extra='placeholders'):
    rows = [(y - 50, heading, False, x)] if heading else []
    rows.append((y, 'By:', True, x, x + 180))
    rows.extend((y + dy, text, False, x) for dy, text in EXTRAS[extra])
    rows.append((y + 60, 'Date:', True, x, x + 180))
    return rows


def layout_pages(layout='same', recital='parsed', heading='THE RECIPIENT',
                 extra='placeholders', affiliate='group'):
    fleet = block('DISCLOSER:', 40)
    fleet.insert(1, (262, 'FLEET TEST CO.', False, 40))
    pat = block(heading, 320, extra=extra)
    ay = 500 if layout == 'same' else 300
    aff = block('HARBOR LIGHT VENTURES LLC' if affiliate == 'ventures'
                else 'HARBOR LIGHT GROUP, INC.', 40, ay) if affiliate != 'none' else []
    if affiliate == 'guarantor':
        aff.insert(0, (ay - 62, 'GUARANTOR:', False, 40))
    pages = [RECITALS[recital]]
    if layout == 'same':
        pages.append(fleet + pat + aff)
    elif layout == 'guarantor':
        pages.extend([fleet + pat, aff])
    else:
        pages.extend([fleet, pat + aff])
        if layout == 'witness':
            pages[-1].extend(block('WITNESS:', 320, 500))
    allowed = {PE: (2 if layout in {'same', 'guarantor'} else 3, 320, 300, 500),
               DE: (2, 40, 300, 220)}
    return pages, allowed


def wrong_fields(result, allowed):
    """Every field must belong to its signer's page, column and By/Date span."""
    wrong = []
    for field in result['fields']:
        page, x, y, end = allowed[field['signer']]
        left, baseline, right = field['evidence']['line']
        if not (field['page'] == page and x <= left < right <= end
                and y <= baseline <= y + 60):
            wrong.append(field)
    return wrong


def matrix_cases():
    for args in product(('same', 'guarantor', 'split', 'witness'),
                        ('none', 'parsed', 'address'), HEADINGS,
                        ('none', 'placeholders', 'print', 'underscores', 'its'),
                        ('group', 'guarantor', 'ventures', 'none'), (False, True)):
        pages, allowed = layout_pages(*args[:-1])
        yield args, pages, args[-1], allowed


def cross_page_cases():
    for args in product(('guarantor', 'split'), ('none', 'parsed', 'address'),
                        HEADINGS[:-1], ('none', 'placeholders'), (False, True)):
        layout, recital, heading, extra, both = args
        pages, allowed = layout_pages(layout, recital, heading, extra)
        yield args, pages, both, allowed
