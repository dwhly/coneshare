"""Small transactional command boundary. Receipts and effects share a transaction."""
import hashlib
import json
import re

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from datarooms.models import Dataroom
from dealroom_sign.models import BoardStaffBinding
from .models import BoardRoom, RoomCommandReceipt


class Conflict(APIException):
    status_code = 409
    default_detail = 'Changed since review; review changes.'


class Gone(APIException):
    status_code = 410
    default_detail = 'This room was deleted; the command cannot be repeated.'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def fields(data, allowed, required=None):
    if not isinstance(data, dict) or set(data) - set(allowed) or set(required or allowed) - set(data):
        raise ValidationError('Invalid command fields.')


def command_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}', value):
        raise ValidationError('Invalid command key.')
    return value


def receipt(request, operation, payload):
    key = command_key(payload.get('idempotency_key'))
    old = RoomCommandReceipt.objects.filter(board_id=request.board_binding.board_id, command_key=key).first()
    if old:
        if old.room_id is not None:
            get_object_or_404(BoardRoom, room_id=old.room_id, board_id=request.board_binding.board_id,
                              room__organization_id=request.user.organization_id)
        if (old.actor != request.board_context['login'] or old.via != request.board_context['via']
                or old.operation != operation or old.payload_sha256 != digest(payload)):
            raise Conflict('Command key has different inputs.')
        if old.room_id is None:
            raise Gone()
    return old


def record(request, operation, payload, room, result, *, manifest=None, approval=None):
    return RoomCommandReceipt.objects.create(board_id=request.board_binding.board_id,
        command_key=payload['idempotency_key'], actor=request.board_context['login'], via=request.board_context['via'],
        operation=operation, payload_sha256=digest(payload), approved_manifest=manifest, result=result, room=room,
        approval_key=approval.command_key if approval else '', import_id=result['import_id'],
        client_item_id=payload.get('client_item_id', ''))


def locked_room(request, pk):
    # All continuation and legacy paths acquire this lock before reading any receipt.
    room = get_object_or_404(Dataroom.objects.select_for_update(), pk=pk,
                            organization=request.user.organization)
    row = get_object_or_404(BoardRoom, room=room, board_id=request.board_binding.board_id)
    return room, row


def approval(request, room, row, payload):
    old = RoomCommandReceipt.objects.filter(board_id=row.board_id, room=room,
        command_key=payload.get('approval_key'), operation__in=['create', 'imports']).first()
    if (not old or old.actor != request.board_context['login'] or old.via != request.board_context['via']
            or old.import_id != payload.get('import_id')):
        raise Conflict('A matching human approval receipt is required.')
    return old


def active(row, approved):
    if row.staged_import != approved.import_id:
        raise Conflict('This import is no longer staged.')


def execute(request, operation, pk=None):
    from .room_import import start, folder, upload, complete
    payload = dict(request.data.items())
    file = request.FILES.get('file')
    if file:
        payload.pop('file', None)
        payload['file_sha256'] = hashlib.sha256(b''.join(file.chunks())).hexdigest()
        payload['filename'] = file.name
        file.seek(0)
        for name in ('position',):
            try:
                payload[name] = int(payload[name])
            except (ValueError, KeyError, TypeError):
                raise ValidationError('Invalid position.') from None
        if payload.get('folder_id') == '':
            payload['folder_id'] = None
    status = 200 if operation == 'complete' else 201
    with transaction.atomic():
        if operation == 'create':
            # Serialize the normal same-binding double click; unique constraints cover other bindings.
            get_object_or_404(BoardStaffBinding.objects.select_for_update(), pk=request.board_binding.pk)
            room = row = None
        else:
            room, row = locked_room(request, pk)
        fresh = BoardStaffBinding.objects.select_related('send_user').filter(pk=request.board_binding.pk, enabled=True).first()
        if (not fresh or fresh.send_user_id != request.user.pk or not fresh.send_user.is_active
                or not fresh.send_user.is_staff or fresh.send_user.organization_id != request.user.organization_id
                or fresh.role not in {'writer', 'manager'} or 'write' not in fresh.room_capabilities):
            raise PermissionDenied('Your Dealroom access changed.')
        request.board_binding = fresh
        old = receipt(request, operation, payload)
        if old:
            if room and old.room_id != room.pk:
                raise Conflict('Command belongs to another room.')
            return Response(old.result, status=status)
        try:
            with transaction.atomic():
                if operation in ('create', 'imports'):
                    result = start(request, operation, payload, room, row)
                else:
                    approved = approval(request, room, row, payload)
                    active(row, approved)
                    result = {'folders': folder, 'upload': upload, 'complete': complete}[operation](
                        request, payload, room, row, approved, file)
                return Response(result, status=status)
        except IntegrityError:
            old = receipt(request, operation, payload)
            if old:
                return Response(old.result, status=status)
            raise Conflict('Command is in progress; retry the same key.') from None
