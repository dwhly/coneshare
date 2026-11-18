"""Execute the immutable r19 page-scope assertion on every measured candidate."""
from collections import Counter
from contextlib import ExitStack
from itertools import product
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock, patch

from candidate_sources import sources

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'backend'), str(OUT.parent / 'c2a-r23')]
import replay
from dealroom_sign.tests import test_placement_r19 as original

replay.prior.OUT = OUT


def main():
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    test = original.test_company_competition_uses_identity_before_vetoes
    axes = [(mark.args[0].split(','), mark.args[1]) for mark in test.pytestmark
            if mark.name == 'parametrize']
    counts, results = {}, []
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    with ExitStack() as stack:
        modules = {v: replay.prior.make_module('page_assert_' + v, s, stack)
                   for v,s in sources().items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for values in product(*(values for _,values in axes)):
            kwargs = {}
            for (names, _), value in zip(axes, values):
                kwargs.update(zip(names, value if len(names) > 1 else (value,)))
            row = dict(args=kwargs, outcomes={})
            for version,module in modules.items():
                with patch.object(original, 'placement', module):
                    try:
                        test(**kwargs)
                    except AssertionError:
                        outcome = 'failed'
                    else:
                        outcome = 'passed'
                counts.setdefault(version, Counter())[outcome] += 1
                row['outcomes'][version] = outcome
            results.append(row)
        forbidden.assert_not_called()
    assert counts['cand3'] == {'passed': 20, 'failed': 20}
    assert all(counts[v] == {'passed': 40} for v in ('r21', 'r23', 'cand', 'r24'))
    output = dict(test='test_placement_r19.py::test_company_competition_uses_identity_before_vetoes',
                  assertion='score == (0 if same_page else 4)',
                  counts=counts, cases=results, external_http_calls=0,
                  note='Original r24 key is the narrow candidate. Final fallback is cand3. No test code or input was changed.')
    target = OUT / 'fallback-test-conflict.json'
    assert not target.exists()
    target.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
