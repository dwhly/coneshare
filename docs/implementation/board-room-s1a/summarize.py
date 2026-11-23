"""Compare the retained current/base pytest logs without discarding failed node IDs."""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent
results = {}
lines = []
for suite in ('packages', 'full'):
    sides = {}
    for side, filename in [('base', f'base-{suite}.txt'), ('current', f'{suite}.txt')]:
        text = (root / filename).read_text()
        summaries = [line for line in text.splitlines()
                     if re.match(r'\d+ (failed|passed|error)', line) and ' in ' in line]
        if not summaries:
            raise SystemExit(f'No completed pytest summary in {filename}')
        failures = sorted(set(re.findall(r'^(?:FAILED|ERROR) (.+?)(?: - |$)', text, re.M)))
        sides[side] = {'summary': summaries[-1], 'failures': failures}
    before, after = set(sides['base']['failures']), set(sides['current']['failures'])
    sides['new_failures'] = sorted(after - before)
    sides['resolved_failures'] = sorted(before - after)
    results[suite] = sides
    lines += [suite, 'BASE: ' + sides['base']['summary'], 'CURRENT: ' + sides['current']['summary'],
              'Pre-existing failures retained:'] + sorted(before & after)
    lines += ['Resolved baseline failures:'] + sides['resolved_failures']
    lines += ['New failures:'] + (sides['new_failures'] or ['None']) + ['']
(root / 'comparison.json').write_text(json.dumps(results, indent=2) + '\n')
(root / 'pre-existing-failures.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
