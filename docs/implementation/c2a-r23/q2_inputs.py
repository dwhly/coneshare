"""Reconstruction of the r22 review's 22-recital, 5,280-cell Q2 matrix.

The review preserves inline worker inputs and the axes, but not its stdin
matrix generator. All reconstructed recital text is explicit here.
"""
from itertools import product

from dealroom_sign.tests import placement_r21_review_cases as rc
from dealroom_sign.tests.placement_r22_review_cases import recital_rows
from dealroom_sign.tests.test_placement import TWO

PREFIX = 'This Agreement is entered into between Fleet Test Co. ("Discloser") and '
ADDRESS = 'a Delaware corporation with offices at 100 Harbor Way, Suite 400, Boston, Massachusetts 02110'
HLA = 'Harbor Light Analytics, Inc.'
FIRST = PREFIX + 'HARBOR LIGHT ANALYTICS, INC. ("Recipient").'
NW = PREFIX + 'Northwind Traders LLC ("Recipient").'
THREE = 'This Agreement is entered into between Fleet Test Co., a Delaware corporation, and Harbor Light Group, Inc., a Delaware corporation, and '
RECITALS = {
    'inc_repeat': [FIRST + ' The parties agree with Harbor Light Analytics Inc ("Recipient").'],
    'description_repeat': [FIRST + ' The parties agree with Harbor Light Analytics Inc., a Delaware corporation ("Recipient").'],
    'description_repeat_pages': [FIRST, 'The parties agree with Harbor Light Analytics Inc., a Delaware corporation ("Recipient").'],
    'conflict_hla_nw': [FIRST + ' The parties agree with Northwind Traders LLC ("Recipient").'],
    'conflict_nw_hla': [NW + ' The parties agree with Harbor Light Analytics Inc ("Recipient").'],
    'signature_nw': [FIRST, 'IN WITNESS WHEREOF the parties agree with Northwind Traders LLC ("Recipient").'],
    'signature_hla': [NW, 'IN WITNESS WHEREOF the parties agree with Harbor Light Analytics Inc ("Recipient").'],
    'signature_same': [FIRST, 'IN WITNESS WHEREOF the parties agree with Harbor Light Analytics Inc ("Recipient").'],
    'three_quoted': ['This Agreement is entered into by and among Fleet Test Co. ("Discloser"), Harbor Light Group, Inc. ("Guarantor"), and ' + HLA + ' ("Recipient").'],
    'three_two_joins': [THREE + HLA + ', a Delaware corporation ("Recipient").'],
    'three_middle_address': ['This Agreement is entered into between Fleet Test Co., a Delaware corporation, and ' + HLA + ', ' + ADDRESS + ' ("Recipient"), and Harbor Light Group, Inc. ("Guarantor").'],
    'three_last_address': [THREE + HLA + ', ' + ADDRESS + ' ("Recipient").'],
    'llp_short': [PREFIX + 'Smith and Jones LLP ("Recipient").'],
    'llp_address': [PREFIX + 'Smith and Jones LLP, ' + ADDRESS + ' ("Recipient").'],
    'smith_short_description': [PREFIX + 'Smith and Jones, Inc., a Delaware corporation ("Recipient").'],
    'b1_inc_address': [PREFIX + 'Smith and Jones, Inc., ' + ADDRESS + ' ("Recipient").'],
    'b1_co_address': [PREFIX + 'Smith and Jones Co., ' + ADDRESS + ' ("Recipient").'],
    'b1_llc_hereinafter': [PREFIX + 'Smith and Jones LLC, ' + ADDRESS + ' (hereinafter "Recipient").'],
    'b1_three': ['This Agreement is entered into between Fleet Test Co., a Delaware corporation, and Smith and Jones Holdings, LLC, a Delaware corporation, and Smith and Jones, Inc., ' + ADDRESS + ' ("Recipient").'],
    'b2_lazy_tail': [PREFIX + HLA + ', ' + ADDRESS + ', successor in interest to Lantern and Northwind Co. ("Recipient").'],
    'brown_company': [PREFIX + HLA + ', ' + ADDRESS + ', acting through Brown and Company ("Recipient").'],
    'research_center': [PREFIX + HLA + ', ' + ADDRESS + ' and Research and Development Center ("Recipient").'],
}


def matrix(recitals=RECITALS):
    # No duplicate caption-on/off cells when there is no affiliate block.
    affiliates = [('group', False), ('group', True), ('ventures', False), ('ventures', True), ('none', False)]
    for args in product(recitals, ('same', 'guarantor', 'split'),
                        ('RECIPIENT:', 'THE RECIPIENT', 'Recipient', None),
                        affiliates, ('placeholders', 'printed'), (False, True)):
        key, layout, heading, (affiliate, caption), extra, both = args
        pages, allowed = rc.layout_pages(layout, 'none', heading, extra, affiliate)
        smith = 'Smith and Jones' in recitals[key][0]
        pat = dict(name='Pat Smith', email='pat@smithjones.fleet.test' if smith else rc.PE)
        if smith:
            pages = [[(y, t.replace('HARBOR LIGHT GROUP, INC.', 'SMITH AND JONES HOLDINGS, LLC').replace('HARBOR LIGHT VENTURES LLC', 'SMITH AND JONES CONSULTING LLC'), rule, *pos)
                      for y, t, rule, *pos in page] for page in pages]
            allowed[pat['email']] = allowed.pop(rc.PE)
        if caption and affiliate != 'none':
            page = pages[1] if layout == 'same' else pages[2]
            page.insert(0, ((500 if layout == 'same' else 300) - 62, 'GUARANTOR:', False, 40))
        pages[0] = recital_rows(recitals[key][0], True)
        if len(recitals[key]) > 1:
            pages[1] = recital_rows(recitals[key][1], True) + pages[1]
        yield args, pages, [TWO[1], pat] if both else [pat], allowed


def worker_case(kind, both, explicit=False, layout='same', heading='RECIPIENT:'):
    if kind == 'b1':
        recital = [(80, PREFIX + 'Smith and Jones, Inc., a Delaware', False, 40),
                   (94, 'corporation with offices at 100 Harbor Way, Suite 400, Boston, Massachusetts 02110 ("Recipient").', False, 40)]
        pat = dict(name='Pat Smith', email='pat@smithjones.fleet.test')
        company = 'Smith and Jones, Inc.'
        affiliate = 'ventures'
    else:
        recital = [(80, 'between Fleet Test Co. ("Discloser") and Harbor Light Analytics, Inc., a Delaware', False, 40),
                   (94, 'corporation with offices at 100 Harbor Way, Suite 400, Boston, Massachusetts 02110, successor in interest', False, 40),
                   (108, 'to Lantern and Northwind Co. ("Recipient").', False, 40)]
        pat = dict(name='Pat Smith', email=rc.PE)
        company = HLA
        affiliate = 'group'
    if explicit:
        pat['company'] = company
    pages, allowed = rc.layout_pages(layout, 'none', heading, 'placeholders', affiliate)
    pages[0] = recital
    if kind == 'b1':
        pages = [[(y, t.replace('HARBOR LIGHT VENTURES LLC', 'SMITH AND JONES CONSULTING LLC'), rule, *pos)
                  for y, t, rule, *pos in page] for page in pages]
        allowed[pat['email']] = allowed.pop(rc.PE)
    return pages, [TWO[1], pat] if both else [pat], allowed
