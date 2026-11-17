"""Room NDAs return the signer to the room that started them, only after verified publication (Gate 3 M7)."""
from unittest.mock import patch

import pytest
from django.utils import timezone

from dealroom_sign.models import ObservedSignEvent
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_gate3_routes import BASE, browser_session, nda, observe_completion
from dealroom_sign.tests.test_workflows import envelope, fixture, pdf, recipients

pytestmark = pytest.mark.django_db


def bound_room(access, fixture, origin='https://room.test:9447'):
    from dealroom.models import RoomPolicy
    from sharelinks.models import ShareLink
    nda(access, fixture)
    link = ShareLink.objects.create(dataroom=fixture.room, created_by=fixture.user)
    RoomPolicy.objects.create(room=fixture.room, entry_link=link)
    ObservedSignEvent.objects.create(workflow=access.workflow, kind='room.return', source_id='room.return',
        payload={'room_id': str(access.workflow.room_id), 'origin': origin})
    return link


def test_bound_room_nda_waits_while_sealing_then_returns_to_its_room(access, fixture, settings):
    link = bound_room(access, fixture)
    settings.SITE_DOMAIN = 'https://staff.test:9443'
    browser, session, raw = browser_session(access)
    observe_completion(access, timezone.now())
    access.workflow.state = 'awaiting_seal'; access.workflow.save()
    path = '/s/return/' + str(access.workflow_id)
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow, 'COMPLETED')):
        waiting = browser.get(path + '?return_url=https://elsewhere.test', **BASE)
        assert waiting.status_code == 200
        assert b'opening the data room' in waiting.content and b'http-equiv="refresh"' in waiting.content
        assert b'elsewhere.test' not in waiting.content
        access.workflow.state = 'done'; access.workflow.save()
        response = browser.get(path + '?return_url=https://elsewhere.test', **BASE)
    assert response.status_code == 303
    assert response['Location'] == 'https://room.test:9447/view/' + link.slug + '?nda=complete'


def test_binding_for_another_room_is_ignored(access, fixture, settings):
    bound_room(access, fixture)
    ObservedSignEvent.objects.filter(workflow=access.workflow, kind='room.return').update(
        payload={'room_id': '00000000-0000-0000-0000-000000000009', 'origin': 'https://evil.test'})
    settings.SITE_DOMAIN = 'https://staff.test:9443'
    browser, session, raw = browser_session(access)
    observe_completion(access, timezone.now())
    access.workflow.state = 'done'; access.workflow.save()
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow, 'COMPLETED')):
        response = browser.get('/s/return/' + str(access.workflow_id), **BASE)
    assert response.status_code == 303 and 'evil.test' not in response['Location']
    assert response['Location'] == 'https://staff.test:9443/signing/nda/' + str(access.workflow.room_id)


def test_signed_context_page_uses_the_same_terminal(access, fixture, settings):
    link = bound_room(access, fixture)
    browser, session, raw = browser_session(access)
    observe_completion(access, timezone.now())
    access.workflow.state = 'done'; access.workflow.save()
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow, 'COMPLETED')):
        response = browser.get('/s/session/context', **BASE)
    assert response.status_code == 303
    assert response['Location'] == 'https://room.test:9447/view/' + link.slug + '?nda=complete'
