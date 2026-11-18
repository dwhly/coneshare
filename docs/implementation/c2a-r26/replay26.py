"""Fresh r26 four-source replay; all earlier generators, oracles and evidence are read-only."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
import copy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OLD = OUT.parent / 'c2a-r25'
sys.path[:0] = [str(ROOT / 'backend'), str(OLD)]
sys.path.insert(0, str(OUT.parent / 'c2a-r24'))
import measure
from dealroom_sign.tests import placement_r26_review_cases as exact
import ordinary_ndas
import review_q3b
from dealroom_sign.tests import placement_r25_review_cases as q3

PARTS = ('historical', 'review', 'layouts', 'wrapped', 'new', 'stress', 'q2',
         'extra', 'workers', 'attack', 'boundary', 'h1_review', 'veto',
         'workers24', 'workers_h1_uncaptioned', 'h1', 'q3a', 'q3b', 'workers25',
         'q3b_aligned', 'ordinary_ndas', 'exact_q3a', 'exact_q3b', 'exact_q3c',
         'exhibits', 'three_party', 'workers26')
VERSIONS = ('r21', 'r24', 'r25', 'r26')


def write(folder, name, data):
    with (folder / name).open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')


def inputs(part, generator):
    if part in {'q3b_aligned', 'ordinary_ndas'}:
        yield from (ordinary_ndas if part == 'ordinary_ndas' else review_q3b).inputs(part, generator)
        return
    if part.startswith('exact_') or part in {'exhibits', 'three_party', 'workers26'}:
        if part == 'workers26':
            rows = exact.worker_cases()
        else:
            family = 'cand5_controls' if part == 'three_party' else part.removeprefix('exact_')
            rows = exact.captured(family)
            if part == 'three_party':
                # This additional control family is the middle loop of call 37;
                # its Q3c and H1 loops are covered in full by their own families.
                rows = rows[468:504]
                assert len(rows) == 36
        for index, (args, pages, people, allowed) in enumerate(rows):
            group = (part + ' ' + args['L'] if part == 'exact_q3c' else
                     part + ' ' + args['ex'] if part == 'exhibits' else part)
            yield group, str(index) + ': ' + repr(args), exact.rc.pages_pdf(pages), people, None, None, allowed, part == 'workers26'
        return
    if part not in {'q3a', 'q3b', 'workers25'}:
        yield from measure.inputs(part, generator, {})
        return
    rows = (q3.q3a() if part == 'q3a' else q3.q3b() if part == 'q3b' else
            ((args, *q3.worker_case(*args)) for args in
             __import__('itertools').product(('msa_supplier', 'nda_member', 'nda_caption', 'nda_named'), (False, True))))
    for args, pages, people, allowed in rows:
        group = ('Q3a ' + args[0][0] if part == 'q3a' else
                 'Q3b ordinary' if part == 'q3b' and args[3] == 'none' else
                 'Q3b affiliate' if part == 'q3b' else args[0])
        yield group, repr(args), q3.rc.pages_pdf(pages), people, None, None, allowed, part == 'workers25'


def main(part, folder, source):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    variants = {name: (OUT / (name + '-source.py.txt')).read_text()
                for name in VERSIONS if name != 'r26'}
    variants['r26'] = source.read_text()
    archive_path = OLD / 'final' / (part + '-cases.json')
    archived = json.loads(archive_path.read_text()) if archive_path.exists() else None
    expected_rows = {(r['group'], r['case']): r for r in archived['cases']} if archived else {}
    golden = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    measure.replay.prior.OUT = folder
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    groups, rows, outcomes, workers = {}, [], {}, []
    transitions = defaultdict(Counter)
    with ExitStack() as stack:
        modules = {name: measure.replay.prior.make_module('r26_' + part + '_' + name, text, stack)
                   for name, text in variants.items()}
        # r24/cand4/r25 have identical extractors. Deep-copy a pristine parse;
        # each scorer runs independently. Real workers always reparse the PDF.
        parses = {name: lru_cache(maxsize=1)(modules[name].extract) for name in ('r21', 'r24')}
        for name, module in modules.items():
            fn = parses['r21' if name == 'r21' else 'r24']
            stack.enter_context(patch.object(module, 'extract',
                                lambda pdf, deadline=None, fn=fn: copy.deepcopy(fn(pdf))))
        generator = measure.replay.prior.make_module('generator_' + part, subprocess.check_output(
            ['git', 'show', measure.replay.old.BASE + ':' + measure.PRODUCT], cwd=ROOT).decode(), stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pdf, people, line, replies, allowed, worker in inputs(part, generator):
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            expected = expected_rows.get((group, case))
            row = dict(group=group, case=case, results={}, wrong={}, raw_wrong={}, model_calls={},
                       input_sha256=hashlib.sha256(pdf).hexdigest())
            states, results = {}, {}

            def client():
                if group == 'Seven goldens':
                    return Mock(side_effect=measure.replay.old.model_answer)
                if replies == []:
                    return None
                return Mock(side_effect=copy.deepcopy(replies)) if replies is not None else Mock()

            for name, module in modules.items():
                model = client()
                result = measure.replay.old.r14.in_process(module, pdf, people, model)
                results[name] = result
                if expected and name in {'r21', 'r24', 'r25'}:
                    assert result == archived['outcomes'][expected['results'][name]], (part, case, name, 'archive differs')
                digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
                outcomes[digest] = result
                row['results'][name] = digest
                if allowed is not None:
                    oracle = measure.replay.prior.prior.new.wrong_fields if part in {'historical', 'review'} else q3.rc.wrong_fields
                    raw = bool(oracle(result, allowed))
                elif line:
                    raw = bool(measure.replay.old.r15.wrong_pat_fields(result, line))
                else:
                    raw = measure.replay.old.earlier_wrong(group, case, result,
                        archived['outcomes'][expected['results']['r21']] if expected else None)
                wrong = raw
                if group == 'Competition' and measure.replay.prior.permitted_named_competition(case, result, allowed):
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
                if group == 'Seven goldens':
                    counts[name + '_golden_diffs'] += measure.replay.old.versionless(result) != measure.replay.old.versionless(golden[case])
                    counts[name + '_native_diffs'] += any(module.to_native_fields(result, p['email']) != module.to_native_fields(golden[case], p['email']) for p in people)
                if worker:
                    actual = module.place(pdf, people, model_client=client())
                    assert actual == result, (part, case, name, 'worker differs')
                    workers.append(dict(group=group, case=case, variant=name, result=digest))
            for before in ('r21', 'r24', 'r25'):
                for name in ('r26',):
                    prefix = before + '_to_' + name + '_'
                    counts[prefix + 'n_to_p'] += states[before] == 'n' and states[name] in {'c', 'w'}
                    counts[prefix + 'c_to_w'] += states[before] == 'c' and states[name] == 'w'
                    counts[prefix + 'c_to_n'] += states[before] == 'c' and states[name] == 'n'
                    counts[prefix + 'w_to_n'] += states[before] == 'w' and states[name] == 'n'
            if row['raw_wrong']['r26']:
                counts['r26_remaining_flag_differs_r21'] += (not row['raw_wrong']['r21'] or
                    measure.replay.old.versionless(results['r26']) != measure.replay.old.versionless(results['r21']))
            transitions[group][' -> '.join(states[n] for n in VERSIONS)] += 1
            rows.append(row)
            if len(rows) % 240 == 0:
                print(part, len(rows), 'r26 raw', sum(g['r26_raw_wrong'] for g in groups.values()), flush=True)
        forbidden.assert_not_called()
    if archived:
        assert {(r['group'], r['case']) for r in rows} == set(expected_rows)
    summary = dict(part=part, cases=len(rows), groups=groups, transitions=transitions,
                   source_sha256={n: hashlib.sha256(s.encode()).hexdigest() for n, s in variants.items()},
                   archive_results_exact=bool(archived), external_http_calls=forbidden.call_count,
                   worker_evaluations=len(workers))
    write(folder, part + '-summary.json', summary)
    write(folder, part + '-cases.json', dict(cases=rows, outcomes=outcomes))
    write(folder, part + '-workers.json', workers)
    assert all(g[b + '_to_r26_n_to_p'] == g[b + '_to_r26_c_to_w'] == 0
               for b in ('r21', 'r24', 'r25') for g in groups.values())
    print(part, 'complete', len(rows), flush=True)


def run(part, folder, source):
    with (folder / (part + '-replay.txt')).open('x') as log:
        proc = subprocess.run([sys.executable, __file__, part, str(folder), str(source)],
                              stdout=log, stderr=subprocess.STDOUT, cwd=ROOT,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return part, proc.returncode


if __name__ == '__main__':
    part, folder, source = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    folder.mkdir(exist_ok=True)
    if part == 'all':
        results = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            for job in as_completed([pool.submit(run, p, folder, source) for p in PARTS]):
                p, rc = job.result()
                results[p] = rc
                print(p, 'rc=' + str(rc), flush=True)
        write(folder, 'returncodes.json', results)
        sys.exit(int(any(results.values())))
    else:
        main(part, folder, source)
