"""Conflicting role recitals hold; direct definitions retain their local company."""
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests import placement_r21_review_cases as rc
from dealroom_sign.tests import placement_r22_review_cases as cases
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process
from dealroom_sign.tests.test_placement_r17 import signers


@pytest.mark.parametrize('args,pages,both,allowed', list(cases.conflict_probes()))
def test_conflicting_role_definitions_hold(args, pages, both, allowed):
    model = Mock()
    result = in_process(placement, rc.pages_pdf(pages), signers(both), model)
    assert not rc.wrong_fields(result, allowed), (args, result)
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()


@pytest.mark.parametrize('both', [False, True])
def test_review_hla_nw_real_worker(both):
    pages, _ = rc.layout_pages('same', 'none', 'RECIPIENT:', 'placeholders', 'group')
    model = Mock()
    result = placement.place(rc.pages_pdf([cases.HLA, cases.NW] + pages[1:]),
                             signers(both), model_client=model)
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()


@pytest.mark.parametrize('args,pages,both,allowed', list(cases.l1_matrix()))
def test_recital_precedence_matrix(args, pages, both, allowed):
    model = Mock()
    pdf = rc.pages_pdf(pages)
    _, _, roles = placement.extract(pdf)
    assert 'harbor light analytics' in roles['recipient'].lower(), roles
    assert 'fleet' not in roles['recipient'].lower(), roles
    result = in_process(placement, pdf, signers(both), model)
    assert not rc.wrong_fields(result, allowed), (args, result)
    model.assert_not_called()


@pytest.mark.parametrize('joiner', [', and ', ' and '])
def test_description_stops_before_next_capitalised_company(joiner):
    text = ('between Fleet Test Co., a Delaware corporation' + joiner
            + 'Harbor Light Analytics, Inc., with offices at 100 Harbor Way ("Recipient")')
    matches = list(placement.ROLE_DESCRIPTION.finditer(text))
    assert [m.group(1) for m in matches] == ['Harbor Light Analytics, Inc.']


@pytest.mark.parametrize('sequence', [(cases.HLA, cases.NW, cases.HLA),
                                      (cases.NW, cases.HLA, cases.NW)])
def test_conflict_cannot_be_cleared_by_a_repeated_definition(sequence):
    rows = [(80 + i * 40, page[0][1], False, 40) for i, page in enumerate(sequence)]
    _, _, roles = placement.extract(rc.pages_pdf([rows]))
    assert placement.party_role_text(roles['recipient']), roles
