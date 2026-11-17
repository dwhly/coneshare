"""r19 review inputs copied into the repository for durable regressions."""
from itertools import product

from dealroom_sign.tests.test_placement import TWO
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR

PE, DE = PAT[0]['email'], TWO[1]['email']
ALLOW = {PE: (40, 290, 220), DE: (280, 290, 460)}

RECITALS = {
    'parsed': 'This Agreement is entered into between FLEET TEST CO. ("Discloser") and HARBOR LIGHT ANALYTICS, INC. ("Recipient").',
    'address': ('This Agreement is entered into between Fleet Test Co. ("Discloser") and Harbor Light Analytics, Inc., '
                'a Delaware corporation with offices at 100 Harbor Way, Boston MA ("Recipient").'),
    'hereinafter': 'This Agreement is entered into between Fleet Test Co. ("Discloser") and Harbor Light Analytics, Inc. (hereinafter "Recipient").',
    'none': None,
}
SECOND = {'guarantor': 'HARBOR LIGHT GROUP, INC.', 'ventures': 'HARBOR LIGHT VENTURES LLC'}

WORKER_ROWS = [(80, 'This Agreement is entered into between Fleet Test Co. ("Discloser") and Harbor Light Analytics, Inc.,', False, 40),
        (94, 'a Delaware corporation with offices at 100 Harbor Way, Boston MA ("Recipient").', False, 40),
        (250, 'DISCLOSER:', False, 40), (262, 'FLEET TEST CO.', False, 40), (300, 'By:', True, 40, 220), (360, 'Date:', True, 40, 220),
        (250, 'RECIPIENT:', False, 300), (300, 'By:', True, 300, 480), (360, 'Date:', True, 300, 480),
        (450, 'HARBOR LIGHT GROUP, INC.', False, 40), (490, 'By:', True, 40, 220), (550, 'Date:', True, 40, 220)]

def realistic_cases():
    for (rk, recital), head, (ak, aff), both in product(RECITALS.items(), ['RECIPIENT:', 'COMPANY:', None],
                                                        SECOND.items(), [False, True]):
        rows = []
        if recital:
            # wrap at ~95 chars so each row stays on the page
            words, line, y = recital.split(), '', 80
            for w in words:
                if len(line) + len(w) > 95:
                    rows.append((y, line.strip(), False, 40)); line, y = '', y + 14
                line += ' ' + w
            rows.append((y, line.strip(), False, 40))
        rows += [(250, 'DISCLOSER:', False, 40), (262, 'FLEET TEST CO.', False, 40),
                 (300, 'By:', True, 40, 220), (360, 'Date:', True, 40, 220)]
        if head:
            rows.append((250, head, False, 300))
        rows += [(300, 'By:', True, 300, 480), (360, 'Date:', True, 300, 480)]
        rows += [(450, aff, False, 40), (490, 'By:', True, 40, 220), (550, 'Date:', True, 40, 220)]
        allowed = {PAT[0]['email']: (300, 300, 480), TWO[1]['email']: (40, 300, 220)}
        yield 'Realistic NDA matrix', repr((rk, head, ak, both)), rows, both, allowed


def page(pat_head, extra_rows=(), pat_extra=None, aff=None, fleet=FLEET):
    rows = []
    if pat_head:
        rows.append((250, pat_head, False, 40))
    rows += [(290, 'By:', True, 40, 220)]
    if pat_extra:
        rows.append((302, pat_extra, False, 40))
    rows += [(350, 'Date:', True, 40, 220)]
    if fleet:
        rows.append((250, fleet, False, 280))
    rows += [(290, 'By:', True, 280, 460), (350, 'Date:', True, 280, 460)]
    if aff:
        rows += [(410, aff, False, 40), (450, 'By:', True, 40, 220), (510, 'Date:', True, 40, 220)]
    return rows + list(extra_rows)


Q4_CASES = {
    # (a) dodge similarity on the real block, affiliate still matches the domain
    'dodge hyphen real + GROUP aff': page('HARBOR-LIGHT ANALYTICS, INC.', aff='HARBOR LIGHT GROUP, INC.'),
    'dodge HLA real + GROUP aff': page('HLA ANALYTICS, INC.', aff='HARBOR LIGHT GROUP, INC.'),
    'dodge British real + GROUP aff': page('HARBOUR LIGHT ANALYTICS, INC.', aff='HARBOR LIGHT GROUP, INC.'),
    'dodge real matches, aff spelt HARBOUR': page(HARBOR, pat_extra='Notary Public', aff='HARBOUR LIGHT GROUP, INC.'),
    'dodge real vetoed, aff HARBORLIGHT one word': page(HARBOR, pat_extra='Notary Public', aff='HARBORLIGHT GROUP, INC.'),
    'dodge real vetoed, aff "HL GROUP, INC."': page(HARBOR, pat_extra='Notary Public', aff='HL GROUP, INC.'),
    # (b) parent only in a recital
    'parent in recital, ordinary page': page(HARBOR, extra_rows=[(80, 'Harbor Light Analytics, Inc. is a subsidiary of Harbor Light Group, Inc.', False, 40)]),
    'parent in recital, real vetoed': page(HARBOR, pat_extra='Notary Public', extra_rows=[(80, 'Harbor Light Analytics, Inc. is a subsidiary of Harbor Light Group, Inc.', False, 40)]),
    'parent defined as role in recital': page('RECIPIENT:', extra_rows=[(80, 'between Fleet Test Co. ("Discloser") and Harbor Light Group, Inc. ("Recipient")', False, 40)]),
    # (c) company in header / footer
    'header HARBOR GROUP, ordinary page': page(HARBOR, extra_rows=[(30, 'HARBOR LIGHT GROUP, INC.', False, 40)]),
    'footer HARBOR GROUP, ordinary page': page(HARBOR, extra_rows=[(760, 'HARBOR LIGHT GROUP, INC.', False, 40)]),
    'header GROUP, real vetoed': page(HARBOR, pat_extra='Notary Public', extra_rows=[(30, 'HARBOR LIGHT GROUP, INC.', False, 40)]),
    'header GROUP, real unnamed': page('RECIPIENT:', extra_rows=[(30, 'HARBOR LIGHT GROUP, INC.', False, 40)]),
    'header Analytics, real unnamed': page('RECIPIENT:', extra_rows=[(30, HARBOR, False, 40)]),
    # (d) ordinary pages that repeat the counterparty's name
    'ordinary two-party': page(HARBOR),
    'notice block below (no rule)': page(HARBOR, extra_rows=[(420, 'Notices to Recipient:', False, 40), (432, HARBOR, False, 40),
                                                             (444, '100 Harbor Way, Boston MA', False, 40)]),
    'second Harbor block (acknowledgment)': page(HARBOR, aff=HARBOR),
    'stacked co-signer under one heading': [(250, HARBOR, False, 40), (290, 'By:', True, 40, 220), (330, 'By:', True, 40, 220),
                                            (370, 'Date:', True, 40, 220), (250, FLEET, False, 280), (290, 'By:', True, 280, 460),
                                            (370, 'Date:', True, 280, 460)],
    'heading repeated in caption "For HARBOR..."': page(HARBOR, pat_extra=None, extra_rows=[(270, 'For ' + HARBOR, False, 40)]),
}
