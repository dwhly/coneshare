"""Cross-page identity cases transcribed from the r24 review's stated axes.

The review lists 42 Q3a shapes (4,536 cells), although its total is 3,888.
Keep every stated shape; do not remove cells to match a reported total.
Q3b role pairs are explicit here because the review did not enumerate them.
"""
from itertools import product

from dealroom_sign.tests import placement_r24_review_cases as prior
from dealroom_sign.tests.test_placement import TWO

rc = prior.rc
ROLE_HEADINGS = ('MEMBER:', 'CONTRACTOR:', 'SUPPLIER:', 'VENDOR:',
                 'CONSULTANT:', 'CLIENT:', 'CUSTOMER:', 'LENDER:',
                 'INVESTOR:', 'MANAGER:', 'THE CONTRACTOR', 'RECEIVING PARTY:')
OWN_NAMES = ('HL ANALYTICS, INC.', 'H.L.A., INC.',
             'HARBOUR LIGHT ANALYTICS, INC.', 'BRIGHTWATER, INC.')
CAPTIONS = ('Recipient Signature', 'as Recipient', 'Its: Recipient',
            '(Recipient)', 'RECIPIENT')
ROLE_PAIRS = (('Customer', 'Supplier'), ('Company', 'Consultant'),
              ('Company', 'Vendor'), ('Company', 'Client'),
              ('Client', 'Contractor'), ('Company', 'Investor'),
              ('Borrower', 'Lender'), ('Discloser', 'Recipient'),
              ('Company', 'Customer'))
ALLOWED = {rc.PE: (2, 320, 300, 500), rc.DE: (2, 40, 300, 220)}


def people(kind):
    pat = dict(name='Pat Smith', email=rc.PE)
    if kind == 'explicit':
        pat['company'] = 'Harbor Light Analytics, Inc.'
    return [TWO[1], pat] if kind == 'both' else [pat]


def arrange(recital, own, caption, location):
    aff = prior.company_block(caption, prior.AFFILIATES[0], 40,
                              300 if location == 'after' else 180)
    if location == 'after':
        return [list(recital), own, aff]
    shifted = [(y + 400, text, rule, *pos) for y, text, rule, *pos in recital]
    return [aff + shifted, own]


def q3a():
    shapes = [('role', heading, company, None)
              for heading, company in product(ROLE_HEADINGS, (prior.HLA, None))]
    shapes += [('named', heading, company, None)
               for company, heading in product(OWN_NAMES, (None, 'RECIPIENT:'))]
    shapes += [('caption', None, company, caption)
               for caption, company in product(CAPTIONS, (prior.HLA, None))]
    for args in product(shapes, ('none', 'parsed', 'address'),
                        ('after', 'before'), (None, 'GUARANTOR:', 'PARENT:'),
                        ('placeholders', 'printed'), ('domain', 'explicit', 'both')):
        (kind, heading, company, own_caption), recital, location, caption, extra, signer = args
        own = (prior.company_block('DISCLOSER:', 'FLEET TEST CO.', 40)
               + prior.company_block(heading, company, 320, extra=extra))
        if own_caption:
            own.append((372, own_caption, False, 320))
        yield args, arrange(rc.RECITALS[recital], own, caption, location), people(signer), ALLOWED


def q3b():
    for args in product(ROLE_PAIRS, ('none', 'short', 'address'),
                        ('colon', 'article', 'none'), ('none', 'plain', 'guarantor'),
                        ('after', 'before'), ('placeholders', 'printed'),
                        ('domain', 'explicit', 'both')):
        (sender, recipient), recital, heading, affiliate, location, extra, signer = args
        first = f'This Agreement is entered into between Fleet Test Co. ("{sender}") and Harbor Light Analytics, Inc.'
        rec = ([] if recital == 'none' else
               [(80, first + f' ("{recipient}").', False, 40)] if recital == 'short' else
               [(80, first + ',', False, 40),
                (94, f'a Delaware corporation with offices at 100 Harbor Way, Boston MA ("{recipient}").', False, 40)])
        own_heading = (recipient.upper() + ':' if heading == 'colon' else
                       'THE ' + recipient.upper() if heading == 'article' else None)
        own = (prior.company_block(sender.upper() + ':', 'FLEET TEST CO.', 40)
               + prior.company_block(own_heading, prior.HLA, 320, extra=extra))
        pages = ([rec, own] if affiliate == 'none' else
                 arrange(rec, own, 'GUARANTOR:' if affiliate == 'guarantor' else None, location))
        yield args, pages, people(signer), ALLOWED


def worker_case(kind, both=False):
    fleet = prior.company_block('DISCLOSER:', 'FLEET TEST CO.', 40)
    recital = list(rc.RECITALS['parsed'])
    if kind == 'msa_supplier':
        recital = [(80, 'This Agreement is entered into between Fleet Test Co. ("Customer") and Harbor Light Analytics, Inc. ("Supplier").', False, 40)]
        fleet = prior.company_block('THE CUSTOMER', 'FLEET TEST CO.', 40)
        own = prior.company_block('THE SUPPLIER', prior.HLA, 320)
    elif kind == 'nda_member':
        own = prior.company_block('MEMBER:', prior.HLA, 320)
    elif kind == 'nda_caption':
        own = prior.company_block(None, prior.HLA, 320) + [(372, 'Recipient Signature', False, 320)]
    elif kind == 'nda_named':
        own = prior.company_block('RECIPIENT:', 'HL ANALYTICS, INC.', 320)
    else:
        raise ValueError(kind)
    return [recital, fleet + own, prior.company_block(None, prior.AFFILIATES[0], 40)], people('both' if both else 'domain'), ALLOWED
