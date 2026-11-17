"""Replay every r16 family and the Gate 3 r17 regressions, without network."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import l1_candidate

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r16_evidence', OUT.parent / 'c2a-r16/check_evidence.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
old = prior.old
old.OUT = OUT
from dealroom_sign.tests import test_placement_r17 as new  # noqa: E402


def write(name, value):
    (OUT / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')


def added_cases():
    yield from l1_candidate.cases(new)
    for args in new.A2:
        caption, dy, heading, reverse, both = args
        yield 'A2 exact witness captions', repr(args), new.witness_rows(caption, dy, heading=heading, reverse=reverse), both, {}
    # Include dy=20 too: the review's verbal axes imply 576 rather than 480.
    for args in new.A2:
        caption, dy, heading, reverse, both = args
        if dy == 0:
            yield 'A2 additional dy=20', repr(args), new.witness_rows(caption, 20, heading=heading, reverse=reverse), both, {}
    for args in new.SWEEP:
        caption, dy, gap, own_name, heading, reverse, both = args
        yield 'Witness wider sweep', repr(args), new.witness_rows(caption, dy, gap, own_name, heading, reverse), both, {}
    for args in new.F:
        order, dy, short, own_name, both = args
        rows, allowed = new.three_party_rows(order, dy, short, own_name)
        yield 'F three-party permutations', repr(args), rows, both, allowed
    for args in new.F_GAPS:
        gap, short, order, dy, both = args
        rows, allowed = new.three_party_rows(order, dy, short, gap=gap)
        yield 'F heading gaps ' + ('short' if short else 'long'), repr(args), rows, both, allowed
    for both in [False, True]:
        yield 'B1 reproduction', str(both), new.witness_rows(), both, {}
        rows, allowed = new.three_party_rows()
        yield 'B2 reproduction', str(both), rows, both, allowed


def main():
    sys.dont_write_bytecode = True
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    base = subprocess.check_output(['git', 'show', '75837b04:' + old.PRODUCT], cwd=ROOT).decode()
    sources = {'r16': base, 'b1_only': base.replace(' and not witness_block(other)', ''),
               'r17': (ROOT / old.PRODUCT).read_text()}
    sources['l1'] = l1_candidate.candidate(sources['r17'])
    (OUT / 'l1-placement.py.txt').write_text(sources['l1'])
    archived = json.loads((OUT.parent / 'c2a-r16/counterfactual-cases.json').read_text())
    accepted = {(r['group'], r['case']): archived['outcomes'][r['results']['chosen']] for r in archived['cases']}
    published = json.loads((OUT.parent / 'c2a-r16/counterfactual-summary.json').read_text())
    goldens = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    groups, records, outcomes, workers, inventory = {}, [], {}, [], {}
    transitions = defaultdict(Counter)
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {name: old.make_module(name, source, stack) for name, source in sources.items()}
        r14_source = subprocess.check_output(['git', 'show', old.BASE + ':' + old.PRODUCT], cwd=ROOT).decode()
        r14_module = old.make_module('generator_r14', r14_source, stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))

        def cases():
            for group, case, pdf, signers, line in old.cases():
                yield group, case, pdf, signers, line, None, accepted[group, case], None
            for group, case, pdf, signers, line, replies, expected in prior.control_cases(r14_module, inventory):
                yield group, case, pdf, signers, line, replies, accepted[group, case], None
            for group, case, rows, both, allowed in added_cases():
                yield group, case, new.rows_pdf(rows), new.signers(both), None, None, None, allowed

        for group, case, pdf, signers, line, replies, expected, allowed in cases():
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
                if allowed is not None:
                    wrong = bool(new.wrong_fields(result, allowed))
                else:
                    wrong = (bool(old.r15.wrong_pat_fields(result, line)) if line else
                             old.earlier_wrong(group, case, result, expected))
                row['wrong'][name] = wrong
                count[name + '_wrong'] += wrong
                for status in ['placed', 'needs_sender', 'bare']:
                    count[name + '_' + ('holds' if status == 'needs_sender' else status)] += result['status'] == status
                count[name + '_model_calls'] += row['model_calls'][name]
                if group == 'Seven goldens':
                    count[name + '_golden_diffs'] += old.versionless(result) != old.versionless(goldens[case])
                    for signer in signers:
                        native_equal = module.to_native_fields(result, signer['email']) == module.to_native_fields(goldens[case], signer['email'])
                        count[name + '_native_diffs'] += not native_equal
                        if name != 'l1':
                            assert native_equal
            if expected is not None:
                assert old.versionless(results['r16']) == old.versionless(expected), (group, case, 'r16 replay')
                expected_calls = len(replies) if replies is not None else int(group == 'Seven goldens' and case == 'unusual')
                assert row['model_calls']['r16'] == expected_calls, (group, case, 'model calls')
            count['r17_full_diffs'] += old.versionless(results['r17']) != old.versionless(results['r16'])
            before = 'wrong' if row['wrong']['r16'] else results['r16']['status']
            after = 'wrong' if row['wrong']['r17'] else results['r17']['status']
            transitions[group][before + ' -> ' + after] += 1
            records.append(row)
            if group in {'Seven goldens', 'r14 reproduction', 'r14 correct controls',
                         'r15 M1 reproduction', 'r15 M2 reproduction', 'B1 reproduction', 'B2 reproduction'}:
                for name, module in modules.items():
                    model = new_model()
                    actual = module.place(pdf, signers, model_client=model)
                    assert actual == results[name], (name, group, case, 'worker')
                    workers.append({'candidate': name, 'group': group, 'case': case, 'result': remember(actual)})
            if len(records) % 250 == 0:
                print(f'{len(records)} cases compared', flush=True)

    forbidden.assert_not_called()
    for group, counts in published['groups'].items():
        for key in ['wrong', 'placed', 'holds', 'bare']:
            assert groups[group]['r16_' + key] == counts['chosen_' + key], (group, key)
            assert groups[group]['b1_only_' + key] == counts['chosen_' + key], (group, 'B1 count', key)
    bars = {'zero_wrong_every_family': all(g['r17_wrong'] == 0 for g in groups.values()),
            'goldens_exact': groups['Seven goldens']['r17_golden_diffs'] == 0,
            'r16_replay_exact': True, 'b1_preserves_every_r16_family_count': True}
    summary = {'base': '75837b04da05c3b736d6f48648536627bd062ca0',
               'source_sha256': {name: hashlib.sha256(s.encode()).hexdigest() for name, s in sources.items()},
               'cases': len(records), 'groups': groups, 'bars': bars,
               'external_http_calls': forbidden.call_count, 'transitions': transitions,
               'worker_evaluations': len(workers)}
    write('counterfactual-cases', {'cases': records, 'outcomes': outcomes})
    write('counterfactual-summary', summary)
    write('counterfactual-workers', workers)
    write('placements', {r['case']: outcomes[r['results']['r17']] for r in records if r['group'] == 'Seven goldens'})
    print(json.dumps(summary, indent=2), flush=True)
    assert all(bars.values()), bars


if __name__ == '__main__':
    main()
