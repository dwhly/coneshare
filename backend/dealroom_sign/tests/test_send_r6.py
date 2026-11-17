"""Placement holds keep raw PDF identities out of workflow records and logs."""
import json
from unittest.mock import Mock, patch

import pytest

from dealroom_sign.models import ObservedSignEvent, Workflow
from dealroom_sign.placement import place
from dealroom_sign.tests.test_placement import LEE
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r4 import harbor_variant
from dealroom_sign.tests.test_placement_r6 import contact_rule_pdf, running_text_pdf
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients  # noqa: F401
from dealroom_sign.workflows import PlacementRequired, command

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('source_kind', ['contact', 'footer', 'title', 'period'])
def test_r6_holds_keep_other_names_out_of_history(fixture, settings, caplog, source_kind):
    settings.BOARD_SIGN_BOARDS = {'board-c2a': {'owner_ids': [str(fixture.user.pk)],
        'room_ids': [str(fixture.room.pk)], 'team_ids': [3]}}
    if source_kind == 'contact':
        source = contact_rule_pdf('Email', 'Lee Harbor')
    elif source_kind == 'footer':
        source = running_text_pdf(footer='Page 1 of 2')
    else:
        source = harbor_variant(wording='Title: Dan Whaley, CEO' if source_kind == 'title' else 'DAN WHALEY.')
    company_only = source_kind in {'contact', 'footer'}
    signers = PAT if company_only else [{k: LEE[0][k] for k in ('name', 'email')}]
    other_name = 'lee harbor' if company_only else 'dan whaley'
    model, analyzed = Mock(), []
    counts = (Workflow.objects.count(), ObservedSignEvent.objects.count())

    def analyze(pdf, signers):
        result = place(pdf, signers, model_client=model)
        analyzed.append(result)
        return result

    with patch('dealroom_sign.workflows.source_bytes', return_value=source), \
         patch('dealroom_sign.workflows.place', side_effect=analyze), \
         pytest.raises(PlacementRequired) as caught:
        command(owner=fixture.user, room=fixture.room, version=fixture.version,
                recipients=signers, idempotency_key='r6-private', board_id='board-c2a', placement='auto')
    assert analyzed[0]['status'] == 'needs_sender'
    assert analyzed[0]['fields'] == []
    assert 'nothing was sent' in analyzed[0]['reason'].lower()
    model.assert_not_called()
    assert (Workflow.objects.count(), ObservedSignEvent.objects.count()) == counts
    emitted = json.dumps([analyzed, caught.value.result,
        list(ObservedSignEvent.objects.values_list('payload', flat=True))], default=str)
    assert other_name not in (emitted + caplog.text).lower()
