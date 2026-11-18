"""Load the exact Gate 3 r31 generators without executing their runner setup."""
import copy
from itertools import product
from pathlib import Path

from dealroom_sign.tests import placement_r24_review_cases as R24

rc = R24.rc
FIXTURES = Path(__file__).with_name('fixtures') / 'r32'
FAMILIES = {'misspell': 6480, 'misspell_sender': 1080, 'role_other': 2610,
            'same_company': 1350, 'prev_column': 4050, 'affiliate_sender': 14580}


def namespace():
    source = (FIXTURES / 'reviewer-r31-own-final.py.txt').read_text()
    body = source[source.index('NOWHERE ='):source.index('\nfam = sys.argv[1]')]
    scope = dict(rc=rc, product=product)
    exec(compile(body, 'reviewer-r31-own-final.py.txt', 'exec'), scope)
    return scope


def captured(family):
    rows = list(namespace()['cases'](family))
    assert len(rows) == FAMILIES[family]
    return rows


def worker_case():
    source = (FIXTURES / 'reviewer-r31-aff_repro.py.txt').read_text()
    body = source[source.index('HLA_ROWS ='):source.index('\nmode =')]
    scope = dict(rc=rc)
    exec(compile(body, 'reviewer-r31-aff_repro.py.txt', 'exec'), scope)
    return scope
