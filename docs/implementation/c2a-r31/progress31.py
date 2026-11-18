"""Read-only compact progress across the release validations."""
import json
from pathlib import Path

out = Path(__file__).resolve().parent
summaries = list((out/'shipping-inherited').glob('*-summary.json'))
rows = [json.loads(p.read_text()) for p in summaries]
print('Inherited:', len(rows), '/ 27 families,', sum(r['cases'] for r in rows), 'cells,',
      sum(g.get('r31_raw_wrong', 0) for r in rows for g in r['groups'].values()), 'raw wrong')
for prefix in ('shipping-', 'rechecked-review-'):
    for p in sorted(out.glob(prefix+'*-summary.json')):
        r = json.loads(p.read_text()); c = r.get('counts', {})
        print(r.get('family',p.name),r.get('cases'), 'wrong',c.get('r31_w',0),
              'vs-live nc/nw/cw',*(c.get('r29_to_r31_'+k,0) for k in ('nc','nw','cw')))
for p in sorted(out.glob('shipping-full-suite-part*.txt')):
    s = p.read_text();print(p.name, s[-100:].replace('\n',' | '))
for name in ('shipping-inherited-run.txt','shipping-matrices-run.txt','shipping-review-run.txt','shipping-full-suite-run.txt'):
    p=out/name
    print(name, p.read_text()[-200:].replace('\n',' | '))
