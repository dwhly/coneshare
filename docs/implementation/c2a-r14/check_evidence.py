"""Execute both proposed counterfactuals before selecting a production change.

The large matrices use extract + prepare_blocks in process, as in the review.
Reproduction and goldens also use the unchanged real worker in temporary import
roots containing each candidate's placement source. No product file is edited.
"""
from collections import Counter, defaultdict
from contextlib import ExitStack
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = '2ff90be102b4a4a3f65cee15a3f8258fcb445685'
PRODUCT = 'backend/dealroom_sign/placement.py'
sys.path.insert(0, str(ROOT / 'backend'))

from dealroom_sign import placement  # noqa: E402
from dealroom_sign.tests import test_placement_r14 as r14  # noqa: E402
from dealroom_sign.tests.test_placement import TWO, model_answer  # noqa: E402
from dealroom_sign.tests.test_placement_r3 import PAT  # noqa: E402
from dealroom_sign.tests.test_placement_r9 import FLEET, rows_pdf  # noqa: E402


def load_r13_generator():
    spec = importlib.util.spec_from_file_location('r13_evidence', OUT.parent / 'c2a-r13/check_evidence.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.cases


def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


def candidate_sources(base):
    versioned = replace_once(base, "VERSION = 'c2a.13'", "VERSION = 'c2a.14'")
    a = replace_once(versioned,
        "                # Include the whole row band, including text beside or directly\n"
        "                # under the rule. Neighbouring columns stop the band; text in\n"
        "                # the gap between two rules belongs to both until disambiguated.\n"
        "                neighbours = [r for r in unique if r is not sig\n"
        "                              and r.semantic not in COMPANION_SEMANTICS\n"
        "                              and abs(r.y - sig.y) < 30]",
        "                # Column gutters bound evidence even when rules are staggered.\n"
        "                # Keep the gap shared until its identity is disambiguated.\n"
        "                neighbours = [r for r in unique if r is not sig\n"
        "                              and r.semantic not in COMPANION_SEMANTICS]")
    b = replace_once(versioned,
        "    for block, extent in extents:\n        texts, rules, _ = pages[block.line.page]",
        "    mixed_heading_names = {}\n"
        "    for block, extent in extents:\n        texts, rules, _ = pages[block.line.page]")
    b = replace_once(b,
        "        if conflicting_company_headings(block, extent, texts, rules, roles):\n"
        "            block.uncertain_identity = True",
        "        if conflicting_company_headings(block, extent, texts, rules, roles):\n"
        "            block.uncertain_identity = True\n"
        "            mixed_heading_names.setdefault(block.line.page, []).extend(\n"
        "                t for t in block.raw_labels\n"
        "                if any(person_text(part) for part in identity_parts(t['text'])))")
    b = replace_once(b,
        "    return blocks, sizes, roles\n\n\ndef accounted_label",
        "    # A mixed-company block cannot lend its printed name to another block.\n"
        "    # Propagate by the same physical row on the same page, after collecting\n"
        "    # every conflict, so traversal order cannot clear or miss a veto.\n"
        "    for block, extent in extents:\n"
        "        if any(inside_extent(text, extent)\n"
        "               for text in mixed_heading_names.get(block.line.page, [])):\n"
        "            block.uncertain_identity = True\n"
        "    return blocks, sizes, roles\n\n\ndef accounted_label")
    return {'r13': base, 'a': a, 'b': b}


def make_module(name, source, stack):
    module = ModuleType('r14_counterfactual_' + name)
    module.__file__ = placement.__file__
    sys.modules[module.__name__] = module
    exec(compile(source, module.__name__, 'exec'), module.__dict__)
    worker_root = Path(stack.enter_context(TemporaryDirectory(prefix='worker-' + name + '-', dir=OUT)))
    package = worker_root / 'dealroom_sign'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'placement.py').write_text(source)
    (package / 'placement_worker.py').write_bytes(
        (ROOT / 'backend/dealroom_sign/placement_worker.py').read_bytes())
    module.WORKER_CWD = worker_root
    return module


def versionless(result):
    return {key: value for key, value in result.items() if key != 'analysis_version'}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def write_breakdown(records, outcomes, differences):
    by_signers, fixed_wrong, transitions = defaultdict(Counter), Counter(), Counter()
    for row in records:
        if row['group'] == 'r14 grid':
            signers = 'DAN+PAT' if row['case'].endswith('/True') else 'PAT'
            by_signers[signers]['cases'] += 1
            for candidate, digest in row['results'].items():
                by_signers[signers][candidate + '_' + outcomes[digest]['status']] += 1
        elif row['group'] == 'r14 fixed sweep':
            side, y, *_ = row['case'].split('/')
            if r14.wrong_pat_fields(outcomes[row['results']['r13']], (r14.columns(side)[0], int(y))):
                fixed_wrong[y] += 1
    for row in differences:
        if row['candidate'] == 'b':
            before, after = (outcomes[row[key]]['status'] for key in ['before', 'after'])
            transitions[row['group'], before, after, row['wrong_to_hold']] += 1
    write('grid-breakdown.json', {'grid_by_signer_set': by_signers, 'fixed_wrong_by_y': fixed_wrong})
    write('chosen-transitions.json', [
        {'group': group, 'before': before, 'after': after, 'wrong_to_hold': wrong, 'count': count}
        for (group, before, after, wrong), count in transitions.items()
    ])


