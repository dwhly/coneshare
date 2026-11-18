"""Capture the exact Gate 3 r29 generators without editing their source."""
from collections import Counter
from contextlib import nullcontext
import copy
import inspect
from itertools import product
from pathlib import Path
from types import SimpleNamespace
import time
from unittest.mock import Mock

from reportlab.pdfbase.pdfmetrics import stringWidth

from dealroom_sign.tests import placement_r24_review_cases as R24
from dealroom_sign.tests.test_placement import TWO

rc = R24.rc
FIXTURES = Path(__file__).with_name('fixtures') / 'r30'


def captured(family):
    filename = 'stray' if family == 'stray' else 'q3new'
    source = (FIXTURES / f'reviewer-r29-{filename}.py.txt').read_text()
    start = 'STRAY =' if family == 'stray' else 'W = lambda'
    body = source[source.index(start):]
    rows = []

    def capture(module, pages, people, model):
        if not module:
            return {'fields': []}
        local = inspect.currentframe().f_back.f_locals
        axes = {k: copy.deepcopy(local[k]) for k in (
            'layout', 'v', 'fleetname', 'datefirst', 'recital', 'signer',
            'stray', 'where', 'patname') if k in local}
        rows.append((axes, copy.deepcopy(pages), copy.deepcopy(people),
                     copy.deepcopy(local['allowed'])))
        return {'fields': []}

    namespace = dict(
        rc=SimpleNamespace(pages_pdf=lambda pages: pages, RECITALS=rc.RECITALS,
                           PE=rc.PE, DE=rc.DE, wrong_fields=lambda *args: []),
        TWO=TWO, Counter=Counter, product=product, time=time, Mock=Mock,
        stringWidth=stringWidth, patch=lambda *a, **kw: nullcontext(),
        print=lambda *a, **kw: None, http=Mock(), calls=Counter(),
        M={'capture': True, 'paired': False}, in_process=capture,
        sys=SimpleNamespace(argv=['capture', 'date' if family == 'date' else 'base']))
    exec(compile(body, f'reviewer-r29-{filename}.py.txt', 'exec'), namespace)
    return rows
