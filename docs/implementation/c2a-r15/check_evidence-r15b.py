"""Compare r14 with nearest-column ownership, including omitted suite controls.

Run with the supplied send interpreter and PYTHONDONTWRITEBYTECODE=1.
The original r15 table is reused verbatim. Additional control PDFs and local
model replies are captured by executing the unchanged original test functions
against r14, including all their parametrizations and assertions. They are then
replayed against both sources. No test file, fixture or prior evidence is edited.
"""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
import difflib
import hashlib
import importlib
import importlib.util
import inspect
from itertools import product
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
spec = importlib.util.spec_from_file_location('r15_evidence', OUT / 'check_evidence.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
placement = old.placement
COMBINED = '--combine' in sys.argv
SUFFIX = '-combined-r15b' if COMBINED else '-r15b'

# r3-r10: all fixture-free geometry/wording controls, including negative
# members of the same families. Unit-only predicates produce no PDF cases.
# r9/r11-r14 families already in the original table are excluded below.
R2 = {
    'test_reviewer_wrong_signer_goldens', 'test_unnamed_signer_never_takes_named_block',
    'test_nearby_body_is_redacted_and_model_identity_is_minimal',
    'test_caption_cannot_claim_next_block', 'test_date_cannot_be_borrowed_from_next_column',
    'test_native_signature_is_tight_and_bottom_anchored',
    'test_printed_name_variants_veto_company_match', 'test_named_caption_is_not_dropped_when_it_is_long',
    'test_unlabelled_unrecognized_caption_cannot_be_ignored',
    'test_heading_cannot_cross_a_previous_unlabelled_rule',
    'test_date_in_close_right_column_with_unlabelled_signature_is_not_borrowed',
}
EXTRA = {
    9: {'test_b1_same_row_right_behalf_holds', 'test_absorbed_identity_vetoes_every_overlapping_host'},
    11: {'test_subordinating_rule_without_block_keeps_identity_veto'},
    14: {'test_separate_printing_of_same_name_is_not_vetoed'},
}


def write(stem, value):
    (OUT / (stem + SUFFIX + '.json')).write_text(json.dumps(value, indent=2) + '\n')


def aligned_columns(source):
    before = """    own = column(block)
    # Stacked blocks can share a column; only distinct columns compete.
    others = {column(other) for other in blocks if other.line.page == block.line.page} - {own}
"""
    after = """    # Aligned rules are one column even when their lengths differ.
    columns = {}
    for other in [block, *blocks]:
        if other.line.page == block.line.page:
            left, right = column(other)
            columns[left] = max(columns.get(left, right), right)
    left = column(block)[0]
    own = (left, columns[left])
    others = [(x, right) for x, right in columns.items() if x != left]
"""
    if before in source:
        return old.replace_once(source, before, after)
    assert after in source
    return source


def combine_veto(source):
    # Adapt the exact prior (b-prime) patch to the new page-context argument.
    source = source.replace('printed_names(block, blocks)', 'printed_names(block)')
    source = source.replace('score(s, block, roles, blocks)', 'score(s, block, roles)')
    source = old.generalised_veto(source)
    source = source.replace('printed_names(block)', 'printed_names(block, blocks)')
    return source.replace('score(s, block, roles)', 'score(s, block, roles, blocks)')


def nearest_source(base):
    """Reconstruct the candidate from HEAD, independent of the final worktree."""
    before = """def printed_names(block):
    return [tokens(name) for label in (block.raw_labels or block.labels)
            for part in identity_parts(label['text']) if (name := person_text(part))]
"""
    after = """def printed_names(block, blocks=()):
    def column(other):
        return (min(other.line.x0, other.line.label.get('rect', [other.line.x0])[0]),
                other.line.x1)

    own = column(block)
    # Stacked blocks can share a column; only distinct columns compete.
    others = {column(other) for other in blocks if other.line.page == block.line.page} - {own}

    def owns(row):
        def distance(bounds):
            return max(bounds[0] - row['rect'][2], row['rect'][0] - bounds[1], 0)

        # Edge distance admits outdented names, but a tie within 2 pt
        # supplies identity to neither column. Vertical attribution is unchanged.
        return all(distance(other) > distance(own) + 2 for other in others)

    return [tokens(name) for label in (block.raw_labels or block.labels)
            if owns(label)
            for part in identity_parts(label['text']) if (name := person_text(part))]
"""
    source = old.replace_once(base, before, after)
    source = old.replace_once(source, "VERSION = 'c2a.14'", "VERSION = 'c2a.15'")
    source = source.replace('printed_names(block)', 'printed_names(block, blocks)')
    source = source.replace('score(s, block, roles)', 'score(s, block, roles, blocks)')
    source = old.replace_once(source, 'def score(signer, block, roles):', 'def score(signer, block, roles, blocks=()):')
    return aligned_columns(source)


def parameters(function):
    axes = []
    for mark in getattr(function, 'pytestmark', []):
        if mark.name == 'parametrize':
            names, values = mark.args[:2]
            names = [n.strip() for n in names.split(',')] if isinstance(names, str) else names
            axes.append([dict(zip(names, (value,) if len(names) == 1 else value)) for value in values])
    for combination in product(*axes):
        yield {k: v for axis in combination for k, v in axis.items()}


def control_cases(baseline, inventory):
    for revision in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14]:
        module = importlib.import_module(f'dealroom_sign.tests.test_placement_r{revision}')
        for name, function in vars(module).items():
            if not name.startswith('test_') or function.__module__ != module.__name__:
                continue
            if revision == 2 and name not in R2:
                continue
            if revision in EXTRA and name not in EXTRA[revision]:
                continue
            if 'seven_goldens' in name:
                continue
            for params in parameters(function):
                # Fixture-based transport, logging and synthetic extraction
                # checks are run unchanged by the full suite, not PDF replays.
                if set(inspect.signature(function).parameters) != set(params):
                    continue
                captured = []

                def capture(pdf, signers, *, model_client=None):
                    replies = []

                    def model(payload):
                        reply = model_client(payload)
                        replies.append(copy.deepcopy(reply))
                        return reply

                    result = old.r14.in_process(baseline, pdf, signers, model if model_client else None)
                    captured.append((pdf, copy.deepcopy(signers), replies, copy.deepcopy(result)))
                    return result

                with patch.object(placement, 'place', capture), patch.object(placement, 'extract', baseline.extract):
                    function(**params)  # Original assertions validate the r14 oracle.
                for index, (pdf, signers, replies, expected) in enumerate(captured):
                    group = f'r{revision} {name.removeprefix("test_")}'
                    # Keep the exact missed family visible, rather than burying it.
                    if revision == 10 and name == 'test_signature_out_of_slot_controls_unchanged':
                        group += ' / ' + params['variant']
                    case = json.dumps(params, sort_keys=True) + f' / call {index + 1}'
                    entry = inventory.setdefault(group, {'test': module.__name__ + '::' + name, 'cases': 0})
                    entry['cases'] += 1
                    yield group, case, pdf, signers, None, replies, expected


