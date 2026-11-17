"""Distant identity and annotation holds do not expose PDF evidence to History."""
import json
from unittest.mock import Mock, patch

import pytest

from dealroom_sign.models import ObservedSignEvent, Workflow
from dealroom_sign.placement import place
from dealroom_sign.workflows import PlacementRequired, command
from dealroom_sign.tests.test_placement_r3 import PAT
from dealroom_sign.tests.test_placement_r5 import annotation_pdf, distant_identity_pdf
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('source_kind', ['distant', 'widget', 'freetext'])
def test_r5_holds_keep_other_names_out_of_history(fixture, settings, caplog, source_kind):
    settings.BOARD_SIGN_BOARDS = {'board-c2a': {'owner_ids': [str(fixture.user.pk)],
        'room_ids': [str(fixture.room.pk)], 'team_ids': [3]}}
    source = (distant_identity_pdf() if source_kind == 'distant' else
              annotation_pdf(kind='FreeText' if source_kind == 'freetext' else 'Widget'))
    model = Mock()
    analyzed = []
    counts = (Workflow.objects.count(), ObservedSignEvent.objects.count())

    def analyze(pdf, signers):
        result = place(pdf, signers, model_client=model)
        analyzed.append(result)
        return result

    with patch('dealroom_sign.workflows.source_bytes', return_value=source), \
         patch('dealroom_sign.workflows.place', side_effect=analyze), \
         pytest.raises(PlacementRequired) as caught:
        command(owner=fixture.user, room=fixture.room, version=fixture.version,
                       recipients=PAT, idempotency_key='r5-private', board_id='board-c2a', placement='auto')
    assert analyzed[0]['status'] == 'needs_sender'
    assert analyzed[0]['fields'] == []
    model.assert_not_called()
    assert (Workflow.objects.count(), ObservedSignEvent.objects.count()) == counts
    emitted = json.dumps([analyzed, caught.value.result,
        list(ObservedSignEvent.objects.values_list('payload', flat=True))], default=str)
    assert 'lee harbor' not in (emitted + caplog.text).lower()