def new_cases():
    yield 'r14 reproduction', 'verbatim', r14.reproduction_pdf(), PAT, (330, 350)
    for args in r14.GRID:
        rows, line = r14.grid_rows(*args[:-1])
        yield 'r14 grid', '/'.join(map(str, args)), rows_pdf(rows), [TWO[1], *PAT] if args[-1] else PAT, line
    for side, y, heading, title, both in r14.FIXED:
        rows, line = r14.fixed_rows(side, y, heading, title)
        yield 'r14 fixed sweep', '/'.join(map(str, (side, y, heading, title, both))), rows_pdf(rows), (
            [TWO[1], *PAT] if both else PAT), line
    for side in ['left', 'right']:
        rows, line = r14.fixed_rows(side)
        yield 'r14 correct controls', side, rows_pdf([r for r in rows if r[1] != FLEET]), PAT, line


def main():
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('PLACE_MODEL', None)
    sys.dont_write_bytecode = True
    base = subprocess.check_output(['git', 'show', BASE + ':' + PRODUCT], cwd=ROOT).decode()
    sources = candidate_sources(base)
    for name in ['a', 'b']:
        (OUT / ('candidate-' + name + '.patch')).write_text(''.join(difflib.unified_diff(
            base.splitlines(True), sources[name].splitlines(True),
            fromfile='a/' + PRODUCT, tofile='b/' + PRODUCT)))
    old_evidence = json.loads((OUT.parent / 'c2a-r13/counterfactual-cases.json').read_text())
    old_cases = {(row['group'], row['case']): old_evidence['outcomes'][row['results']['r13']]
                 for row in old_evidence['cases']}
    records, outcomes, groups, differences, worker_records = [], {}, {}, [], []
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {name: make_module(name, source, stack) for name, source in sources.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        cases = [(group, case, pdf, signers, None)
                 for group, case, pdf, signers in load_r13_generator()()]
        assert len(cases) == 2699
        cases.extend(new_cases())
        for group, case, pdf, signers, our_line in cases:
            row = {'group': group, 'case': case, 'results': {}, 'model_calls': {}}
            count = groups.setdefault(group, Counter())
            count['cases'] += 1
            results = {}
            for name, module in modules.items():
                model = Mock(side_effect=model_answer) if group == 'Seven goldens' else Mock()
                result = r14.in_process(module, pdf, signers, model)
                results[name] = versionless(result)
                row['results'][name] = remember(result)
                row['model_calls'][name] = model.call_count
                assert model.call_count == (1 if group == 'Seven goldens' and case == 'unusual' else 0)
                count[name + '_placed'] += result['status'] == 'placed'
                count[name + '_holds'] += result['status'] == 'needs_sender'
                count[name + '_bare'] += result['status'] == 'bare'
                count[name + '_wrong'] += bool(our_line and r14.wrong_pat_fields(result, our_line))
            if (group, case) in old_cases:
                assert results['r13'] == versionless(old_cases[group, case]), (group, case)
            for name in ['a', 'b']:
                changed = results[name] != results['r13']
                count[name + '_full_diffs'] += changed
                if changed:
                    differences.append({'candidate': name, 'group': group, 'case': case,
                                        'before': row['results']['r13'], 'after': row['results'][name],
                                        'wrong_to_hold': bool(our_line and r14.wrong_pat_fields(results['r13'], our_line)
                                                              and results[name]['status'] == 'needs_sender')})
            records.append(row)
            if group in {'Seven goldens', 'r14 reproduction', 'r14 correct controls'}:
                for name, module in modules.items():
                    model = Mock(side_effect=model_answer) if group == 'Seven goldens' else Mock()
                    actual = module.place(pdf, signers, model_client=model)
                    assert versionless(actual) == results[name], (name, group, case, actual)
                    assert model.call_count == row['model_calls'][name]
                    worker_records.append({'candidate': name, 'group': group, 'case': case,
                                           'result': remember(actual), 'model_calls': model.call_count,
                                           'matches_in_process': True})
            if len(records) % 250 == 0:
                print(f'{len(records)} cases compared across r13, a, b', flush=True)
    forbidden.assert_not_called()
    bars = {}
    for name in ['a', 'b']:
        preserved = [d for d in differences if d['candidate'] == name and not d['group'].startswith('r14 ')]
        repro = next(outcomes[r['result']] for r in worker_records
                     if r['candidate'] == name and r['group'] == 'r14 reproduction')
        bars[name] = {
            'bar1_zero_wrong': all(groups[g][name + '_wrong'] == 0
                                   for g in ['r14 reproduction', 'r14 grid']),
            'reproduction_holds': (repro['status'], repro.get('reason_code'), repro['fields']) == (
                'needs_sender', 'ambiguous_identity', []),
            'bar2_exact_preserved': not preserved,
            'preserved_full_differences': len(preserved),
            'bar3_goldens_exact': groups['Seven goldens'][name + '_full_diffs'] == 0,
            'correct_controls_placed': groups['r14 correct controls'][name + '_placed'] == 2,
        }
        bars[name]['passes'] = all(v for k, v in bars[name].items() if k != 'preserved_full_differences')
    chosen = next((name for name in ['a', 'b'] if bars[name]['passes']), None)
    summary = {
        'base': BASE, 'method': 'in-process matrices; isolated unchanged real workers for reproduction, controls, goldens',
        'source_sha256': {name: hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()},
        'cases': len(records), 'groups': groups, 'bars': bars, 'chosen': chosen,
        'external_http_calls': forbidden.call_count,
        'old_r13_results_exact': 2699,
    }
    write('counterfactual-cases.json', {'cases': records, 'outcomes': outcomes})
    write('counterfactual-differences.json', differences)
    write('counterfactual-workers.json', worker_records)
    write('counterfactual-summary.json', summary)
    write_breakdown(records, outcomes, differences)
    print(json.dumps(summary, indent=2))
    if chosen is None:
        raise SystemExit('Neither candidate passes; do not ship or invent a third without a new table.')


if __name__ == '__main__':
    main()
