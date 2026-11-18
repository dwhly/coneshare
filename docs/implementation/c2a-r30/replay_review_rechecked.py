"""Replay prior reviewer families with immutable r29 baseline result archives."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
import copy
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import measure30 as measure

OUT, ROOT = measure.OUT, measure.ROOT
sys.path.insert(0, str(ROOT / 'backend'))
from dealroom_sign.tests import placement_r27_review_cases as old
from dealroom_sign.tests import placement_r28_review_cases as review28
from dealroom_sign.tests import placement_r29_review_cases as review29
from dealroom_sign.tests.test_placement_r14 import in_process

FAMILIES = ('variants', 'extended', 'ordinary', 'stacks', 'recitals', 'r27', 'notices', 'workers')
VERSIONS = ('r21', 'r28', 'r29', 'r30')


def main(family):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    archive = OUT.parent / ('c2a-r29/verified-review-' + family)
    with gzip.open(archive / 'cases.json.gz', 'rt') as stream:
        previous = json.load(stream)
    provenance = json.loads((archive / 'summary.json').read_text())
    for version in VERSIONS[:-1]:
        assert provenance['source_sha256'][version] == hashlib.sha256(
            (OUT / (version + '-source.py.txt')).read_bytes()).hexdigest()
    if family in {'variants', 'ordinary', 'stacks', 'recitals'}:
        cells = review28.captured(family)
    elif family == 'extended':
        cells = list(review28.extended())
    elif family == 'r27':
        cells = old.captured('ABCD') + old.captured('E')
    elif family == 'workers':
        cells = review29.workers()
    else:
        cells = review29.captured(family)
    assert len(cells) == len(previous)
    source = (OUT / 'shipping-source.py.txt').read_text()
    module = measure.module('review_' + family, source)
    http = Mock(side_effect=AssertionError('External HTTP forbidden'))
    counts, rows = Counter(), []
    with ExitStack() as stack:
        fn = lru_cache(maxsize=12)(module.extract)
        stack.enter_context(patch.object(module, 'extract',
            lambda pdf, deadline=None: copy.deepcopy(fn(pdf))))
        render = lru_cache(maxsize=12)(lambda pages: review29.pdf(json.loads(pages)))
        stack.enter_context(patch('httpx.Client.send', http))
        for index, ((axes, pages, people, allowed), prior) in enumerate(zip(cells, previous)):
            assert json.loads(json.dumps(axes)) == prior['axes'] and index == prior['index']
            pdf = render(json.dumps(pages))
            client = Mock()
            result = in_process(module, pdf, people, client)
            wrong = bool(result['fields']) if family == 'workers' else bool(review29.rc.wrong_fields(result, allowed))
            state = 'w' if wrong else 'c' if result['fields'] else 'n'
            row = dict(index=index, axes=axes, results={v: prior['results'][v] for v in VERSIONS[:-1]},
                       states={v: prior['raw_states'][v] for v in VERSIONS[:-1]},
                       model_calls={v: prior['model_calls'][v] for v in VERSIONS[:-1]},
                       retained_policy_control=prior['retained_policy_control'])
            row['results']['r30'], row['states']['r30'], row['model_calls']['r30'] = result, state, client.call_count
            for version in VERSIONS:
                counts[version + '_' + row['states'][version]] += 1
                counts[version + '_model_calls'] += row['model_calls'][version]
            for base in VERSIONS[:-1]:
                counts[base + '_to_r30_' + row['states'][base] + state] += 1
            if family == 'workers':
                assert module.place(pdf, people, model_client=Mock()) == result
            rows.append(row)
            if len(rows) % 300 == 0:
                print(family, len(rows), flush=True)
    http.assert_not_called()
    with gzip.open(OUT / ('rechecked-review-' + family + '-cases.json.gz'), 'wt') as stream:
        json.dump(rows, stream)
    summary = dict(family=family, cases=len(rows), counts=counts, external_http_calls=0,
                   source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                   baseline_method='immutable c2a.29 reviewer archives; hashes and case axes checked')
    (OUT / ('rechecked-review-' + family + '-summary.json')).write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


def run(family):
    with (OUT / ('rechecked-review-' + family + '.txt')).open('x') as log:
        result = subprocess.run([sys.executable, __file__, family], stdout=log, stderr=subprocess.STDOUT)
    return family, result.returncode


if __name__ == '__main__':
    if sys.argv[1] != 'all':
        main(sys.argv[1])
    else:
        codes = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            for future in as_completed([pool.submit(run, family) for family in FAMILIES]):
                family, code = future.result(); codes[family] = code
                print(family, code, flush=True)
        (OUT / 'rechecked-review-returncodes.json').write_text(json.dumps(codes, indent=2) + '\n')
        sys.exit(int(any(codes.values())))
