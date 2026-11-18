"""Reproduce the exact cand5 / immutable r13 positive-control conflict."""
from collections import Counter
from contextlib import ExitStack
from itertools import product
import os
from unittest.mock import Mock, patch

import replay26 as replay
from dealroom_sign.tests.test_placement import TWO
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r8 import CAPTIONS
from dealroom_sign.tests.test_placement_r12 import HEADINGS
from dealroom_sign.tests.test_placement_r13 import own_company_pdf


def main():
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    rows, counts = [], Counter()
    replay.measure.replay.prior.OUT = replay.OUT
    with ExitStack() as stack:
        modules = {name: replay.measure.replay.prior.make_module(
            'suite_conflict_' + name, (replay.OUT / (name + '-source.py.txt')).read_text(), stack)
            for name in ('r21', 'r24', 'r25', 'r26')}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for both, heading, caption in product((False, True), HEADINGS, CAPTIONS):
            pdf = own_company_pdf(caption, heading)
            people = [TWO[1], *PAT] if both else PAT
            row = dict(both_signers=both, heading=heading, caption=caption, versions={})
            for name, module in modules.items():
                blocks, _, roles = module.extract(pdf)
                raw = [dict(id=b.id, page=b.line.page, y=b.line.y, heading=b.heading,
                            witness=module.witness_block(b),
                            uncertain=b.uncertain_identity,
                            printed=module.printed_names(b, blocks)) for b in blocks]
                module.prepare_blocks(blocks, roles, people)
                for data, block in zip(raw, blocks):
                    data.update(scores=block.scores,
                                unclaimed_guard=getattr(block, 'unclaimed_cross_page', None))
                model = Mock()
                result = replay.measure.replay.old.r14.in_process(module, pdf, people, model)
                worker = module.place(pdf, people, model_client=model)
                assert worker == result
                model.assert_not_called()
                counts[name + '_' + result['status']] += 1
                row['versions'][name] = dict(blocks=raw, result=result, worker_exact=True, model_calls=0)
            if not both:
                assert all(row['versions'][v]['result']['status'] == 'placed' for v in ('r21', 'r24', 'r25'))
                assert row['versions']['r26']['result']['status'] == 'needs_sender'
                assert [b['scores'] for b in row['versions']['r26']['blocks']] == [[0], [0], [4]]
                assert all(not b['witness'] for b in row['versions']['r26']['blocks'])
                counts['immutable_test_conflicts'] += 1
            rows.append(row)
        forbidden.assert_not_called()
    assert counts['immutable_test_conflicts'] == 20
    replay.write(replay.OUT, 'suite-conflict.json', dict(cases=len(rows), counts=counts,
                 rows=rows, external_http_calls=0, model_calls=0, worker_evaluations=4 * len(rows)))
    print(dict(counts))


if __name__ == '__main__':
    main()
