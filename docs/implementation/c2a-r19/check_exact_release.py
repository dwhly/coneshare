"""Final-source replay of every exact review case, with preserved counterfactuals."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from unittest.mock import Mock, patch

import check_evidence as replay
from dealroom_sign.tests import placement_r19_review_cases as families
from dealroom_sign.tests.test_placement_r19_review import justified_company_only


def main():
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    archive = json.loads((replay.OUT / 'exact-review-cases.json').read_text())
    prior = {(r['group'], r['case']): r for r in archive['cases']}
    baseline_summary = json.loads((replay.OUT / 'exact-review-summary.json').read_text())
    variants = replay.sources()
    for name in ['r18', 'candidate', 'narrower']:
        assert hashlib.sha256(variants[name].encode()).hexdigest() == baseline_summary['source_sha256'][name]
    groups, records, outcomes, workers = {}, [], archive['outcomes'].copy(), []
    transitions = defaultdict(lambda: defaultdict(Counter))
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    (replay.OUT / 'release-review-chosen.py.txt').write_text(variants['chosen'])

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        module = replay.make_module('release_review', variants['chosen'], stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for generator in [families.competition, families.l1_cases, families.f_fine]:
            for group, case, rows, both, allowed in generator():
                count = groups.setdefault(group, Counter())
                count['cases'] += 1
                record = copy.deepcopy(prior[group, case])
                pdf = replay.new.rows_pdf(rows)
                model = Mock()
                result = replay.old.r14.in_process(module, pdf, replay.new.signers(both), model)
                assert model.call_count == 0
                raw_wrong = bool(replay.new.wrong_fields(result, allowed))
                justified = group == 'Competition' and justified_company_only(case, result, allowed)
                record['raw_wrong']['chosen'] = raw_wrong
                record['wrong']['chosen'] = raw_wrong and not justified
                record['justified']['chosen'] = justified
                record['results']['chosen'] = remember(result)
                record['classification']['chosen'] = ('sole_domain_company_match' if justified else
                    'wrong_rule' if record['wrong']['chosen'] else 'held' if result['status'] == 'needs_sender' else 'correct_rule')
                for name in variants:
                    actual = outcomes[record['results'][name]]
                    count[name + '_raw_wrong'] += record['raw_wrong'][name]
                    count[name + '_wrong'] += record['wrong'][name]
                    count[name + '_justified'] += record['justified'][name]
                    for status in ['placed', 'needs_sender', 'bare']:
                        count[name + '_' + ('holds' if status == 'needs_sender' else status)] += actual['status'] == status
                    if name != 'r18':
                        baseline = outcomes[record['results']['r18']]
                        before = 'wrong' if record['wrong']['r18'] else baseline['status']
                        after = 'wrong' if record['wrong'][name] else actual['status']
                        transitions[group][name][before + ' -> ' + after] += 1
                records.append(record)
                if group == 'Competition' and (record['wrong']['candidate'] or count['cases'] % 40 == 0):
                    model = Mock()
                    worker = module.place(pdf, replay.new.signers(both), model_client=model)
                    assert worker == result
                    assert model.call_count == 0
                    workers.append({'group': group, 'case': case, 'result': remember(worker)})
                if len(records) % 500 == 0:
                    print(f'{len(records)} release review cases compared', flush=True)
    forbidden.assert_not_called()
    replay.write('release-review-cases', {'cases': records, 'outcomes': outcomes})
    replay.write('release-review-summary', {'groups': groups, 'transitions': transitions, 'cases': len(records),
                 'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n,s in variants.items()},
                 'external_http_calls': forbidden.call_count, 'worker_evaluations': len(workers)})
    replay.write('release-review-workers', workers)
    print(json.dumps(groups, indent=2), flush=True)
    assert all(g['chosen_wrong'] == 0 for g in groups.values())


if __name__ == '__main__':
    main()
