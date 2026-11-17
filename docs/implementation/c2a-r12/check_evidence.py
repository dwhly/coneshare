"""Execute the review table against r11, fix A, and fix B without editing code.

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
BASE = '0c190e9b45db25ee5c1b8d71cdc2b040cd956fab'
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


def main():
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('PLACE_MODEL', None)
    assert placement.VERSION == 'c2a.12'
    source = subprocess.check_output(
        ['git', 'show', BASE + ':backend/dealroom_sign/placement.py'], cwd=ROOT).decode()
    start = source.index('def subordinating_host(')
    end = source.index('\ndef subordinate_caption(', start)
    host_source = source[start:end]
    assert host_source.count('for host in rules:') == 1
    nearest_source = source[:start] + host_source.replace(
        'for host in rules:', 'for host in sorted(rules, key=lambda r: -r.y):') + source[end:]
    modules = {'r11': counterfactual_module('r11_baseline', source), 'fix_A': placement,
               'fix_B': counterfactual_module('r11_nearest_first', nearest_source)}
    outcomes, records, groups = {}, [], {}
    goldens, comparisons = {}, {}
    forbidden = Mock(side_effect=AssertionError('External model I/O forbidden'))
    with patch('httpx.Client.send', forbidden):
        for group, case, pdf, signers in cases():
            row = {'group': group, 'case': case, 'results': {}, 'model_calls': {}}
            results = {}
            for name, module in modules.items():
                model = Mock(side_effect=model_answer) if group == 'Seven goldens' else Mock()
                result = in_process(module, pdf, signers, model)
                assert model.call_count == (1 if group == 'Seven goldens' and case == 'unusual' else 0)
                results[name] = versionless(result)
                digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
                outcomes[digest] = result
                row['results'][name] = digest
                row['model_calls'][name] = model.call_count
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            for name, result in results.items():
                counts[name + '_placed'] += result['status'] == 'placed'
                counts[name + '_bare'] += result['status'] == 'bare'
            for name in ('fix_A', 'fix_B'):
                row[name + '_differs_from_r11'] = results[name] != results['r11']
                counts[name + '_diffs'] += row[name + '_differs_from_r11']
            if group in {'Matrix 1', 'Matrix 2', 'Same-band right host'}:
                assert results['fix_A']['status'] == 'needs_sender', row
                assert results['fix_A']['reason_code'] == 'ambiguous_identity', row
                assert results['fix_A']['fields'] == [], row
            else:
                assert results['fix_A'] == results['r11'] == results['fix_B'], row
            if group == 'Seven goldens':
                model = Mock(side_effect=model_answer)
                actual = placement.place(pdf, signers, model_client=model)
                assert versionless(actual) == results['fix_A']
                assert model.call_count == (1 if case == 'unusual' else 0)
                if case == 'bare':
                    assert actual['status'] == 'bare' and not actual['fields']
                else:
                    assert_golden(actual, case, signers)
                for rev in ('c2a-r4', 'c2a-r5', 'c2a-r11'):
                    previous = json.loads((OUT.parent / rev / 'placements.json').read_text())[case]
                    assert versionless(actual) == versionless(previous), (case, rev)
                    for signer in signers:
                        assert placement.to_native_fields(actual, signer['email']) == placement.to_native_fields(
                            previous, signer['email'])
                blocks, _, _ = placement.extract(pdf)
                assert not any(block.uncertain_identity for block in blocks)
                goldens[case] = actual
                comparisons[case] = {'exact_full_result_except_analysis_version': ['c2a-r4', 'c2a-r5', 'c2a-r11'],
                                     'model_calls': model.call_count,
                                     'pdf_sha256': hashlib.sha256(pdf).hexdigest()}
            records.append(row)
            if len(records) % 100 == 0:
                print(f'{len(records)} cases compared', flush=True)
        forbidden.assert_not_called()
    expected_placed = {
        'Matrix 1': (120, 120, 0, 0), 'Matrix 2': (270, 135, 0, 0),
        'r11 B-1': (1020, 0, 0, 0), 'Signature controls': (204, 6, 6, 6),
        'M-1': (16, 16, 16, 16), 'r9 heading matrix': (72, 6, 6, 6),
        'r9 H-1': (40, 0, 0, 0), 'Seven goldens': (7, 6, 6, 6),
        'Same-band right host': (1, 1, 0, 1),
    }
    for group, expected in expected_placed.items():
        assert tuple(groups[group][k] for k in ('cases', 'r11_placed', 'fix_A_placed', 'fix_B_placed')) == expected, groups[group]
    write('counterfactual-cases.json', {'cases': records, 'outcomes': outcomes})
    write('placements.json', goldens)
    write('golden-comparison.json', comparisons)
    summary = {
        'base': BASE, 'analysis_version': placement.VERSION,
        'baseline_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'production_sha256': hashlib.sha256(Path(placement.__file__).read_bytes()).hexdigest(),
        'method': 'place via in-process extract + prepare_blocks; goldens also via real worker',
        'fix_B_in_product': False, 'external_model_calls': 0,
        'matrix2_extra_form': 'baseline_10 (eight forms explicit in review; nine required by total)',
        'cases': len(records), 'groups': groups,
    }
    write('counterfactual-summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
