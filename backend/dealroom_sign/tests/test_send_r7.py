"""New caption and repeated-body holds do not create workflows or disclose names."""
import json
from unittest.mock import Mock, patch

import pytest

from dealroom_sign.models import ObservedSignEvent, Workflow
from dealroom_sign.placement import place
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r6 import contact_rule_pdf
from dealroom_sign.tests.test_placement_r7 import repeated_body_pdf
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients  # noqa: F401
from dealroom_sign.workflows import PlacementRequired, command

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('source_kind', ['Fax', 'Mobile', 'Contact', 'Attention', 'Notice Address', 'body'])
def test_r7_holds_keep_other_names_out_of_history(fixture, settings, caplog, source_kind):
    settings.BOARD_SIGN_BOARDS = {'board-c2a': {'owner_ids': [str(fixture.user.pk)],
        'room_ids': [str(fixture.room.pk)], 'team_ids': [3]}}
    source = repeated_body_pdf() if source_kind == 'body' else contact_rule_pdf(source_kind, 'Lee Harbor')
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
                recipients=PAT, idempotency_key='r7-private', board_id='board-c2a', placement='auto')
    assert analyzed[0]['status'] == 'needs_sender'
    assert analyzed[0]['fields'] == []
    assert 'nothing was sent' in analyzed[0]['reason'].lower()
    model.assert_not_called()
    assert (Workflow.objects.count(), ObservedSignEvent.objects.count()) == counts
    emitted = json.dumps([analyzed, caught.value.result,
        list(ObservedSignEvent.objects.values_list('payload', flat=True))], default=str)
    assert 'lee harbor' not in (emitted + caplog.text).lower()
