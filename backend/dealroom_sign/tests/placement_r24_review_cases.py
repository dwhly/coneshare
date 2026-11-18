"""Gate 3 r23 recital and cross-page examples, with explicit matrix axes."""
from itertools import product

from dealroom_sign.tests import placement_r23_review_cases as cases
from dealroom_sign.tests.test_placement import TWO

rc = cases.rc
HLA = 'HARBOR LIGHT ANALYTICS, INC.'
AFFILIATES = ('HARBOR LIGHT GROUP, INC.', 'HARBOR LIGHT VENTURES LLC',
              'HARBOR LIGHT HOLDINGS, INC.')
BLOCKING = {
    'b1_joint_venture': [cases.PREFIX + cases.HLA + ', ' + cases.ADDRESS + ', a joint venture of Northwind Traders LLC and Lantern Holdings, Inc. ("Recipient").'],
    'b1_subsidiary': [cases.PREFIX + cases.HLA + ', ' + cases.ADDRESS + ' and a subsidiary of Northwind Corp. and Lantern Co. ("Recipient").'],
    'b1_successor_address': [cases.PREFIX + cases.HLA + ', ' + cases.ADDRESS + ', as successor to Northwind Traders LLC and Lantern Co. ("Recipient").'],
    'b1_successor': [cases.PREFIX + cases.HLA + ', a Delaware corporation, successor to Northwind Traders LLC and Lantern Co. ("Recipient").'],
    'b1_affiliates': [cases.PREFIX + cases.HLA + ', ' + cases.ADDRESS + ', on behalf of itself and its affiliates Northwind Traders LLC and Lantern Co. ("Recipient").'],
    'b2_partners': [cases.PREFIX + 'Harbor Light Co. and Partners, Inc., ' + cases.ADDRESS + ' ("Recipient").'],
    'b2_associates': [cases.PREFIX + 'Harbor Light & Co. and Associates, LLC, ' + cases.ADDRESS + ' ("Recipient").'],
    'b2_affiliates': [cases.PREFIX + 'Harbor Light Inc. and Affiliates LLC, ' + cases.ADDRESS + ' ("Recipient").'],
    'b2_smith': [cases.PREFIX + 'Smith and Jones Co. and Associates, Inc., ' + cases.ADDRESS + ' ("Recipient").'],
}
ATTACK = {
    **BLOCKING,
    'johnson_inc': [cases.PREFIX + 'Johnson and Johnson, Inc., ' + cases.ADDRESS + ' ("Recipient").'],
    'ernst_llp': [cases.PREFIX + 'Ernst and Young LLP, ' + cases.ADDRESS + ' ("Recipient").'],
    'three_llc': ['This Agreement is entered into between Fleet Test Co., a Delaware limited liability company, and Harbor Light Group, Inc., a Delaware LLC, and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
}
BOUNDARY = {
    'procter_first': [cases.PREFIX + 'Procter and Gamble Co., an Ohio corporation, and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
    'smith_llp_first': ['This Agreement is entered into between Fleet Test Co., a Delaware corporation, and Smith and Jones LLP, a Delaware limited liability partnership, and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
    'three_lowercase': ['This Agreement is entered into between Fleet Test Co., a delaware corporation, and Harbor Light Group, Inc., a delaware corporation, and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
    'three_corp': ['This Agreement is entered into between Fleet Test Co., a Delaware corp., and Harbor Light Group, Inc., a Delaware corp., and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
    'trailing_comma': ['This Agreement is entered into between Fleet Test Co., and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
    'offices': ['This Agreement is entered into between Fleet Test Co., with offices at 200 Main Street, Boston MA, and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
    'corporation_offices': ['This Agreement is entered into between Fleet Test Co., a Delaware corporation with offices at 200 Main Street, Boston, MA, and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
    'lowercase_inc': [cases.PREFIX + 'Harbor Light Analytics, inc., ' + cases.ADDRESS + ' ("Recipient").'],
    'quoted_joins': ['This Agreement is entered into between Fleet Test Co. ("Discloser"), and Harbor Light Group, Inc. ("Guarantor"), and ' + cases.HLA + ' ("Recipient").'],
    'northwind_first': [cases.PREFIX + 'Northwind Traders LLC, a Delaware limited liability company, and ' + cases.HLA + ', ' + cases.ADDRESS + ' ("Recipient").'],
}


def company_block(heading, company, x, y=300, extra='placeholders'):
    rows = rc.block(heading, x, y, extra)
    if company:
        rows.insert(1 if heading else 0, (y - 38, company, False, x))
    return rows


def worker_case(kind, both=False):
    if kind == 'b1':
        recital = [(80, cases.PREFIX + cases.HLA + ', a', False, 40),
                   (94, 'Delaware corporation, on behalf of itself and its affiliates Northwind Traders LLC and Lantern Co. ("Recipient").', False, 40)]
    else:
        recital = [(80, cases.PREFIX + 'Harbor Light & Co. and Associates, LLC,', False, 40),
                   (94, 'a Delaware corporation with offices at 100 Harbor Way, Suite 400, Boston, Massachusetts 02110 ("Recipient").', False, 40)]
    pages = [recital, company_block('DISCLOSER:', 'FLEET TEST CO.', 40)
             + rc.block('RECIPIENT:', 320) + rc.block(AFFILIATES[0], 40, 500)]
    pat = dict(name='Pat Smith', email=rc.PE)
    return pages, [TWO[1], pat] if both else [pat], {rc.PE: (2, 320, 300, 500), rc.DE: (2, 40, 300, 220)}


def cross_page_matrix():
    """4 recitals × 5 own blocks × 2 pages × 3 affiliates × 3 captions × 2 extras × 3 signer sets."""
    own_blocks = (('RECIPIENT:', HLA), ('THE RECIPIENT', HLA),
                  ('COUNTERPARTY:', HLA), (None, HLA), ('RECIPIENT:', None))
    for args in product(rc.RECITALS, own_blocks, ('after', 'before'), AFFILIATES,
                        (None, 'GUARANTOR:', 'THE GUARANTOR'),
                        ('placeholders', 'printed'), ('domain', 'explicit', 'both')):
        recital, (heading, company), location, affiliate, caption, extra, signer = args
        own = company_block('DISCLOSER:', 'FLEET TEST CO.', 40) + company_block(heading, company, 320, extra=extra)
        aff = company_block(caption, affiliate, 40, 300 if location == 'after' else 180)
        if location == 'after':
            pages = [list(rc.RECITALS[recital]), own, aff]
        else:
            rec = [(y + 400, text, rule, *pos) for y, text, rule, *pos in rc.RECITALS[recital]]
            pages = [aff + rec, own]
        pat = dict(name='Pat Smith', email=rc.PE)
        if signer == 'explicit':
            pat['company'] = 'Harbor Light Analytics, Inc.'
        people = [TWO[1], pat] if signer == 'both' else [pat]
        yield args, pages, people, {rc.PE: (2, 320, 300, 500), rc.DE: (2, 40, 300, 220)}


def h1_worker_case():
    pages = [list(rc.RECITALS['parsed']),
             company_block('DISCLOSER:', 'FLEET TEST CO.', 40)
             + company_block('COUNTERPARTY:', HLA, 320),
             company_block('GUARANTOR:', AFFILIATES[0], 40)]
    return pages, [dict(name='Pat Smith', email=rc.PE)], {rc.PE: (2, 320, 300, 500)}


def h1_uncaptioned_worker_case():
    pages, people, allowed = h1_worker_case()
    pages[-1] = company_block(None, AFFILIATES[0], 40)
    return pages, people, allowed


def veto_matrix():
    """Reconstruct the review's 3 × 2 × 5 × 7 × 2 × 3 alias-veto axes."""
    own_blocks = (('RECIPIENT:', HLA), ('THE RECIPIENT', HLA),
                  ('COUNTERPARTY:', HLA), (None, HLA), ('RECIPIENT:', None))
    locations = ('none', 'same_recipient', 'before_recipient', 'after_recipient',
                 'same_discloser', 'before_discloser', 'after_discloser')
    for args in product(('none', 'parsed', 'address'), ('DISCLOSER:', 'THE DISCLOSER'),
                        own_blocks, locations, ('placeholders', 'printed'),
                        ('domain', 'explicit', 'both')):
        recital, fleet_heading, (heading, company), location, extra, signer = args
        own = company_block(fleet_heading, 'FLEET TEST CO.', 40) + company_block(heading, company, 320, extra=extra)
        pages = [list(rc.RECITALS[recital]), own]
        if location != 'none':
            where, role = location.split('_')
            repeated = rc.block('THE ' + role.upper(), 40, 500 if where == 'same' else 300)
            if where == 'same':
                pages[1] += repeated
            elif where == 'after':
                pages.append(repeated)
            else:
                pages[0] += repeated
        pat = dict(name='Pat Smith', email=rc.PE)
        if signer == 'explicit':
            pat['company'] = 'Harbor Light Analytics, Inc.'
        people = [TWO[1], pat] if signer == 'both' else [pat]
        yield args, pages, people, {rc.PE: (2, 320, 300, 500), rc.DE: (2, 40, 300, 220)}
