"""Measure narrow same-page arms against immutable Q3c and live L-2 inputs."""
from collections import Counter
from contextlib import ExitStack
import copy
from itertools import product
from pathlib import Path
import sys
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent))
import replay26 as replay
from dealroom_sign.tests.test_placement import TWO
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r8 import CAPTIONS
from dealroom_sign.tests.test_placement_r12 import HEADINGS
from dealroom_sign.tests.test_placement_r13 import own_company_pdf

OLD = """        same = [b for b in blocks if b is not block
                and b.line.page == block.line.page and not witness_block(b)]
        block.unclaimed_cross_page = bool(unclaimed_pages - {block.line.page}) or (
            len(same) >= 2 and any(not any(b.scores) for b in same))"""
# A matching printed identity may remain vetoed; it is not an independent
# third party. Mixed printed identities must still count.
NAME_COUNT = """        names = [tokens(signer.get('name', ''))
                 for signer, value in zip(signers, block.scores) if value == 4]
        same = []
        for other in blocks:
            if other is block or other.line.page != block.line.page or witness_block(other):
                continue
            printed = printed_names(other, blocks)
            if printed and all(name in names for name in printed):
                continue
            same.append(other)
        block.unclaimed_cross_page = bool(unclaimed_pages - {block.line.page}) or (
            len(same) >= 2 and any(not any(b.scores) for b in same))"""
RECITAL = """        heading = roles.get(block.heading.rstrip(': ').lower(), block.heading)
        heading = (behalf_parts(heading) or ('', heading))[1]
        own_company = any(tokens(heading) == tokens(company) for company in roles.values())
        same = [b for b in blocks if b is not block
                and b.line.page == block.line.page and not witness_block(b)]
        block.unclaimed_cross_page = bool(unclaimed_pages - {block.line.page}) or (
            not own_company and len(same) >= 2 and any(not any(b.scores) for b in same))"""


def cases():
    for args, pages, people, allowed in replay.exact.captured('q3c'):
        if args['L'] == 'same_page3':
            yield 'Q3c same page', repr(args), replay.exact.rc.pages_pdf(pages), people, allowed
    for args, pages, people, allowed in replay.exact.captured('cand5_controls')[468:504]:
        yield 'Three-party controls', repr(args), replay.exact.rc.pages_pdf(pages), people, allowed
    for group, case, pages, both, allowed, _ in replay.measure.stress.cases():
        if group == 'Recitals misspelled_M1':
            yield group, case, replay.exact.rc.pages_pdf(pages), replay.measure.replay.signers(both), allowed
    for heading, caption in product(HEADINGS, CAPTIONS):
        yield 'L-2', repr((heading, caption)), own_company_pdf(caption, heading), PAT, {
            PAT[0]['email']: (1, 72, 560, 290)}


def main():
    base = (OUT.parent / 'r26-source.py.txt').read_text()
    assert base.count(OLD) == 1
    sources = dict(r25=(OUT.parent / 'r25-source.py.txt').read_text(), cand5=base,
                   recital=base.replace(OLD, RECITAL), name_count=base.replace(OLD, NAME_COUNT))
    for name in ('recital', 'name_count'):
        path = OUT / (name + '-source.py.txt')
        if path.exists():
            assert path.read_text() == sources[name]
        else:
            path.write_text(sources[name])
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    groups, rows = {}, []
    replay.measure.replay.prior.OUT = OUT
    with ExitStack() as stack:
        modules = {n: replay.measure.replay.prior.make_module('r26b_pilot_' + n, s, stack)
                   for n, s in sources.items()}
        original = modules['r25'].extract
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pdf, people, allowed in cases():
            extracted = original(pdf)
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            row = dict(group=group, case=case, results={}, states={})
            for name, module in modules.items():
                model = Mock()
                with patch.object(module, 'extract', lambda pdf, deadline=None: copy.deepcopy(extracted)):
                    result = replay.measure.replay.old.r14.in_process(module, pdf, people, model)
                assert result['reason_code'] not in {'worker_error', 'parse_error'}, result
                model.assert_not_called()
                wrong = replay.exact.rc.wrong_fields(result, allowed)
                state = 'w' if wrong else 'c' if result['status'] == 'placed' else 'n'
                counts[name + '_' + state] += 1
                row['results'][name], row['states'][name] = result, state
            for name in ('recital', 'name_count'):
                counts[name + '_r25_n_to_p'] += row['states']['r25'] == 'n' and row['states'][name] != 'n'
                counts[name + '_cand5_hold_recovery'] += row['states']['cand5'] == 'n' and row['states'][name] == 'c'
            rows.append(row)
    forbidden.assert_not_called()
    assert groups['L-2']['r25_c'] == 20
    assert groups['Q3c same page']['r25_w'] == 55
    replay.write(OUT, 'candidate-measurement-v2.json', dict(groups=groups, rows=rows,
                 external_http_calls=0, model_calls=0))
    print(dict(groups), flush=True)


if __name__ == '__main__':
    main()
