"""Gate 3 r3 review regressions, applied in r5."""
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from django.utils import timezone

from dealroom.models import Activity
from dealroom_sign.client import SignError
from dealroom_sign.counterparty_mail import attempt_history, drain, enqueue, ready_at, send_effect
from dealroom_sign.models import CounterpartyEffect, ObservedSignEvent
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_workflows import fixture, pdf, recipients, envelope

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('limit', [1, 3])
def test_waiting_rechecks_have_independent_per_pass_cap(access, limit):
    waiting = [enqueue(access, 'invitation', f'waiting-{i}') for i in range(25)]
    past = timezone.now() - timedelta(minutes=16)
    CounterpartyEffect.objects.filter(pk__in=[e.pk for e in waiting]).update(
        last_error='mail_waiting', updated_at=past)
    sending = [enqueue(access, 'invitation', f'sending-{i}') for i in range(limit + 1)]
    before = Activity.objects.count()
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)) as native, \
         patch('dealroom_sign.recipient_proxy.eligible', side_effect=lambda *_:
               not CounterpartyEffect.objects.filter(state='running', last_error='mail_waiting').exists()), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', return_value=1):
        drain(limit)
    assert native.call_count == 20 + limit
    assert CounterpartyEffect.objects.filter(pk__in=[e.pk for e in waiting], updated_at=past).count() == 5
    assert CounterpartyEffect.objects.filter(pk__in=[e.pk for e in sending], state='succeeded').count() == limit
    assert CounterpartyEffect.objects.filter(pk=sending[-1].pk, state='pending').exists()
    assert ObservedSignEvent.objects.filter(kind='mail.attempt').count() == limit
    assert Activity.objects.count() == before + 2 * limit
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)) as native, \
         patch('dealroom_sign.recipient_proxy.eligible', side_effect=lambda *_:
               not CounterpartyEffect.objects.filter(state='running', last_error='mail_waiting').exists()), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send', return_value=1):
        drain(limit)
    assert native.call_count == 6
    assert not CounterpartyEffect.objects.filter(pk__in=[e.pk for e in waiting], updated_at=past).exists()
    assert CounterpartyEffect.objects.filter(pk=sending[-1].pk, state='succeeded').exists()


def test_waiting_outage_keeps_bounded_preparation_retry_policy(access):
    effect = enqueue(access, 'invitation', 'waiting-outage')
    with patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)), \
         patch('dealroom_sign.recipient_proxy.eligible', return_value=False):
        send_effect(effect.pk)
    effect.refresh_from_db()
    assert effect.last_error == 'mail_waiting' and attempt_history(effect) == 0
    first_failure = effect.updated_at + timedelta(minutes=16)
    with patch('dealroom_sign.recipient_proxy.reconcile_native', side_effect=SignError('sign_transport_error')), \
         patch('dealroom_sign.counterparty_mail.StableMessage.send') as delivery:
        for attempt in range(1, 7):
            clock = first_failure if attempt == 1 else ready_at(effect, attempt_history(effect))
            with patch('dealroom_sign.counterparty_mail.timezone.now', return_value=clock):
                send_effect(effect.pk)
            effect.refresh_from_db()
            assert effect.state == ('pending' if attempt < 6 else 'failed')
            assert attempt_history(effect) == attempt
        delivery.assert_not_called()
    assert clock - first_failure == timedelta(hours=23, minutes=15)
    assert ObservedSignEvent.objects.filter(kind='mail.preparation_attempt').count() == 6
    assert not ObservedSignEvent.objects.filter(kind='mail.attempt').exists()


def test_report_discloses_waiting_outage_retry_exhaustion():
    report = (Path(__file__).resolve().parents[3] / 'docs/implementation/c1b-report.md').read_text()
    assert 'waiting-plus-outage' in report
    assert '23 hours 15 minutes' in report
    assert 'never became eligible' in report
    assert 'manual Retry email' in report
