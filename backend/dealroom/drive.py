"""Small synchronous room importer. Storage and versions are the real product records.

Providers only need list_files(path) and download_file(id); no Google client is used here.
"""
import hashlib
import re
from pathlib import Path

from django.core import signing
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from cloudfiles.providers.base import CloudProviderError
from cloudfiles.providers.drive_snapshot import DriveSnapshotProvider, folder_id
from cloudfiles.providers.google_drive import GOOGLE_EXPORTS
from datarooms.models import Dataroom, DataroomFolder
from documents.fileserver import fileserver_client
from documents.services import create_new_document_version, generate_storage_key
from .activity import record
from .models import Activity
from .uploads import ALLOWED, upload, validate_upload, queue_preview

SERIES_A = [
    {'id': 'company', 'name': 'Company', 'slots': [('overview', 'Company overview', ['company overview'], 'pdf'), ('deck', 'Pitch deck', ['pitch deck'], 'pdf')]},
    {'id': 'financials', 'name': 'Financials', 'slots': [('model', 'Financial model', ['financial model'], 'sheet'), ('pnl', 'Monthly P&L', ['monthly p l', 'monthly pnl'], 'sheet')]},
    {'id': 'legal', 'name': 'Legal', 'slots': [('incorporation', 'Certificate of incorporation', ['certificate of incorporation'], 'pdf'), ('nda', 'Mutual NDA', ['mutual nda', 'non disclosure agreement'], 'pdf')]},
    {'id': 'ownership', 'name': 'Ownership & IP', 'slots': [('cap', 'Cap table', ['cap table'], 'sheet'), ('ip', 'IP assignment agreements', ['ip assignment'], 'pdf')]},
    {'id': 'customers', 'name': 'Customers', 'slots': [('customers', 'Customer list', ['customer list'], 'sheet')]},
    {'id': 'product', 'name': 'Product', 'slots': [('roadmap', 'Product roadmap', ['product roadmap'], 'pdf')]},
    {'id': 'security', 'name': 'Security', 'slots': [('security', 'Security overview', ['security overview'], 'pdf')]},
    {'id': 'team', 'name': 'Team', 'slots': [('team', 'Team bios', ['team bios', 'team biographies'], 'pdf')]},
]
SLOTS = {s[0]: {'id': s[0], 'name': s[1], 'aliases': s[2], 'type': s[3], 'folder': f['id']} for f in SERIES_A for s in f['slots']}


def room_state(room):
    event = Activity.objects.filter(room_id=str(room.pk), organization=room.organization,
                                    event_type='room.outline.saved').first()
    return event.data if event else {'template': '', 'note': '', 'start_here': [], 'slots': {}, 'not_needed': [], 'drive_roots': []}


def save_state(room, actor, data):
    record('room.outline.saved', organization=room.organization, actor=actor, room_id=room.pk, data=data)


def walk_tree(provider, root_id):
    nodes, seen = [], {root_id}

    def visit(parent, path, depth):
        if depth > 30:
            raise CloudProviderError('Folder tree exceeds 30 levels.')
        for item in sorted(provider.list_files(parent), key=lambda n: (n['type'] != 'folder', n['name'].casefold(), n['id'])):
            if item['id'] in seen:
                continue
            seen.add(item['id'])
            if len(seen) > 2000:
                raise CloudProviderError('Import up to 2,000 items at a time.')
            node = {**item, 'parent_id': parent, 'folder_path': path, 'root_id': root_id}
            nodes.append(node)
            if item['type'] == 'folder':
                visit(item['id'], '/'.join(filter(None, [path, item['name']])), depth + 1)
            elif not item.get('modifiedTime'):
                raise CloudProviderError('The provider must include modifiedTime for every file.')
    visit(root_id, '', 0)
    return nodes


def match_template(nodes):
    matched, unsure, occupied = [], [], set()
    for node in nodes:
        if node['type'] == 'folder':
            continue
        name = ' '.join(re.findall(r'[a-z0-9]+', node['name'].lower()))
        mime = node.get('mimeType', '')
        kind = 'sheet' if 'spreadsheet' in mime or node['name'].lower().endswith('.xlsx') else 'pdf' if mime in ('application/pdf', 'application/vnd.google-apps.document') else 'other'
        candidates = [s for s in SLOTS.values() if any(alias in name for alias in s['aliases'])]
        if len(candidates) == 1 and candidates[0]['type'] == kind and candidates[0]['id'] not in occupied:
            slot = candidates[0]['id']
            occupied.add(slot)
            matched.append({**node, 'slot': slot, 'reason': 'Name and file type match'})
        else:
            path = node.get('folder_path', '').lower()
            suggestions = candidates or [s for s in SLOTS.values() if s['folder'] in path and s['type'] == kind]
            unsure.append({**node, 'slot': '', 'suggestions': [s['id'] for s in suggestions],
                           'reason': 'Choose a slot or keep in its Drive folder'})
    return {'matched': matched, 'unsure': unsure, 'missing': [s for k, s in SLOTS.items() if k not in occupied]}


