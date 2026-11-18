"""Re-run live r21 and shipped narrow on every immutable r24 input family."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
import measure

EVIDENCE = Path(__file__).resolve().parent
OUT = EVIDENCE / 'r24b'
ROOT = EVIDENCE.parents[2]
PRODUCT = ROOT / 'backend/dealroom_sign/placement.py'
PARTS = ('historical', 'review', 'layouts', 'wrapped', 'new', 'stress', 'q2',
         'extra', 'workers', 'attack', 'boundary', 'h1_review', 'veto',
         'workers24', 'workers_h1_uncaptioned')


def write(name, value):
    with (OUT / name).open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def main(part):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    live = subprocess.check_output(
        ['git', 'show', 'afb9aa6e:backend/dealroom_sign/placement.py'], cwd=ROOT)
    shipped = PRODUCT.read_bytes()
    assert shipped == (EVIDENCE / 'r24-source.py.txt').read_bytes()
    assert b"VERSION = 'c2a.24'" in shipped
    variants = {'r21': live.decode(), 'r24': shipped.decode()}
    archived = json.loads((EVIDENCE / (part + '-cases.json')).read_text())
    expected_rows = {(row['group'], row['case']): row for row in archived['cases']}
    goldens = json.loads((EVIDENCE.parent / 'c2a-r13/placements.json').read_text())
    measure.replay.prior.OUT = OUT
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    groups, rows, outcomes, workers = {}, [], {}, []
    transitions = defaultdict(Counter)
    with ExitStack() as stack:
        modules = {name: measure.replay.prior.make_module(
            'r24b_' + part + '_' + name, source, stack)
            for name, source in variants.items()}
        generator = measure.replay.prior.make_module(
            'r24b_generator_' + part, subprocess.check_output(
                ['git', 'show', measure.replay.old.BASE + ':' + measure.PRODUCT],
                cwd=ROOT).decode(), stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pdf, people, line, replies, allowed, worker in measure.inputs(part, generator, {}):
            expected = expected_rows[(group, case)]
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            row = dict(group=group, case=case, results={}, wrong={}, raw_wrong={},
                       model_calls={}, input_sha256=hashlib.sha256(pdf).hexdigest())
            states = {}

            def client():
                if group == 'Seven goldens':
                    return Mock(side_effect=measure.replay.old.model_answer)
                if replies == []:
                    return None
                return Mock(side_effect=copy.deepcopy(replies)) if replies is not None else Mock()

            for name, module in modules.items():
                model = client()
                result = measure.replay.old.r14.in_process(module, pdf, people, model)
                # Results include VERSION; shipped narrow must equal the exact
                # archived narrow result, not merely its classified outcome.
                assert result == archived['outcomes'][expected['results'][name]], (part, case, name, 'archive differs')
                digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
                outcomes[digest] = result
                row['results'][name] = digest
                if allowed is not None:
                    oracle = (measure.replay.prior.prior.new.wrong_fields
                              if part in {'historical', 'review'} else measure.added.rc.wrong_fields)
                    raw = bool(oracle(result, allowed))
                elif line:
                    raw = bool(measure.replay.old.r15.wrong_pat_fields(result, line))
                else:
                    raw = measure.replay.old.earlier_wrong(
                        group, case, result, archived['outcomes'][expected['results']['r21']])
                wrong = raw
                if group == 'Competition' and measure.replay.prior.permitted_named_competition(case, result, allowed):
                    wrong = False
                if group == 'Q4 M1 ambiguity':
                    wrong = False
                assert (raw, wrong) == (expected['raw_wrong'][name], expected['wrong'][name])
                row['raw_wrong'][name], row['wrong'][name] = raw, wrong
                state = 'w' if wrong else {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[result['status']]
                states[name] = state
                counts[name + '_' + state] += 1
                counts[name + '_raw_wrong'] += raw
                calls = model.call_count if model is not None else 0
                row['model_calls'][name] = calls
                expected_calls = len(replies) if replies is not None else int(group == 'Seven goldens' and case == 'unusual')
                assert calls == expected_calls
                if group == 'Seven goldens':
                    counts[name + '_golden_diffs'] += measure.replay.old.versionless(result) != measure.replay.old.versionless(goldens[case])
                    counts[name + '_native_diffs'] += any(
                        module.to_native_fields(result, person['email']) != module.to_native_fields(goldens[case], person['email'])
                        for person in people)
                if worker:
                    actual = module.place(pdf, people, model_client=client())
                    assert actual == result, (part, case, name, 'worker differs')
                    workers.append(dict(group=group, case=case, variant=name, result=digest))
            counts['n_to_p'] += states['r21'] == 'n' and states['r24'] in {'c', 'w'}
            counts['c_to_w'] += states['r21'] == 'c' and states['r24'] == 'w'
            counts['n_to_w'] += states['r21'] == 'n' and states['r24'] == 'w'
            counts['c_to_n'] += states['r21'] == 'c' and states['r24'] == 'n'
            transitions[group][' -> '.join(states[name] for name in variants)] += 1
            rows.append(row)
            if len(rows) % 240 == 0:
                print(part, len(rows), flush=True)
        forbidden.assert_not_called()
    assert {(row['group'], row['case']) for row in rows} == set(expected_rows)
    assert len(rows) == len(expected_rows)
    assert PRODUCT.read_bytes() == shipped
    summary = dict(part=part, cases=len(rows), groups=groups, transitions=transitions,
                   source_sha256={n: hashlib.sha256(s.encode()).hexdigest() for n, s in variants.items()},
                   archive_results_exact=True, external_http_calls=forbidden.call_count,
                   worker_evaluations=len(workers))
    write(part + '-summary.json', summary)
    write(part + '-cases.json', dict(cases=rows, outcomes=outcomes))
    write(part + '-workers.json', workers)
    assert all(g['n_to_p'] == g['c_to_w'] == 0 for g in groups.values())
    print(part, 'complete', len(rows), 'cells', len(workers), 'workers', flush=True)


def run(part):
    with (OUT / (part + '-replay.txt')).open('x') as log:
        proc = subprocess.run([sys.executable, __file__, part],
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                              stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
    return part, proc.returncode


if __name__ == '__main__':
    if sys.argv[1] != 'all':
        main(sys.argv[1])
    else:
        results = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = [pool.submit(run, part) for part in (*PARTS, 'h1')]
            for job in as_completed(jobs):
                part, rc = job.result()
                results[part] = rc
                print(part, 'rc=' + str(rc), flush=True)
        write('replay-returncodes.json', results)
        sys.exit(int(any(results.values())))
