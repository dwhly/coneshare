"""Measure the final implementation and exact narrower alternative on the sweeps."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from unittest.mock import Mock, patch

import check_evidence as replay
import review_families as families


def main():
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    archive = json.loads((replay.OUT / 'reconstructed-cases.json').read_text())
    prior = {(r['group'], r['case']): r for r in archive['cases']}
    variants = replay.sources()
    groups, records, outcomes = {}, [], archive['outcomes'].copy()
    transitions = defaultdict(lambda: defaultdict(Counter))
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    for name, source in variants.items():
        (replay.OUT / ('review-final-' + name + '.py.txt')).write_text(source)

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {n: replay.make_module('review_final_' + n, variants[n], stack) for n in ['narrower', 'chosen']}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for generator in [families.fine_f_cases, families.boundary_cases]:
            for group, case, rows, both, allowed in generator():
                count = groups.setdefault(group, Counter())
                count['cases'] += 1
                record = copy.deepcopy(prior[group, case])
                pdf = replay.new.rows_pdf(rows)
                for name, module in modules.items():
                    model = Mock()
                    result = replay.old.r14.in_process(module, pdf, replay.new.signers(both), model)
                    assert model.call_count == 0
                    record['wrong'][name] = bool(replay.new.wrong_fields(result, allowed))
                    record['results'][name] = remember(result)
                for name in variants:
                    result = outcomes[record['results'][name]]
                    count[name + '_wrong'] += record['wrong'][name]
                    for status in ['placed', 'needs_sender', 'bare']:
                        count[name + '_' + ('holds' if status == 'needs_sender' else status)] += result['status'] == status
                    if name != 'r18':
                        baseline = outcomes[record['results']['r18']]
                        before = 'wrong' if record['wrong']['r18'] else baseline['status']
                        after = 'wrong' if record['wrong'][name] else result['status']
                        transitions[group][name][before + ' -> ' + after] += 1
                records.append(record)
                if len(records) % 500 == 0:
                    print(f'{len(records)} final review cases compared', flush=True)
    forbidden.assert_not_called()
    replay.write('review-final-cases', {'cases': records, 'outcomes': outcomes})
    replay.write('review-final-summary', {'groups': groups, 'transitions': transitions, 'cases': len(records),
                 'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n,s in variants.items()},
                 'external_http_calls': forbidden.call_count})
    print(json.dumps(groups, indent=2), flush=True)


if __name__ == '__main__':
    main()
