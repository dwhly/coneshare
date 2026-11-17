"""Read-only historical replay, with isolated candidate workers and HTTP disabled."""
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
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
spec = importlib.util.spec_from_file_location('r18_evidence', OUT.parent / 'c2a-r18/check_evidence.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
old = prior.old
from dealroom_sign.tests import test_placement_r19 as new


def write(name, data):
    (OUT / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')


def make_module(name, source, stack):
    module = ModuleType('r19_counterfactual_' + name)
    module.__file__ = str(ROOT / old.PRODUCT)
    sys.modules[module.__name__] = module
    exec(compile(source, module.__name__, 'exec'), module.__dict__)
    worker_root = Path(stack.enter_context(TemporaryDirectory(prefix='worker-' + name + '-', dir=OUT)))
    package = worker_root / 'dealroom_sign'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'placement.py').write_text(source)
    (package / 'placement_worker.py').write_bytes((ROOT / 'backend/dealroom_sign/placement_worker.py').read_bytes())
    module.WORKER_CWD = worker_root
    return module


def sources():
    baseline = subprocess.check_output(['git', 'show', '9ebf85a0:' + old.PRODUCT], cwd=ROOT).decode()
    before = 'if other is block or not heading_crosses_gutter(other, blocks):'
    assert baseline.count(before) == 1
    candidate = baseline.replace(before, 'if other is block:')
    narrow_before = "                other_heading = roles.get(other.heading.rstrip(': ').lower(), other.heading)"
    narrow_after = """                if not heading_crosses_gutter(other, blocks):
                    other_printed, other_ambiguous = printed_name_evidence(other, blocks)
                    if (score(signer, other, roles) != 0 or other_ambiguous
                            or any(name != person for person in other_printed)
                            or any(unresolved_person(part, roles)
                                   for label in other.raw_labels
                                   for part in identity_parts(label['text']))):
                        continue
                other_heading = roles.get(other.heading.rstrip(': ').lower(), other.heading)"""
    assert candidate.count(narrow_before) == 1
    return {'r18': baseline, 'candidate': candidate,
            'narrower': candidate.replace(narrow_before, narrow_after),
            'chosen': (ROOT / old.PRODUCT).read_text()}


def new_cases():
    for args in new.VETO_MATRIX:
        extra, affiliate, x, both = args
        rows, allowed = new.veto_rows(extra, affiliate, x)
        yield 'Veto matrix', repr(args), rows, both, allowed


def main():
    sys.dont_write_bytecode = True
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    preflight = '--preflight' in sys.argv
    stem = 'preflight' if preflight else 'counterfactual'
    archive = json.loads((OUT.parent / 'c2a-r18/counterfactual-cases.json').read_text())
    accepted = {(r['group'], r['case']): archive['outcomes'][r['results']['l1']] for r in archive['cases']}
    published = json.loads((OUT.parent / 'c2a-r18/counterfactual-summary.json').read_text())
    goldens = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    groups, records, outcomes, workers, inventory = {}, [], {}, [], {}
    transitions = defaultdict(lambda: defaultdict(Counter))
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    variants = sources()
    for name, source in variants.items():
        (OUT / (stem + '-' + name + '.py.txt')).write_text(source)

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {name: make_module(name, source, stack) for name, source in variants.items()}
        generator_source = subprocess.check_output(['git', 'show', old.BASE + ':' + old.PRODUCT], cwd=ROOT).decode()
        generator = make_module('generator_r14', generator_source, stack)
        stack.enter_context(patch('httpx.Client.send', forbidden))

        def cases():
            if not preflight:
                for group, case, pdf, signers, line in old.cases():
                    yield group, case, pdf, signers, line, None, accepted[group, case], None
                for group, case, pdf, signers, line, replies, _ in prior.prior.prior.control_cases(generator, inventory):
                    yield group, case, pdf, signers, line, replies, accepted[group, case], None
                for group, case, rows, both, allowed in prior.prior.added_cases():
                    yield group, case, new.rows_pdf(rows), new.signers(both), None, None, accepted[group, case], allowed
            for group, case, rows, both, allowed in prior.affiliate_cases():
                yield group, case, new.rows_pdf(rows), new.signers(both), None, None, accepted[group, case], allowed
            for group, case, rows, both, allowed in new_cases():
                yield group, case, new.rows_pdf(rows), new.signers(both), None, None, None, allowed

        for group, case, pdf, signers, line, replies, expected, allowed in cases():
            row = {'group': group, 'case': case, 'results': {}, 'model_calls': {}, 'wrong': {}}
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            results = {}

            def model_client():
                if group == 'Seven goldens':
                    return Mock(side_effect=old.model_answer)
                if replies == []:
                    return None
                return Mock(side_effect=copy.deepcopy(replies)) if replies is not None else Mock()

            for name, module in modules.items():
                model = model_client()
                result = old.r14.in_process(module, pdf, signers, model)
                results[name] = result
                row['results'][name] = remember(result)
                calls = model.call_count if model is not None else 0
                row['model_calls'][name] = calls
                wrong = (bool(new.wrong_fields(result, allowed)) if allowed is not None else
                         bool(old.r15.wrong_pat_fields(result, line)) if line else
                         old.earlier_wrong(group, case, result, expected))
                row['wrong'][name] = wrong
                counts[name + '_wrong'] += wrong
                for status in ['placed', 'needs_sender', 'bare']:
                    counts[name + '_' + ('holds' if status == 'needs_sender' else status)] += result['status'] == status
                counts[name + '_model_calls'] += calls
                if group == 'Seven goldens':
                    counts[name + '_golden_diffs'] += old.versionless(result) != old.versionless(goldens[case])
                    for signer in signers:
                        counts[name + '_native_diffs'] += module.to_native_fields(result, signer['email']) != module.to_native_fields(goldens[case], signer['email'])
            if expected is not None:
                assert old.versionless(results['r18']) == old.versionless(expected), (group, case, 'r18 replay')
            expected_calls = len(replies) if replies is not None else int(group == 'Seven goldens' and case == 'unusual')
            assert row['model_calls']['r18'] == expected_calls, (group, case, 'r18 model calls')
            for name in ['candidate', 'narrower', 'chosen']:
                counts[name + '_full_diffs'] += old.versionless(results[name]) != old.versionless(results['r18'])
                before = 'wrong' if row['wrong']['r18'] else results['r18']['status']
                after = 'wrong' if row['wrong'][name] else results[name]['status']
                transitions[group][name][before + ' -> ' + after] += 1
            records.append(row)
            if group in {'Seven goldens', 'r18 B1 reproduction'}:
                for name, module in modules.items():
                    model = model_client()
                    actual = module.place(pdf, signers, model_client=model)
                    assert actual == results[name], (name, group, case, 'worker')
                    workers.append({'variant': name, 'group': group, 'case': case, 'result': remember(actual)})
            if len(records) % 500 == 0:
                print(f'{len(records)} cases compared', flush=True)
    forbidden.assert_not_called()
    for group, counts in groups.items():
        if group in published['groups']:
            for key in ['wrong', 'placed', 'holds', 'bare']:
                assert counts['r18_' + key] == published['groups'][group]['l1_' + key], (group, key)
    summary = {'base': '9ebf85a0', 'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n,s in variants.items()},
               'cases': len(records), 'groups': groups, 'external_http_calls': forbidden.call_count,
               'transitions': transitions, 'worker_evaluations': len(workers)}
    write(stem + '-cases', {'cases': records, 'outcomes': outcomes})
    write(stem + '-summary', summary)
    write(stem + '-workers', workers)
    print(json.dumps({'cases': len(records), 'groups': len(groups), 'wrong': {n:sum(g[n+'_wrong'] for g in groups.values()) for n in variants}}, indent=2), flush=True)


if __name__ == '__main__':
    main()
