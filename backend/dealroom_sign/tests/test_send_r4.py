"""Only sanitized placement evidence is persisted to History."""
import json
from unittest.mock import Mock, patch

import pytest

from dealroom_sign.models import ObservedSignEvent
from dealroom_sign.placement import place
from dealroom_sign.requests import activity
from dealroom_sign.workflows import command
from dealroom_sign.tests.test_placement import LEE
from dealroom_sign.tests.test_placement_r2 import opaque_reply
from dealroom_sign.tests.test_placement_r3 import title_body_pdf
from dealroom_sign.tests.test_placement_r4 import company_body_pdf
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('selected', [False, True])
def test_company_word_body_is_absent_from_history(fixture, settings, caplog, selected):
    settings.BOARD_SIGN_BOARDS = {'board-c2a': {'owner_ids': [str(fixture.user.pk)], 'room_ids': [str(fixture.room.pk)], 'team_ids': [3]}}
    text = 'Project Falcon Acquisition Of Acme Corp.'
    model = Mock(side_effect=opaque_reply)
    source = company_body_pdf() if selected else title_body_pdf(text, extra_block=True)
    with patch('dealroom_sign.workflows.source_bytes', return_value=source), \
         patch('dealroom_sign.workflows.place', side_effect=lambda pdf, signers: place(pdf, signers, model_client=model)):
        work = command(owner=fixture.user, room=fixture.room, version=fixture.version,
                       recipients=[{k: v for k, v in LEE[0].items() if k != 'side'}],
                       idempotency_key='r4-private', board_id='board-c2a', placement='auto')
    assert text not in json.dumps(model.call_args.args[0])
    assert text not in json.dumps(activity(work.signature_request), default=str)
    assert text not in json.dumps(list(ObservedSignEvent.objects.filter(workflow=work).values_list('payload', flat=True)))
    assert text not in caplog.text
