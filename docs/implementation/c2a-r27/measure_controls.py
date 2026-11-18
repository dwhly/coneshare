"""Replay the exact measured r26c subset and supplementary caption controls."""
from collections import Counter, defaultdict
from contextlib import ExitStack, nullcontext
import copy
import gzip
import inspect
from itertools import product
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(OUT.parent / 'c2a-r26')]
import replay26 as prior
from dealroom_sign.tests import placement_r27_review_cases as review
from dealroom_sign.tests.test_placement import TWO
from dealroom_sign.tests.test_placement_r8 import CAPTIONS
from dealroom_sign.tests.test_placement_r12 import HEADINGS
from dealroom_sign.tests.test_placement_r13 import own_company_pdf
from dealroom_sign.tests.test_placement_r3 import PAT as PAT13


def inputs():
    source = (OUT / 'reviewer-r26-call42.py.txt').read_text()
    body = source[source.index('G = Counter(); t = time.time()'):]
    rows = []

    def capture(pdf, people, allowed=None):
        local = inspect.currentframe().f_back.f_locals
        prefix = '\n'.join(body.splitlines()[:inspect.currentframe().f_back.f_lineno])
        group = ('L2 both' if len(people) == 2 else 'L2 single') if allowed is None else (
            'E' if '# L-2 with affiliate' in prefix else 'B' if "for (h, co), recital, signer in product([('RECIPIENT:', 'HL" in prefix else 'A')
        axes = {k: local[k] for k in ('caption', 'heading', 'recital', 'head', 'cap', 'signer', 'h', 'co') if k in local}
        rows.append((group, copy.deepcopy(axes), pdf, copy.deepcopy(people), copy.deepcopy(allowed)))
        return [dict(status='needs_sender', fields=[])] * 3 if allowed is None else ['n'] * 3

    namespace = dict(Counter=Counter, time=time, rc=review.rc, R24=review.R24, TWO=TWO,
                     CAPTIONS=CAPTIONS, HEADINGS=HEADINGS, own_company_pdf=own_company_pdf,
                     PAT13=PAT13, run=capture, product=product, M={}, Mock=Mock,
                     patch=lambda *a, **kw: nullcontext(), print=lambda *a, **kw: None)
    exec(compile(body, 'reviewer-r26-call42.py.txt', 'exec'), namespace)
    for caption, heading in product(['Executed by:', 'Authorised signatory:', 'Authorized signatory:',
                                    'Signatory:', 'Signed:', 'Firma:', 'Unterschrift:', 'Signé:',
                                    'Autograph:', 'Conforme:', ''],
                                   ['For and on behalf of the Recipient', 'harbor light analytics, inc.']):
        pages, people = review.caption_case(caption, heading=heading)
        rows.append(('captions', dict(caption=caption, heading=heading), review.rc.pages_pdf(pages),
                     people, {review.rc.PE: (2, 0, 370, 612)}))
    return rows


def main(label="measured-controls", selected=None):
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    variants = selected or ['r21', 'r25', 'r26', 'r26c', 'vocabulary', 'r27']
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    groups, rows = defaultdict(Counter), []
    calls = Counter()
    prior.measure.replay.prior.OUT = OUT
    with ExitStack() as stack:
        modules = {n: prior.measure.replay.prior.make_module('controls_' + n,
                   (OUT / (n + '-source.py.txt')).read_text(), stack) for n in variants}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, axes, pdf, people, allowed in inputs():
            row = dict(group=group, axes=axes, results={}, states={})
            counts = groups[group + (' ' + axes['recital'] if group in {'A', 'B'} else '')]
            counts['cases'] += 1
            for n, module in modules.items():
                model = Mock()
                result = prior.measure.replay.old.r14.in_process(module, pdf, people, model)
                calls[n] += model.call_count
                if group == 'L2 single':
                    correct = (result['status'] == 'placed' and sorted(f['evidence']['line'][1] for f in result['fields']) == [560, 600]
                               and result['assignments'][0]['score'] == result['assignments'][0]['margin'] == 4)
                    wrong = bool(result['fields']) and not correct
                elif group == 'L2 both':
                    correct = not result['fields'] and result['status'] == 'needs_sender'
                    wrong = not correct
                else:
                    wrong = bool(review.rc.wrong_fields(result, allowed))
                    correct = bool(result['fields']) and not wrong
                state = 'w' if wrong else 'c' if result['fields'] else 'n'
                row['results'][n], row['states'][n] = result, state
                counts[n + '_' + state] += 1
                counts[n + '_expected'] += correct
                if n == 'r27' and group == 'captions':
                    worker = module.place(pdf, people, model_client=Mock())
                    assert worker == result
            rows.append(row)
        forbidden.assert_not_called()
    (OUT / (label + '-summary.json')).write_text(json.dumps(dict(groups=groups, cases=len(rows),
            external_http_calls=0, model_calls=calls, worker_evaluations=22), indent=2) + '\n')
    with gzip.open(OUT / (label + '-cases.json.gz'), 'wt') as stream:
        json.dump(rows, stream)
    print(json.dumps(groups, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else main()
