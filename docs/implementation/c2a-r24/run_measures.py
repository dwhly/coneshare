"""Run independent evidence processes and retain their completion codes."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
PARTS = ('workers24', 'attack', 'boundary', 'veto', 'new', 'historical', 'review',
         'layouts', 'wrapped', 'stress', 'q2', 'extra', 'workers')


def run(part):
    with (OUT / (part + '-replay.txt')).open('x') as log:
        proc = subprocess.run([sys.executable, str(OUT / 'measure.py'), part],
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                              stdout=log, stderr=subprocess.STDOUT)
    return part, proc.returncode


if __name__ == '__main__':
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(run, p) for p in PARTS]
        for job in as_completed(jobs):
            name, rc = job.result()
            results[name] = rc
            print(name, 'rc=' + str(rc), flush=True)
    (OUT / 'measure-returncodes.json').write_text(json.dumps(results, indent=2) + '\n')
    sys.exit(int(any(results.values())))
