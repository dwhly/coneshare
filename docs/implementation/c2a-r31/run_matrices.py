"""Execute the exact current reviewer families on all comparison sources."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
FAMILIES = ('plain', 'swap', 'hidden', 'two_columns', 'no_rule', 'geometry',
            'ruleless_name', 'ordinary_offsets', 'stray')

def run(family):
    with (OUT / ('shipping-' + family + '.txt')).open('x') as log:
        result = subprocess.run([sys.executable, str(OUT/'measure31.py'), family,
            'shipping', 'r29', 'r28', 'r21', 'r30', 'r31'], stdout=log, stderr=subprocess.STDOUT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return family, result.returncode

codes = {}
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(run, family) for family in FAMILIES]):
        family, code = future.result(); codes[family] = code
        print(family, code, flush=True)
(OUT/'shipping-matrix-returncodes.json').write_text(json.dumps(codes, indent=2)+'\n')
sys.exit(int(any(codes.values())))
