"""Replay immutable historical inputs and explicit r24 reconstructions on five sources."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
from functools import lru_cache
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

from candidate_sources import sources, PRODUCT

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(OUT.parent / 'c2a-r23')]
import replay
import stress
from dealroom_sign.tests import placement_r24_review_cases as added
from dealroom_sign.tests.test_placement_r23 import EXTRA, WORKERS
from review_h1 import cases as review_h1_cases

replay.prior.OUT = OUT
VERSIONS = ('r21', 'r23', 'cand', 'cand3', 'r24')


def inputs(part, generator, inventory):
    if part in {'historical', 'review', 'layouts', 'wrapped', 'new'}:
        yield from replay.cases(part, generator, inventory)
        return
    if part == 'stress':
        for group, case, pages, both, allowed, worker in stress.cases():
            yield group, case, added.rc.pages_pdf(pages), replay.signers(both), None, None, allowed, worker
        return
    if part == 'q2':
        rows = added.cases.matrix()
    elif part == 'extra':
        rows = EXTRA
    elif part in {'attack', 'boundary'}:
        rows = added.cases.matrix(added.ATTACK if part == 'attack' else added.BOUNDARY)
    elif part == 'h1':
        rows = added.cross_page_matrix()
    elif part == 'h1_review':
        rows = review_h1_cases()
    elif part == 'veto':
        rows = added.veto_matrix()
    elif part == 'workers':
        rows = ((a, *added.cases.worker_case(*a)) for a in WORKERS)
    elif part == 'workers24':
        rows = [(('b1', both), *added.worker_case('b1', both)) for both in (False, True)]
        rows += [(('b2', both), *added.worker_case('b2', both)) for both in (False, True)]
        rows += [(('h1',), *added.h1_worker_case())]
    elif part == 'workers_h1_uncaptioned':
        rows = [(('h1_uncaptioned',), *added.h1_uncaptioned_worker_case())]
    else:
        raise ValueError(part)
    for args, pages, people, allowed in rows:
        group = part.upper() if part in {'h1', 'h1_review', 'veto'} else args[0]
        yield group, repr(args), added.rc.pages_pdf(pages), people, None, None, allowed, part.startswith('workers')


def main(part):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    variants = sources()
    archives = {}
    prior_path = OUT.parent / 'c2a-r23' / (part + '-cases.json')
    if prior_path.exists():
        prior = json.loads(prior_path.read_text())
        archives = {(r['group'], r['case']): {v: prior['outcomes'][r['results'][v]] for v in ('r21', 'r23')}
                    for r in prior['cases']}
    groups, records, outcomes, workers = {}, [], {}, []
    transitions = defaultdict(Counter)
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    goldens = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    with ExitStack() as stack:
        modules = {n: replay.prior.make_module(part + '_' + n, s, stack) for n, s in variants.items()}
        # Grammar-equivalent variants share only a pristine extraction. Each
        # scorer gets a deep copy; real workers always parse independently.
        parse = {}
        for n in ('r21', 'r23', 'cand'):
            parse[n] = lru_cache(maxsize=1)(modules[n].extract)
        for n, module in modules.items():
            extractor = parse[n if n in parse else 'cand']
            stack.enter_context(patch.object(module, 'extract',
                                lambda pdf, deadline=None, fn=extractor: copy.deepcopy(fn(pdf))))
        generator = replay.prior.make_module('generator_' + part, subprocess.check_output(
            ['git', 'show', replay.old.BASE + ':' + PRODUCT], cwd=ROOT).decode(), stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pdf, people, line, replies, allowed, worker in inputs(part, generator, {}):
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            row = dict(group=group, case=case, results={}, wrong={}, raw_wrong={}, model_calls={},
                       input_sha256=hashlib.sha256(pdf).hexdigest())
            states = {}
            expected = archives.get((group, case))

            def client():
                if group == 'Seven goldens':
                    return Mock(side_effect=replay.old.model_answer)
                if replies == []:
                    return None
                return Mock(side_effect=copy.deepcopy(replies)) if replies is not None else Mock()

            for name, module in modules.items():
                model = client()
                result = replay.old.r14.in_process(module, pdf, people, model)
                digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
                outcomes[digest] = result
                row['results'][name] = digest
                if allowed is not None:
                    oracle = replay.prior.prior.new.wrong_fields if part in {'historical', 'review'} else added.rc.wrong_fields
                    raw = bool(oracle(result, allowed))
                elif line:
                    raw = bool(replay.old.r15.wrong_pat_fields(result, line))
                else:
                    raw = replay.old.earlier_wrong(group, case, result, expected['r21'] if expected else None)
                wrong = raw
                if group == 'Competition' and replay.prior.permitted_named_competition(case, result, allowed):
                    wrong = False
                if group == 'Q4 M1 ambiguity':
                    wrong = False
                row['raw_wrong'][name], row['wrong'][name] = raw, wrong
                state = 'w' if wrong else {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[result['status']]
                states[name] = state
                counts[name + '_' + state] += 1
                counts[name + '_raw_wrong'] += raw
                calls = model.call_count if model is not None else 0
                row['model_calls'][name] = calls
                expected_calls = len(replies) if replies is not None else int(group == 'Seven goldens' and case == 'unusual')
                assert calls == expected_calls, (part, case, name, calls, expected_calls)
                if expected and name in expected:
                    assert replay.old.versionless(result) == replay.old.versionless(expected[name]), (part, case, name, 'archive differs')
                if group == 'Seven goldens':
                    counts[name + '_golden_diffs'] += replay.old.versionless(result) != replay.old.versionless(goldens[case])
                    counts[name + '_native_diffs'] += any(module.to_native_fields(result, p['email']) != module.to_native_fields(goldens[case], p['email']) for p in people)
                if worker:
                    actual = module.place(pdf, people, model_client=client())
                    assert actual == result, (part, case, name, 'worker differs')
                    workers.append(dict(group=group, case=case, variant=name, result=digest))
            for name in VERSIONS[1:]:
                counts[name + '_n_to_p'] += states['r21'] == 'n' and states[name] in {'c', 'w'}
                counts[name + '_c_to_w'] += states['r21'] == 'c' and states[name] == 'w'
                counts[name + '_n_to_w'] += states['r21'] == 'n' and states[name] == 'w'
                counts[name + '_c_to_n'] += states['r21'] == 'c' and states[name] == 'n'
                counts[name + '_cand_c_to_n'] += states['cand'] == 'c' and states[name] == 'n'
            transitions[group][' -> '.join(states[n] for n in VERSIONS)] += 1
            records.append(row)
            if len(records) % 240 == 0:
                print(part, len(records), 'r24 wrong', sum(g['r24_w'] for g in groups.values()), flush=True)
        forbidden.assert_not_called()
    if archives:
        assert {(r['group'], r['case']) for r in records} == set(archives), (part, 'inventory differs')
    summary = dict(part=part, cases=len(records), groups=groups, transitions=transitions,
                   source_sha256={n: hashlib.sha256(s.encode()).hexdigest() for n,s in variants.items()},
                   external_http_calls=forbidden.call_count, worker_evaluations=len(workers))
    for name, data in [(part + '-summary', summary), (part + '-cases', dict(cases=records, outcomes=outcomes)),
                       (part + '-workers', workers)]:
        path = OUT / (name + '.json')
        assert not path.exists(), path
        path.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
