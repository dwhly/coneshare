"""Native audit facts, with nullable historical gaps and recipient-first attribution."""
import ipaddress
import math

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import BoardStaffBinding, ObservedSignEvent
from .requests import people

EVENTS = {'DOCUMENT_SENT': 'envelope.sent', 'DOCUMENT_OPENED': 'envelope.viewed',
    'DOCUMENT_VIEWED': 'envelope.viewed', 'DOCUMENT_RECIPIENT_COMPLETED': 'envelope.signed',
    'DOCUMENT_COMPLETED': 'envelope.completed', 'DOCUMENT_RECIPIENT_REJECTED': 'envelope.declined',
    'DOCUMENT_REJECTED': 'envelope.declined', 'DOCUMENT_CANCELLED': 'envelope.cancelled',
    'DOCUMENT_RECIPIENT_EXPIRED': 'envelope.expired', 'EMAIL_SENT': 'native_email.alert'}


def instant(value):
    try:
        parsed = parse_datetime(value) if isinstance(value, str) else None
        return timezone.make_aware(parsed) if parsed and timezone.is_naive(parsed) else parsed
    except (ValueError, TypeError):
        return None


def ingest(workflow, rows):
    for raw in rows:
        if not isinstance(raw, dict) or raw.get('id') is None:
            continue
        kind = str(raw.get('type') or raw.get('event') or 'UNKNOWN')[:100]
        data = raw.get('data') or raw.get('payload') or {}
        if not isinstance(data, dict):
            data = {}
        recipient = data.get('recipientId')
        if recipient is None and data.get('recipientEmail'):
            matches = [p.get('id') for p in workflow.signer_projection if p.get('email', '').lower() == str(data['recipientEmail']).lower()]
            recipient = matches[0] if len(matches) == 1 else None
        try:
            ip = str(ipaddress.ip_address(raw.get('ipAddress')))
        except ValueError:
            ip = None
        ObservedSignEvent.objects.update_or_create(workflow=workflow, source_id=str(raw['id']),
            kind=EVENTS.get(kind, kind), defaults={'occurred_at': instant(raw.get('createdAt')),
                'actor_email': raw.get('email') or None, 'name': raw.get('name') or None,
                'recipient_id': str(recipient) if recipient is not None else None,
                'ip_address': ip, 'user_agent': raw.get('userAgent') or None,
                'payload': {'type': kind, 'data': data}, 'schema_version': 1})


def refresh_audit(row, client):
    row.audit_complete = False
    row.save(update_fields=['audit_complete'])
    audit = client.audit(row.workflow.envelope_id)
    rows = audit if isinstance(audit, list) else audit['data']
    with transaction.atomic():
        ingest(row.workflow, rows)
        row.audit_complete, row.audit_as_of = True, timezone.now()
        row.save(update_fields=['audit_complete', 'audit_as_of'])


def location(ip):
    if not ip:
        return {'label': None, 'approximate': True, 'reason': 'not_recorded'}
    address = ipaddress.ip_address(ip)
    if address.version == 4 and address in ipaddress.ip_network('100.64.0.0/10'):
        return {'label': 'Company network', 'approximate': True}
    if address.is_private:
        return {'label': 'Private network', 'approximate': True}
    return {'label': None, 'approximate': True, 'reason': 'not_mapped'}


def projection(row):
    facts = list(ObservedSignEvent.objects.filter(workflow=row.workflow).order_by('occurred_at', 'source_id'))
    bound = {email.lower() for email in BoardStaffBinding.objects.filter(board_id=row.board_id, enabled=True,
        send_user__is_active=True).values_list('signer_email', flat=True)}
    result = []
    for person in people(row):
        rid = person['recipient_id']
        events = [f for f in facts if rid is not None and f.recipient_id == str(rid)]
        def first(types):
            return next((f.occurred_at for f in events if f.payload.get('type') in types and f.occurred_at), None)
        sent = next((f.occurred_at for f in events if f.payload.get('type') == 'EMAIL_SENT'
            and f.payload.get('data', {}).get('emailType') == 'SIGNING_REQUEST' and f.occurred_at), None)
        signed = first({'DOCUMENT_RECIPIENT_COMPLETED'}) or instant(person.get('signed_at'))
        addresses = [{'event_id':f.source_id,'at':f.occurred_at,'ip':f.ip_address,'user_agent':f.user_agent} for f in events if f.ip_address or f.user_agent]
        ip = next((f.ip_address for f in reversed(events) if f.ip_address), None)
        ours = person['email'].lower() in bound
        # Slice 1 imports no verified entry. Native completion never upgrades legacy identity.
        classification = {'value': 'board_user' if ours else 'outside', 'reason': 'board_sign_in_not_observed' if ours else 'no_board_binding'}
        observed = 'email_code' if any(f.payload.get('type') in {'ACCESS_AUTH_2FA_VALIDATED', 'DOCUMENT_ACCESS_AUTH_2FA_VALIDATED'} for f in events) else None
        result.append({'recipient_id':rid,'email':person['email'],'name':person['name'],
            'classification':classification,'sent_at':sent or instant(person.get('sent_at')),'opened_at':first({'DOCUMENT_OPENED','DOCUMENT_VIEWED'}),
            'signed_at':signed,'identity':{'configured':None,'observed':observed,'reason':'not_recorded' if not observed else 'native_event'},
            'pages':{'status':'not_recorded','items':[]},'ip':ip,'location':location(ip),
            'device':{'browser':None,'os':None,'reason':'not_recorded'},'events':addresses,
            'signature':None,'consent':{'status':'not_recorded','at':None},
            'source_event_ids':[f.source_id for f in events], 'as_of':row.audit_as_of})
    return result


def snapshot_fields(workflow, snapshot_id, item_id, envelope):
    """Bind observed native geometry to the exact downloaded/verified snapshot."""
    allowed = {'id','recipientId','envelopeItemId','type','page','positionX','positionY','width','height','inserted'}
    fields = [{k:v for k,v in f.items() if k in allowed} for f in envelope.get('fields', [])
              if f.get('envelopeItemId') == item_id]
    ObservedSignEvent.objects.get_or_create(workflow=workflow, source_id=snapshot_id, kind='snapshot.fields',
        defaults={'payload':{'item_id':item_id,'fields':fields,'signers':signer_state(envelope.get('recipients', []))},'occurred_at':timezone.now()})


def fields_for_snapshot(workflow, snapshot_id):
    fact = ObservedSignEvent.objects.filter(workflow=workflow, source_id=snapshot_id, kind='snapshot.fields').first()
    result = []
    for field in fact.payload.get('fields', []) if fact else []:
        try:
            value = {k:float(field[k]) for k in ['positionX','positionY','width','height']}
            page = int(field['page'])
            valid = all(math.isfinite(v) for v in value.values()) and 0 <= value['positionX'] < 100 and 0 <= value['positionY'] < 100
            valid = valid and 0 < value['width'] <= 100-value['positionX'] and 0 < value['height'] <= 100-value['positionY']
            if valid and page > 0 and field['type'] in {'SIGNATURE','FREE_SIGNATURE','INITIALS'}:
                result.append({**value,'id':str(field['id']),'page':page,'recipient_id':field['recipientId'],'inserted':field.get('inserted') is True})
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return result


def signer_state(recipients):
    return sorted([[str(p.get('id')), p.get('email'), p.get('signingStatus'), p.get('signedAt')]
                   for p in recipients], key=lambda p:p[0])