def import_details(node):
    """Describe the actual export and flag files the room upload path cannot accept."""
    mime = node.get('mimeType', '')
    _, extension = GOOGLE_EXPORTS.get(mime, (mime, ''))
    name = node['name']
    if extension and not name.lower().endswith(extension):
        name += extension
    extension = Path(name).suffix.lower()
    labels = {'.pdf': 'PDF', '.docx': 'Word document', '.xlsx': 'Excel file', '.pptx': 'PowerPoint file'}
    workspace = {'application/vnd.google-apps.document': 'Google Doc',
                 'application/vnd.google-apps.spreadsheet': 'Google Sheet',
                 'application/vnd.google-apps.presentation': 'Google Slides'}
    label = labels.get(extension, extension.lstrip('.').upper() or 'File')
    reason = ''
    if mime == 'application/vnd.google-apps.shortcut':
        reason = 'Drive shortcuts cannot be imported. Add the original file instead.'
    elif mime == 'application/vnd.google-apps.form':
        reason = 'Google Forms cannot be imported.'
    elif mime.startswith('application/vnd.google-apps.') and mime not in GOOGLE_EXPORTS:
        reason = 'This Google file type cannot be imported.'
    elif extension not in ALLOWED:
        reason = 'Supported files are PDF, Word (.docx), Excel (.xlsx) and PowerPoint (.pptx).'
    elif int(node.get('size') or 0) > 50 * 1024 * 1024:
        reason = 'This file exceeds the 50 MiB limit.'
    elif node.get('unavailable_reason'):
        reason = node['unavailable_reason']
    if mime in workspace:
        article = 'an' if extension == '.xlsx' else 'a'
        description = f'{workspace[mime]}, saved as {article} {label} copy'
    else:
        description = f'{label}, added as is'
    return {**node, 'final_name': name, 'final_type': extension.lstrip('.'),
            'import_description': description, 'skip_reason': reason}


def review(links, template='', existing_ids=None):
    if not isinstance(links, list) or not 1 <= len(links) <= 10 or any(not isinstance(link, str) for link in links) or template not in ('', 'series_a'):
        raise ValidationError('Provide 1–10 folder links and an optional Series A template.')
    roots, nodes, skipped, seen = [], [], [], set()
    existing_ids = set(existing_ids or ())
    for link in links:
        root = folder_id(link)
        if root in {r['id'] for r in roots}:
            continue
        provider = DriveSnapshotProvider(root)
        roots.append({'id': root, 'name': provider.root_name})
        for node in walk_tree(provider, root):
            if node['id'] not in seen:
                seen.add(node['id'])
                node = import_details(node) if node['type'] == 'file' else node
                if node['type'] == 'file' and node['id'] in existing_ids:
                    node['skip_reason'] = 'Already in this room. Use Check Drive for updates to publish a new version.'
                (skipped if node.get('skip_reason') else nodes).append(node)
    payload = {'roots': roots, 'nodes': nodes, 'template': template, 'skipped': skipped}
    # The client may choose slots, but cannot rewrite source IDs, paths, or timestamps.
    return {**payload, **(match_template(nodes) if template else {'matched': [], 'unsure': [], 'missing': []}),
            'ticket': signing.dumps(payload, salt='drive-review', compress=True)}


def source_metadata(provider, node):
    return {'provider': provider.PROVIDER_NAME, 'root_id': node['root_id'], 'id': node['id'],
            'webViewLink': node.get('webViewLink', ''), 'modifiedTime': node['modifiedTime'],
            'folder_path': node['folder_path'], 'published_at': timezone.now().isoformat()}


def ensure_template(room, actor, state):
    folders = {}
    ids = state.setdefault('template_folders', {})
    for index, group in enumerate(SERIES_A, 1):
        folder = room.folders.filter(pk=ids.get(group['id'])).first() if ids.get(group['id']) else None
        if not folder:
            folder = DataroomFolder.objects.create(dataroom=room, parent=None,
                name=f'{index:02d} {group["name"]}', created_by=actor)
            ids[group['id']] = str(folder.pk)
        folders[group['id']] = folder
    state['template'] = 'series_a'
    state.setdefault('require_nda', True)
    return folders


