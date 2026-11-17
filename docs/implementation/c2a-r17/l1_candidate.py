"""Bounded optional experiment: merge columns with >=80% mutual overlap."""
from itertools import product


def candidate(source):
    before = '''    left = column(block)[0]
    own = (left, columns[left])
    others = [(x, right) for x, right in columns.items() if x != left]
    neighbours = {(column(other)[0], columns[column(other)[0]]) for other in parties
                  if abs(other.line.y - block.line.y) < 30 and column(other)[0] != left}
'''
    after = '''    merged, owners = {}, {}
    for left, right in sorted(columns.items()):
        owner = next((start for start, end in merged.items()
                      if min(right, end) - max(left, start) >= .8 * max(right - left, end - start)), left)
        owners[left] = owner
        merged[owner] = max(merged.get(owner, right), right)
    columns = merged
    left = owners[column(block)[0]]
    own = (left, columns[left])
    others = [(x, right) for x, right in columns.items() if x != left]
    neighbours = {(owners[column(other)[0]], columns[owners[column(other)[0]]]) for other in parties
                  if abs(other.line.y - block.line.y) < 30 and owners[column(other)[0]] != left}
'''
    assert source.count(before) == 1
    return source.replace(before, after)


def cases(new):
    def rows(ours, theirs, dy, heading):
        x, end = ours
        tx, tend = theirs
        result = [(250, new.FLEET, False, x), (290, 'By:', True, x, end),
                  (350, 'Date:', True, x, end), (290 + dy, 'By:', True, tx, tend),
                  (302 + dy, 'Name: Pat Smith', False, tx), (350 + dy, 'Date:', True, tx, tend)]
        if heading:
            result.append((250 + dy, heading, False, tx))
        allowed = {new.PAT[0]['email']: (tx, 290 + dy, tend), new.TWO[1]['email']: (x, 290, end)}
        return result, allowed

    for args in product([-5, 0, 1, 2, 3, 5, 10, 20], [140, 160, 180, 200, 220, 240], new.HEADINGS, [False, True]):
        offset, dy, heading, both = args
        pdf_rows, allowed = rows((72, 290), (72 + offset, 290 + offset), dy, heading)
        yield 'L1 ragged stacked controls', repr(args), pdf_rows, both, allowed
    for args in product([(160, 200), (180, 218), (200, 240), (160, 160), (200, 200), (240, 240)],
                        [100, 160, 220], new.HEADINGS, [False, True]):
        (width, other_width), dy, heading, both = args
        pdf_rows, allowed = rows((306 - width / 2, 306 + width / 2),
                                 (306 - other_width / 2, 306 + other_width / 2), dy, heading)
        yield 'L1 centred stacked controls', repr(args), pdf_rows, both, allowed
