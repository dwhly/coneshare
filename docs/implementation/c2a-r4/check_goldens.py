"""Record exact fixture outcomes and compare every field to the r3 artifact."""
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
baseline = json.loads((out.parent / 'c2a-r3/placements.json').read_text())
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
    previous = [{k: f[k] for k in keys} for f in baseline[name]['fields']]
    assert actual == previous, (name, actual, previous)
    native = [to_native_fields(result, s['email']) for s in signers]
    old_native = [to_native_fields(baseline[name], s['email']) for s in signers]
    assert native == old_native, name
    results[name] = result
    summary[name] = {'status': result['status'], 'fields': len(actual), 'exact_r3_geometry': True,
                     'exact_r3_native_fields': True, 'sha256': hashlib.sha256(pdf).hexdigest()}
(out / 'placements.json').write_text(json.dumps(results, indent=2) + '\n')
(out / 'golden-comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
