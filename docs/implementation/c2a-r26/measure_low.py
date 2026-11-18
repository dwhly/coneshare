"""Measure the proposed explicit-company exemption without shipping it."""
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
import os
from unittest.mock import Mock, patch

import replay26 as replay

OUT = replay.OUT


def main():
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    source = (OUT / 'r26-source.py.txt').read_text()
    old = 'if any(blocks[j].unclaimed_cross_page and scores[i][j] == 4\n'
    new = ('if any(blocks[j].unclaimed_cross_page and scores[i][j] == 4\n'
           "               and not signers[i].get('company')\n")
    assert source.count(old) == 1
    candidate = source.replace(old, new)
    with (OUT / 'low-exemption-source.py.txt').open('x') as stream:
        stream.write(candidate)
    variants = {'r25': (OUT / 'r25-source.py.txt').read_text(),
                'r26': source, 'explicit_exemption': candidate}
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    groups, rows = {}, []
    replay.measure.replay.prior.OUT = OUT
    with ExitStack() as stack:
        modules = {name: replay.measure.replay.prior.make_module('low_' + name, text, stack)
                   for name, text in variants.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for axes, pages, people, allowed in replay.exact.captured('exhibits'):
            counts = groups.setdefault(axes['ex'], Counter())
            counts['cases'] += 1
            row = dict(axes=axes, results={}, states={})
            pdf = replay.exact.rc.pages_pdf(pages)
            for name, module in modules.items():
                model = Mock()
                result = replay.measure.replay.old.r14.in_process(module, pdf, people, model)
                model.assert_not_called()
                wrong = bool(replay.exact.rc.wrong_fields(result, allowed))
                state = 'w' if wrong else 'c' if result['fields'] else 'n'
                row['results'][name], row['states'][name] = result, state
                counts[name + '_' + state] += 1
            for base in ('r25', 'r26'):
                counts[base + '_to_candidate_n_to_p'] += (
                    row['states'][base] == 'n' and row['states']['explicit_exemption'] in {'c', 'w'})
            rows.append(row)
        forbidden.assert_not_called()
    replay.write(OUT, 'low-exemption-measurement.json', dict(
        cases=len(rows), groups=groups, rows=rows, external_http_calls=forbidden.call_count,
        model_calls=0, source_sha256={n: hashlib.sha256(s.encode()).hexdigest() for n, s in variants.items()},
        shipped=False, reason='Reject any hold-to-placement transition under the release bar.'))
    print(json.dumps(groups, indent=2))


if __name__ == '__main__':
    main()
