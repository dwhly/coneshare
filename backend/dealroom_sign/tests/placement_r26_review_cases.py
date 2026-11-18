"""Run the reviewer's verbatim generator bodies with a capture-only evaluator.

The original commands and transcript hashes are retained under c2a-r26. Only
the harness preceding HLA/PAT is omitted; every layout/axis/loop is executed
unchanged. No case is sampled or filtered out of the captured matrices.
"""
from collections import Counter
from contextlib import nullcontext
import copy
import inspect
from itertools import product
from pathlib import Path
import time

from dealroom_sign.tests import placement_r24_review_cases as R24
from dealroom_sign.tests.test_placement import TWO

rc = R24.rc
EVIDENCE = Path(__file__).resolve().parents[3] / 'docs/implementation/c2a-r26'
SOURCES = {'q3a': (24, 19), 'q3b': (24, 20), 'q3c': (25, 30),
           'exhibits': (25, 32), 'cand5_controls': (25, 37)}


def captured(family):
    revision, call = SOURCES[family]
    source = (EVIDENCE / f'reviewer-r{revision}-call{call}.py.txt').read_text()
    body = source[source.index('HLA = R24.HLA\n'):]
    rows = []

    def capture(pages, people, allowed):
        local = inspect.currentframe().f_back.f_locals
        axes = {key: local[key] for key in
                ('kind', 'h', 'co', 'cap', 'L', 'recital', 'loc', 'aff',
                 'acap', 'extra', 'signer', 'fr', 'pr', 'hform', 'ex', 'third')
                if key in local and not callable(local[key])}
        rows.append((copy.deepcopy(axes), copy.deepcopy(pages),
                     copy.deepcopy(people), copy.deepcopy(allowed)))
        return 'nnn'

    namespace = dict(R24=R24, rc=rc, TWO=TWO, run=capture, Counter=Counter,
                     product=product, time=time, calls=Counter(),
                     forbid=type('NoCalls', (), {'call_count': 0})(),
                     patch=lambda *a, **kw: nullcontext(), print=lambda *a, **kw: None)
    exec(compile(body, str(EVIDENCE / f'reviewer-r{revision}-call{call}.py.txt'), 'exec'), namespace)
    return rows


def worker_cases():
    source = (EVIDENCE / 'reviewer-r25-call31.py.txt').read_text()
    body = source[source.index('PAT = '):source.index("with patch('httpx.Client.send'")]
    namespace = dict(R24=R24, rc=rc, TWO=TWO)
    exec(compile(body, 'reviewer-r25-call31.py.txt', 'exec'), namespace)
    for name, pages in namespace['CASES'].items():
        for both in (False, True):
            pat = namespace['PAT']
            people = [TWO[1], pat] if both else [pat]
            allowed = {rc.PE: (2, 320, 300, 500), rc.DE: (2, 40, 300, 220)}
            yield (name, both), pages, people, allowed
