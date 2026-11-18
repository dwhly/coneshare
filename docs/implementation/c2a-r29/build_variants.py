"""Build review suggestion and bounded hold-only variants from frozen c2a.28."""
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = (OUT / 'r28-source.py.txt').read_text()
HELPER = '''def printed_name_boundary(block, blocks, texts, rules, roles):
    """Keep a borrowed printed identity as competition, but veto its placement."""
    line = block.line
    left = min(line.x0, line.label.get('rect', [line.x0])[0])

    def party(text):
        text = re.sub(r'^(?:signed\\s+)?for and on behalf of\\s+', '', text, flags=re.I)
        key = text.rstrip(': ').lower()
        mapped = roles.get(key, roles.get(key.removeprefix('the ')))
        company = mapped or (behalf_parts(text) or ('', text))[1]
        if mapped or (company_text(company) and not BLOCK_WORDING.fullmatch(company)):
            return tuple(t for t in tokens(company) if t not in STOP)
        return ()

    own_party = party(block.heading)
    for row in block.raw_labels:
        # Inspect only rows that actually contribute a printed identity to this
        # column. Evidence assigned to a neighbouring rule remains competition.
        single = replace(block, raw_labels=[row])
        names, ambiguous = printed_name_evidence(single, blocks)
        if not names or ambiguous:
            continue
        x0, y0, x1, _ = row['rect']
        if x0 >= line.x1 or x1 <= left:
            return True
        headings = [t for t in texts if t is not row and party(t['text'])
                    and t['rect'][0] < x1 and t['rect'][2] > x0]
        above = [t for t in headings if t['rect'][3] <= y0]
        nearest = max(above, key=lambda t: t['rect'][3], default=None)
        if (nearest is not None and own_party and party(nearest['text']) != own_party
                and y0 - nearest['rect'][3] < 125):
            return True
        # A heading between a leading name and this rule closes the earlier
        # party's identity; a heading below this rule begins a separate block.
        if any(min(line.y, y0) < t['rect'][1] < max(line.y, y0)
               for t in headings):
            return True
        DATE_GUARD
    return False


'''
for name, date_guard in [('suggested', ''), ('bounded', '''# A completed signature/date stack cannot absorb a later ruleless
        # name. A companion Date is a boundary even without a party heading.
        if any(line.y < r.y < y0 and r.semantic == 'DATE'
               and r.x1 > left and r.label.get('rect', [r.x0])[0] < line.x1
               for r in rules):
            return True''')]:
    src = BASE.replace('from dataclasses import dataclass, field', 'from dataclasses import dataclass, field, replace')
    src = src.replace('    unclaimed_cross_page: bool = False', '    unclaimed_cross_page: bool = False\n    printed_name_blocked: bool = False')
    src = src.replace('def extract(pdf, *, deadline=None):', HELPER.replace('DATE_GUARD',date_guard) + 'def extract(pdf, *, deadline=None):')
    src = src.replace('        texts, rules, _ = pages[block.line.page]\n        if shared_company_heading', '        texts, rules, _ = pages[block.line.page]\n        block.printed_name_blocked = printed_name_boundary(block, blocks, texts, rules, roles)\n        if shared_company_heading')
    src = src.replace("        result['status'] = 'placed'", "        if any(blocks[j].printed_name_blocked and scores[i][j] >= 6\n               for i, (j, _) in accepted.items()):\n            return hold(result, 'ambiguous_identity',\n                        'A printed name crosses a signing boundary and requires placement review.')\n        result['status'] = 'placed'")
    (OUT / (name + '-source.py.txt')).write_text(src)