@transaction.atomic
def import_tree(room, actor, providers, nodes, template='', choices=None, excluded=None, destinations=None):
    Dataroom.objects.select_for_update().get(pk=room.pk)
    state = room_state(room)
    choices = {} if choices is None else choices
    excluded = [] if excluded is None else excluded
    destinations = {} if destinations is None else destinations
    file_ids = {n['id'] for n in nodes if n['type'] == 'file'}
    folder_ids = {n['id'] for n in nodes if n['type'] == 'folder'} | set(providers)
    if not isinstance(excluded, list) or any(not isinstance(id, str) or id not in file_ids for id in excluded):
        raise ValidationError('Exclude only files from this review.')
    if not isinstance(destinations, dict) or any(id not in file_ids or not isinstance(folder, str) or folder not in folder_ids
                                               for id, folder in destinations.items()):
        raise ValidationError('Move only reviewed files to reviewed folders.')
    if not isinstance(choices, dict):
        raise ValidationError('File placements must be an object keyed by file ID.')
    if set(choices) - file_ids or any(not isinstance(v, str) or (v and v not in SLOTS) for v in choices.values()):
        raise ValidationError('Choose valid file IDs and template slots.')
    assigned = [v for id, v in choices.items() if v and id not in excluded]
    if len(assigned) != len(set(assigned)):
        raise ValidationError('Each template slot holds one file. Resolve duplicate choices.')
    folders = ensure_template(room, actor, state) if template else {}
    # Persist provider IDs separately from names: two folders may have the same name.
    folder_ids = state.setdefault('drive_folders', {})
    drive_folders = {key: folder for key, id in folder_ids.items()
                     if (folder := room.folders.filter(pk=id).first())}
    if len(providers) > 1:
        for root, provider in providers.items():
            if root not in drive_folders:
                folder = DataroomFolder.objects.create(dataroom=room, name=getattr(provider, 'root_name', root), created_by=actor)
                drive_folders[root], folder_ids[root] = folder, str(folder.pk)
    imported = []
    existing = {v.metadata.get('drive_source', {}).get('id') for item in room.documents.all()
                for v in item.document.versions.filter(is_primary=True)}
    for node in nodes:
        if node['type'] == 'folder':
            if node['id'] not in drive_folders:
                folder = DataroomFolder.objects.create(dataroom=room, name=node['name'], parent=drive_folders.get(node['parent_id']), created_by=actor)
                drive_folders[node['id']], folder_ids[node['id']] = folder, str(folder.pk)
    # All destination folders must exist before importing a moved file, including later siblings.
    for node in nodes:
        if node['type'] == 'folder' or node['id'] in excluded or node['id'] in existing:
            continue
        if import_details(node)['skip_reason']:
            continue
        slot = choices.get(node['id'], '') if template else ''
        if slot and slot in state['slots']:
            raise ValidationError('A selected slot already has a file.')
        provider = providers[node['root_id']]
        data = provider.download_file(node['id'])
        try:
            if data.get('modifiedTime') != node['modifiedTime']:
                raise ValidationError('Drive changed after review. Check the folder again.')
            file = UploadedFile(data['content'], name=data['name'], size=data['size'], content_type=data.get('content_type'))
            folder = folders[SLOTS[slot]['folder']] if slot else drive_folders.get(destinations.get(node['id'], node['parent_id']))
            item = upload(room, actor, file, str(folder.pk) if folder else None)
            version = item.document.versions.get(is_primary=True)
            version.metadata = {**version.metadata, 'drive_source': source_metadata(provider, node)}
            version.save(update_fields=['metadata'])
            if slot:
                state['slots'][slot] = str(item.pk)
            imported.append(str(item.pk))
        finally:
            data['content'].close()
    state['drive_roots'] = list(dict.fromkeys(state['drive_roots'] + list(providers)))
    save_state(room, actor, state)
    return imported


def check_updates(room, providers):
    current = {n['id']: n for root, provider in providers.items() for n in walk_tree(provider, root) if n['type'] == 'file'}
    updates = []
    for item in room.documents.select_related('document'):
        version = item.document.versions.filter(is_primary=True).first()
        source = version.metadata.get('drive_source') if version else None
        if not source or source['id'] not in current:
            continue
        node = current[source['id']]
        if source['modifiedTime'] != node['modifiedTime']:
            updates.append({**node, 'item_id': str(item.pk), 'version_id': str(version.pk),
                            'previous_modifiedTime': source['modifiedTime']})
    return updates


@transaction.atomic
def publish_update(room, actor, provider, update):
    Dataroom.objects.select_for_update().get(pk=room.pk)
    item = room.documents.select_related('document').get(pk=update['item_id'])
    version = item.document.versions.get(is_primary=True)
    if str(version.pk) != update['version_id']:
        raise ValidationError('This document was already updated. Check Drive again.')
    data = provider.download_file(update['id'])
    key = None
    try:
        if data.get('modifiedTime') != update['modifiedTime']:
            raise ValidationError('Drive changed again. Check for updates before publishing.')
        # Reuse the same file validation as room uploads before replacing the primary.
        file = UploadedFile(data['content'], name=data['name'], size=data['size'])
        pages = validate_upload(file)
        mime = ALLOWED[Path(file.name).suffix.lower()]
        key = generate_storage_key(room.organization_id, file.name)
        fileserver_client.upload_file(key, file, content_type=mime)
        file.seek(0)
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
        new = create_new_document_version(item.document, actor, key, data['size'], mime)
        new.metadata = {'drive_source': source_metadata(provider, update), 'source_sha256': digest}
        if pages:
            new.num_pages = pages
        new.save(update_fields=['metadata', 'num_pages'])
        queue_preview(new)
        record('document.version_published', organization=room.organization, actor=actor, room_id=room.pk,
               target_id=item.pk, data={'version_id': str(new.pk)})
        return new
    except Exception:
        if key:
            fileserver_client.delete_file(key)
        raise
    finally:
        data['content'].close()
