"""Complete inherited jobs whose original log names collided with new reviews."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def run(part):
    with (OUT / (part + '-inherited-run.txt')).open('x') as log:
        proc = subprocess.run([sys.executable, str(OUT / 'replay28.py'), part,
                               str(OUT / 'final'), str(OUT / 'r28-source.py.txt')],
                              cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return part, proc.returncode


with ThreadPoolExecutor(max_workers=2) as pool:
    codes = dict(pool.map(run, ('new', 'workers')))
with (OUT / 'gap-returncodes.json').open('x') as stream:
    json.dump(codes, stream, indent=2)
print(codes)
sys.exit(int(any(codes.values())))
