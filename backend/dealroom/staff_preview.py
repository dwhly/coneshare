"""Identified staff preview issuance, independent of recipient sessions and copies."""
import hashlib
import uuid
from io import BytesIO

import requests
from django.utils import timezone
from PIL import Image

from documents.fileserver import fileserver_client
from sharelinks.views import _apply_watermark_to_image
from .activity import record

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


def issue_staff_preview(binding, room, item, version, page, storage_key):
    """Return only stamped PNG bytes. The caller holds the render semaphore."""
    copy_id = 'preview-' + uuid.uuid4().hex
    identity = {
        'copy_id': copy_id, 'email': binding.login,
        'name': binding.send_user.get_full_name() or binding.login,
        'organisation': binding.send_user.organization.name,
        'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M UTC'),
    }
    url = fileserver_client.generate_download_url(storage_key, is_internal=True)
    with requests.get(url, stream=True, timeout=(5, 30), allow_redirects=False) as upstream:
        if upstream.status_code != 200:
            raise ValueError('Preview fetch failed.')
        if int(upstream.headers.get('Content-Length', 0)) > MAX_IMAGE_BYTES:
            raise ValueError('Preview is too large.')
        buffer = BytesIO()
        for chunk in upstream.iter_content(chunk_size=65536):
            if buffer.tell() + len(chunk) > MAX_IMAGE_BYTES:
                raise ValueError('Preview is too large.')
            buffer.write(chunk)
    buffer.seek(0)
    with Image.open(buffer) as source:
        if source.width * source.height > MAX_IMAGE_PIXELS:
            raise ValueError('Preview is too large.')
        with source.convert('RGBA') as image:
            # This existing primitive also draws the structured identity / Copy ID footer.
            with _apply_watermark_to_image(image, f'{binding.login} · Preview Copy {copy_id}', identity=identity) as stamped:
                output = BytesIO()
                stamped.save(output, format='PNG')
                content = output.getvalue()
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError('Preview is too large.')
    record('board.preview.issued', organization=room.organization, actor=binding.send_user,
           room_id=room.pk, target_id=item.document_id,
           data={'binding_id': str(binding.pk), 'board_id': binding.board_id,
                 'copy_id': copy_id, 'item_id': str(item.pk), 'version_id': str(version.pk),
                 'page': page, 'artifact_sha256': hashlib.sha256(content).hexdigest()})
    return content, copy_id
