"""Capture real-worker placement evidence and compare r11 with unchanged r10."""
from collections import Counter
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))

from dealroom_sign import placement  # noqa: E402
from dealroom_sign.tests.test_placement import (  # noqa: E402
    EXPECTED, FIXTURES, assert_golden, model_answer,
)
from dealroom_sign.tests.test_placement_r11 import (  # noqa: E402
    CROSS_CAPTIONS, CROSS_LAYOUTS, FORMS, HEADINGS, PAT,
    assert_cross_host_placement, host_extent_pdf,
)
from dealroom_sign.tests.test_placement_r10 import assert_stack_hold  # noqa: E402


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def versionless(result):
    return {key: value for key, value in result.items() if key != 'analysis_version'}


def compact(result, model_calls=0):
    return {
        **{key: result[key] for key in ('status', 'reason_code', 'analysis_version')},
        'fields': [{**{key: field[key] for key in ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')},
                    'line': field['evidence']['line']} for field in result['fields']],
        'model_calls': model_calls,
    }


def controls():
    results = {}
    for form, layout, heading in product(FORMS, ('C12', 'C13'), HEADINGS):
        model = Mock()
        result = placement.place(host_extent_pdf(layout, heading, 'Signature:', form), PAT, model_client=model)
        model.assert_not_called()
        results['/'.join((form, layout, heading))] = compact(result)
    return results


def grouped(results):
    groups = []
    for case, outcome in results.items():
        group = next((item for item in groups if item['outcome'] == outcome), None)
        if group is None:
            group = {'outcome': outcome, 'cases': []}
            groups.append(group)
        group['cases'].append(case)
    return groups


def goldens():
    before = json.loads((OUT / 'r10-golden-placements.json').read_text())
    older = {rev: json.loads((OUT.parent / rev / 'placements.json').read_text())
             for rev in ('c2a-r4', 'c2a-r5')}
    results, comparisons = {}, {}
    keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
    for name, golden in EXPECTED['fixtures'].items():
        source = (FIXTURES / (name + '.pdf')).read_bytes()
        model = Mock(side_effect=model_answer)
        result = placement.place(source, golden['signers'], model_client=model)
        if name == 'bare':
            assert result['status'] == 'bare' and result['fields'] == []
        else:
            assert_golden(result, name, golden['signers'])
        assert model.call_count == (1 if name == 'unusual' else 0)
        assert versionless(result) == versionless(before[name]), name
        for rev, baseline in older.items():
            assert result['status'] == baseline[name]['status'], (name, rev)
            assert [{key: field[key] for key in keys} for field in result['fields']] == [
                {key: field[key] for key in keys} for field in baseline[name]['fields']]
            for signer in golden['signers']:
                assert placement.to_native_fields(result, signer['email']) == placement.to_native_fields(
                    baseline[name], signer['email'])
        blocks, _, _ = placement.extract(source)
        assert not any(block.uncertain_identity for block in blocks)
        results[name] = result
        comparisons[name] = {
            'full_result_exact_except_analysis_version': '945ad159',
            'exact_geometry_confidence_and_native': list(older),
            'pdf_sha256': hashlib.sha256(source).hexdigest(),
            'model_calls': model.call_count,
        }
    write('placements.json', results)
    write('golden-comparison.json', comparisons)


def main():
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('PLACE_MODEL', None)
    forbidden = Mock(side_effect=AssertionError('External model I/O forbidden'))
    with patch('httpx.Client.send', forbidden):
        current_controls = controls()
        if sys.argv[1:] == ['baseline']:
            assert placement.VERSION == 'c2a.10'
            write('r10-signature-controls.json', grouped(current_controls))
            print(dict(Counter(result['status'] for result in current_controls.values())))
            return
        baseline = {case: group['outcome']
                    for group in json.loads((OUT / 'r10-signature-controls.json').read_text())
                    for case in group['cases']}
        assert {key: versionless(value) for key, value in current_controls.items()} == {
            key: versionless(value) for key, value in baseline.items()}
        goldens()
        cases = {}
        for form, layout in product(FORMS, ('C12', 'C13')):
            result = assert_stack_hold(host_extent_pdf(layout, 'RECIPIENT:', 'Firma:', form), PAT)
            cases['B-1/' + layout + '/' + form] = compact(result)
        for layout, caption in product(CROSS_LAYOUTS, CROSS_CAPTIONS):
            cases['M-1/' + layout + '/' + caption] = compact(assert_cross_host_placement(layout, caption))
        write('review-placements.json', grouped(cases))
        write('signature-controls.json', grouped(current_controls))
        forbidden.assert_not_called()
    summary = {
        'analysis_version': placement.VERSION,
        'production_sha256': hashlib.sha256(Path(placement.__file__).read_bytes()).hexdigest(),
        'execution': 'Real reportlab PDFs through placement.place and its parser subprocess.',
        'B-1_representatives': len(FORMS) * 2,
        'M-1_cases': len(CROSS_LAYOUTS) * len(CROSS_CAPTIONS),
        'Signature_controls_exact_to_r10': len(current_controls),
        'seven_goldens_exact_to_r10_except_version': True,
        'external_model_calls': 0, 'golden_model_stub_calls': 1,
        'raw_logs_retained': False,
    }
    write('placement-summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
