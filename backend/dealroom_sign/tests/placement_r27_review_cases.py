"""Capture the r26 review's exact loops; retain every generated case."""
from collections import Counter
from contextlib import nullcontext
import copy
import inspect
from itertools import product
from pathlib import Path
import time

from dealroom_sign.tests import placement_r24_review_cases as R24
from dealroom_sign.tests.test_placement import TWO
from dealroom_sign.tests.test_placement_r8 import CAPTIONS

rc = R24.rc
EVIDENCE = Path(__file__).resolve().parents[3] / 'docs/implementation/c2a-r27'


def captured(family):
    call = 25 if family == 'E' else 28
    source = (EVIDENCE / f'reviewer-r26-call{call}.py.txt').read_text()
    body = source[source.index('X = 72\n' if family == 'E' else 'HLA = R24.HLA\n'):]
    rows = []

    def capture(pages, people, allowed):
        local = inspect.currentframe().f_back.f_locals
        axes = {key: local[key] for key in
                ('h', 'co', 'second', 'recital', 'fleet_extra', 'signer',
                 'ntext', 'variant', 'head', 'cap', 'aff', 'acap', 'fleet')
                if key in local and not callable(local[key])}
        # The same transcript contains A/B/C/D loops. Record their identity
        # from the active loop's source line, without rewriting the loop.
        line = inspect.currentframe().f_back.f_lineno
        prefix = '\n'.join(body.splitlines()[:line])
        group = 'E' if family == 'E' else max(
            ('A', 'B', 'C', 'D'), key=lambda g: prefix.rfind('# ' + g + ':'))
        axes['group'] = group
        axes['signers'] = len(people)
        rows.append((copy.deepcopy(axes), copy.deepcopy(pages),
                     copy.deepcopy(people), copy.deepcopy(allowed)))
        return ('nnn', {}) if family == 'E' else 'nnn'

    namespace = dict(R24=R24, rc=rc, TWO=TWO, CAPTIONS=CAPTIONS,
                     run=capture, Counter=Counter, product=product, time=time,
                     calls=Counter(), forbid=type('NoCalls', (), {'call_count': 0})(),
                     patch=lambda *a, **kw: nullcontext(), print=lambda *a, **kw: None)
    exec(compile(body, f'reviewer-r26-call{call}.py.txt', 'exec'), namespace)
    return rows


def caption_case(caption, recital='parsed', heading='For and on behalf of the Recipient'):
    rows = [(240, 'FLEET TEST CO.', False, 72), (270, 'By:', True, 72),
            (300, 'Date:', True, 72), (340, heading, False, 72),
            (370, caption, True, 72), (382, 'Name: Pat Smith', False, 72),
            (420, 'Date:', True, 72), (520, 'HARBOR LIGHT GROUP, INC.', False, 72),
            (560, 'By:', True, 72), (600, 'Date:', True, 72)]
    return [list(rc.RECITALS[recital]), rows], [dict(name='Pat Smith', email=rc.PE)]
