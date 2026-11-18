"""Measure unmodified reviewer cells with independent source modules."""
from collections import Counter
from contextlib import ExitStack
import copy
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from dealroom_sign.tests import placement_r29_review_cases as r29
from dealroom_sign.tests import placement_r30_review_cases as r30
from dealroom_sign.tests import placement_r31_review_cases as r31
from dealroom_sign.tests.test_placement_r14 import in_process


def module(name, source):
    result = ModuleType('measure31_' + name)
    result.__file__ = str(ROOT / 'backend/dealroom_sign/placement.py')
    sys.modules[result.__name__] = result
    exec(compile(source, result.__name__, 'exec'), result.__dict__)
    return result


def cells(family):
    if family in {'plain', 'swap'}:
        return r31.captured(family)
    if family in {'date', 'ordinary_offsets', 'stray'}:
        return r30.captured(family)
    return r29.captured(family)


def main(family, label, versions):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    sources = {v: (OUT / (os.environ.get('R31_SOURCE', 'shipping-source.py.txt')
                          if v == 'r31' else v + '-source.py.txt')).read_text()
               for v in versions}
    rows, counts = [], Counter()
    http = Mock(side_effect=AssertionError('External HTTP forbidden'))
    with ExitStack() as stack:
        modules = {v: module(v, source) for v, source in sources.items()}
        for m in modules.values():
            fn = lru_cache(maxsize=12)(m.extract)
            stack.enter_context(patch.object(m, 'extract',
                lambda pdf, deadline=None, fn=fn: copy.deepcopy(fn(pdf))))
        render = lru_cache(maxsize=12)(lambda p: r29.pdf(json.loads(p)))
        stack.enter_context(patch('httpx.Client.send', http))
        for index, (axes, pages, people, allowed) in enumerate(cells(family)):
            pdf = render(json.dumps(pages))
            row = dict(index=index, axes=axes, results={}, states={}, model_calls={})
            for v, m in modules.items():
                client = Mock()
                result = in_process(m, pdf, people, client)
                state = 'w' if r29.rc.wrong_fields(result, allowed) else 'c' if result['fields'] else 'n'
                row['results'][v], row['states'][v] = result, state
                row['model_calls'][v] = client.call_count
                counts[v + '_' + state] += 1
                counts[v + '_model_calls'] += client.call_count
            for base in versions:
                for v in versions:
                    counts[base + '_to_' + v + '_' + row['states'][base] + row['states'][v]] += 1
            rows.append(row)
            if len(rows) % 300 == 0:
                print(family, len(rows), flush=True)
    http.assert_not_called()
    with gzip.open(OUT / (label + '-' + family + '-cases.json.gz'), 'wt') as stream:
        json.dump(rows, stream)
    summary = dict(family=family, cases=len(rows), counts=counts, external_http_calls=0,
                   source_sha256={v: hashlib.sha256(s.encode()).hexdigest() for v, s in sources.items()})
    (OUT / (label + '-' + family + '-summary.json')).write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
