"""Execute the review table against r11, r12, and A-prime without editing code.

Run with PYTHONDONTWRITEBYTECODE=1 and the supplied send-venv interpreter.
Table extraction is in-process, matching the review's counterfactual method;
the seven goldens additionally use the real worker. Pytest covers all matrix
families through the real worker, with separate per-case reports.
"""
from collections import Counter
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = '4ad9f7e20822ca15e8c5a5196f8b61c8cb59a312'
R11 = '0c190e9b45db25ee5c1b8d71cdc2b040cd956fab'
sys.path.insert(0, str(ROOT / 'backend'))

from dealroom_sign import placement  # noqa: E402
from dealroom_sign.tests.test_placement import (  # noqa: E402
    EXPECTED, FIXTURES, TWO, assert_golden, model_answer,
)
from dealroom_sign.tests.test_placement_r3 import PAT  # noqa: E402
from dealroom_sign.tests.test_placement_r8 import CAPTIONS  # noqa: E402
from dealroom_sign.tests import test_placement_r9 as r9  # noqa: E402
from dealroom_sign.tests import test_placement_r11 as r11  # noqa: E402
from dealroom_sign.tests import test_placement_r12 as r12  # noqa: E402
from dealroom_sign.tests import test_placement_r13 as r13  # noqa: E402


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def versionless(result):
    return {key: value for key, value in result.items() if key != 'analysis_version'}


def counterfactual_module(name, source):
    module = ModuleType(name)
    module.__file__ = placement.__file__
    sys.modules[name] = module
    exec(compile(source, '<' + name + '>', 'exec'), module.__dict__)
    return module


def in_process(module, pdf, signers, model):
    def bounded(pdf, deadline, signers):
        blocks, sizes, roles = module.extract(pdf, deadline=deadline)
        module.prepare_blocks(blocks, roles, signers)
        return blocks, sizes, roles

    with patch.object(module, 'bounded_extract', bounded):
        return module.place(pdf, signers, model_client=model)


def cases():
    for second, caption, heading, name in product(r12.SECOND_RULES, CAPTIONS, r12.HEADINGS, r12.NAMES):
        yield 'Matrix 1', '/'.join((second, caption, heading, name)), r12.matrix1_pdf(
            second, heading, caption, name), PAT
    for stack, caption, form, signer_set in product(r12.STACKS, CAPTIONS, r12.FORMS, r12.SIGNERS):
        yield 'Matrix 2', '/'.join((stack, caption, form, signer_set)), r12.matrix2_pdf(
            stack, caption, form), r12.SIGNERS[signer_set]
    for form, layout, heading, caption in product(r11.FORMS, ('C12', 'C13'), r9.HEADINGS, CAPTIONS):
        yield 'r11 B-1', '/'.join((form, layout, heading, caption)), r11.host_extent_pdf(
            layout, heading, caption, form), PAT
    for form, layout, heading in product(r11.FORMS, ('C12', 'C13'), r9.HEADINGS):
        yield 'Signature controls', '/'.join((form, layout, heading)), r11.host_extent_pdf(
            layout, heading, 'Signature:', form), PAT
    for layout, caption in product(r11.CROSS_LAYOUTS, r11.CROSS_CAPTIONS):
        yield 'M-1', '/'.join((layout, caption)), r11.cross_host_pdf(layout, caption), (
            PAT if layout == 'stacked_pat' else [TWO[1], *PAT])
    for layout, heading, caption in product(('C12', 'C13'), r9.HEADINGS, [*CAPTIONS, 'Signature:']):
        yield 'r9 heading matrix', '/'.join((layout, heading, caption)), r9.heading_pdf(
            layout, heading, caption), PAT
    for (company, name, signers), between, caption in product(r9.PARTIES, r9.BETWEEN, CAPTIONS):
        yield 'r9 H-1', '/'.join((company, str(between), caption)), r9.stack_pdf(
            company, name, between, caption), signers
    for name, expected in EXPECTED['fixtures'].items():
        yield 'Seven goldens', name, (FIXTURES / (name + '.pdf')).read_bytes(), expected['signers']
    yield 'Same-band right host', 'same_y_right', r12.same_band_right_pdf(), PAT


    yield 'r12 B-1 reproduction', 'Firma_260', r13.reproduction_pdf(), PAT
    for caption, x, dy in product([*CAPTIONS, 'Fax:', 'Sign:'], [150, 200, 260], [0, 20]):
        yield 'r13 same-band grid', '/'.join(map(str, (caption, x, dy))), r9.rows_pdf(
            r13.same_band_rows(caption, x, 330, dy, 'fleet_right')), PAT
    for caption, x, right, dy, top, name in product(
            r13.SHORT_CAPTIONS, [200, 230, 260, 280], [300, 330, 360], [0, 20],
            r13.TOP_VARIANTS, ['Pat Smith', 'Name: Pat Smith']):
        yield 'r12 B-1 sweep', '/'.join(map(str, (caption, x, right, dy, top, name))), r9.rows_pdf(
            r13.same_band_rows(caption, x, right, dy, top, name)), PAT
    for x in [150, 200]:
        yield 'L-1 short-rule controls', str(x), r13.short_rule_pdf(x), PAT
    for caption, heading, both in product(CAPTIONS, r12.HEADINGS, [False, True]):
        yield 'L-2 own-company controls', '/'.join(map(str, (caption, heading, both))), r13.own_company_pdf(
            caption, heading), [TWO[1], *PAT] if both else PAT


