"""Measure ordinary two-party NDA hold cost, including separated signature pages."""
from itertools import product

import replay25 as replay


def inputs(part, generator):
    c = replay.q3
    for args in product(('none', 'parsed', 'address'),
                        ('colon', 'article', 'companies', 'roles_only'),
                        ('placeholders', 'printed'), ('domain', 'explicit', 'both'),
                        ('same', 'split', 'reverse')):
        recital, heading, extra, signer, layout = args
        fh, ph = {'colon': ('DISCLOSER:', 'RECIPIENT:'),
                  'article': ('THE DISCLOSER', 'THE RECIPIENT'),
                  'companies': (None, None),
                  'roles_only': ('DISCLOSER:', 'RECIPIENT:')}[heading]
        fleet = c.prior.company_block(fh, None if heading == 'roles_only' else 'FLEET TEST CO.', 40)
        pat = c.prior.company_block(ph, None if heading == 'roles_only' else c.prior.HLA, 320, extra=extra)
        pages = [list(c.rc.RECITALS[recital])]
        if layout == 'same':
            pages.append(fleet + pat)
            pp, dp = 2, 2
        elif layout == 'split':
            pages.extend([fleet, pat])
            pp, dp = 3, 2
        else:
            pages.extend([pat, fleet])
            pp, dp = 2, 3
        allowed = {c.rc.PE: (pp, 320, 300, 500), c.rc.DE: (dp, 40, 300, 220)}
        group = 'Ordinary NDA ' + layout + ' ' + signer
        yield group, repr(args), c.rc.pages_pdf(pages), c.people(signer), None, None, allowed, False


if __name__ == '__main__':
    replay.inputs = inputs
    replay.main('ordinary_ndas', replay.OUT / 'final', replay.OUT / 'structural-source.py.txt')
