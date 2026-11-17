"""Replay every unchanged r15b case against r14, nearest-only, and r16."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r15b_evidence', OUT.parent / 'c2a-r15/check_evidence-r15b.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
old = prior.old
# Temporary worker packages belong to the new evidence directory.
old.OUT = OUT
# The historical case generator resolves earlier files relative to r15.
# Both directories share the same parent, so that lookup remains unchanged.
control_cases = prior.control_cases


def write(stem, value):
    (OUT / (stem + '.json')).write_text(json.dumps(value, indent=2) + '\n')


def main():
    sys.dont_write_bytecode = True
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    base = subprocess.check_output(['git', 'show', old.BASE + ':' + old.PRODUCT], cwd=ROOT).decode()
    chosen = 'chosen'
    sources = {'r14': base, 'nearest': prior.nearest_source(base),
               chosen: (ROOT / old.PRODUCT).read_text()}
    assert "VERSION = 'c2a.16'" in sources[chosen]
    (OUT / 'candidate.patch').write_text(''.join(difflib.unified_diff(
        base.splitlines(True), sources[chosen].splitlines(True),
        fromfile='a/' + old.PRODUCT, tofile='b/' + old.PRODUCT)))
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
    archived_nearest = json.loads((OUT.parent / 'c2a-r15/counterfactual-summary-r15b.json').read_text())
    assert sources['nearest'] == (OUT / 'nearest-placement.py.txt').read_text()
    assert set(groups) == set(archived_nearest['groups'])
    for group, counts in archived_nearest['groups'].items():
        for key, value in counts.items():
            if key != 'nearest_full_diffs':
                assert groups[group][key] == value, (group, key)
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
