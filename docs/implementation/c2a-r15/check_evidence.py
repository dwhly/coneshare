"""Compare r14, column ownership, generalised veto, and their combination.

Product source stays untouched until all candidates have completed the full
table. Run with PYTHONDONTWRITEBYTECODE=1 and the supplied send interpreter.
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
BASE = 'd88bfb889f3863796b276a6f0aef3da57539c4c3'
PRODUCT = 'backend/dealroom_sign/placement.py'
sys.path.insert(0, str(ROOT / 'backend'))

from dealroom_sign import placement  # noqa: E402
from dealroom_sign.tests import test_placement_r14 as r14  # noqa: E402
from dealroom_sign.tests import test_placement_r15 as r15  # noqa: E402
from dealroom_sign.tests.test_placement import TWO, model_answer  # noqa: E402
from dealroom_sign.tests.test_placement_r3 import PAT  # noqa: E402
from dealroom_sign.tests.test_placement_r9 import FLEET, HARBOR, rows_pdf  # noqa: E402


def earlier_cases():
    spec = importlib.util.spec_from_file_location('r13_evidence', OUT.parent / 'c2a-r13/check_evidence.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.cases()


def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


def column_ownership(source):
    return replace_once(source,
        "def printed_names(block):\n"
        "    return [tokens(name) for label in (block.raw_labels or block.labels)\n"
        "            for part in identity_parts(label['text']) if (name := person_text(part))]",
        "def printed_names(block):\n"
        "    # A name may identify only a horizontally overlapping label/rule\n"
        "    # column. Allow 10 pt at either edge for slightly outdented names.\n"
        "    left = min(block.line.x0, block.line.label.get('rect', [block.line.x0])[0])\n"
        "    return [tokens(name) for label in (block.raw_labels or block.labels)\n"
        "            if label['rect'][0] < block.line.x1 + 10 and label['rect'][2] > left - 10\n"
        "            for part in identity_parts(label['text']) if (name := person_text(part))]")


def generalised_veto(source):
    source = replace_once(source, '    mixed_heading_names = {}\n', '')
    source = replace_once(source,
        "            mixed_heading_names.setdefault(block.line.page, []).extend(\n"
        "                t for t in block.raw_labels\n"
        "                if any(person_text(part) for part in identity_parts(t['text'])))\n", '')
    source = replace_once(source,
        "    # A mixed-company block cannot lend its printed name to another block.\n"
        "    # Propagate by the same physical row on the same page, after collecting\n"
        "    # every conflict, so traversal order cannot clear or miss a veto.\n"
        "    for block, extent in extents:\n"
        "        if any(inside_extent(text, extent)\n"
        "               for text in mixed_heading_names.get(block.line.page, [])):\n"
        "            block.uncertain_identity = True\n",
        "    # Keep physical-row peers only until local scoring; never serialize\n"
        "    # these references in the worker's dataclass output.\n"
        "    for block, extent in extents:\n"
        "        names = [t for t in block.raw_labels\n"
        "                 if any(person_text(part) for part in identity_parts(t['text']))]\n"
        "        block._identity_peers = [other for other, other_extent in extents\n"
        "                                 if other is not block and other.line.page == block.line.page\n"
        "                                 and any(inside_extent(t, extent) and inside_extent(t, other_extent)\n"
        "                                         for t in names)]\n")
    return replace_once(source,
        "    for block in blocks:\n"
        "        block.scores = [score(s, block, roles) for s in signers]\n"
        "        if not printed_names(block) and sum(v >= 4 for v in block.scores) != 1:\n"
        "            block.scores = [0] * len(signers)\n",
        "    initial = {id(block): [score(s, block, roles) for s in signers] for block in blocks}\n"
        "    for block in blocks:\n"
        "        block.scores = [value if not any(initial[id(peer)][i] == 0\n"
        "                                         for peer in getattr(block, '_identity_peers', [])) else 0\n"
        "                        for i, value in enumerate(initial[id(block)])]\n"
        "        if hasattr(block, '_identity_peers'):\n"
        "            del block._identity_peers\n"
        "        if not printed_names(block) and sum(v >= 4 for v in block.scores) != 1:\n"
        "            block.scores = [0] * len(signers)\n")


def candidate_sources(base):
    versioned = replace_once(base, "VERSION = 'c2a.14'", "VERSION = 'c2a.15'")
    return {'r14': base, 'c': column_ownership(versioned),
            'bprime': generalised_veto(versioned),
            'c+bprime': generalised_veto(column_ownership(versioned))}


def make_module(name, source, stack):
    module = ModuleType('r15_counterfactual_' + name)
    module.__file__ = placement.__file__
    sys.modules[module.__name__] = module
    exec(compile(source, module.__name__, 'exec'), module.__dict__)
    worker_root = Path(stack.enter_context(TemporaryDirectory(prefix='worker-' + name + '-', dir=OUT)))
    package = worker_root / 'dealroom_sign'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'placement.py').write_text(source)
    (package / 'placement_worker.py').write_bytes((ROOT / 'backend/dealroom_sign/placement_worker.py').read_bytes())
    module.WORKER_CWD = worker_root
    return module


def versionless(result):
    return {key: value for key, value in result.items() if key != 'analysis_version'}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def is_l1(args):
    side, lower, dy, gap, own_name, heading, title, both = args
    # All and only the review's 72 r13 correct -> r14 hold cases.
    return (lower == 'theirs' and not both and heading == HARBOR
            and own_name in {'none', 'blank'} and dy in {60, 80, 100}
            and dy + gap <= 125)


def cases():
    for group, case, pdf, signers in earlier_cases():
        yield group, case, pdf, signers, None
    yield 'r14 reproduction', 'verbatim', r14.reproduction_pdf(), PAT, (330, 350)
    for args in r14.GRID:
        rows, line = r14.grid_rows(*args[:-1])
        yield 'r14 grid', '/'.join(map(str, args)), rows_pdf(rows), [TWO[1], *PAT] if args[-1] else PAT, line
    for args in r14.FIXED:
        rows, line = r14.fixed_rows(*args[:-1])
        yield 'r14 fixed sweep', '/'.join(map(str, args)), rows_pdf(rows), [TWO[1], *PAT] if args[-1] else PAT, line
    for side in ['left', 'right']:
        rows, line = r14.fixed_rows(side)
        yield 'r14 correct controls', side, rows_pdf([r for r in rows if r[1] != FLEET]), PAT, line
    for args in r14.GRID:
        if is_l1(args):
            rows, line = r14.grid_rows(*args[:-1])
            yield 'r14 L-1 (grid subset)', '/'.join(map(str, args)), rows_pdf(rows), PAT, line
    for mechanism, pdf, line in [('M1', r15.m1_reproduction_pdf(), (330, 350)),
                                 ('M2', r15.m2_reproduction_pdf(), (72, 290))]:
        for both in [False, True]:
            yield 'r15 ' + mechanism + ' reproduction', str(both), pdf, [TWO[1], *PAT] if both else PAT, line
    for args in r15.M1:
        rows, line = r14.fixed_rows(*args[:-1])
        yield 'r15 M1', '/'.join(map(str, args)), rows_pdf(rows), [TWO[1], *PAT] if args[-1] else PAT, line
    for args in r15.M2:
        rows, line = r15.m2_rows(*args[:-1])
        yield 'r15 M2', '/'.join(map(str, args)), rows_pdf(rows), [TWO[1], *PAT] if args[-1] else PAT, line


def earlier_wrong(group, case, result, baseline):
    if result['status'] != 'placed':
        return False
    # Earlier closures require holds. Placed controls have independently pinned
    # field geometry in their original tests; compare against that accepted result.
    if baseline['status'] != 'placed':
        return True
    return result['fields'] != baseline['fields']


def main():
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('PLACE_MODEL', None)
    sys.dont_write_bytecode = True
    base = subprocess.check_output(['git', 'show', BASE + ':' + PRODUCT], cwd=ROOT).decode()
    sources = candidate_sources(base)
    for name in ['c', 'bprime', 'c+bprime']:
        (OUT / ('candidate-' + name + '.patch')).write_text(''.join(difflib.unified_diff(
            base.splitlines(True), sources[name].splitlines(True), fromfile='a/' + PRODUCT, tofile='b/' + PRODUCT)))
    old = json.loads((OUT.parent / 'c2a-r14/counterfactual-cases.json').read_text())
    accepted = {(r['group'], r['case']): old['outcomes'][r['results']['b']] for r in old['cases']}
    goldens = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    groups, records, outcomes, differences, workers = {}, [], {}, [], []
    transitions = defaultdict(Counter)
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {name: make_module(name, source, stack) for name, source in sources.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pdf, signers, line in cases():
            row = {'group': group, 'case': case, 'results': {}, 'model_calls': {}}
            count = groups.setdefault(group, Counter())
            count['cases'] += 1
            results, wrong = {}, {}
            for name, module in modules.items():
                model = Mock(side_effect=model_answer) if group == 'Seven goldens' else Mock()
                result = r14.in_process(module, pdf, signers, model)
                results[name] = result
                row['results'][name] = remember(result)
                row['model_calls'][name] = model.call_count
                assert model.call_count == (1 if group == 'Seven goldens' and case == 'unusual' else 0)
                wrong[name] = (bool(r15.wrong_pat_fields(result, line)) if line else
                               earlier_wrong(group, case, result, accepted[group, case]))
                for status in ['placed', 'needs_sender', 'bare']:
                    count[name + '_' + ('holds' if status == 'needs_sender' else status)] += result['status'] == status
                count[name + '_wrong'] += wrong[name]
                if group == 'Seven goldens':
                    count[name + '_golden_diffs'] += versionless(result) != versionless(goldens[case])
            if (group, case) in accepted:
                assert versionless(results['r14']) == versionless(accepted[group, case]), (group, case)
            for name in ['c', 'bprime', 'c+bprime']:
                changed = versionless(results[name]) != versionless(results['r14'])
                count[name + '_full_diffs'] += changed
                before = 'wrong' if wrong['r14'] else results['r14']['status']
                after = 'wrong' if wrong[name] else results[name]['status']
                if before != after:
                    transitions[name][group + ': ' + before + ' -> ' + after] += 1
                if changed:
                    differences.append({'candidate': name, 'group': group, 'case': case,
                                        'before': row['results']['r14'], 'after': row['results'][name]})
            records.append(row)
            if group in {'Seven goldens', 'r14 reproduction', 'r14 correct controls',
                         'r15 M1 reproduction', 'r15 M2 reproduction'}:
                for name, module in modules.items():
                    model = Mock(side_effect=model_answer) if group == 'Seven goldens' else Mock()
                    actual = module.place(pdf, signers, model_client=model)
                    assert actual == results[name], (name, group, case, actual)
                    assert model.call_count == row['model_calls'][name]
                    workers.append({'candidate': name, 'group': group, 'case': case,
                                    'result': remember(actual), 'model_calls': model.call_count})
            if len(records) % 250 == 0:
                print(f'{len(records)} cases compared across r14, c, bprime, c+bprime', flush=True)
    forbidden.assert_not_called()
    assert len(records) == 9826
    assert groups['r14 L-1 (grid subset)']['cases'] == 72
    assert groups['r15 M1']['r14_wrong'] == 100 and groups['r15 M2']['r14_wrong'] == 432
    bars = {name: {'zero_wrong_every_family': all(g[name + '_wrong'] == 0 for g in groups.values()),
                   'goldens_exact': groups['Seven goldens'][name + '_golden_diffs'] == 0}
            for name in ['c', 'bprime', 'c+bprime']}
    chosen = next((name for name in ['c', 'bprime', 'c+bprime'] if all(bars[name].values())), None)
    summary = {'base': BASE, 'source_sha256': {name: hashlib.sha256(s.encode()).hexdigest() for name, s in sources.items()},
               'cases_including_L1_subset': len(records), 'unique_cases': len(records) - 72,
               'groups': groups, 'bars': bars, 'chosen': chosen,
               'external_http_calls': forbidden.call_count, 'transitions': transitions}
    write('counterfactual-cases.json', {'cases': records, 'outcomes': outcomes})
    write('counterfactual-differences.json', differences)
    write('counterfactual-workers.json', workers)
    write('counterfactual-summary.json', summary)
    print(json.dumps(summary, indent=2))
    if chosen is None:
        raise SystemExit('No candidate passes; ship nothing.')


if __name__ == '__main__':
    main()
