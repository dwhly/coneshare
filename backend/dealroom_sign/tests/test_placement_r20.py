"""Domain evidence cannot resolve a third party's unnamed signing block."""
import ast
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.placement_r19_review_cases import competition
from dealroom_sign.tests.placement_r20_review_cases import WORKER_ROWS, realistic_cases
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import rows_pdf
from dealroom_sign.tests.test_placement_r14 import in_process
from dealroom_sign.tests.test_placement_r17 import signers, wrong_fields


REALISTIC = list(realistic_cases())
COMPETITION = list(competition())


def permitted_named_competition(case, result, allowed):
    """The review permits the affiliate only when another person is printed."""
    head, extra, affiliate, column, fleet_cross, both = ast.literal_eval(case)
    wrong = wrong_fields(result, allowed)
    if (not wrong or head not in {'RECIPIENT:', 'COMPANY', None}
            or extra not in {'Chris Jones', 'Name: Chris Jones'}):
        return False
    x = 40 if column == 0 else 280
    return all(field['signer'] == PAT[0]['email']
               and x < field['evidence']['line'][0] < x + 180
               and field['evidence']['line'][1] == (450 if field['type'] == 'SIGNATURE' else 510)
               and field['evidence']['line'][2] == x + 180
               for field in wrong)


@pytest.mark.parametrize('group,case,rows,both,allowed', REALISTIC,
                         ids=[str(i) for i in range(len(REALISTIC))])
def test_realistic_nda_unnamed_party_holds(group, case, rows, both, allowed):
    model = Mock()
    result = in_process(placement, rows_pdf(rows), signers(both), model)
    assert not wrong_fields(result, allowed), (case, result)
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    model.assert_not_called()


@pytest.mark.parametrize('group,case,rows,both,allowed', COMPETITION,
                         ids=[str(i) for i in range(len(COMPETITION))])
def test_review_competition_unnamed_party_holds(group, case, rows, both, allowed):
    model = Mock()
    result = in_process(placement, rows_pdf(rows), signers(both), model)
    wrong = wrong_fields(result, allowed)
    assert not wrong or permitted_named_competition(case, result, allowed), (case, result)
    if result['status'] == 'needs_sender':
        assert result['fields'] == [], result
    model.assert_not_called()


@pytest.mark.parametrize('both', [False, True])
def test_review_address_recital_real_worker_holds(both):
    model = Mock()
    result = placement.place(rows_pdf(WORKER_ROWS), signers(both), model_client=model)
    assert (result['status'], result['fields']) == ('needs_sender', []), result
    assert result == in_process(placement, rows_pdf(WORKER_ROWS), signers(both), model)
    model.assert_not_called()
