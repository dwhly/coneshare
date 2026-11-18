"""Separate Q3b reconstruction with paired heading forms and five affiliate layouts.

The first, broader test matrix is retained unchanged. This matrix uses one
no-affiliate layout and two positions for each of the two affiliate captions.
Both parties use the selected heading form. The nine explicit role pairs are
the documented reconstruction, not a claim to have recovered the stdin code.
"""
import sys

import replay25 as replay


def inputs(part, generator):
    for args, pages, people, allowed in replay.q3.q3b():
        (sender, recipient), recital, heading, affiliate, location, extra, signer = args
        if affiliate == 'none' and location == 'before':
            continue  # This new matrix has five distinct affiliate layouts.
        sender_heading = sender.upper() + ':'
        pages = [[row for row in page
                  if not (heading == 'none' and row[1] == sender_heading)] for page in pages]
        if heading == 'article':
            pages = [[(row[0], 'THE ' + sender.upper(), *row[2:])
                      if row[1] == sender_heading else row for row in page] for page in pages]
        group = 'Q3b ordinary' if affiliate == 'none' else 'Q3b affiliate'
        yield group, repr(args), replay.q3.rc.pages_pdf(pages), people, None, None, allowed, False


if __name__ == '__main__':
    replay.inputs = inputs
    replay.main('q3b_aligned', replay.OUT / 'v1', replay.OUT / 'structural-v1-source.py.txt')
