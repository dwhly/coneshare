"""Replay the untouched r17 families and affiliate matrix without external HTTP."""
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


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent / 'c2a-r17'))
spec = importlib.util.spec_from_file_location('r17_evidence', OUT.parent / 'c2a-r17/check_evidence.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
old = prior.old
old.OUT = OUT
from dealroom_sign.tests import test_placement_r18 as new  # noqa: E402


def write(name, value):
    (OUT / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')


def l1_candidate(source):
    start = source.index('def heading_crosses_gutter(')
    end = source.index('\ndef company_text(', start)
    function = source[start:end]
    for before, after in [
        ("row['rect'][2] > block.line.x1", "row['rect'][2] > other_left"),
        ("row['rect'][0] < left", "row['rect'][0] < other.line.x1"),
    ]:
        assert function.count(before) == 1
        function = function.replace(before, after)
    return source[:start] + function + source[end:]


def affiliate_cases():
    for args in new.AFFILIATE_MATRIX:
        affiliate, width, gap, x, heading, both, fleet = args
        rows, allowed = new.affiliate_rows(affiliate, width, gap, x, heading, fleet)
        yield 'Affiliate matrix', repr(args), rows, both, allowed
    for both in [False, True]:
        rows, allowed = new.affiliate_rows()
        yield 'r18 B1 reproduction', str(both), rows, both, allowed


def main():
    sys.dont_write_bytecode = True
    preflight = '--preflight' in sys.argv
    stem = 'l1-preflight' if preflight else 'counterfactual'
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    base = subprocess.check_output(['git', 'show', '1084b075:' + old.PRODUCT], cwd=ROOT).decode()
    b1_path = OUT / 'b1-placement.py.txt'
    b1 = b1_path.read_text() if b1_path.exists() else (ROOT / old.PRODUCT).read_text()
    sources = {'r17': base, 'b1': b1, 'l1': l1_candidate(b1)}
    assert "VERSION = 'c2a.18'" in b1
    for name, source in sources.items():
        path = OUT / (name + '-placement.py.txt')
        if path.exists():
            assert path.read_text() == source
        else:
            path.write_text(source)
    archived = json.loads((OUT.parent / 'c2a-r17/counterfactual-cases.json').read_text())
    accepted = {(r['group'], r['case']): archived['outcomes'][r['results']['r17']] for r in archived['cases']}
    published = json.loads((OUT.parent / 'c2a-r17/counterfactual-summary.json').read_text())
    goldens = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    groups, records, outcomes, workers, inventory = {}, [], {}, [], {}
    transitions = defaultdict(lambda: defaultdict(Counter))
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {name: old.make_module(name, source, stack) for name, source in sources.items()}
        r14_source = subprocess.check_output(['git', 'show', old.BASE + ':' + old.PRODUCT], cwd=ROOT).decode()
        generator = old.make_module('generator_r14', r14_source, stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))

        def cases():
            if not preflight:
                for group, case, pdf, signers, line in old.cases():
                    yield group, case, pdf, signers, line, None, accepted[group, case], None
                for group, case, pdf, signers, line, replies, _ in prior.prior.control_cases(generator, inventory):
                    yield group, case, pdf, signers, line, replies, accepted[group, case], None
            for group, case, rows, both, allowed in prior.added_cases():
                if preflight and not group.startswith('F '):
                    continue
                yield group, case, new.rows_pdf(rows), new.signers(both), None, None, accepted[group, case], allowed
            if not preflight:
                for group, case, rows, both, allowed in affiliate_cases():
                    yield group, case, new.rows_pdf(rows), new.signers(both), None, None, None, allowed

        for group, case, pdf, signers, line, replies, expected, allowed in cases():
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
                calls = model.call_count if model is not None else 0
                row['model_calls'][name] = calls
                if allowed is not None:
                    wrong = bool(new.wrong_fields(result, allowed))
                else:
                    wrong = (bool(old.r15.wrong_pat_fields(result, line)) if line else
                             old.earlier_wrong(group, case, result, expected))
                row['wrong'][name] = wrong
                count[name + '_wrong'] += wrong
                for status in ['placed', 'needs_sender', 'bare']:
                    count[name + '_' + ('holds' if status == 'needs_sender' else status)] += result['status'] == status
                count[name + '_model_calls'] += calls
                if group == 'Seven goldens':
                    count[name + '_golden_diffs'] += old.versionless(result) != old.versionless(goldens[case])
                    for signer in signers:
                        count[name + '_native_diffs'] += module.to_native_fields(result, signer['email']) != module.to_native_fields(goldens[case], signer['email'])
            if expected is not None:
                assert old.versionless(results['r17']) == old.versionless(expected), (group, case, 'r17 replay')
            expected_calls = len(replies) if replies is not None else int(group == 'Seven goldens' and case == 'unusual')
            assert row['model_calls']['r17'] == expected_calls, (group, case, 'r17 model calls')
            for name in ['b1', 'l1']:
                count[name + '_full_diffs'] += old.versionless(results[name]) != old.versionless(results['r17'])
                before = 'wrong' if row['wrong']['r17'] else results['r17']['status']
                after = 'wrong' if row['wrong'][name] else results[name]['status']
                transitions[group][name][before + ' -> ' + after] += 1
            records.append(row)
            if not preflight and group in {
                'Seven goldens', 'r14 reproduction', 'r14 correct controls',
                'r15 M1 reproduction', 'r15 M2 reproduction', 'B1 reproduction',
                'B2 reproduction', 'r18 B1 reproduction',
            }:
                for name, module in modules.items():
                    model = new_model()
                    actual = module.place(pdf, signers, model_client=model)
                    assert actual == results[name], (name, group, case, 'worker')
                    calls = model.call_count if model is not None else 0
                    assert calls == row['model_calls'][name]
                    workers.append({'candidate': name, 'group': group, 'case': case,
                                    'result': remember(actual), 'model_calls': calls})
            if len(records) % 500 == 0:
                print(f'{len(records)} cases compared', flush=True)

    forbidden.assert_not_called()
    for group, counts in groups.items():
        if group in published['groups']:
            for key in ['wrong', 'placed', 'holds', 'bare']:
                assert counts['r17_' + key] == published['groups'][group]['r17_' + key], (group, key)
    bars = {'b1_zero_wrong_every_family': all(g['b1_wrong'] == 0 for g in groups.values()),
            'l1_zero_wrong_every_family': all(g['l1_wrong'] == 0 for g in groups.values()),
            'r17_replay_exact': True}
    if not preflight:
        assert set(published['groups']).issubset(groups)
        assert groups['Affiliate matrix']['r17_wrong'] == 320
        assert groups['Affiliate matrix']['r17_placed'] == 416
        assert groups['Affiliate matrix']['b1_placed'] == 96
        bars['b1_preserves_every_r17_full_result'] = all(groups[g]['b1_full_diffs'] == 0 for g in published['groups'])
        for name in ['b1', 'l1']:
            bars[name + '_goldens_exact'] = groups['Seven goldens'][name + '_golden_diffs'] == 0
            bars[name + '_native_fields_exact'] = groups['Seven goldens'][name + '_native_diffs'] == 0
    summary = {'base': '1084b075', 'source_sha256': {name: hashlib.sha256(s.encode()).hexdigest() for name, s in sources.items()},
               'cases': len(records), 'groups': groups, 'bars': bars,
               'external_http_calls': forbidden.call_count, 'transitions': transitions,
               'worker_evaluations': len(workers)}
    write(stem + '-cases', {'cases': records, 'outcomes': outcomes})
    write(stem + '-summary', summary)
    write(stem + '-workers', workers)
    print(json.dumps({'cases': len(records), 'bars': bars, 'http_calls': forbidden.call_count}, indent=2), flush=True)
    assert bars['b1_zero_wrong_every_family'], bars
    if not preflight:
        assert bars['b1_preserves_every_r17_full_result'], bars


if __name__ == '__main__':
    main()
