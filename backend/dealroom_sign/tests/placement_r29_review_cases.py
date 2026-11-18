"""Capture Gate 3 r28 loop bodies without editing the source fixtures."""
from collections import Counter
from contextlib import nullcontext
import copy
import inspect
import io
from itertools import product
from pathlib import Path
from types import SimpleNamespace
import time
from unittest.mock import Mock

from reportlab.pdfgen import canvas

from dealroom_sign.tests import placement_r24_review_cases as R24
from dealroom_sign.tests.test_placement import TWO

rc = R24.rc
FIXTURES = Path(__file__).with_name('fixtures') / 'r29'


def captured(family):
    call, start = {
        'hidden': (32, 'X = 72\n'),
        'two_columns': (33, 'X = 72;'),
        'no_rule': (34, 'X = 72\n'),
        'geometry': (37, 'X = 72\n'),
        'ruleless_name': (41, 'G = Counter();'),
        'notices': (30, 'CAPS ='),
    }[family]
    source = (FIXTURES / f'reviewer-r28-call{call}.py.txt').read_text()
    body = source[source.index(start):]
    if family == 'two_columns':
        body = body[:body.index('    # conformed /s/ detail')]
    body = body.split("print('http'", 1)[0].split("print('elapsed'", 1)[0]
    rows = []

    def capture(pages, people, allowed):
        local = inspect.currentframe().f_back.f_locals
        axes = {key: copy.deepcopy(local[key]) for key in (
            'shape', 'nm', 'head', 'recital', 'signer', 'sk', 'aff', 'fx', 'gap',
            'side', 'mention', 'dy', 'dx', 'fleetname', 'pat_page', 'where', 'cap',
            'tail', 'msa',
        ) if key in local}
        rows.append((axes, copy.deepcopy(pages), copy.deepcopy(people), copy.deepcopy(allowed)))
        return 'nn'

    namespace = dict(R24=R24, rc=rc, TWO=TWO, run=capture, Counter=Counter,
                     product=product, time=time, X=72, calls=Counter(),
                     http=Mock(), Mock=Mock, patch=lambda *a, **kw: nullcontext(),
                     print=lambda *a, **kw: None,
                     sys=SimpleNamespace(argv=['capture', 'sig_page_below', 'exhibit_page',
                                               'recital_page', 'table_exhibit']))
    if family == 'ruleless_name':
        # This generator calls in_process directly rather than its run adapter.
        namespace['rc'] = SimpleNamespace(pages_pdf=lambda pages: pages,
                                         RECITALS=rc.RECITALS, PE=rc.PE, DE=rc.DE,
                                         wrong_fields=lambda result, allowed: [])
        namespace['M'] = {'capture': None}
        def direct(module, pages, people, model):
            local = inspect.currentframe().f_back.f_locals
            capture(pages, people, {rc.PE: local['allowed'], rc.DE: (2, 60, 270, 290)})
            rows[-1][0].update({k: copy.deepcopy(local[k]) for k in (
                'mention', 'dy', 'dx', 'fleetname', 'pat_page', 'recital', 'signer')})
            return {'fields': []}
        namespace['in_process'] = direct
    exec(compile(body, f'reviewer-r28-call{call}.py.txt', 'exec'), namespace)
    return rows


def pdf(pages):
    source = (FIXTURES / 'reviewer-r28-call32.py.txt').read_text()
    body = source[source.index('def pdf('):source.index('http = Mock(')]
    namespace = dict(io=io, canvas=canvas)
    exec(compile(body, 'reviewer-r28-call32.py.txt', 'exec'), namespace)
    return namespace['pdf'](pages)


def workers():
    source = (FIXTURES / 'reviewer-r28-call40.py.txt').read_text()
    body = source[source.index('fleet ='):source.index('# also:')]
    rows = []
    def capture(pdf, people, model_client):
        local = inspect.currentframe().f_back.f_locals
        rows.append(({'head': local['head'], 'recital': local['recital']},
                     copy.deepcopy(pdf), copy.deepcopy(people), {}))
        return dict(status='captured', fields=[], assignments=[])
    namespace = dict(X=72, rc=SimpleNamespace(pages_pdf=lambda p: p, RECITALS=rc.RECITALS, PE=rc.PE),
                     placement=SimpleNamespace(place=capture), Mock=Mock,
                     patch=lambda *a, **kw: nullcontext(), print=lambda *a, **kw: None)
    exec(compile(body, 'reviewer-r28-call40.py.txt', 'exec'), namespace)
    return rows
