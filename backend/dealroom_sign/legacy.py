"""One legacy board mapping for live workflow creation and operator imports."""
from rest_framework.exceptions import ValidationError

from .models import SignatureRequest
from .requests import board_config


def legacy_request(work, board_id, task_ref, *, creator=None, apply=True):
    """Validate even on dry runs; callers own the workflow/import transaction.

    The creator FK identifies a Send account. A shared legacy JWT does not verify
    the board login, and operator imports do not establish a board sign-in either.
    """
    cfg = board_config(board_id)
    credential = work.owner.signcredential
    creator = creator or work.owner
    if (not cfg or str(work.owner_id) not in cfg.get('owner_ids', [])
            or credential.team_id not in cfg.get('team_ids', [])
            or str(work.room_id) not in cfg.get('room_ids', []) or not credential.enabled
            or creator.organization_id != work.room.organization_id or work.purpose != 'room_document'):
        raise ValidationError('Invalid owner/team/room mapping for board request.')
    if task_ref is not None and (not isinstance(task_ref, dict) or set(task_ref) - {'id', 'title'}
            or not isinstance(task_ref.get('id'), str) or not task_ref['id']
            or ('title' in task_ref and not isinstance(task_ref['title'], str))):
        raise ValidationError('Invalid task reference.')
    # A live legacy send retains its shared Send owner even when an import later
    # names an individual operator. Importing must not relabel that creator.
    existing = SignatureRequest.objects.filter(workflow=work).first()
    if existing and (existing.board_id != board_id or existing.task_ref != task_ref
            or existing.creator_id not in {creator.pk, work.owner_id}):
        raise ValidationError('Existing request mapping conflict.')
    if not apply:
        return existing
    row, _ = SignatureRequest.objects.get_or_create(workflow=work, defaults={
        'board_id':board_id, 'creator':creator, 'title':work.title, 'kind':'unknown',
        'task_ref':task_ref, 'room':work.room, 'state':work.state,
        'source_context':{'identity':'legacy_reported', 'creator_login':None}})
    # Recheck the winner of a concurrent get_or_create before accepting a replay.
    if (row.board_id != board_id or row.task_ref != task_ref
            or row.creator_id not in {creator.pk, work.owner_id}):
        raise ValidationError('Existing request mapping conflict.')
    return row
