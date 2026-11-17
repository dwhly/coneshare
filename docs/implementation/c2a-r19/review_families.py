"""Review-described geometry sweeps, with explicit reproducible input axes.

The exact reviewer scratch generators are not part of this repository. The F
fine sweep reconstructs all 6,912 described cases. Boundary reconstruction
retains all 5,400 Cartesian cases rather than inferring the 120-case filter
which is not specified in the review.
"""
from itertools import permutations, product
from reportlab.pdfbase.pdfmetrics import stringWidth

from dealroom_sign.tests.test_placement import TWO
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR
from dealroom_sign.tests.test_placement_r18 import LONG_HARBOR


def fine_f_cases():
    for width, gap, order, dy, short, both, named in product(
            [140, 160], range(4, 61, 2), permutations(range(3)),
            [0, 20, 60], [False, True], [False, True], [False, True]):
        if 40 + 3 * width + 2 * gap > 600:
            continue
        companies = [FLEET, 'HARBOR, INC.' if short else HARBOR, 'NORTHWIND TRADERS LLC']
        rows, allowed = [], {}
        for column, party in enumerate(order):
            x = 40 + column * (width + gap)
            y = 290 + (dy if party == 0 else 0)
            rows += [(y - 40, companies[party], False, x),
                     (y, 'By:', True, x, x + width), (y + 60, 'Date:', True, x, x + width)]
            if party == 1 and named:
                rows.append((y + 12, 'Name: Pat Smith', False, x))
            if party < 2:
                allowed[(PAT[0] if party == 1 else TWO[1])['email']] = (x, y, x + width)
        args = (width, gap, order, dy, short, both, named)
        yield 'F fine ' + ('printed name' if named else 'company only'), repr(args), rows, both, allowed


def boundary_cases():
    for reverse, heading, width, fleet, affiliate_x, both, delta in product(
            [False, True], [HARBOR, LONG_HARBOR, 'FLEET TEST CO. INTERNATIONAL HOLDINGS'],
            [100, 120, 150], [False, True], [None, 40, 280], [False, True], range(-12, 13)):
        owner = 'Fleet' if heading.startswith('FLEET') else 'Pat'
        heading_x = 40 + width + delta if reverse else 280 + delta - stringWidth(heading, 'Helvetica', 10)
        own_x, other_x = (280, 40) if reverse else (40, 280)
        pat_x, fleet_x = (other_x, own_x) if owner == 'Fleet' else (own_x, other_x)
        rows = [(250, heading, False, heading_x)]
        if owner == 'Fleet':
            if fleet:  # The review's on/off axis controls the non-overhanging heading.
                rows.append((250, HARBOR, False, pat_x))
        elif fleet:
            rows.append((250, FLEET, False, fleet_x))
        for x in [40, 280]:
            rows += [(290, 'By:', True, x, x + width), (350, 'Date:', True, x, x + width)]
        if affiliate_x is not None:
            rows += [(410, 'HARBOR LIGHT GROUP, INC.', False, affiliate_x),
                     (450, 'By:', True, affiliate_x, affiliate_x + width),
                     (510, 'Date:', True, affiliate_x, affiliate_x + width)]
        allowed = {PAT[0]['email']: (pat_x, 290, pat_x + width),
                   TWO[1]['email']: (fleet_x, 290, fleet_x + width)}
        args = (reverse, heading, width, fleet, affiliate_x, both, delta)
        yield 'Reconstructed L1 ' + owner, repr(args), rows, both, allowed
