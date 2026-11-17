"""Record compact r8 placements; assert unchanged goldens and review layouts."""
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))

from dealroom_sign import placement  # noqa: E402
from dealroom_sign.tests.test_placement import (  # noqa: E402
    EXPECTED, FIXTURES, assert_golden, model_answer,
)
from dealroom_sign.tests.test_placement_r8 import (  # noqa: E402
    CAPTIONS, HOST_Y, LAYOUTS, NEIGHBOUR_Y, confirming_model, layout_pdf, layout_signers,
)

OUT = Path(__file__).resolve().parent
os.environ.pop('OPENROUTER_API_KEY', None)
os.environ.pop('PLACE_MODEL', None)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def compact(result):
    return {**{key: result[key] for key in ('status', 'reason_code', 'analysis_version')},
            'model': result['model'],
            'fields': [{**{key: field[key] for key in ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')},
                        'line': field['evidence']['line']} for field in result['fields']]}


def main():
    baselines = {revision: json.loads((OUT.parent / revision / 'placements.json').read_text())
                 for revision in ('c2a-r4', 'c2a-r5')}
    results, comparisons = {}, {}
    keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
    for name, golden in EXPECTED['fixtures'].items():
        pdf = (FIXTURES / (name + '.pdf')).read_bytes()
        signers = golden['signers']
        result = placement.place(pdf, signers, model_client=model_answer if name == 'unusual' else None)
        if name == 'bare':
            assert result['status'] == 'bare' and not result['fields']
        else:
            assert_golden(result, name, signers)
        actual = [{key: field[key] for key in keys} for field in result['fields']]
        native = [placement.to_native_fields(result, signer['email']) for signer in signers]
        for revision, baseline in baselines.items():
            previous = baseline[name]
            assert result['status'] == previous['status'], (name, revision)
            assert actual == [{key: field[key] for key in keys} for field in previous['fields']], (name, revision)
            assert native == [placement.to_native_fields(previous, signer['email']) for signer in signers], (name, revision)
        results[name] = result
        comparisons[name] = {'status': result['status'], 'fields': len(actual),
                             'exact_geometry_confidence_and_native': list(baselines),
                             'pdf_sha256': hashlib.sha256(pdf).hexdigest()}
    write('placements.json', results)
    write('golden-comparison.json', comparisons)

    regressions = {'B-1': {}, 'defence_alone': {}, 'M-1': {}, 'L-1': {}, 'signature_controls': {}}
    for layout in LAYOUTS:
        for caption in CAPTIONS:
            source, signers = layout_pdf(layout, caption), layout_signers(layout)
            result = placement.place(source, signers)
            assert result['status'] == 'needs_sender' and result['fields'] == []
            blocks, _, _ = placement.extract(source)
            candidates = [b.line.y for b in blocks]
            assert HOST_Y[layout] in candidates
            regressions['B-1'][layout + '/' + caption] = dict(compact(result), candidate_rules=candidates)
            if layout in {'C8', 'C12', 'C13'}:
                with patch.object(placement, 'subordinate_caption', return_value=True):
                    blocks, sizes, roles = placement.extract(source)
                assert [b.line.y for b in blocks] == [NEIGHBOUR_Y[layout]]
                assert blocks[0].uncertain_identity
                placement.prepare_blocks(blocks, roles, signers)
                assert blocks[0].scores == [0]
                model = Mock()
                with patch.object(placement, 'bounded_extract', return_value=(blocks, sizes, roles)):
                    result = placement.place(source, signers, model_client=model)
                assert result['status'] == 'needs_sender' and result['fields'] == []
                model.assert_not_called()
                regressions['defence_alone'][layout + '/' + caption] = dict(
                    compact(result), candidate_rules=[blocks[0].line.y], uncertain_identity=True, scores=[0])
        result = placement.place(layout_pdf(layout, 'Signature:'), layout_signers(layout))
        assert result['status'] == ('placed' if layout == 'C12' else 'needs_sender')
        regressions['signature_controls'][layout] = compact(result)
    for caption in CAPTIONS:
        model = Mock(side_effect=confirming_model)
        result = placement.place(layout_pdf('C7', caption), layout_signers('C7'), model_client=model)
        assert result['status'] == 'placed'
        assert {c['line'][1] for c in model.call_args.args[0]['candidates']} == {340, 400}
        assert {(f['type'], f['evidence']['line'][1]) for f in result['fields']} == {('SIGNATURE', 400), ('DATE', 430)}
        regressions['M-1'][caption] = dict(compact(result), model_candidate_rules=[340, 400])
    result = placement.place(layout_pdf('only'), layout_signers('only'), model_client=confirming_model)
    assert result['status'] == 'placed' and all(f['confidence'] == 'model-high' for f in result['fields'])
    regressions['L-1']['Authorised signatory:'] = compact(result)
    assert not hasattr(placement, 'MODEL_SIGNATURE_CAPTION')
    write('regression-placements.json', regressions)
    print('Seven goldens exact against r4/r5, including native fields; 51 review-layout outcomes verified.')


if __name__ == '__main__':
    main()
