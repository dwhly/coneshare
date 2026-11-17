"""Review layout matrix, cross-page subset, role words, and exact worker cases."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import ast
import hashlib
from itertools import product
import json
import os
import subprocess
from unittest.mock import Mock, patch

from check_evidence import OUT, ROOT, make_module, old, write
from variants import variants
from dealroom_sign.tests.placement_r21_review_cases import (
    ROLE_WORDS, cross_page_cases, layout_pages, matrix_cases, pages_pdf, wrong_fields,
)
from dealroom_sign.tests.test_placement_r17 import signers


def cases():
    for args, pages, both, allowed in matrix_cases():
        yield 'Review matrix ' + args[0], repr(args), pages, both, allowed, False
    for args, pages, both, allowed in cross_page_cases():
        yield 'Cross-page regression ' + args[0], repr(args), pages, both, allowed, False
    for layout, both, extra in product(('same', 'guarantor', 'split'), (False, True),
                                      ('placeholders', 'printed')):
        pages, allowed = layout_pages(layout, extra=extra)
        yield 'B2 exact worker', repr((layout, both, extra)), pages, both, allowed, True
    for word, plural, leading in product(ROLE_WORDS, (False, True), ('', 'THE ')):
        if plural:
            word = word[:-1] + 'ies' if word.endswith('y') else word + 's'
        heading = leading + word.upper()
        pages, allowed = layout_pages(heading=heading)
        yield 'B2 role vocabulary', repr((heading,)), pages, False, allowed, False
    # Measure the widened grammar separately on the same layouts, including
    # the review's hereinafter wording. Each field still has the same oracle.
    for layout, recital, heading, affiliate, both in product(
            ('same', 'guarantor', 'split', 'witness'), ('address', 'hereinafter'),
            ('RECIPIENT:', 'THE RECIPIENT', None), ('group', 'none'), (False, True)):
        pages, allowed = layout_pages(layout, recital, heading, 'placeholders', affiliate)
        yield 'ROLE_DEF layouts', repr((layout, recital, heading, affiliate, both)), pages, both, allowed, False


def main():
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    baseline = subprocess.check_output(['git', 'show', 'e0ed35e7:' + old.PRODUCT], cwd=ROOT).decode()
    sources = variants(baseline)
    groups, records, outcomes, workers = {}, [], {}, []
    transitions = defaultdict(lambda: defaultdict(Counter))
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))

    def remember(result):
        digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        outcomes[digest] = result
        return digest

    with ExitStack() as stack:
        modules = {n: make_module(n, s, stack) for n, s in sources.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pages, both, allowed, worker in cases():
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            row = {'group': group, 'case': case, 'results': {}, 'wrong': {}, 'model_calls': {}}
            previous = None
            pdf = pages_pdf(pages)
            for name, module in modules.items():
                model = Mock()
                result = old.r14.in_process(module, pdf, signers(both), model)
                wrong = bool(wrong_fields(result, allowed))
                row['results'][name] = remember(result)
                row['wrong'][name] = wrong
                row['model_calls'][name] = model.call_count
                counts[name + '_wrong'] += wrong
                counts[name + '_' + {'placed': 'placed', 'needs_sender': 'holds', 'bare': 'bare'}[result['status']]] += 1
                counts[name + '_model_calls'] += model.call_count
                assert model.call_count == 0
                state = 'wrong' if wrong else result['status']
                if previous:
                    transitions[group][name][previous + ' -> ' + state] += 1
                previous = state
                if worker:
                    actual = module.place(pdf, signers(both), model_client=model)
                    assert actual == result, (name, group, case, 'worker mismatch')
                    workers.append({'variant': name, 'case': case, 'result': remember(actual)})
                model.assert_not_called()
            records.append(row)
            if len(records) % 250 == 0:
                print(len(records), 'cases; r21 wrong', sum(g['r21_wrong'] for g in groups.values()), flush=True)
    forbidden.assert_not_called()
    # The 1,800 cross-page cases are the two cross-page matrix layouts,
    # excluding the named heading and no-affiliate controls, as in the review.
    cross = Counter()
    for row in records:
        if row['group'] not in {'Review matrix guarantor', 'Review matrix split'}:
            continue
        args = ast.literal_eval(row['case'])
        if args[2] == 'HARBOR LIGHT ANALYTICS, INC.' or args[4] == 'none':
            continue
        cross['cases'] += 1
        for name in modules:
            cross[name + '_wrong'] += row['wrong'][name]
            result = outcomes[row['results'][name]]
            cross[name + '_' + {'placed': 'placed', 'needs_sender': 'holds', 'bare': 'bare'}[result['status']]] += 1
    assert cross['cases'] == 1800
    summary = {'cases': len(records), 'groups': groups, 'cross_page_1800_subset': cross,
               'transitions': transitions, 'external_http_calls': forbidden.call_count,
               'worker_evaluations': len(workers),
               'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n, s in sources.items()}}
    write('layouts-summary', summary)
    write('layouts-cases', {'cases': records, 'outcomes': outcomes})
    write('layouts-workers', workers)
    print(json.dumps(summary, indent=2), flush=True)
    assert all(g['r21_wrong'] == 0 for g in groups.values())


if __name__ == '__main__':
    main()
