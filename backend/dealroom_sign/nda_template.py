"""A sender confirms the template once; every visitor uses its pinned geometry."""
import json
import subprocess
import sys
import uuid

from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from datarooms.models import Dataroom
from dealroom.activity import record
from dealroom.drive import room_state
from dealroom.models import Activity
from . import placement
from .models import NdaPolicy
from .storage import source_bytes
from .validation import digest, request_digest, validate_recipients

PLACEHOLDER = {'email': 'recipient@template.invalid', 'name': 'Recipient', 'company': ''}


class NdaNotPlaced(APIException):
    status_code = 409
    default_detail = {'detail': 'Place the NDA fields before sharing this room.',
                      'action': 'Place the NDA fields', 'code': 'nda_positions_required'}


def confirmed(policy):
    # Keep fields a native list for older preview processes sharing this database.
    # The existing audit JSON binds explicit confirmation to both source and geometry.
    return bool(policy and policy.fields and Activity.objects.filter(
        organization=policy.room.organization, room_id=str(policy.room_id), event_type='nda.positions_confirmed',
        data__revision=str(policy.revision), data__source_sha256=policy.source_sha256,
        data__fields_sha256=request_digest(policy.fields)).exists())


def require_share_ready(room):
    policy = NdaPolicy.objects.filter(room=room, enabled=True).first()
    if (policy or room_state(room).get('require_nda')) and not confirmed(policy):
        raise NdaNotPlaced()


def suggestions(pdf):
    analysis = placement.place(pdf, [PLACEHOLDER])
    fields = []
    if placement.PARSE_SLOTS.acquire(blocking=False):
        try:
            result = subprocess.run([sys.executable, '-m', 'dealroom_sign.placement_worker', '3'],
                input=b'{"template":true}\n' + pdf, capture_output=True, timeout=4,
                cwd=placement.WORKER_CWD, env=placement.WORKER_ENV)
            fields = json.loads(result.stdout).get('template_fields', []) if not result.returncode else []
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        finally:
            placement.PARSE_SLOTS.release()
    # Accept the existing engine's signature geometry only if it belongs to the
    # independently located blank recipient rule, never the discloser's block.
    if analysis['status'] == 'placed' and fields:
        for native in placement.to_native_fields(analysis, PLACEHOLDER['email']):
            for i, blank in enumerate(fields):
                if (native['type'] == blank['type'] and native['page'] == blank['page']
                    and abs(native['positionX'] - blank['positionX']) < 2
                    and abs(native['positionY'] + native['height'] - blank['positionY'] - blank['height']) < 1):
                    fields[i] = {k: v for k, v in native.items() if k != 'fieldMeta'}
    return fields


@transaction.atomic
def save_policy(room, actor, version, pdf, *, fields=None, confirm=False, revision=None, enabled=True):
    Dataroom.objects.select_for_update().get(pk=room.pk)
    previous = NdaPolicy.objects.select_for_update().filter(room=room).first()
    sha = digest(pdf)
    same_source = previous and previous.source_version_id == version.pk and previous.source_sha256 == sha
    if confirm:
        if not same_source or str(previous.revision) != str(revision):
            raise ValidationError('The NDA changed. Reload it and check the positions again.')
        fields = fields or []
        if len(fields) > 100 or any(f.get('type') not in {'SIGNATURE', 'NAME', 'TEXT', 'DATE', 'INITIALS'} for f in fields):
            raise ValidationError('Choose up to 100 Signature, Name, Company, Date or Initials fields.')
        validate_recipients([{**PLACEHOLDER, 'fields': fields}], pdf)
    else:
        # Selection never means confirmation; preserve an unchanged selection only.
        fields = previous.fields if same_source else []
        validate_recipients([PLACEHOLDER], pdf, automatic=True)
    rev = previous.revision if same_source and fields == previous.fields else uuid.uuid4()
    policy, _ = NdaPolicy.objects.update_or_create(room=room, defaults={
        'source_version': version, 'source_sha256': sha, 'fields': fields,
        'revision': rev, 'enabled': enabled})
    record('nda.policy_updated', organization=room.organization, actor=actor, room_id=room.pk,
        data={'revision': str(policy.revision), 'enabled': enabled})
    if confirm:
        record('nda.positions_confirmed', organization=room.organization, actor=actor, room_id=room.pk,
            data={'revision': str(policy.revision), 'source_sha256': sha, 'fields_sha256': request_digest(fields)})
    return policy


def recipient_fields(policy, member):
    if not confirmed(policy):
        raise NdaNotPlaced()
    fields = [dict(f) for f in policy.fields]
    # NAME is populated by Sign from recipient.name and remains editable.
    for field in fields:
        if field['type'] == 'TEXT':
            field['fieldMeta'] = {'type': 'text', 'text': member.recipient_org.name[:200] if member.recipient_org else '',
                                  'readOnly': False}
    return fields


def describe(policy, *, suggest=False):
    if not policy:
        return {'enabled': False, 'confirmed': False, 'fields': []}
    ready = confirmed(policy)
    return {'enabled': policy.enabled, 'confirmed': ready, 'revision': str(policy.revision),
        'source_version_id': str(policy.source_version_id), 'source_sha256': policy.source_sha256,
        'name': policy.source_version.document.name, 'fields': policy.fields,
        'suggestions': suggestions(source_bytes(policy.source_version)) if suggest and not ready else [],
        'pdf_url': f'/api/v1/dealroom/rooms/{policy.room_id}/entry-nda-source/?revision={policy.revision}'}
