"""Execute the review matrices and record compact placements, without model I/O."""
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
    EXPECTED, FIXTURES, LEE, assert_golden, model_answer,
)
from dealroom_sign.tests.test_placement_r3 import PAT  # noqa: E402
from dealroom_sign.tests.test_placement_r6 import contact_rule_pdf  # noqa: E402
from dealroom_sign.tests.test_placement_r8 import (  # noqa: E402
    LAYOUTS, confirming_model, layout_pdf, layout_signers,
)
from dealroom_sign.tests.test_placement_r9 import (  # noqa: E402
    BETWEEN, CAPTIONS, FLEET, HARBOR, HEADINGS, PARTIES, assert_identity_hold,
    behalf_right_pdf, heading_pdf, heading_rows, rows_pdf, stack_pdf,
)

OUT = Path(__file__).resolve().parent
os.environ.pop('OPENROUTER_API_KEY', None)
os.environ.pop('PLACE_MODEL', None)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def compact(result):
    return {**{key: result[key] for key in ('status', 'reason_code', 'analysis_version', 'model')},
            'fields': [{**{key: field[key] for key in ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')},
                        'line': field['evidence']['line']} for field in result['fields']]}


def held(source, signers=PAT):
    result = placement.place(source, signers)
    assert result['status'] == 'needs_sender' and result['fields'] == [], result
    return compact(result)


def goldens():
    baselines = {rev: json.loads((OUT.parent / rev / 'placements.json').read_text())
                 for rev in ('c2a-r4', 'c2a-r5')}
    results, comparisons = {}, {}
    keys = ('signer', 'type', 'page', 'x', 'y', 'w', 'h', 'confidence')
    for name, golden in EXPECTED['fixtures'].items():
        source = (FIXTURES / (name + '.pdf')).read_bytes()
        signers = golden['signers']
        result = placement.place(source, signers, model_client=model_answer if name == 'unusual' else None)
        if name == 'bare':
            assert result['status'] == 'bare' and result['fields'] == []
        else:
            assert_golden(result, name, signers)
        actual = [{key: f[key] for key in keys} for f in result['fields']]
        for rev, baseline in baselines.items():
            previous = baseline[name]
            assert result['status'] == previous['status'], (name, rev)
            assert actual == [{key: f[key] for key in keys} for f in previous['fields']], (name, rev)
            for signer in signers:
                assert placement.to_native_fields(result, signer['email']) == placement.to_native_fields(
                    previous, signer['email']), (name, rev)
        # Observe classifications locally; placement above uses the real worker.
        original = placement.subordinate_caption
        decisions = []

        def observed(*args):
            decision = original(*args)
            decisions.append(decision)
            return decision

        with patch.object(placement, 'subordinate_caption', side_effect=observed):
            placement.extract(source)
        assert not any(decisions), name
        results[name] = result
        comparisons[name] = {'status': result['status'], 'fields': len(actual),
                             'exact_geometry_confidence_and_native': list(baselines),
                             'subordinate_caption_calls': len(decisions), 'rules_subordinated': sum(decisions),
                             'pdf_sha256': hashlib.sha256(source).hexdigest()}
    write('placements.json', results)
    write('golden-comparison.json', comparisons)


def regressions():
    results = {'B-1': [], 'same_row_right_behalf': [], 'H-1': [], 'signature_controls': []}
    for layout in ('C12', 'C13'):
        for heading in HEADINGS:
            for caption in CAPTIONS:
                result = assert_identity_hold(heading_pdf(layout, heading, caption), PAT)
                results['B-1'].append(dict(layout=layout, heading=heading, caption=caption,
                                          **compact(result), uncertain_identity=True, scores=[0], model_calls=0))
            result = placement.place(heading_pdf(layout, heading, 'Signature:'), PAT)
            if layout == 'C12':
                assert result['status'] == 'placed'
                assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
                    ('SIGNATURE', 360, 'high'), ('DATE', 395, 'high'),
                }
            else:
                assert result['status'] == 'needs_sender' and result['fields'] == []
            results['signature_controls'].append(dict(layout=layout, heading=heading, **compact(result)))
    for caption in CAPTIONS:
        result = assert_identity_hold(behalf_right_pdf(caption), PAT)
        results['same_row_right_behalf'].append(dict(caption=caption, **compact(result)))
        for company, name, signers in PARTIES:
            for between in BETWEEN:
                result = assert_identity_hold(stack_pdf(company, name, between, caption), signers)
                results['H-1'].append(dict(company=company, signer=name, between=between, caption=caption,
                                          **compact(result), uncertain_identity=True, scores=[0], model_calls=0))
    write('regression-placements.json', results)
    return {key: len(value) for key, value in results.items()}


