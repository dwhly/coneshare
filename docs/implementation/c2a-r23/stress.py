"""Explicit reconstructions of the r21 review's recital and page-probe axes.

The review's stdin generator was not preserved. These inputs are recorded here;
raw geometry flags remain visible, including the carried M-1 misspelling class.
"""
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
from itertools import product
import json
import os
import sys
from unittest.mock import Mock, patch

import replay
from dealroom_sign.tests.test_placement_r22_conflict_probes import PROBES

rc, new, OUT, ROOT = replay.rc, replay.new, replay.OUT, replay.ROOT
RECITALS = {
    'northwind': new.NW,
    'affiliate': new.recital_rows(new.HLA[0][1].replace('HARBOR LIGHT ANALYTICS, INC.', 'HARBOR LIGHT GROUP, INC.')),
    'misspelled_M1': new.recital_rows(new.HLA[0][1].replace('HARBOR LIGHT', 'HARBOUR LIGHT')),
    'role_word': new.recital_rows(new.HLA[0][1].replace('HARBOR LIGHT ANALYTICS, INC.', 'THE COMPANY')),
    'conflict_hla_nw': [new.HLA[0], (110, new.NW[0][1], False, 40)],
    'conflict_nw_hla': [new.NW[0], (110, new.HLA[0][1], False, 40)],
    'description_inline': new.recital_rows(new.DESCRIPTION),
    'description_wrapped': new.recital_rows(new.DESCRIPTION, True),
    'simple_between': new.recital_rows('This Agreement is entered into between Fleet Test Co. and Harbor Light Analytics, Inc. ("Recipient").'),
    'subsidiary': new.recital_rows('This Agreement is entered into between FLEET TEST CO. ("Discloser") and HARBOR LIGHT GROUP, INC., on behalf of its subsidiary HARBOR LIGHT ANALYTICS ("Recipient").'),
    'hereinafter': rc.RECITALS['hereinafter'],
}


def cases():
    for args in product(RECITALS, ('RECIPIENT:', 'THE RECIPIENT', 'Recipient', None),
                        ('same', 'guarantor', 'split'), ('group', 'guarantor', 'ventures', 'none'),
                        (False, True), (False, True)):
        recital, heading, layout, affiliate, fleet_name, both = args
        pages, allowed = rc.layout_pages(layout, 'none', heading, 'placeholders', affiliate)
        pages[0] = RECITALS[recital]
        if not fleet_name:
            pages = [[r for r in page if r[1] != 'FLEET TEST CO.'] for page in pages]
        yield 'Recitals ' + recital, repr(args), pages, both, allowed, False
    for args in product(('nw_page2', 'nw_page3', 'nw_after_sigs_only', 'nw_section1',
                         'conflict_pages12', 'conflict_section1', 'the_recipient_page2'),
                        ('same', 'guarantor', 'split'), ('RECIPIENT:', 'THE RECIPIENT', 'Recipient'),
                        ('group', 'guarantor', 'ventures', 'none'), (False, True)):
        location, layout, heading, affiliate, both = args
        pages, allowed = rc.layout_pages(layout, 'none', heading, 'placeholders', affiliate)
        shift = 0
        if location in {'nw_page2', 'the_recipient_page2'}:
            rows = new.NW if location == 'nw_page2' else new.recital_rows(new.NW[0][1].replace('"Recipient"', '"The Recipient"'))
            pages = [[], rows, *pages[1:]]
            shift = 1
        elif location == 'nw_page3':
            pages = [[], [], new.NW, *pages[1:]]
            shift = 2
        elif location == 'nw_after_sigs_only':
            pages.append(new.NW)
        elif location == 'nw_section1':
            pages[0] = [(80, 'Section 2. Parties', False, 40), (200, new.NW[0][1], False, 40)]
        elif location == 'conflict_pages12':
            pages = [new.HLA, new.NW, *pages[1:]]
            shift = 1
        else:
            pages[0] = [new.HLA[0], (200, new.NW[0][1], False, 40)]
        allowed = {k: (p + shift, x, y, end) for k, (p, x, y, end) in allowed.items()}
        yield 'Page probes ' + location, repr(args), pages, both, allowed, False
    for args in PROBES:
        layout, heading, extra, both = args
        pages, allowed = rc.layout_pages(layout, 'none', heading, extra, 'group')
        allowed = {k: (p + 1, x, y, end) for k, (p, x, y, end) in allowed.items()}
        yield 'M2 36 failing probes', repr(args), [new.HLA, new.NW, *pages[1:]], both, allowed, True
    for args in product(('same', 'guarantor', 'split'), ('none', 'parsed', 'address'),
                        ('none', 'placeholders', 'printed'), (False, True)):
        layout, recital, extra, both = args
        pages, allowed = rc.layout_pages(layout, recital, 'THE RECIPIENT', extra, 'group')
        yield 'B2 54 worker cells', repr(args), pages, both, allowed, True


