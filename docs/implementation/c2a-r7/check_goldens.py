"""Record fixture results and compare exact placement and native fields to r4/r5."""
import hashlib
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / 'backend'))
from dealroom_sign.placement import place, to_native_fields
from dealroom_sign.tests.test_placement import EXPECTED, FIXTURES, assert_golden, model_answer

out = Path(__file__).resolve().parent
baselines = {revision: json.loads((out.parent / revision / 'placements.json').read_text())
             for revision in ('c2a-r4', 'c2a-r5')}
results, summary = {}, {}
os.environ.pop('OPENROUTER_API_KEY', None)
os.environ.pop('PLACE_MODEL', None)
keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
for name, golden in EXPECTED['fixtures'].items():
    pdf = (FIXTURES / (name + '.pdf')).read_bytes()
    signers = golden['signers']
    result = place(pdf, signers, model_client=model_answer if name == 'unusual' else None)
    if name == 'bare':
        assert result['status'] == 'bare' and not result['fields']
    else:
        assert_golden(result, name, signers)
    actual = [{k: f[k] for k in keys} for f in result['fields']]
    native = [to_native_fields(result, s['email']) for s in signers]
    comparisons = {}
    for revision, baseline in baselines.items():
        previous = baseline[name]
        assert result['status'] == previous['status'], (name, revision)
        assert actual == [{k: f[k] for k in keys} for f in previous['fields']], (name, revision)
        assert native == [to_native_fields(previous, s['email']) for s in signers], (name, revision)
        comparisons[revision] = {'exact_geometry_confidence': True, 'exact_native_fields': True}
    results[name] = result
    summary[name] = {'status': result['status'], 'fields': len(actual), 'comparisons': comparisons,
                     'sha256': hashlib.sha256(pdf).hexdigest()}
(out / 'placements.json').write_text(json.dumps(results, indent=2) + '\n')
(out / 'golden-comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
