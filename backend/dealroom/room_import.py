"""Manifest-derived effects. Caller data can never replace an approved manifest."""
import re
import uuid
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from datarooms.models import Dataroom, DataroomFolder, DataroomItemOrder, DataroomDocument
from documents.models import DocumentVersion
from dealroom_sign.models import NdaPolicy
from documents.renderers import get_renderer
from sharelinks.models import ShareLink, ShareLinkDataroomSetting
from .activity import record as activity
from .models import BoardRoom, RoomPolicy, RoomCommandReceipt
from .room_commands import Conflict, digest, fields, record
from .uploads import upload as store_upload

COMMON = {'approval_key', 'import_id', 'idempotency_key'}


def validate_manifest(value, checksum):
    fields(value, {'name', 'items', 'nda', 'access', 'intended_emails'})
    if digest(value) != checksum:
        raise Conflict('Approved manifest checksum differs.')
    serializers.CharField(max_length=255).run_validation(value['name'])
    nda = value['nda']
    if not isinstance(nda, dict) or set(nda)-{'enabled', 'source', 'fields', 'revision'} or type(nda.get('enabled')) is not bool:
        raise ValidationError('Invalid NDA approval.')
    access = value['access']
    fields(access, {'download_ceiling', 'expires_at'})
    if access['download_ceiling'] not in ('none', 'watermarked'):
        raise ValidationError('Invalid download ceiling.')
    if access['expires_at'] is not None:
        serializers.DateTimeField().run_validation(access['expires_at'])
    if not isinstance(value['intended_emails'], list) or len(value['intended_emails']) > 200:
        raise ValidationError('Invalid people approval.')
    for email in value['intended_emails']:
        serializers.EmailField().run_validation(email)
    items = value['items']
    if not isinstance(items, list) or len(items) > 2000:
        raise ValidationError('At most 2000 manifest items are allowed.')
    seen = {}; positions = set()
    for item in items:
        fields(item, {'client_item_id', 'kind', 'name', 'parent_id', 'position', 'sha256', 'purpose'},
               {'client_item_id', 'kind', 'name', 'parent_id', 'position'})
        iid = item['client_item_id']
        if not isinstance(iid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', iid) or iid in seen:
            raise ValidationError('Invalid or duplicate manifest item.')
        if item['kind'] not in ('folder', 'file') or type(item['position']) is not int or item['position'] < 0:
            raise ValidationError('Invalid kind/order.')
        serializers.CharField(max_length=255).run_validation(item['name'])
        if item['kind'] == 'folder' and item['name'].casefold() == 'executed':
            raise ValidationError('Reserved folder name; resolve before import.')
        parent = item['parent_id']
        if parent is not None and (not isinstance(parent, str) or parent not in seen or seen[parent]['kind'] != 'folder'):
            raise ValidationError('Manifest must be parent-first and acyclic.')
        position = (parent, item['position'])
        if position in positions:
            raise ValidationError('Duplicate sibling order.')
        positions.add(position)
        if item['kind'] == 'file':
            if not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', ''))) or item.get('purpose') not in ('document', 'nda'):
                raise ValidationError('File checksum and purpose required.')
            if item['name'].lower().endswith('.doc'):
                raise ValidationError('Please save as .docx.')
        seen[iid] = item
    return value


def start(request, operation, payload, room, row):
    required = {'approved_manifest', 'manifest_sha256', 'idempotency_key'}
    required |= {'name', 'board_draft_id', 'draft_revision'} if operation == 'create' else {'expected_revision'}
    fields(payload, required)
    manifest = validate_manifest(payload['approved_manifest'], payload['manifest_sha256'])
    import_id = str(uuid.uuid4())
    if operation == 'create':
        if payload['name'] != manifest['name'] or type(payload['draft_revision']) is not int or payload['draft_revision'] < 1:
            raise Conflict()
        serializers.CharField(max_length=100).run_validation(payload['board_draft_id'])
        if BoardRoom.objects.filter(board_id=request.board_binding.board_id, draft_id=payload['board_draft_id']).exists():
            raise Conflict('Draft already has a room.')
        # A creation tombstone also protects a retry under a different command key.
        if RoomCommandReceipt.objects.filter(board_id=request.board_binding.board_id, operation='create',
                result__draft_id=payload['board_draft_id']).exists():
            raise Conflict('Draft already has a retained creation receipt.')
        room = Dataroom.objects.create(organization=request.user.organization, created_by=request.user,
                                     name=manifest['name'], enable_qna=False)
        link = ShareLink.objects.create(dataroom=room, created_by=request.user, name='Room entry',
            restrict_to_grants=True, requires_email=True, requires_email_verification=True, enable_watermark=True, enable_qna=False)
        RoomPolicy.objects.create(room=room, entry_link=link)
        row = BoardRoom.objects.create(board_id=request.board_binding.board_id, room=room,
            creator_binding=request.board_binding, draft_id=payload['board_draft_id'],
            manifest_sha256=payload['manifest_sha256'], staged_import=import_id)
    else:
        if row.build_state != 'ready' or row.staged_import or type(payload['expected_revision']) is not int or row.revision != payload['expected_revision']:
            raise Conflict()
        # S2 batches cannot change access/NDA policy on an existing room.
        if NdaPolicy.objects.filter(room=room, enabled=True).exists() or room.share_links.filter(require_nda=True).exists():
            raise Conflict('NDA comes next; this import is not available yet.')
        if not RoomPolicy.objects.filter(room=room).exists():
            raise Conflict('Room policy is not configured.')
        original = RoomCommandReceipt.objects.filter(room=room, operation='create').first()
        if manifest['nda']['enabled'] or (original and manifest['access'] != original.approved_manifest['access']):
            raise Conflict('Review existing access; NDA comes next.')
        row.staged_import = import_id
        row.revision += 1
        row.save(update_fields=['staged_import', 'revision'])
    result = {'id': str(room.pk), 'draft_id': row.draft_id, 'approval_key': payload['idempotency_key'],
              'import_id': import_id, 'revision': row.revision, 'build_state': row.build_state}
    record(request, operation, payload, room, result, manifest=manifest)
    activity('room.created' if operation == 'create' else 'room.import.started', organization=room.organization,
             actor=request.user, room_id=room.pk)
    return result


def expected_item(payload, approved, kind):
    item = next((i for i in approved.approved_manifest['items'] if i['client_item_id'] == payload.get('client_item_id')), None)
    if not item or item['kind'] != kind:
        raise Conflict('Item is outside the approved manifest.')
    if RoomCommandReceipt.objects.filter(board_id=approved.board_id, import_id=approved.import_id,
            operation='folders' if kind == 'folder' else 'upload', client_item_id=item['client_item_id']).exists():
        raise Conflict('Item already has a receipt; retry its original key.')
    parent = None
    if item['parent_id']:
        step = RoomCommandReceipt.objects.filter(board_id=approved.board_id, import_id=approved.import_id,
            operation='folders', client_item_id=item['parent_id']).first()
        if not step:
            raise Conflict('Parent folder has not completed.')
        parent = step.result['id']
    provided_parent = payload.get('parent_id' if kind == 'folder' else 'folder_id')
    if provided_parent != parent or payload.get('position') != item['position']:
        raise Conflict('Item parent/order differs from approval.')
    return item, parent


def step_result(row, approved):
    row.revision += 1
    row.save(update_fields=['revision'])
    return {'import_id': approved.import_id, 'revision': row.revision}


def folder(request, payload, room, row, approved, file):
    fields(payload, COMMON | {'name', 'parent_id', 'position', 'client_item_id'})
    item, parent = expected_item(payload, approved, 'folder')
    if payload['name'] != item['name']:
        raise Conflict('Folder name differs from approval.')
    obj = DataroomFolder.objects.create(dataroom=room, name=item['name'], parent_id=parent, created_by=request.user)
    DataroomItemOrder.objects.create(dataroom=room, item_type='folder', folder=obj, parent_folder_id=parent, position=item['position'])
    for link in room.share_links.all():
        ShareLinkDataroomSetting.objects.update_or_create(share_link=link, dataroom_folder=obj,
            defaults={'is_visible': False, 'enable_watermark': True, 'allow_download': False})
    result = {**step_result(row, approved), 'id': str(obj.pk), 'name': obj.name}
    record(request, 'folders', payload, room, result, approval=approved)
    return result


def upload(request, payload, room, row, approved, file):
    fields(payload, COMMON | {'folder_id', 'position', 'client_item_id', 'source_sha256', 'purpose', 'file_sha256', 'filename'})
    item, parent = expected_item(payload, approved, 'file')
    if (not file or payload['file_sha256'] != item['sha256'] or payload['source_sha256'] != item['sha256']
            or payload['purpose'] != item['purpose'] or payload['filename'] != item['name']):
        raise Conflict('Uploaded bytes/name/purpose differ from approval.')
    storage_key = f"{room.organization_id}/board-import/{room.pk}/{digest([row.board_id, payload['idempotency_key']])}/{item['sha256']}"
    obj = store_upload(room, request.user, file, parent, storage_key=storage_key, visible=False)
    version = DocumentVersion.objects.get(pk=obj.upload_version_id)
    version.metadata = {**version.metadata, 'board_import_purpose': item['purpose']}
    version.save(update_fields=['metadata'])
    DataroomItemOrder.objects.create(dataroom=room, item_type='document', dataroom_document=obj,
                                    parent_folder_id=parent, position=item['position'])
    result = {**step_result(row, approved), 'id': str(obj.pk), 'document_id': str(obj.document_id),
              'version_id': obj.upload_version_id, 'sha256': obj.upload_sha256, 'status': 'processing'}
    record(request, 'upload', payload, room, result, approval=approved)
    return result


def complete(request, payload, room, row, approved, file):
    fields(payload, COMMON | {'expected_revision', 'manifest_sha256', 'items', 'nda_revision', 'access'})
    manifest = approved.approved_manifest
    if type(payload['expected_revision']) is not int or row.revision != payload['expected_revision'] or payload['manifest_sha256'] != digest(manifest):
        raise Conflict()
    if (manifest['nda']['enabled'] or payload['nda_revision'] is not None
            or NdaPolicy.objects.filter(room=room, enabled=True).exists() or room.share_links.filter(require_nda=True).exists()):
        raise Conflict('NDA comes next; this room remains private and incomplete.')
    if payload['access'] != manifest['access']:
        raise Conflict('Access differs from approval.')
    steps = {r.client_item_id: r for r in RoomCommandReceipt.objects.filter(
        board_id=row.board_id, import_id=approved.import_id, operation__in=['folders', 'upload'])}
    expected_files = []; item_ids = []; folder_ids = []
    for item in manifest['items']:
        step = steps.get(item['client_item_id'])
        if not step:
            raise Conflict('Import is incomplete.')
        result = step.result
        if item['kind'] == 'folder':
            obj = DataroomFolder.objects.filter(pk=result['id'], dataroom=room, name=item['name']).first()
            order = DataroomItemOrder.objects.filter(dataroom=room, folder=obj).first() if obj else None
            folder_ids.append(result['id'])
        else:
            obj = DataroomDocument.objects.select_related('document').filter(pk=result['id'], dataroom=room).first()
            version = DocumentVersion.objects.filter(pk=result['version_id'], document_id=result['document_id'], is_primary=True).first()
            if (not obj or obj.document_id != (version.document_id if version else None) or obj.document.deleted_at
                    or version.metadata.get('source_sha256') != item['sha256'] or result['sha256'] != item['sha256']):
                raise Conflict('Document version or checksum changed.')
            if get_renderer(version).get_effective_render_status(version) != DocumentVersion.RENDER_READY:
                raise Conflict('Previews are still processing or need attention.')
            if not 1 <= (version.num_pages or version.pages.count()) <= 500:
                raise Conflict('A preview with 1–500 pages is required.')
            expected_files.append({'client_item_id': item['client_item_id'], 'version_id': result['version_id'], 'sha256': result['sha256']})
            order = DataroomItemOrder.objects.filter(dataroom=room, dataroom_document=obj).first()
            if item['purpose'] == 'document':
                item_ids.append(result['id'])
        parent = steps[item['parent_id']].result['id'] if item['parent_id'] else None
        actual_parent = str(obj.parent_id if item['kind'] == 'folder' else obj.folder_id) if obj else None
        if not obj or actual_parent != (parent or 'None') or not order or order.position != item['position'] or str(order.parent_folder_id) != (parent or 'None'):
            raise Conflict('Tree changed since approval.')
    if payload['items'] != expected_files:
        raise Conflict('Completion items differ from approval.')
    for link in room.share_links.all():
        link.enable_watermark = True
        link.save(update_fields=['enable_watermark'])
        ShareLinkDataroomSetting.objects.filter(share_link=link, dataroom_document_id__in=item_ids).update(
            is_visible=True, enable_watermark=True, allow_download=manifest['access']['download_ceiling']=='watermarked',
            download_ceiling=manifest['access']['download_ceiling'])
        ShareLinkDataroomSetting.objects.filter(share_link=link, dataroom_folder_id__in=folder_ids).update(is_visible=True)
    if approved.operation == 'create':
        expiry = manifest['access']['expires_at']
        RoomPolicy.objects.filter(room=room).update(expires_at=serializers.DateTimeField().run_validation(expiry) if expiry else None)
    row.build_state = 'ready'; row.staged_import = ''; row.revision += 1
    row.save(update_fields=['build_state', 'staged_import', 'revision'])
    result = {'id': str(room.pk), 'import_id': approved.import_id, 'revision': row.revision, 'build_state': 'ready'}
    record(request, 'complete', payload, room, result, approval=approved)
    return result
