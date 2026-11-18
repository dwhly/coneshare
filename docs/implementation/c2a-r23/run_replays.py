"""Run independent evidence processes; retain every return code and log."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
JOBS = [('q2_replay.py', 'workers'), ('replay.py', 'new'), ('replay.py', 'historical'),
        ('q2_replay.py', 'q2'), ('replay.py', 'review'), ('replay.py', 'layouts'),
        ('replay.py', 'wrapped'), ('q2_replay.py', 'extra'), ('stress.py', None)]


def run(job):
    script, part = job
    name = part or 'stress'
    with (OUT / (name + '-replay.txt')).open('w') as log:
        proc = subprocess.run([sys.executable, str(OUT / script), *([part] if part else [])],
                              cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                              stdout=log, stderr=subprocess.STDOUT)
    return name, proc.returncode


if __name__ == '__main__':
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run, job) for job in JOBS]
        for future in as_completed(futures):
            name, rc = future.result()
            results[name] = rc
            print(name, 'rc=' + str(rc), flush=True)
    (OUT / 'replay-returncodes.json').write_text(json.dumps(results, indent=2) + '\n')
    sys.exit(int(any(results.values())))
