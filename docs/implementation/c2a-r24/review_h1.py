"""Supplement the retained reconstruction with the title-case Recipient block.

The six-cell baseline gap is consistent with a fifth own-block form carrying
`Recipient` plus HLA, rather than RECIPIENT without a company heading. Keep the
original matrix unchanged and measure this separate, explicit reconstruction.
"""
from dealroom_sign.tests import placement_r24_review_cases as added


def cases():
    for args, pages, people, allowed in added.cross_page_matrix():
        recital, own, location, affiliate, caption, extra, signer = args
        if own == ('RECIPIENT:', None):
            own = ('Recipient', added.HLA)
            pages = [list(page) for page in pages]
            pages[1] = (added.company_block('DISCLOSER:', 'FLEET TEST CO.', 40)
                        + added.company_block(*own, 320, extra=extra))
        yield (recital, own, location, affiliate, caption, extra, signer), pages, people, allowed
