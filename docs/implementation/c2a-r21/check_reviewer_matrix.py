"""Reviewer matrix with the r19 realistic generator's 95-character wrap.

The separately preserved inline-reproduction matrix uses the literal review
rows. This run keeps all the same matrix axes and uses the reviewer's existing
recital wrap, which also affects the cross-page identity walk.
"""
import check_layouts
from dealroom_sign.tests.placement_r21_review_cases import matrix_cases


def cases():
    for args, pages, both, allowed in matrix_cases():
        recital = ' '.join(row[1] for row in pages[0])
        rows, line, y = [], '', 80
        for word in recital.split():
            if len(line) + len(word) > 95:
                rows.append((y, line.strip(), False, 40))
                line, y = '', y + 14
            line += ' ' + word
        if line:
            rows.append((y, line.strip(), False, 40))
        yield 'Review matrix ' + args[0], repr(args), [rows, *pages[1:]], both, allowed, False


if __name__ == '__main__':
    check_layouts.cases = cases
    check_layouts.main()
