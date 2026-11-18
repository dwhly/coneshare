"""Construct the two proposed boundary experiments from untouched c2a.29."""
from pathlib import Path
OUT = Path(__file__).resolve().parent
source = (OUT / 'r29-source.py.txt').read_text()
old = """        if any(line.y < r.y < y0 - 22 and r.semantic == 'DATE'
               and r.x1 > left and r.label.get('rect', [r.x0])[0] < line.x1
               for r in rules):"""
variants = {
    'heading_or_rule': """        if any(line.y < r.y < y0 - 22 and r.semantic == 'DATE'
               and r.x1 > left and r.label.get('rect', [r.x0])[0] < line.x1
               for r in rules) and any(
                   line.y < r.y < y0 and r.semantic not in {'DATE', 'NAME', 'TITLE'}
                   and r.x1 > left and r.label.get('rect', [r.x0])[0] < line.x1
                   for r in rules):""",
    'row_pitch': """        if any(line.y < r.y < y0 - max(22, 2 * (r.y - line.y))
               and r.semantic == 'DATE'
               and r.x1 > left and r.label.get('rect', [r.x0])[0] < line.x1
               for r in rules):""",
}
assert source.count(old) == 1
for name, replacement in variants.items():
    (OUT / (name + '-source.py.txt')).write_text(source.replace(old, replacement))
