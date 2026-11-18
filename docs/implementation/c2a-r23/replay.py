"""Execute unmodified historical generators and oracles against r21, r22 and r23."""
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

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'backend'), str(OUT.parent / 'c2a-r21')]
import check_evidence as prior
import check_layouts as layouts
from dealroom_sign.tests import placement_r22_review_cases as new
from dealroom_sign.tests import placement_r21_review_cases as rc
from dealroom_sign.tests.test_placement_r17 import signers

old = prior.old
prior.OUT = OUT  # Only scratch workers; original source/evidence stays read-only.


def write(name, data):
    path = OUT / (name + '.json')
    assert not path.exists(), path
    path.write_text(json.dumps(data, indent=2) + '\n')


def cases(part, generator, inventory):
    if part == 'historical':
        for group, case, pdf, people, line in old.cases():
            yield group, case, pdf, people, line, None, None, group == 'Seven goldens'
        for group, case, pdf, people, line, replies, _ in prior.prior.prior.prior.prior.control_cases(generator, inventory):
            yield group, case, pdf, people, line, replies, None, False
        generators = [prior.prior.prior.prior.added_cases, prior.prior.prior.affiliate_cases, prior.prior.new_cases]
    elif part == 'review':
        generators = [prior.families.competition, prior.families.l1_cases,
                      prior.families.f_fine, prior.review.realistic_cases]
    else:
        generators = []
    for gen in generators:
        for group, case, rows, both, allowed in gen():
            yield group, case, prior.prior.new.rows_pdf(rows), signers(both), None, None, allowed, group == 'r18 B1 reproduction'
    if part == 'review':
        for both in [False, True]:
            yield 'B1 real worker', str(both), prior.prior.new.rows_pdf(prior.review.WORKER_ROWS), signers(both), None, None, {prior.review.PE: (300, 300, 480), prior.review.DE: (40, 300, 220)}, True
        for case, rows in prior.review.Q4_CASES.items():
            for both in [False, True]:
                yield 'Q4 ' + ('M1 ambiguity' if case.startswith(('dodge hyphen', 'dodge HLA', 'dodge British')) else 'controls'), repr((case, both)), prior.prior.new.rows_pdf(rows), signers(both), None, None, prior.review.ALLOW, False
    if part == 'layouts':
        for group, case, pages, both, allowed, worker in layouts.cases():
            yield group, case, rc.pages_pdf(pages), signers(both), None, None, allowed, worker
    if part == 'wrapped':
        for args, pages, both, allowed in rc.matrix_cases():
            pages = [new.recital_rows(' '.join(r[1] for r in pages[0]), True), *pages[1:]]
            yield 'Wrapped matrix ' + args[0], repr(args), rc.pages_pdf(pages), signers(both), None, None, allowed, False
    if part == 'new':
        for gen, group in [(new.conflict_probes, 'M2 conflict probes'), (new.l1_matrix, 'L1 recital matrix')]:
            for args, pages, both, allowed in gen():
                yield group, repr(args), rc.pages_pdf(pages), signers(both), None, None, allowed, group.startswith('M2')


