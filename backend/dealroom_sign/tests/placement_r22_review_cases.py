"""Gate 3 r21 conflict and recital-precedence cases, using the r21 geometry oracle."""
from itertools import product

from dealroom_sign.tests import placement_r21_review_cases as rc

HLA = rc.RECITALS['parsed']
NW = [(y, text.replace('HARBOR LIGHT ANALYTICS, INC.', 'NORTHWIND TRADERS LLC'), rule, x)
      for y, text, rule, x in HLA]
DESCRIPTION = ('This Agreement is entered into between Fleet Test Co., a Delaware corporation, '
               'and Harbor Light Analytics, Inc., a Delaware corporation ("Recipient").')


def recital_rows(text, wrap=False):
    if not wrap:
        return [(80, text, False, 40)]
    lines, line = [], ''
    for word in text.split():
        if len(line) + len(word) > 95:
            lines.append(line.strip())
            line = ''
        line += ' ' + word
    if line:
        lines.append(line.strip())
    return [(80 + 14 * i, text, False, 40) for i, text in enumerate(lines)]


def conflict_probes():
    # Both recital pages precede the signatures, as in the inline HLA + NW case.
    for args in product(('same', 'guarantor', 'split'), ('RECIPIENT:', 'Recipient'),
                        ('group', 'guarantor', 'ventures'), (False, True)):
        layout, heading, affiliate, both = args
        pages, allowed = rc.layout_pages(layout, 'none', heading, 'placeholders', affiliate)
        allowed = {k: (p + 1, x, y, end) for k, (p, x, y, end) in allowed.items()}
        yield args, [HLA, NW, *pages[1:]], both, allowed


def l1_matrix():
    for args in product((False, True), ('RECIPIENT:', 'THE RECIPIENT', 'Recipient', None),
                        ('same', 'guarantor', 'split'),
                        ('group', 'guarantor', 'ventures', 'none'), (False, True), (False, True)):
        wrapped, heading, layout, affiliate, fleet_name, both = args
        pages, allowed = rc.layout_pages(layout, 'none', heading, 'placeholders', affiliate)
        pages[0] = recital_rows(DESCRIPTION, wrapped)
        if not fleet_name:
            pages = [[row for row in page if row[1] != 'FLEET TEST CO.'] for page in pages]
        yield args, pages, both, allowed
