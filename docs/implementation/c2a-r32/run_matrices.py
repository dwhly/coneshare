"""Execute each exact review family against live r29, r31 and r32."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
FAMILIES = ('affiliate_sender', 'misspell', 'misspell_sender', 'role_other', 'same_company', 'prev_column',
            'plain', 'swap', 'date', 'hidden', 'two_columns', 'no_rule', 'geometry',
            'ruleless_name', 'ordinary_offsets', 'stray', 'narrow_affiliate', 'narrow_affiliate_matrix')

def run(family):
    with (OUT / ('shipping-' + family + '.txt')).open('x') as log:
        result = subprocess.run([sys.executable, str(OUT / 'measure32.py'), family,
                                'shipping', 'r29', 'r31', 'r32'], stdout=log, stderr=subprocess.STDOUT,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return family, result.returncode

codes = {}
with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(run, family) for family in FAMILIES]):
        family, code = future.result(); codes[family] = code
        print(family, code, flush=True)
(OUT / 'shipping-matrix-returncodes.json').write_text(json.dumps(codes, indent=2) + '\n')
sys.exit(int(any(codes.values())))
