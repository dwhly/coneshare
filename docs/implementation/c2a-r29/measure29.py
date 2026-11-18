"""Replay exact review loops with independent historical and candidate sources."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(OUT.parent / 'c2a-r27')]
import replay27 as prior
from dealroom_sign.tests import placement_r27_review_cases as old
from dealroom_sign.tests import placement_r28_review_cases as old_review
from dealroom_sign.tests import placement_r29_review_cases as review
from dealroom_sign.tests.test_placement_r14 import in_process


def main(family, versions):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    sources = {n: (OUT / (os.environ.get('R29_CANDIDATE_SOURCE', 'r29-source.py.txt') if n == 'r29' else n + '-source.py.txt')).read_text() for n in versions}
    folder = OUT / (os.environ.get('R29_MEASURE_PREFIX', 'measured-') + family)
    folder.mkdir(exist_ok=True)
    prior.measure.replay.prior.OUT = folder
    rows, groups, changes = [], defaultdict(Counter), defaultdict(Counter)
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    if family in {'variants', 'ordinary', 'stacks', 'recitals'}:
        cells = old_review.captured(family)
    elif family == 'r27':
        cells = old.captured('ABCD') + old.captured('E')
    elif family == 'extended':
        cells = list(old_review.extended())
    elif family == 'workers':
        cells = review.workers()
    elif family == 'conformed':
        cells = [r for r in review.captured('hidden') if r[0]['shape'] == 'conformed_s']
    else:
        cells = review.captured(family)
    @lru_cache(maxsize=16)
    def rendered(serialized_pages):
        # Signer variants use the exact same document bytes. Cache rendering
        # only; every source scores a deep copy of its own extracted evidence.
        return review.pdf(json.loads(serialized_pages))

    with ExitStack() as stack:
        modules = {n: prior.measure.replay.prior.make_module(family + '_' + n, s, stack)
                   for n, s in sources.items()}
        for module in modules.values():
            fn = lru_cache(maxsize=16)(module.extract)
            stack.enter_context(patch.object(module, 'extract',
                                lambda pdf, deadline=None, fn=fn: copy.deepcopy(fn(pdf))))
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for index, (axes, pages, people, allowed) in enumerate(cells):
            group, policy = family, False
            if family in {'ordinary', 'stacks'}:
                group += ' ' + axes['where']
                policy = family == 'stacks' and axes['nm'] == 'Name: Pat Smith'
            if family == 'recitals':
                group += ' ' + (axes['kind'] if axes['group'] == 'E' else axes['group'])
                policy = axes['group'] == 'E' and axes['kind'] == 'E L-2 own line'
            if family == 'r27':
                group += ' ' + axes['group'] + ' ' + axes['recital']
                policy = ((axes['group'] == 'D' and axes['variant'] != 'blank_name')
                          or (axes['group'] == 'B' and len(people) == 1)
                          or (axes['group'] == 'E' and axes['aff'] != 'HARBOR LIGHT GROUP, INC.')
                          or (axes['group'] in {'A', 'B', 'E'} and axes['recital'] == 'none'))
            if family == 'notices':
                group += ' ' + axes['where']
                policy = axes['nm'] == 'Pat Smith'
            pdf = rendered(json.dumps(pages))
            row = dict(index=index, group=group, axes=axes, results={}, states={}, raw_states={},
                       model_calls={}, retained_policy_control=policy,
                       input_sha256=hashlib.sha256(pdf).hexdigest())
            counts = groups[group]
            counts['cases'] += 1
            for name, module in modules.items():
                model = Mock()
                result = in_process(module, pdf, people, model)
                raw = bool(result['fields']) if family == 'workers' else bool(review.rc.wrong_fields(result, allowed))
                state = 'w' if raw and not policy else 'c' if result['fields'] else 'n'
                row['results'][name] = result
                row['states'][name] = state
                row['raw_states'][name] = 'w' if raw else 'c' if result['fields'] else 'n'
                row['model_calls'][name] = model.call_count
                counts[name + '_' + state] += 1
                counts[name + '_raw_wrong'] += raw
                counts[name + '_model_calls'] += model.call_count
                if family == 'workers':
                    actual = module.place(pdf, people, model_client=Mock())
                    assert actual == result, (name, axes, 'worker differs')
            for base in ('r21', 'r27', 'r28'):
                if base not in versions:
                    continue
                for candidate in versions:
                    before, after = row['raw_states'][base], row['raw_states'][candidate]
                    key = base + '_to_' + candidate
                    changes[key][before + '_to_' + after] += 1
                    changes[key]['n_to_p'] += before == 'n' and after in {'c', 'w'}
                    for metric, condition in (
                        ('n_to_p', before == 'n' and after in {'c', 'w'}),
                        ('c_to_w', before == 'c' and after == 'w'),
                        ('c_to_n', before == 'c' and after == 'n'),
                        ('w_to_n', before == 'w' and after == 'n'),
                    ):
                        counts[key + '_' + metric] += condition
            rows.append(row)
            if len(rows) % 240 == 0:
                print(family, len(rows), flush=True)
        forbidden.assert_not_called()
    summary = dict(cases=len(rows), groups=groups, comparisons=changes,
                   source_sha256={n: hashlib.sha256(s.encode()).hexdigest() for n, s in sources.items()},
                   external_http_calls=forbidden.call_count, render_cache=rendered.cache_info()._asdict(),
                   model_calls={n: sum(g[n + '_model_calls'] for g in groups.values()) for n in versions})
    with gzip.open(folder / 'cases.json.gz', 'wt') as stream:
        json.dump(rows, stream)
    with (folder / 'summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
