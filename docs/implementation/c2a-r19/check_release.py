"""Replay the final source, retaining the measured historical alternatives."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import ast
import copy
import hashlib
import json
import os
from unittest.mock import Mock, patch

import check_evidence as replay


def main():
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    archive = json.loads((replay.OUT / 'final-cases.json').read_text())
    previous = {(r['group'], r['case']): r for r in archive['cases']}
    summary = json.loads((replay.OUT / 'final-summary.json').read_text())
    golden = json.loads((replay.OUT.parent / 'c2a-r13/placements.json').read_text())
    source = (replay.ROOT / replay.old.PRODUCT).read_text()
    narrower_source = replay.sources()['narrower']
    (replay.OUT / 'release-placement.py.txt').write_text(source)
    (replay.OUT / 'release-narrower.py.txt').write_text(narrower_source)
    groups, records, outcomes, workers, inventory = {}, [], archive['outcomes'].copy(), [], {}
    transitions = defaultdict(lambda: defaultdict(Counter))
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        module = replay.make_module('final', source, stack)
        narrower = replay.make_module('final_narrower', narrower_source, stack)
        r18 = replay.make_module('final_r18', replay.sources()['r18'], stack)
        baseline = replay.make_module('generator_r14', replay.subprocess.check_output(
            ['git', 'show', replay.old.BASE + ':' + replay.old.PRODUCT], cwd=replay.ROOT).decode(), stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))

        def cases():
            for group, case, pdf, signers, line in replay.old.cases():
                yield group, case, pdf, signers, line, None, None
            for group, case, pdf, signers, line, replies, _ in replay.prior.prior.prior.control_cases(baseline, inventory):
                yield group, case, pdf, signers, line, replies, None
            for generator in [replay.prior.prior.added_cases, replay.prior.affiliate_cases, replay.new_cases]:
                for group, case, rows, both, allowed in generator():
                    yield group, case, replay.new.rows_pdf(rows), replay.new.signers(both), None, None, allowed

        for group, case, pdf, signers, line, replies, allowed in cases():
            row = copy.deepcopy(previous[group, case])
            expected = outcomes[row['results']['r18']]
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1

            def client():
                if group == 'Seven goldens':
                    return Mock(side_effect=replay.old.model_answer)
                if replies == []:
                    return None
                return Mock(side_effect=copy.deepcopy(replies)) if replies is not None else Mock()

            for name, variant in [('chosen', module)]:
                model = client()
                result = replay.old.r14.in_process(variant, pdf, signers, model)
                row['results'][name] = remember(result)
                row['wrong'][name] = (bool(replay.new.wrong_fields(result, allowed)) if allowed is not None else
                    bool(replay.old.r15.wrong_pat_fields(result, line)) if line else
                    replay.old.earlier_wrong(group, case, result, expected))
                row['model_calls'][name] = model.call_count if model is not None else 0
            for name in ['r18', 'candidate', 'narrower', 'chosen']:
                actual = outcomes[row['results'][name]]
                counts[name + '_wrong'] += row['wrong'][name]
                counts[name + '_model_calls'] += row['model_calls'][name]
                for status in ['placed', 'needs_sender', 'bare']:
                    counts[name + '_' + ('holds' if status == 'needs_sender' else status)] += actual['status'] == status
                if name != 'r18':
                    counts[name + '_full_diffs'] += replay.old.versionless(actual) != replay.old.versionless(expected)
                    before = 'wrong' if row['wrong']['r18'] else expected['status']
                    after = 'wrong' if row['wrong'][name] else actual['status']
                    transitions[group][name][before + ' -> ' + after] += 1
                if group == 'Seven goldens':
                    counts[name + '_golden_diffs'] += replay.old.versionless(actual) != replay.old.versionless(golden[case])
                    for signer in signers:
                        counts[name + '_native_diffs'] += module.to_native_fields(actual, signer['email']) != module.to_native_fields(golden[case], signer['email'])
            records.append(row)
            veto_worker = (group == 'Veto matrix'
                           and ast.literal_eval(case)[1:3] == (replay.new.AFFILIATES[0], 40))
            if group in {'Seven goldens', 'r18 B1 reproduction'} or veto_worker:
                actual = module.place(pdf, signers, model_client=client())
                assert actual == result, (group, case, 'worker')
                workers.append({'variant': 'chosen', 'group': group, 'case': case, 'result': remember(actual)})
                if veto_worker:
                    actual = r18.place(pdf, signers, model_client=client())
                    assert actual == expected, (group, case, 'r18 worker')
                    workers.append({'variant': 'r18', 'group': group, 'case': case, 'result': remember(actual)})
            if len(records) % 500 == 0:
                print(f'{len(records)} final cases compared', flush=True)
    forbidden.assert_not_called()
    assert len(records) == summary['cases']
    assert all(g['chosen_wrong'] == 0 for g in groups.values())
    assert groups['Seven goldens']['chosen_golden_diffs'] == groups['Seven goldens']['chosen_native_diffs'] == 0
    replay.write('release-cases', {'cases': records, 'outcomes': outcomes})
    summary.update(groups=groups, transitions=transitions, final_worker_evaluations=len(workers))
    summary['source_sha256']['chosen'] = hashlib.sha256(source.encode()).hexdigest()
    summary['source_sha256']['narrower'] = hashlib.sha256(narrower_source.encode()).hexdigest()
    replay.write('release-summary', summary)
    replay.write('release-workers', workers)
    replay.write('release-placements', {r['case']: outcomes[r['results']['chosen']] for r in records if r['group'] == 'Seven goldens'})
    print(json.dumps({'cases': len(records), 'groups': len(groups), 'wrong': 0, 'golden_diffs': 0}, indent=2), flush=True)


if __name__ == '__main__':
    main()
