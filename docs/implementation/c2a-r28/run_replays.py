"""Run each complete replay in an isolated process, retaining all return codes."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def run(job):
    name, args = job
    with (OUT / (name + '-run.txt')).open('x') as log:
        proc = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT,
                              stdout=log, stderr=subprocess.STDOUT,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return name, proc.returncode


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'inherited':
        from replay28 import PARTS
        jobs = [(p, [OUT / 'replay28.py', p, OUT / 'final', OUT / 'r28-source.py.txt'])
                for p in PARTS if p != 'historical']
    else:
        jobs = [(p, [OUT / 'measure28.py', p, 'r21', 'r26', 'r27', 'r28'])
                for p in ('workers', 'ordinary', 'stacks', 'recitals', 'r27', 'extended')]
    codes = {}
    with ThreadPoolExecutor(max_workers=3 if mode == 'inherited' else 2) as pool:
        for future in as_completed([pool.submit(run, job) for job in jobs]):
            name, code = future.result()
            codes[name] = code
            print(name, code, flush=True)
    with (OUT / (mode + '-returncodes.json')).open('x') as stream:
        json.dump(codes, stream, indent=2)
    sys.exit(int(any(codes.values())))
