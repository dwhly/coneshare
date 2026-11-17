"""Read exported Drive snapshots through the ordinary cloud provider interface."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.utils.dateparse import parse_datetime

from .base import BaseCloudProvider, CloudProviderError
from .google_drive import GOOGLE_EXPORTS


FOLDER_MIME = 'application/vnd.google-apps.folder'


def folder_id(value):
    parsed = urlparse(value)
    match = re.fullmatch(r'/drive/(?:u/\d+/)?folders/([\w-]+)/?', parsed.path)
    if parsed.scheme != 'https' or parsed.hostname != 'drive.google.com' or not match:
        raise CloudProviderError('Paste a Google Drive folder link, one per line.')
    return match.group(1)


class DriveSnapshotProvider(BaseCloudProvider):
    PROVIDER_NAME = 'google_drive_snapshot'

    def __init__(self, root_id, snapshot_dir=None):
        super().__init__()
        directory = snapshot_dir if snapshot_dir is not None else settings.DEALROOM_DRIVE_SNAPSHOT_DIR
        if not directory:
            raise CloudProviderError('Drive snapshots are not configured on this server.')
        if not re.fullmatch(r'[\w-]+', root_id):
            raise CloudProviderError('Invalid folder ID.')
        base = Path(directory).resolve()
        self.directory = (base / root_id).resolve()
        if not self.directory.is_relative_to(base):
            raise CloudProviderError('Snapshot must be inside the configured directory.')
        try:
            manifest = self.directory / 'manifest.json'
            if not manifest.resolve().is_relative_to(self.directory) or manifest.stat().st_size > 5 * 1024 * 1024:
                raise ValueError('manifest bounds')
            data = json.loads(manifest.read_text())
            if data['root_id'] != root_id or len(data['nodes']) > 2000:
                raise ValueError('manifest root or size')
            self.root_id, self.root_name = root_id, data['root_name']
            self.taken_at = data['taken_at']
            if not isinstance(self.root_name, str) or not isinstance(self.taken_at, str):
                raise ValueError('root metadata')
            for node in data['nodes']:
                if any(not isinstance(node.get(k), str) or not node[k] for k in ('id', 'name', 'mimeType', 'modifiedTime')):
                    raise ValueError('node metadata')
                if not isinstance(node.get('parents'), list) or any(not isinstance(p, str) for p in node['parents']):
                    raise ValueError('node parents')
                if not parse_datetime(node['modifiedTime']):
                    raise ValueError('node timestamp')
                if node.get('path') is not None and not isinstance(node['path'], str):
                    raise ValueError('node path')
            self.nodes = {node['id']: node for node in data['nodes']}
            if len(self.nodes) != len(data['nodes']):
                raise ValueError('duplicate node IDs')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CloudProviderError('Snapshot unavailable or invalid for this folder.') from exc

    def list_files(self, path='/'):
        parent = self.root_id if path == '/' else path
        files = []
        for node in self.nodes.values():
            if parent not in node.get('parents', []) or node['id'] == parent:
                continue
            item = dict(node, type='folder' if node['mimeType'] == FOLDER_MIME else 'file',
                        path=node['id'], size=int(node.get('size') or 0))
            if item['type'] == 'file':
                exported = (self.directory / (node.get('path') or '')).resolve()
                if exported.is_relative_to(self.directory) and exported.is_file():
                    item['size'] = max(item['size'], exported.stat().st_size)
                else:
                    item['unavailable_reason'] = 'The exported copy is unavailable in this snapshot.'
            files.append(item)
        return files

    def download_file(self, file_id):
        node = self.nodes.get(file_id)
        if not node or not node.get('path') or node['mimeType'] == FOLDER_MIME:
            raise CloudProviderError('Exported file is unavailable.')
        path = (self.directory / node['path']).resolve()
        if not path.is_relative_to(self.directory) or not path.is_file():
            raise CloudProviderError('Exported file must be inside its snapshot directory.')
        mime, extension = GOOGLE_EXPORTS.get(node['mimeType'], (node['mimeType'], ''))
        if node.get('exportedMimeType') and node['exportedMimeType'] != mime:
            raise CloudProviderError('Snapshot export format does not match the Drive export mapping.')
        name = node['name']
        if extension and not name.lower().endswith(extension):
            name += extension
        return {'name': name, 'size': path.stat().st_size, 'content': path.open('rb'),
                'content_type': mime, 'modifiedTime': node['modifiedTime'],
                'webViewLink': node.get('webViewLink', ''), 'etag_or_rev': node['modifiedTime']}
