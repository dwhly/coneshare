import hashlib
from pathlib import Path
import zipfile
from pypdf import PdfReader
from datarooms.services import get_or_create_dataroom_storage_folder
from django.db import transaction
from rest_framework.exceptions import ValidationError
from datarooms.models import DataroomDocument, DataroomFolder
from documents.fileserver import fileserver_client
from documents.services import create_document_from_upload, generate_storage_key
from documents.renderers import get_renderer
from sharelinks.models import ShareLinkDataroomSetting
from .activity import record

ALLOWED = {'.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}


def upload(room, actor, file, folder_id=None, *, storage_key=None, visible=True):
    ext = Path(file.name).suffix.lower()
    if ext == '.doc':
        raise ValidationError('Please save as .docx.')
    if ext not in ALLOWED or file.size > 50 * 1024 * 1024:
        raise ValidationError('Supported PDF/DOCX/PPTX/XLSX up to 50 MiB required. Macros and video are disabled.')
    folder = None
    if folder_id:
        folder = DataroomFolder.objects.filter(pk=folder_id, dataroom=room).first()
        if not folder:
            raise ValidationError('Folder is not in this room.')
    if ext == '.pdf':
        try:
            reader = PdfReader(file)
            if reader.is_encrypted:
                raise ValueError('encrypted PDF')
            pages = len(reader.pages)
            if pages > 500 or pages < 1:
                raise ValueError('page bound')
        except Exception as exc:
            raise ValidationError('A readable PDF with 1–500 pages is required.') from exc
    else:
        try:
            with zipfile.ZipFile(file) as package:
                if (len(package.infolist()) > 2000 or any('vbaproject' in n.lower() for n in package.namelist())
                        or any(x.flag_bits & 1 for x in package.infolist())
                        or sum(x.file_size for x in package.infolist()) > 200 * 1024 * 1024
                        or {'.docx':'word/document.xml', '.pptx':'ppt/presentation.xml', '.xlsx':'xl/workbook.xml'}[ext] not in package.namelist()):
                    raise ValueError('macros or expanded-size bound')
        except Exception as exc:
            raise ValidationError('Unsafe Office package.') from exc
    file.seek(0)
    source_hash = hashlib.sha256()
    for chunk in file.chunks():
        source_hash.update(chunk)
    file.seek(0)
    key = storage_key or generate_storage_key(room.organization_id, file.name)
    fileserver_client.upload_file(key, file, content_type=ALLOWED[ext])
    user = getattr(actor, 'user', actor)
    vault = get_or_create_dataroom_storage_folder(room, user)
    document = create_document_from_upload(user, vault, key, Path(file.name).name, file.size, ALLOWED[ext], track_user_quota=False)
    version = document.versions.get(is_primary=True)
    version.metadata = {**version.metadata, 'source_sha256': source_hash.hexdigest()}
    version.save(update_fields=['metadata'])
    item = DataroomDocument.objects.create(dataroom=room, document=document, folder=folder, name=Path(file.name).name, is_direct_upload=True)
    for link in room.share_links.all():
        ShareLinkDataroomSetting.objects.update_or_create(share_link=link, dataroom_document=item, defaults={'enable_watermark':True, 'allow_download':False, 'is_visible': visible})
    transaction.on_commit(lambda: get_renderer(version).enqueue_render_task(version), robust=True)
    record('document.uploaded', organization=room.organization, actor=actor, room_id=room.pk, target_id=document.pk, data={'source_sha256': source_hash.hexdigest(), 'version_id': str(version.pk)})
    item.upload_version_id = str(version.pk)
    item.upload_sha256 = source_hash.hexdigest()
    return item