def main():
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    sources = {n: (OUT / ('new-' + n + '.py.txt')).read_text() for n in ['r21', 'r22', 'r23']}
    assert sources['r23'] == (ROOT / replay.old.PRODUCT).read_text()
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    groups, records, outcomes, workers = {}, [], {}, []
    transitions = defaultdict(Counter)
    with ExitStack() as stack:
        modules = {n: replay.prior.make_module('stress_' + n, s, stack) for n, s in sources.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for group, case, pages, both, allowed, worker in cases():
            counts = groups.setdefault(group, Counter())
            counts['cases'] += 1
            row = {'group': group, 'case': case, 'results': {}, 'raw_wrong': {}, 'model_calls': {}}
            results = {}
            for name, module in modules.items():
                model = Mock()
                pdf = rc.pages_pdf(pages)
                result = replay.old.r14.in_process(module, pdf, replay.signers(both), model)
                results[name] = result
                digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
                outcomes[digest] = result
                row['results'][name] = digest
                raw = bool(rc.wrong_fields(result, allowed))
                row['raw_wrong'][name] = raw
                counts[name + '_raw_wrong'] += raw
                counts[name + '_' + {'needs_sender': 'holds', 'placed': 'placed', 'bare': 'bare'}[result['status']]] += 1
                row['model_calls'][name] = model.call_count
                model.assert_not_called()
                if worker:
                    actual = module.place(pdf, replay.signers(both), model_client=model)
                    assert actual == result, (group, case, name)
                    workers.append({'group': group, 'case': case, 'variant': name, 'result': digest})
            counts['new_raw_wrong'] += row['raw_wrong']['r23'] and not row['raw_wrong']['r21']
            before = 'raw_wrong' if row['raw_wrong']['r21'] else results['r21']['status']
            after = 'raw_wrong' if row['raw_wrong']['r23'] else results['r23']['status']
            transitions[group][before + ' -> ' + after] += 1
            records.append(row)
            if len(records) % 250 == 0:
                print(len(records), 'cells; new raw wrong', sum(g['new_raw_wrong'] for g in groups.values()), flush=True)
    forbidden.assert_not_called()
    summary = {'cases': len(records), 'groups': groups, 'transitions': transitions,
               'external_http_calls': forbidden.call_count, 'worker_evaluations': len(workers),
               'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n, s in sources.items()}}
    replay.write('stress-summary', summary)
    replay.write('stress-cases', {'cases': records, 'outcomes': outcomes})
    replay.write('stress-workers', workers)
    print(json.dumps(summary, indent=2), flush=True)
    assert all(g['new_raw_wrong'] == 0 for g in groups.values())
    assert all(g['r23_raw_wrong'] == 0 for group, g in groups.items()
               if not (group in {'Recitals northwind', 'Recitals misspelled_M1'}
                       or group.startswith('Page probes nw_')
                       or group == 'Page probes the_recipient_page2'))


if __name__ == '__main__':
    main()