def main():
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('PLACE_MODEL', None)
    assert placement.VERSION == 'c2a.13'
    sources = {rev: subprocess.check_output(
        ['git', 'show', sha + ':backend/dealroom_sign/placement.py'], cwd=ROOT).decode()
        for rev, sha in [('r11', R11), ('r12', BASE)]}
    modules = {name: counterfactual_module(name + '_baseline', source)
               for name, source in sources.items()}
    modules['r13'] = placement
    outcomes, records, groups, surprises = {}, [], {}, []
    goldens, comparisons = {}, {}
    changing = {'r12 B-1 reproduction', 'r13 same-band grid', 'r12 B-1 sweep'}
    forbidden = Mock(side_effect=AssertionError('External model I/O forbidden'))

    def persist():
        write('counterfactual-cases.json', {'cases': records, 'outcomes': outcomes})
        write('placements.json', goldens)
        write('golden-comparison.json', comparisons)
        summary = {
            'base': BASE, 'r11_base': R11, 'analysis_version': placement.VERSION,
            'baseline_sha256': {name: hashlib.sha256(source.encode()).hexdigest()
                                for name, source in sources.items()},
            'production_sha256': hashlib.sha256(Path(placement.__file__).read_bytes()).hexdigest(),
            'method': 'place via in-process extract + prepare_blocks; goldens also via real worker',
            'external_model_calls': forbidden.call_count,
            'cases': len(records), 'groups': groups, 'unexpected_differences': surprises,
        }
        write('counterfactual-summary.json', summary)
        return summary

    def stop(message, row):
        surprises.append({'message': message, 'case': row})
        persist()
        with (OUT / 'edd-note.md').open('a') as note:
            note.write('\n## STOP: unexpected execution difference\n\n' + message + '\n\n'
                       + '```json\n' + json.dumps(row, indent=2) + '\n```\n')
        raise SystemExit(message)

    with patch('httpx.Client.send', forbidden):
        for group, case, pdf, signers in cases():
            row = {'group': group, 'case': case, 'results': {}, 'model_calls': {}}
            results = {}
            for name, module in modules.items():
                model = Mock(side_effect=model_answer) if group == 'Seven goldens' else Mock()
                result = in_process(module, pdf, signers, model)
                results[name] = versionless(result)
                digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
                outcomes[digest] = result
                row['results'][name] = digest
                row['model_calls'][name] = model.call_count
            records.append(row)
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            for name, result in results.items():
                counts[name + '_placed'] += result['status'] == 'placed'
                counts[name + '_bare'] += result['status'] == 'bare'
            for left, right in [('r12', 'r11'), ('r13', 'r12')]:
                key = left + '_vs_' + right + '_diffs'
                row[key] = results[left] != results[right]
                counts[key] += row[key]
            expected_calls = 1 if group == 'Seven goldens' and case == 'unusual' else 0
            if any(calls != expected_calls for calls in row['model_calls'].values()):
                stop('Unexpected model call count', row)
            if group not in changing and results['r13'] != results['r12']:
                stop('A-prime changed a full result in a preserved family', row)
            if group in changing:
                result = results['r13']
                if (result['status'], result.get('reason_code'), result['fields']) != (
                        'needs_sender', 'ambiguous_identity', []):
                    stop('A-prime did not hold a requested B-1 case', row)
            if group == 'Seven goldens':
                model = Mock(side_effect=model_answer)
                actual = placement.place(pdf, signers, model_client=model)
                if versionless(actual) != results['r13'] or model.call_count != expected_calls:
                    stop('Golden worker differs from in-process result or model call count', row)
                if case == 'bare':
                    assert actual['status'] == 'bare' and not actual['fields']
                else:
                    assert_golden(actual, case, signers)
                revisions = ['c2a-r4', 'c2a-r5', 'c2a-r11', 'c2a-r12']
                for rev in revisions:
                    previous = json.loads((OUT.parent / rev / 'placements.json').read_text())[case]
                    if versionless(actual) != versionless(previous):
                        stop('Golden full result differs from ' + rev, row)
                    for signer in signers:
                        assert placement.to_native_fields(actual, signer['email']) == placement.to_native_fields(
                            previous, signer['email'])
                goldens[case] = actual
                comparisons[case] = {'exact_full_result_except_analysis_version': revisions,
                                     'model_calls': model.call_count,
                                     'pdf_sha256': hashlib.sha256(pdf).hexdigest()}
            if len(records) % 100 == 0:
                print(f'{len(records)} cases compared', flush=True)
        forbidden.assert_not_called()
    expected_placed = {
        'Matrix 1': (120, 120, 0, 0), 'Matrix 2': (270, 135, 0, 0),
        'r11 B-1': (1020, 0, 0, 0), 'Signature controls': (204, 6, 6, 6),
        'M-1': (16, 16, 16, 16), 'r9 heading matrix': (72, 6, 6, 6),
        'r9 H-1': (40, 0, 0, 0), 'Seven goldens': (7, 6, 6, 6),
        'Same-band right host': (1, 1, 0, 0),
        'r12 B-1 reproduction': (1, 1, 1, 0),
        'r12 B-1 sweep': (864, 864, 540, 0),
        'L-1 short-rule controls': (2, 2, 2, 2),
        'L-2 own-company controls': (40, 20, 20, 20),
    }
    for group, expected in expected_placed.items():
        actual = tuple(groups[group][k] for k in ('cases', 'r11_placed', 'r12_placed', 'r13_placed'))
        if actual != expected:
            stop('Table counts differ from the measured review baseline',
                 {'group': group, 'expected': expected, 'actual': actual})
    print(json.dumps(persist(), indent=2))


if __name__ == '__main__':
    main()
