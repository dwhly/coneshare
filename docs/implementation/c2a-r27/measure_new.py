"""Execute every exact r26 review cell with independent source/oracle evidence."""
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
sys.path[:0] = [str(ROOT / 'backend'), str(OUT.parent / 'c2a-r26')]
import replay26 as prior
from dealroom_sign.tests import placement_r27_review_cases as review


def main(label, variants):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    sources = {n: (OUT / (n + '-source.py.txt')).read_text() for n in variants}
    folder = OUT / label
    folder.mkdir(exist_ok=True)
    prior.measure.replay.prior.OUT = folder
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    rows, groups, changes = [], defaultdict(Counter), defaultdict(Counter)
    with ExitStack() as stack:
        modules = {n: prior.measure.replay.prior.make_module(label + '_' + n, s, stack)
                   for n, s in sources.items()}
        # Share parsing only for source-identical extractors. New structural
        # extraction is always run separately from all historical extractors.
        parses = {}
        for name, module in modules.items():
            key = sources[name][sources[name].index('def extract('):sources[name].index('\ndef accounted_label(')]
            # Include helpers, constants and dataclasses for new candidates.
            if name not in {'r25', 'r26', 'r26c', 'cand5'}:
                key = name
            fn = parses.setdefault(key, lru_cache(maxsize=1)(module.extract))
            stack.enter_context(patch.object(module, 'extract',
                                lambda pdf, deadline=None, fn=fn: copy.deepcopy(fn(pdf))))
        stack.enter_context(patch('httpx.Client.send', forbidden))
        cells = review.captured('ABCD') + review.captured('E')
        for index, (axes, pages, people, allowed) in enumerate(cells):
            group = axes['group']
            if group == 'D':
                group += ' ' + axes['variant']
            if group == 'E':
                group += ' ' + ('affiliate' if axes['aff'] == 'HARBOR LIGHT GROUP, INC.' else 'own_company')
            group += ' ' + ('recital' if axes['recital'] != 'none' else 'no_recital')
            pdf = review.rc.pages_pdf(pages)
            row = dict(index=index, group=group, axes=axes, results={}, raw_states={}, states={}, model_calls={})
            counts = groups[group]
            counts['cases'] += 1
            for name, module in modules.items():
                model = Mock()
                result = prior.measure.replay.old.r14.in_process(module, pdf, people, model)
                row['model_calls'][name] = model.call_count
                counts[name + '_model_calls'] += model.call_count
                raw = bool(review.rc.wrong_fields(result, allowed))
                # Explicit immutable policies, as identified by the reviewer:
                # a printed name is authoritative, and absent recitals the
                # separate own-company line retains r13 L-2 semantics.
                policy = ((axes['group'] == 'D' and axes['variant'] != 'blank_name')
                          or (axes['group'] == 'B' and len(people) == 1)
                          or (axes['group'] == 'E' and axes['aff'] != 'HARBOR LIGHT GROUP, INC.')
                          or (axes['group'] in {'A', 'B', 'E'} and axes['recital'] == 'none'))
                state = 'w' if raw and not policy else 'c' if result['fields'] else 'n'
                row['results'][name] = result
                row['raw_states'][name] = 'w' if raw else 'c' if result['fields'] else 'n'
                row['states'][name] = state
                counts[name + '_' + state] += 1
                counts[name + '_raw_wrong'] += raw
            for base in ('r21', 'r25', 'r26'):
                if base not in variants:
                    continue
                for candidate in variants:
                    before, after = row['states'][base], row['states'][candidate]
                    k = base + '_to_' + candidate
                    changes[k][before + '_to_' + after] += 1
                    changes[k]['n_to_p'] += before == 'n' and after in {'c', 'w'}
            rows.append(row)
            if len(rows) % 240 == 0:
                print(label, len(rows), flush=True)
        forbidden.assert_not_called()
    summary = dict(cases=len(rows), groups=groups, comparisons=changes,
                   source_sha256={n: hashlib.sha256(s.encode()).hexdigest() for n, s in sources.items()},
                   external_http_calls=0,
                   model_calls={n: sum(g[n + '_model_calls'] for g in groups.values()) for n in variants})
    with gzip.open(folder / 'cases.json.gz', 'wt') as f:
        json.dump(rows, f)
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
