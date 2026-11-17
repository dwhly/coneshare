"""Run verbatim reviewer generators with unchanged raw oracles and explicit adjudication."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import ast
import hashlib
import json
import os
from unittest.mock import Mock, patch

import check_evidence as replay
from dealroom_sign.tests import placement_r19_review_cases as families
from dealroom_sign.tests.test_placement_r19_review import assert_competition_result, justified_company_only


def main():
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    variants = replay.sources()
    groups, records, outcomes, workers = {}, [], {}, []
    transitions = defaultdict(lambda: defaultdict(Counter))
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    for name, source in variants.items():
        (replay.OUT / ('exact-review-' + name + '.py.txt')).write_text(source)

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {n: replay.make_module('exact_' + n, s, stack) for n, s in variants.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        # Competition first: preserve the failing-first historical assertions.
        for generator in [families.competition, families.l1_cases, families.f_fine]:
            for group, case, rows, both, allowed in generator():
                count = groups.setdefault(group, Counter())
                count['cases'] += 1
                record = {'group': group, 'case': case, 'results': {}, 'raw_wrong': {}, 'wrong': {},
                          'justified': {}, 'classification': {}}
                results = {}
                pdf = replay.new.rows_pdf(rows)
                for name, module in modules.items():
                    model = Mock()
                    result = replay.old.r14.in_process(module, pdf, replay.new.signers(both), model)
                    assert model.call_count == 0
                    results[name] = result
                    raw_wrong = bool(replay.new.wrong_fields(result, allowed))
                    justified = group == 'Competition' and justified_company_only(case, result, allowed)
                    wrong = raw_wrong and not justified
                    record['raw_wrong'][name] = raw_wrong
                    record['wrong'][name] = wrong
                    record['justified'][name] = justified
                    record['results'][name] = remember(result)
                    record['classification'][name] = ('sole_domain_company_match' if justified else
                        'wrong_rule' if wrong else 'held' if result['status'] == 'needs_sender' else 'correct_rule')
                    count[name + '_raw_wrong'] += raw_wrong
                    count[name + '_wrong'] += wrong
                    count[name + '_justified'] += justified
                    for status in ['placed', 'needs_sender', 'bare']:
                        count[name + '_' + ('holds' if status == 'needs_sender' else status)] += result['status'] == status
                    if group == 'Competition':
                        try:
                            assert_competition_result(case, result, allowed)
                        except AssertionError:
                            count[name + '_test_failed'] += 1
                        else:
                            count[name + '_test_passed'] += 1
                for name in ['candidate', 'narrower', 'chosen']:
                    before = 'wrong' if record['wrong']['r18'] else results['r18']['status']
                    after = 'wrong' if record['wrong'][name] else results[name]['status']
                    transitions[group][name][before + ' -> ' + after] += 1
                records.append(record)
                if group == 'Competition' and (record['wrong']['candidate'] or count['cases'] % 40 == 0):
                    for name in ['r18', 'chosen']:
                        model = Mock()
                        actual = modules[name].place(pdf, replay.new.signers(both), model_client=model)
                        assert actual == results[name], (name, case, 'worker')
                        assert model.call_count == 0
                        workers.append({'variant': name, 'group': group, 'case': case, 'result': remember(actual)})
                if group == 'Competition' and count['cases'] == 480:
                    print('Competition', json.dumps(count), flush=True)
                    replay.write('competition-failing-first', dict(count))
                if len(records) % 500 == 0:
                    print(f'{len(records)} exact review cases compared', flush=True)
    forbidden.assert_not_called()
    assert groups['Competition']['r18_raw_wrong'] == 348
    assert groups['Competition']['candidate_raw_wrong'] == 300
    assert groups['L1 boundary pat']['cases'] == 3480
    assert groups['L1 boundary fleet']['cases'] == 1800
    assert groups['L1 boundary pat']['r18_raw_wrong'] == 94
    assert groups['L1 boundary fleet']['r18_raw_wrong'] == 192
    assert sum(g['cases'] for g in groups.values()) == 12672
    replay.write('exact-review-cases', {'cases': records, 'outcomes': outcomes})
    replay.write('exact-review-summary', {'groups': groups, 'transitions': transitions, 'cases': len(records),
                 'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n,s in variants.items()},
                 'external_http_calls': forbidden.call_count, 'worker_evaluations': len(workers)})
    replay.write('exact-review-workers', workers)
    print(json.dumps(groups, indent=2), flush=True)
    assert all(g['chosen_wrong'] == 0 for g in groups.values())


if __name__ == '__main__':
    main()
