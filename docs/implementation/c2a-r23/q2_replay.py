"""Compare the recorded Q2 inputs, supplements and real workers across releases."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
import json
import os
import subprocess
import sys
from unittest.mock import Mock, patch

import replay
from dealroom_sign.tests import placement_r23_review_cases as cases
from dealroom_sign.tests.test_placement_r23 import EXTRA, WORKERS


def inputs(part):
    if part == 'q2':
        for args, pages, people, allowed in cases.matrix():
            yield args[0], repr(args), pages, people, allowed, False
    elif part == 'extra':
        for args, pages, people, allowed in EXTRA:
            yield args[0], repr(args), pages, people, allowed, False
    else:
        for args in WORKERS:
            pages, people, allowed = cases.worker_case(*args)
            yield args[0], repr(args), pages, people, allowed, True


def main(part):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    sources = {n: subprocess.check_output(['git', 'show', sha + ':' + replay.old.PRODUCT], cwd=replay.ROOT).decode()
               for n, sha in [('r21', 'afb9aa6e'), ('r22', 'e2d7ba11')]}
    sources['r23'] = (replay.ROOT / replay.old.PRODUCT).read_text()
    groups, records, outcomes, workers = {}, [], {}, []
    transitions = defaultdict(Counter)
    forbidden = Mock(side_effect=AssertionError('HTTP forbidden'))
    with ExitStack() as stack:
        modules = {n: replay.prior.make_module(part + '_' + n, s, stack) for n, s in sources.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pages, people, allowed, worker in inputs(part):
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            row = {'group': group, 'case': case, 'results': {}, 'wrong': {}, 'roles': {}}
            pdf = cases.rc.pages_pdf(pages)
            row['input_sha256'] = hashlib.sha256(pdf).hexdigest()
            states = []
            for name, module in modules.items():
                model = Mock()
                result = replay.old.r14.in_process(module, pdf, people, model)
                wrong = bool(cases.rc.wrong_fields(result, allowed))
                digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
                outcomes[digest] = result
                row['results'][name] = digest
                row['wrong'][name] = wrong
                row['roles'][name] = module.extract(pdf)[2]
                counts[name + '_wrong'] += wrong
                counts[name + '_' + ('wrong_placements' if wrong else {'placed': 'placed', 'needs_sender': 'holds', 'bare': 'bare'}[result['status']])] += 1
                model.assert_not_called()
                states.append('wrong' if wrong else result['status'])
                if worker:
                    actual = module.place(pdf, people, model_client=model)
                    assert actual == result, (case, name, actual, result)
                    model.assert_not_called()
                    workers.append({'case': case, 'variant': name, 'result': digest})
            transitions[group][' -> '.join(states)] += 1
            records.append(row)
            if len(records) % 240 == 0:
                print(part, len(records), 'cells;', sum(g['r23_wrong'] for g in groups.values()), 'r23 wrong', flush=True)
    forbidden.assert_not_called()
    summary = {'cases': len(records), 'groups': groups, 'transitions': transitions,
               'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n, s in sources.items()},
               'external_http_calls': forbidden.call_count, 'worker_evaluations': len(workers)}
    replay.write(part + '-summary', summary)
    replay.write(part + '-cases', {'cases': records, 'outcomes': outcomes})
    replay.write(part + '-workers', workers)
    print(json.dumps(summary, indent=2), flush=True)
    assert all(g['r23_wrong'] == 0 for g in groups.values())


if __name__ == '__main__':
    main(sys.argv[1])
