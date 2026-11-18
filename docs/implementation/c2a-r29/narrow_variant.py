"""Preserve established inline and explicitly exempt contact-row controls."""
from pathlib import Path

OUT = Path(__file__).resolve().parent
s = (OUT/'final-source.py.txt').read_text()
helper = '''def printed_name_column(row, line):
    """A caption-row continuation can sit just beyond the drawn rule end."""
    x0, top, x1, bottom = row['rect']
    left = min(line.x0, line.label.get('rect', [line.x0])[0])
    if x0 < line.x1 and x1 > left:
        return True
    # Preserve the existing inline-signature control, using the text-row gap
    # limit. This does not extend a column to names above or below the rule.
    return (line.semantic == 'SIGNATURE' and top <= line.y <= bottom
            and 0 <= x0 - line.x1 <= 24)


'''
s = s.replace('def printed_name_boundary(', helper+'def printed_name_boundary(')
old="""        x0, y0, x1, _ = row['rect']
        if x0 >= line.x1 or x1 <= left:
            return True"""
new="""        x0, y0, x1, _ = row['rect']
        # Preserve only the six explicit contact captions already exempt in
        # extraction; an absorbed unknown signing caption is not a contact.
        contacts = [r for r in rules if line.y < r.y and -10 <= y0 - r.y < 125
                    and re.fullmatch(r'(?:email|e-mail|address|phone|tel|company)\\s*:\\s*',
                                     r.label.get('text', ''), re.I)
                    and (printed_name_column(row, r)
                         or (y0 <= r.y <= row['rect'][3] and 0 <= x0 - r.x1 <= 24))]
        if contacts and not any(line.y < t['rect'][1] < y0 and party(t['text'])
                                and t['rect'][0] < max(x1, line.x1)
                                and t['rect'][2] > min(x0, left) for t in texts):
            continue
        if not printed_name_column(row, line):
            return True"""
assert old in s;s=s.replace(old,new)
old="""                and not any(r.semantic not in COMPANION_SEMANTICS
                            and t['rect'][0] < r.x1
                            and t['rect'][2] > r.label.get('rect', [r.x0])[0]
                            for r in rules)"""
new="""                and not any((r.semantic not in COMPANION_SEMANTICS
                             or re.fullmatch(r'(?:email|e-mail|address|phone|tel|company)\\s*:\\s*',
                                             r.label.get('text', ''), re.I))
                            and (printed_name_column(t, r)
                                 or (t['rect'][1] <= r.y <= t['rect'][3]
                                     and 0 <= t['rect'][0] - r.x1 <= 24))
                            for r in rules)"""
assert old in s;s=s.replace(old,new)
(OUT/'narrow-source.py.txt').write_text(s)
