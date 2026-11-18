"""Capture the unchanged r30 reviewer's close Date-band generators."""
from collections import Counter
from contextlib import nullcontext
import copy
import inspect
from itertools import product
from pathlib import Path
from types import SimpleNamespace
import time
from unittest.mock import Mock

from dealroom_sign.tests import placement_r24_review_cases as R24
from dealroom_sign.tests.test_placement import TWO

rc = R24.rc
FIXTURES = Path(__file__).with_name('fixtures') / 'r31'


def captured(direction):
    source = (FIXTURES / 'reviewer-r30-band.py.txt').read_text()
    body = source[source.index('FLEET ='):]
    rows = []

    def capture(module, pages, people, model):
        if module:
            local = inspect.currentframe().f_back.f_locals
            axes = {k: copy.deepcopy(local[k]) for k in (
                'swap', 'p', 'g', 'form', 'topname', 'other', 'dx', 'signer', 'recital')}
            rows.append((axes, copy.deepcopy(pages), copy.deepcopy(people),
                         copy.deepcopy(local['allowed'])))
        return {'fields': []}

    namespace = dict(
        rc=SimpleNamespace(pages_pdf=lambda pages: pages, RECITALS=rc.RECITALS,
                           PE=rc.PE, DE=rc.DE, wrong_fields=lambda *args: []),
        TWO=TWO, Counter=Counter, product=product, time=time, Mock=Mock,
        patch=lambda *a, **kw: nullcontext(), print=lambda *a, **kw: None,
        http=Mock(), calls=Counter(), M={'capture': True, 'paired': False},
        in_process=capture, sys=SimpleNamespace(argv=['capture', direction]))
    exec(compile(body, 'reviewer-r30-band.py.txt', 'exec'), namespace)
    assert len(rows) == 9216
    return rows


def workers():
    source = (FIXTURES / 'reviewer-r30-repro.py.txt').read_text()
    body = source[source.index("pat = dict"):]
    rows = []

    def capture(pages, people, model_client):
        local = inspect.currentframe().f_back.f_locals
        rows.append(({k: local[k] for k in ('p', 'g', 'right')},
                     copy.deepcopy(pages), copy.deepcopy(people)))
        return dict(status='capture', reason_code='capture', fields=[])

    namespace = dict(
        rc=SimpleNamespace(pages_pdf=lambda pages: pages, RECITALS=rc.RECITALS, PE=rc.PE),
        placement=SimpleNamespace(place=capture), Mock=Mock, OLD={},
        patch=lambda *a, **kw: nullcontext(), print=lambda *a, **kw: None)
    exec(compile(body, 'reviewer-r30-repro.py.txt', 'exec'), namespace)
    assert len(rows) == 36
    return rows