def main(part):
    assert part in {'historical', 'review', 'layouts', 'wrapped', 'new'}
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    archive_name = {'historical': 'historical', 'review': 'review', 'layouts': 'layouts', 'wrapped': 'reviewer-layouts'}.get(part)
    archived = {}
    if archive_name:
        archive = json.loads((OUT.parent / 'c2a-r21' / ('r21b-final-' + archive_name + '-cases.json')).read_text())
        archived = {(r['group'].replace('Review matrix', 'Wrapped matrix') if part == 'wrapped' else r['group'], r['case']): archive['outcomes'][r['results']['r21']] for r in archive['cases']}
    r22_archive = json.loads((OUT.parent / 'c2a-r22' / (part + '-cases.json')).read_text())
    r22_expected = {(r['group'], r['case']): r22_archive['outcomes'][r['results']['r22']] for r in r22_archive['cases']}
    sources = {'r21': subprocess.check_output(['git', 'show', 'afb9aa6e:' + old.PRODUCT], cwd=ROOT).decode(),
               'r22': subprocess.check_output(['git', 'show', 'e2d7ba11:' + old.PRODUCT], cwd=ROOT).decode(),
               'r23': (ROOT / old.PRODUCT).read_text()}
    for name, source in sources.items():
        path = OUT / (part + '-' + name + '.py.txt')
        assert not path.exists(), path
        path.write_text(source)
    groups, records, outcomes, workers, inventory = {}, [], {}, [], {}
    transitions = defaultdict(Counter)
    golden = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {n: prior.make_module(part + '_' + n, s, stack) for n, s in sources.items()}
        generator = prior.make_module('generator_' + part, subprocess.check_output(['git', 'show', old.BASE + ':' + old.PRODUCT], cwd=ROOT).decode(), stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pdf, people, line, replies, allowed, worker in cases(part, generator, inventory):
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            expected = archived.get((group, case))
            row = {'group': group, 'case': case, 'results': {}, 'wrong': {}, 'raw_wrong': {}, 'model_calls': {}, 'input_sha256': hashlib.sha256(pdf).hexdigest()}
            results = {}

            def client():
                if group == 'Seven goldens':
                    return Mock(side_effect=old.model_answer)
                if replies == []:
                    return None
                return Mock(side_effect=copy.deepcopy(replies)) if replies is not None else Mock()

            for name, module in modules.items():
                model = client()
                result = old.r14.in_process(module, pdf, people, model)
                results[name] = result
                row['results'][name] = remember(result)
                wrong = (bool((rc.wrong_fields if part in {'layouts', 'wrapped', 'new'} else prior.prior.new.wrong_fields)(result, allowed)) if allowed is not None else bool(old.r15.wrong_pat_fields(result, line)) if line else old.earlier_wrong(group, case, result, expected))
                row['raw_wrong'][name] = wrong
                if group == 'Competition' and prior.permitted_named_competition(case, result, allowed):
                    wrong = False
                if group == 'Q4 M1 ambiguity':
                    wrong = False
                row['wrong'][name] = wrong
                calls = model.call_count if model is not None else 0
                row['model_calls'][name] = calls
                counts[name + '_wrong'] += wrong
                counts[name + '_raw_wrong'] += row['raw_wrong'][name]
                counts[name + '_model_calls'] += calls
                counts[name + '_' + {'needs_sender': 'holds', 'placed': 'placed', 'bare': 'bare'}[result['status']]] += 1
                if archive_name and name == 'r21':
                    assert expected is not None, (group, case, 'missing archive')
                    assert old.versionless(result) == old.versionless(expected), (group, case, 'r21 archive mismatch')
                if name == 'r22':
                    assert old.versionless(result) == old.versionless(r22_expected[(group, case)]), (group, case, 'r22 archive mismatch')
                expected_calls = len(replies) if replies is not None else int(group == 'Seven goldens' and case == 'unusual')
                assert calls == expected_calls, (group, case, name, calls, expected_calls)
                if group == 'Seven goldens':
                    counts[name + '_golden_diffs'] += old.versionless(result) != old.versionless(golden[case])
                    for person in people:
                        counts[name + '_native_diffs'] += module.to_native_fields(result, person['email']) != module.to_native_fields(golden[case], person['email'])
                if worker:
                    actual = module.place(pdf, people, model_client=client())
                    assert actual == result, (name, group, case, 'worker mismatch')
                    workers.append({'variant': name, 'group': group, 'case': case, 'result': remember(actual)})
            before = 'wrong' if row['wrong']['r21'] else results['r21']['status']
            after = 'wrong' if row['wrong']['r23'] else results['r23']['status']
            transitions[group][before + ' -> ' + after] += 1
            counts['full_result_diffs'] += old.versionless(results['r21']) != old.versionless(results['r23'])
            records.append(row)
            if len(records) % 250 == 0:
                print(part, len(records), 'r23 wrong', sum(g['r23_wrong'] for g in groups.values()), flush=True)
        forbidden.assert_not_called()
    if archive_name:
        assert {(r['group'], r['case']) for r in records} == set(archived), 'archive case inventory differs'
    assert {(r['group'], r['case']) for r in records} == set(r22_expected)
    summary = {'part': part, 'cases': len(records), 'groups': groups, 'transitions': transitions,
               'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n, s in sources.items()},
               'external_http_calls': forbidden.call_count, 'worker_evaluations': len(workers)}
    write(part + '-summary', summary)
    write(part + '-cases', {'cases': records, 'outcomes': outcomes})
    write(part + '-workers', workers)
    print(json.dumps(summary, indent=2), flush=True)
    assert all(g['r23_wrong'] == 0 for g in groups.values())
    if part == 'historical':
        assert groups['Seven goldens']['r23_golden_diffs'] == groups['Seven goldens']['r23_native_diffs'] == 0
        write('placements', {r['case']: outcomes[r['results']['r23']] for r in records if r['group'] == 'Seven goldens'})


if __name__ == '__main__':
    main(sys.argv[1])
