"""Execute the r10 review matrix; retain grouped placements, never raw logs."""
import importlib.util
from itertools import product
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))

from dealroom_sign import placement  # noqa: E402
from dealroom_sign.tests.test_placement_r3 import PAT  # noqa: E402
from dealroom_sign.tests.test_placement_r9 import (  # noqa: E402
    BETWEEN, CAPTIONS, HEADINGS, PARTIES, assert_identity_hold, stack_pdf,
)
from dealroom_sign.tests.test_placement_r10 import (  # noqa: E402
    CONTACTS, DY_VALUES, EXEMPT_CONTACTS, MATCHING_SIGNERS, VARIANTS,
    assert_signature_control, assert_stack_hold, contact_out_of_slot_pdf, out_of_slot_pdf,
    stack_out_of_slot_pdf,
)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def main():
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('PLACE_MODEL', None)
    spec = importlib.util.spec_from_file_location('r9_evidence', OUT.parent / 'c2a-r9/check_evidence.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    # Reuse the existing exact golden comparison, writing only into r10.
    previous.OUT = OUT
    groups = {}

    def record(group, case, result, identity_hold=False):
        outcome = previous.compact(result)
        outcome['model_calls'] = 0
        if identity_hold:
            outcome.update(uncertain_identity=True, scores=[0])
        # Store a common asserted outcome once, plus every executed case ID.
        entries = groups.setdefault(group, [])
        entry = next((entry for entry in entries if entry['outcome'] == outcome), None)
        if entry is None:
            entry = {'outcome': outcome, 'cases': []}
            entries.append(entry)
        entry['cases'].append(case)

    forbidden = Mock(side_effect=AssertionError('External model I/O forbidden'))
    with patch('httpx.Client.send', forbidden):
        previous.goldens()
        for variant, layout, heading, caption in product(VARIANTS, ('C12', 'C13'), HEADINGS, CAPTIONS):
            result = assert_identity_hold(out_of_slot_pdf(layout, heading, caption, variant), PAT)
            record('B-1', '/'.join((variant, layout, heading, caption)), result, True)
        print('B-1: 240 holds', flush=True)
        for dy, layout, caption in product(DY_VALUES, ('C12', 'C13'), CAPTIONS):
            result = assert_identity_hold(out_of_slot_pdf(layout, 'RECIPIENT:', caption, dy=dy), PAT)
            record('dy_sweep', '/'.join((str(dy), layout, caption)), result, True)
        for variant, layout, heading in product(VARIANTS, ('C12', 'C13'), HEADINGS):
            result = assert_signature_control(out_of_slot_pdf(layout, heading, 'Signature:', variant), layout)
            record('Signature_controls', '/'.join((variant, layout, heading)), result)
        print('dy sweep: 60 holds; Signature controls: 48 unchanged', flush=True)
        for (company, name, signers), caption in product(PARTIES, CAPTIONS):
            for variant in VARIANTS:
                result = assert_stack_hold(stack_out_of_slot_pdf(company, name, caption, variant), signers)
                record('H-1_out_of_slot', '/'.join((name, caption, variant)), result)
            for between in BETWEEN:
                result = assert_identity_hold(stack_pdf(company, name, between, caption), signers)
                record('H-1_existing', '/'.join((name, caption, between or 'no row')), result, True)
        print('H-1: 80 holds', flush=True)
        for variant, (name, signers), label in product(VARIANTS, MATCHING_SIGNERS, CONTACTS):
            result = assert_identity_hold(contact_out_of_slot_pdf(label, name, variant), signers)
            record('M-1', '/'.join((variant, name, label)), result, True)
        for variant, (name, signers), label in product(VARIANTS, MATCHING_SIGNERS, EXEMPT_CONTACTS):
            model = Mock()
            result = placement.place(contact_out_of_slot_pdf(label, name, variant), signers, model_client=model)
            assert result['status'] == 'placed'
            assert len(result['fields']) == 2
            assert {(f['type'], f['evidence']['line'][1], f['confidence']) for f in result['fields']} == {
                ('SIGNATURE', 400, 'high'), ('DATE', 430, 'high'),
            }
            model.assert_not_called()
            record('exempt_contacts', '/'.join((variant, name, label)), result)
        forbidden.assert_not_called()
    write('review-placements.json', groups)
    summary = {
        'analysis_version': placement.VERSION,
        'execution': 'Real reportlab PDFs through placement.place and its parser subprocess; local extraction also verifies identity scores.',
        'cases': {group: sum(len(entry['cases']) for entry in entries) for group, entries in groups.items()},
        'goldens_exact': 7, 'golden_baselines': ['c2a-r4', 'c2a-r5'],
        'external_model_calls': 0, 'golden_model_stub_calls': 1,
        'raw_logs_retained': False,
    }
    write('placement-summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
