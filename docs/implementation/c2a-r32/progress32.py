"""Compact read-only progress for the release verification jobs."""
import json
from pathlib import Path

out=Path(__file__).resolve().parent
for name in ('shipping-full-suite-run.txt','shipping-matrices-run.txt','shipping-inherited-run.txt','shipping-review-run.txt','shipping-exact-workers.txt'):
 p=out/name
 if p.exists():
  lines=p.read_text().splitlines()
  print(name, ' | '.join(lines[-3:])[:450])
for p in sorted(out.glob('shipping-full-suite-part*.txt')):
 lines=p.read_text().splitlines()
 print(p.name, ' | '.join(lines[-2:])[:240])
for group in ('shipping-*-summary.json','shipping-inherited/*-summary.json'):
 files=list(out.glob(group))
 print(group, len(files), 'completed')
for p in sorted(out.glob('shipping-*-summary.json')):
 r=json.loads(p.read_text());c=r.get('counts',{})
 print(r.get('family',p.name),r.get('cases'), 'wrong',c.get('r32_w',0),'np',c.get('r29_to_r32_nc',0),'nW',c.get('r29_to_r32_nw',0),'cw',c.get('r29_to_r32_cw',0))
