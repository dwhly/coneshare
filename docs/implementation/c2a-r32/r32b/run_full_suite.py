"""Run every collected Send test in isolated pytest processes, without -x."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
EVIDENCE = OUT.parent
ROOT = OUT.parents[3]
source = ROOT/'backend/dealroom_sign/placement.py'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source.read_bytes() == (EVIDENCE/'shipping-source.py.txt').read_bytes()
command = [sys.executable,str(EVIDENCE/'run_tests.py')]
collection = subprocess.run([*command,'dealroom_sign/tests','--collect-only'],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(OUT/'shipping-full-collection.txt').write_text(collection.stdout)
assert collection.returncode == 0, collection.stdout[-2000:]
nodes = [line for line in collection.stdout.splitlines()
         if line.startswith('dealroom_sign/tests/') and '::' in line]
assert len(nodes) == len(set(nodes)) and len(nodes) > 58058, len(nodes)
files = sorted({n.split('::',1)[0] for n in nodes})
counts = Counter(n.split('::',1)[0] for n in nodes)
prior = list(ET.parse(EVIDENCE.parent/'c2a-r29/full-suite-complete.xml').getroot().iter('testcase'))
times = Counter()
for case in prior:
    name = case.attrib['classname'].replace('.', '/') + '.py'
    if name in files:
        times[name] += float(case.get('time','0'))
# New matrix tests use in-process parsing; allocate their measured duration.
for f in files:
    if f not in times:
        times[f] = max(1, counts[f] * .025)
shards = [[] for _ in range(4)]
loads = [0.] * 4
for f in sorted(files,key=lambda f:times[f],reverse=True):
    i = min(range(4),key=loads.__getitem__)
    shards[i].append(f); loads[i] += times[f]
(OUT/'shipping-full-suite-manifest.json').write_text(json.dumps(dict(
    source_sha256=source_hash,collected=len(nodes),files=len(files),
    shards=shards,estimated_seconds=loads,skip_filters=False,fail_fast=False),indent=2)+'\n')

def run(i):
    with (OUT/f'shipping-full-suite-part{i}.txt').open('x') as log:
        result = subprocess.run([*command,*shards[i],'--tb=short',
            f'--junitxml=../docs/implementation/c2a-r32/r32b/shipping-full-suite-part{i}.xml'],
            stdout=log,stderr=subprocess.STDOUT)
    return i,result.returncode

codes = {}
with ThreadPoolExecutor(max_workers=4) as pool:
    for future in as_completed([pool.submit(run,i) for i in range(4)]):
        i,code = future.result();codes[str(i)] = code; print('part',i,'rc',code,flush=True)
merged = ET.Element('testsuites')
actual = []
for i in range(4):
    root = ET.parse(OUT/f'shipping-full-suite-part{i}.xml').getroot()
    for suite in root:
        suite.set('name',f'pytest-part{i}')
        merged.append(copy.deepcopy(suite))
        for case in suite.iter('testcase'):
            path = case.attrib['classname'].replace('.','/') + '.py'
            actual.append(path+'::'+case.attrib['name'])
assert Counter(actual) == Counter(nodes), (len(actual),len(nodes),list((Counter(nodes)-Counter(actual)).elements())[:10])
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
ET.ElementTree(merged).write(OUT/'shipping-full-suite-complete.xml',encoding='utf-8',xml_declaration=True)
summary = dict(passed=0,failed=0,errors=0,skipped=0)
for case in merged.iter('testcase'):
    status = ('failed' if case.find('failure') is not None else 'errors' if case.find('error') is not None
              else 'skipped' if case.find('skipped') is not None else 'passed')
    summary[status] += 1
(OUT/'shipping-full-suite-completion.json').write_text(json.dumps(dict(returncodes=codes,
    source_sha256=source_hash,collected_ids_exact=True,counts=summary),indent=2)+'\n')
print(json.dumps(summary),flush=True)
sys.exit(int(any(codes.values()) or any(summary[k] for k in ('failed','errors','skipped'))))
