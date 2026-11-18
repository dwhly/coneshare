"""Run independent matrix processes and retain each log and return code."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys
OUT = Path(__file__).resolve().parent
label, *versions = sys.argv[1:]
families = ['date', 'hidden', 'two_columns', 'no_rule', 'geometry', 'ruleless_name']
if label == 'release':
    families += ['ordinary_offsets', 'stray']
def run(family):
    with (OUT / (label + '-' + family + '.txt')).open('x') as log:
        result = subprocess.run([sys.executable, str(OUT/'measure30.py'), family, label, *versions], stdout=log, stderr=subprocess.STDOUT)
    return family, result.returncode
codes = {}
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run, family) for family in families]):
        family, code = future.result(); codes[family] = code; print(family, code, flush=True)
(OUT / (label + '-returncodes.json')).write_text(json.dumps(codes, indent=2)+'\n')
sys.exit(int(any(codes.values())))