def main():
    sys.dont_write_bytecode = True
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    base = subprocess.check_output(['git', 'show', old.BASE + ':' + old.PRODUCT], cwd=ROOT).decode()
    candidate = nearest_source(base)
    if COMBINED:
        candidate = combine_veto(candidate)
    chosen = 'combined' if COMBINED else 'nearest'
    assert "VERSION = 'c2a.15'" in candidate
    sources = {'r14': base, chosen: candidate}
    (OUT / ('candidate' + SUFFIX + '.patch')).write_text(''.join(difflib.unified_diff(
        base.splitlines(True), candidate.splitlines(True), fromfile='a/' + old.PRODUCT,
        tofile='b/' + old.PRODUCT)))
    archived = json.loads((OUT.parent / 'c2a-r14/counterfactual-cases.json').read_text())
    accepted = {(r['group'], r['case']): archived['outcomes'][r['results']['b']] for r in archived['cases']}
    goldens = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    groups, records, outcomes, differences, workers, inventory = {}, [], {}, [], [], {}
    transitions = defaultdict(Counter)
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {name: old.make_module(name, source, stack) for name, source in sources.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))

        def cases():
            for group, case, pdf, signers, line in old.cases():
                yield group, case, pdf, signers, line, None, accepted.get((group, case))
            yield from control_cases(modules['r14'], inventory)

        for group, case, pdf, signers, line, replies, expected in cases():
            row = {'group': group, 'case': case, 'results': {}, 'model_calls': {}, 'wrong': {}}
            count = groups.setdefault(group, Counter())
            count['cases'] += 1
            results = {}

            def new_model():
                if group == 'Seven goldens':
                    return Mock(side_effect=old.model_answer)
                if replies == []:
                    return None
                return Mock(side_effect=copy.deepcopy(replies)) if replies is not None else Mock()

            for name, module in modules.items():
                model = new_model()
                result = old.r14.in_process(module, pdf, signers, model)
                results[name] = result
                row['results'][name] = remember(result)
                row['model_calls'][name] = model.call_count if model is not None else 0
                expected_calls = len(replies) if replies is not None else int(group == 'Seven goldens' and case == 'unusual')
                assert row['model_calls'][name] == expected_calls, (group, case, name, 'model_calls')
                wrong = (bool(old.r15.wrong_pat_fields(result, line)) if line else
                         old.earlier_wrong(group, case, result, expected))
                row['wrong'][name] = wrong
                for status in ['placed', 'needs_sender', 'bare']:
                    count[name + '_' + ('holds' if status == 'needs_sender' else status)] += result['status'] == status
                count[name + '_wrong'] += wrong
                if group == 'Seven goldens':
                    count[name + '_golden_diffs'] += old.versionless(result) != old.versionless(goldens[case])
                    for signer in signers:
                        assert module.to_native_fields(result, signer['email']) == module.to_native_fields(goldens[case], signer['email'])
            if expected is not None:
                assert old.versionless(results['r14']) == old.versionless(expected), (group, case, 'baseline')
            changed = old.versionless(results[chosen]) != old.versionless(results['r14'])
            count[chosen + '_full_diffs'] += changed
            before = 'wrong' if row['wrong']['r14'] else results['r14']['status']
            after = 'wrong' if row['wrong'][chosen] else results[chosen]['status']
            if before != after:
                transitions[group][before + ' -> ' + after] += 1
            if changed:
                differences.append({'group': group, 'case': case, 'before': row['results']['r14'],
                                    'after': row['results'][chosen]})
            records.append(row)
            if group in {'Seven goldens', 'r14 reproduction', 'r14 correct controls',
                         'r15 M1 reproduction', 'r15 M2 reproduction'} or group.endswith('/ caption_row_right'):
                for name, module in modules.items():
                    model = new_model()
                    actual = module.place(pdf, signers, model_client=model)
                    assert actual == results[name], (name, group, case, 'worker')
                    calls = model.call_count if model is not None else 0
                    assert calls == row['model_calls'][name]
                    workers.append({'candidate': name, 'group': group, 'case': case,
                                    'result': remember(actual), 'model_calls': calls})
            if len(records) % 250 == 0:
                print(f'{len(records)} cases compared across r14 and {chosen}', flush=True)

    forbidden.assert_not_called()
    assert groups['r14 L-1 (grid subset)']['cases'] == 72
    assert groups['r15 M1']['r14_wrong'] == 100 and groups['r15 M2']['r14_wrong'] == 432
    bars = {'zero_wrong_every_family': all(g[chosen + '_wrong'] == 0 for g in groups.values()),
            'goldens_exact': groups['Seven goldens'][chosen + '_golden_diffs'] == 0}
    summary = {'base': old.BASE, 'source_sha256': {name: hashlib.sha256(s.encode()).hexdigest() for name, s in sources.items()},
               'cases_including_L1_subset': len(records), 'cases_excluding_L1_subset': len(records) - 72,
               'original_cases_excluding_L1_subset': 9754, 'added_control_cases': sum(v['cases'] for v in inventory.values()),
               'candidate': chosen, 'groups': groups, 'bars': bars, 'external_http_calls': forbidden.call_count,
               'transitions': transitions, 'worker_evaluations': len(workers)}
    write('counterfactual-cases', {'cases': records, 'outcomes': outcomes})
    write('counterfactual-differences', differences)
    write('counterfactual-workers', workers)
    write('counterfactual-summary', summary)
    write('added-control-families', inventory)
    write('placements', {r['case']: outcomes[r['results'][chosen]] for r in records if r['group'] == 'Seven goldens'})
    print(json.dumps(summary, indent=2), flush=True)
    assert all(bars.values()), bars


if __name__ == '__main__':
    main()
