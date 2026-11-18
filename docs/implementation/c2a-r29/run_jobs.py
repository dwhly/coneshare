"""Drain isolated replay processes and retain each exit code."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
mode = sys.argv[1]
if mode == 'experiments':
    jobs = [(f, ['measure29.py', f, 'r21', 'r27', 'r28', 'suggested', 'bounded'])
            for f in ('no_rule', 'geometry', 'ruleless_name')]
elif mode == 'inherited' or mode == 'final-inherited':
    from replay29 import PARTS
    jobs = [(f, ['replay29.py', f, str(OUT/('final-v2' if mode == 'final-inherited' else 'final')), str(OUT/('final-source.py.txt' if mode == 'final-inherited' else 'r29-source.py.txt'))]) for f in PARTS]
else:
    jobs = [(f, ['measure29.py', f, 'r21', 'r27', 'r28', 'r29']) for f in
            ('conformed', 'no_rule', 'geometry', 'ruleless_name', 'hidden', 'two_columns',
             'workers', 'variants', 'ordinary', 'stacks', 'recitals', 'r27', 'extended', 'notices')]

def run(job):
    name, args = job
    with (OUT/(mode+'-'+name+'-run.txt')).open('x') as log:
        result = subprocess.run([sys.executable, str(OUT/args[0]), *args[1:]], cwd=ROOT,
            stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', R29_MEASURE_PREFIX=mode+'-', R29_CANDIDATE_SOURCE=os.environ.get('R29_CANDIDATE_SOURCE', ('narrow2-source.py.txt' if mode == 'release-review' else 'final-source.py.txt' if mode.startswith('final-') else 'r29-source.py.txt'))))
    return name, result.returncode

codes = {}
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run, job) for job in jobs]):
        name, code = future.result(); codes[name] = code; print(name, code, flush=True)
with (OUT/(mode+'-returncodes.json')).open('x') as stream:
    json.dump(codes, stream, indent=2)
sys.exit(int(any(codes.values())))
