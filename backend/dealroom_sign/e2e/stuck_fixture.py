"""Fault fixture: a real Sign draft after a lost distribution attempt, never a fake signature."""
import json
import sys
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from dealroom_sign.client import Documenso
from dealroom_sign.models import NdaPolicy, SignCredential
from dealroom_sign.workflows import adopt, command
from sharelinks.models import Viewer

assert settings.SIGN_DEPLOYMENT_ID == 'chief-glue-v1'
data = json.load(sys.stdin)
policy = NdaPolicy.objects.select_related('room__created_by', 'source_version__document').get(room_id=data['room_id'])
room = policy.room
member = Viewer.objects.get(organization=room.organization, email=data['email'], verified_at__isnull=False)
with transaction.atomic():
    work = command(owner=room.created_by, room=room, version=policy.source_version,
        recipients=[{'email':member.email, 'name':member.name, 'fields':policy.fields}],
        idempotency_key=f'nda:{room.pk}:{member.pk}:{policy.revision}', purpose='nda', member=member, policy=policy)
    assert work.state == 'queued' and not work.envelope_id
    with Documenso(SignCredential.objects.get(owner=room.created_by)) as client:
        from dealroom_sign.storage import source_bytes
        envelope_id = client.create(work, source_bytes(policy.source_version))
        adopt(work, client, envelope_id)
    # Explicit fault injection: crash at the persisted distribute intent, before delivery.
    work.state = 'distributing'
    work.last_error = 'distribution_outcome_uncertain'
    work.next_attempt_at = timezone.now()
    work.save()
    print(json.dumps({'workflow_id':str(work.pk),'envelope_id':envelope_id}))
