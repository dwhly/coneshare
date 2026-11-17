"""The exact competition family retains identity and field-level oracles."""
import ast
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.placement_r19_review_cases import competition
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r9 import rows_pdf
from dealroom_sign.tests.test_placement_r14 import in_process
from dealroom_sign.tests.test_placement_r17 import signers, wrong_fields


COMPETITION = list(competition())


def justified_company_only(case, result, allowed):
    """Adjudicate the review's absent-company exception without changing its oracle."""
    head, extra, affiliate, affiliate_column, fleet_cross, both = ast.literal_eval(case)
    wrong = wrong_fields(result, allowed)
    if not wrong:
        return False
    # This input supplies Pat's domain, but neither her legal company nor a
    # company/name identifying the original blank as hers. The affiliate is
    # the only Harbor-named block; another person's caption cannot identify Pat.
    if head not in {'RECIPIENT:', 'COMPANY', None} or PAT[0].get('company'):
        return False
    x = 40 if affiliate_column == 0 else 280
    return all(field['signer'] == PAT[0]['email']
               and x < field['evidence']['line'][0] < x + 180
               and field['evidence']['line'][1] == (450 if field['type'] == 'SIGNATURE' else 510)
               and field['evidence']['line'][2] == x + 180
               for field in wrong)


def assert_competition_result(case, result, allowed):
    wrong = wrong_fields(result, allowed)
    assert not wrong or justified_company_only(case, result, allowed), (case, result)
    if result['status'] == 'needs_sender':
        assert result['fields'] == [], result


@pytest.mark.parametrize('group,case,rows,both,allowed', COMPETITION,
                         ids=[str(i) for i in range(len(COMPETITION))])
def test_exact_review_competition(group, case, rows, both, allowed):
    model = Mock()
    result = in_process(placement, rows_pdf(rows), signers(both), model)
    assert_competition_result(case, result, allowed)
    model.assert_not_called()