def preservation():
    results = {'column_bands': {}, 'recognised_headings': {}, 'no_typed_name': {},
               'original_layouts': {}, 'forced_subordination': {}, 'model_paths': {}, 'contacts': {}}
    for caption in CAPTIONS:
        for wide in (False, True):
            rows = [(260, FLEET, False), (300, 'By:', True, 72, 400 if wide else 290),
                    (330, HARBOR, False, 330), (360, caption, True, 330),
                    (372, 'Name: Pat Smith', False, 330), (395, 'Date:', True, 330)]
            results['column_bands'][('wide' if wide else 'two_column') + '/' + caption] = held(rows_pdf(rows))
        rows = heading_rows('C12', HARBOR, caption)
        rows[3:] = [(*row, 200) for row in rows[3:]]
        results['column_bands']['indented/' + caption] = held(rows_pdf(rows))
        for layout in ('C12', 'C13'):
            headings = [HARBOR, 'Harbor Light Analytics, Inc.', 'HARBOR LIGHT',
                        'For and on behalf of ' + HARBOR, 'two-line Delaware']
            for heading in headings:
                rows = heading_rows(layout, HARBOR if heading == 'two-line Delaware' else heading, caption)
                if heading == 'two-line Delaware':
                    y = 344 if layout == 'C12' else 359
                    rows.append((y, 'a Delaware corporation', False))
                results['recognised_headings'][layout + '/' + heading + '/' + caption] = held(rows_pdf(rows))
            for heading in HEADINGS:
                for name in ('Name:', None):
                    rows = heading_rows(layout, heading, caption)
                    rows = [(y, name, rule) if text == 'Name: Pat Smith' else (y, text, rule)
                            for y, text, rule in rows if name is not None or text != 'Name: Pat Smith']
                    key = '/'.join((layout, heading, name or 'no name', caption))
                    results['no_typed_name'][key] = held(rows_pdf(rows))
        for layout in LAYOUTS:
            results['original_layouts'][layout + '/' + caption] = held(layout_pdf(layout, caption), layout_signers(layout))
            if layout in {'C8', 'C12', 'C13'}:
                source = layout_pdf(layout, caption)
                with patch.object(placement, 'subordinate_caption', return_value=True):
                    blocks, sizes, roles = placement.extract(source)
                assert len(blocks) == 1 and blocks[0].uncertain_identity
                placement.prepare_blocks(blocks, roles, PAT)
                assert blocks[0].scores == [0]
                model = Mock()
                with patch.object(placement, 'bounded_extract', return_value=(blocks, sizes, roles)):
                    result = placement.place(source, PAT, model_client=model)
                assert result['status'] == 'needs_sender' and result['fields'] == []
                model.assert_not_called()
                results['forced_subordination'][layout + '/' + caption] = dict(compact(result), scores=[0], model_calls=0)
        for layout in ('C7', 'only'):
            model = Mock(side_effect=confirming_model)
            result = placement.place(layout_pdf(layout, caption), layout_signers(layout), model_client=model)
            assert result['status'] == 'placed' and model.call_count == 1
            assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
                ('SIGNATURE', 400, 'model-high'), ('DATE', 430, 'model-high'),
            }
            candidates = [c['line'][1] for c in model.call_args.args[0]['candidates']]
            assert candidates == ([340, 400] if layout == 'C7' else [400])
            results['model_paths'][layout + '/' + caption] = dict(compact(result), candidate_rules=candidates)
    results['column_bands']['Fax_other_band'] = held(rows_pdf([
        (360, HARBOR, False), (400, 'By:', True), (430, 'Date:', True),
        (460, 'Fax:', True, 330), (472, 'Name: Lee Harbor', False, 330),
    ]))
    contacts = ['Email', 'E-mail', 'Address', 'Phone', 'Tel', 'Company']
    for label in contacts + ['Fax', 'Mobile', 'Contact', 'Attention', 'Notice Address', 'Initials', 'Sign']:
        for name, signers in [('Lee Harbor', PAT), ('Lee Harbor', LEE), ('Pat Smith', PAT)]:
            result = placement.place(contact_rule_pdf(label, name), signers)
            expected_placed = label in contacts and name == signers[0]['name']
            assert result['status'] == ('placed' if expected_placed else 'needs_sender')
            if expected_placed:
                assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
                    ('SIGNATURE', 400, 'high'), ('DATE', 430, 'high'),
                }
            else:
                assert result['fields'] == []
            results['contacts']['/'.join((label, name, signers[0]['name']))] = compact(result)
    write('preservation-placements.json', results)
    return {key: len(value) for key, value in results.items()}


def main():
    goldens()
    counts = {'analysis_version': placement.VERSION, 'goldens': 7,
              'review_matrix': regressions(), 'preservation': preservation(),
              'execution': 'Real reportlab PDFs through the placement worker, except forced-subordination isolation.',
              'external_model_calls': 0}
    write('placement-summary.json', counts)
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
