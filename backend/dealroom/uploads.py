import hashlib
from pathlib import Path
from django.db import transaction
from rest_framework.exceptions import ValidationError
from datarooms.models import DataroomDocument, DataroomFolder
from documents.fileserver import fileserver_client
from documents.tasks import generate_pdf_pages_task, convert_office_to_pdf_task
from documents.services import create_document_from_upload, generate_storage_key
from datarooms.services import get_or_create_dataroom_storage_folder
from pypdf import PdfReader
import zipfile
from sharelinks.models import ShareLinkDataroomSetting
from .activity import record

ALLOWED = {'.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}


def validate_upload(file):
    ext = Path(file.name).suffix.lower()
    if ext not in ALLOWED or file.size > 50 * 1024 * 1024:
        raise ValidationError('Supported PDF/DOCX/PPTX/XLSX up to 50 MiB required. Macros and video are disabled.')
    if ext == '.pdf':
        try:
            pages = len(PdfReader(file).pages)
            if pages > 500 or pages < 1:
                raise ValueError('page bound')
        except Exception as exc:
            raise ValidationError('A readable PDF with 1–500 pages is required.') from exc
    else:
        try:
            with zipfile.ZipFile(file) as package:
                if any('vbaProject' in n for n in package.namelist()) or sum(x.file_size for x in package.infolist()) > 200 * 1024 * 1024:
                    raise ValueError('macros or expanded-size bound')
        except Exception as exc:
            raise ValidationError('Unsafe Office package.') from exc
    file.seek(0)
    return pages if ext == '.pdf' else None


def queue_preview(version):
    task = generate_pdf_pages_task if Path(version.original_storage_key).suffix.lower() == '.pdf' else convert_office_to_pdf_task
    transaction.on_commit(lambda: task.delay(str(version.pk)))


def upload(room, actor, file, folder_id=None, *, entry_nda=False):
    if entry_nda and Path(file.name).suffix.lower() != '.pdf':
        raise ValidationError('Choose a PDF for the entry NDA.')
    pages = validate_upload(file)
    ext = Path(file.name).suffix.lower()
    folder = None
    if folder_id:
        folder = DataroomFolder.objects.filter(pk=folder_id, dataroom=room).first()
        if not folder:
            raise ValidationError('Folder is not in this room.')
    source_hash = hashlib.sha256()
    for chunk in file.chunks():
        source_hash.update(chunk)
    file.seek(0)
    key = generate_storage_key(room.organization_id, file.name)
    fileserver_client.upload_file(key, file, content_type=ALLOWED[ext])
    user = getattr(actor, 'user', actor)
    vault = get_or_create_dataroom_storage_folder(room, user)
    document = create_document_from_upload(user, vault, key, Path(file.name).name, file.size, ALLOWED[ext], track_user_quota=False)
    version = document.versions.get(is_primary=True)
    version.metadata = {**version.metadata, 'source_sha256': source_hash.hexdigest()}
    if entry_nda:
        version.metadata['entry_nda_room'] = str(room.pk)
    if pages:
        version.num_pages = pages
    version.save(update_fields=['metadata', 'num_pages'])
    if entry_nda:
        queue_preview(version)
        return version
    item = DataroomDocument.objects.create(dataroom=room, document=document, folder=folder, name=document.name, is_direct_upload=True)
    for link in room.share_links.filter(is_active=True):
        ShareLinkDataroomSetting.objects.update_or_create(share_link=link, dataroom_document=item, defaults={'enable_watermark':True, 'allow_download':False})
    queue_preview(version)
    record('document.uploaded', organization=room.organization, actor=actor, room_id=room.pk, target_id=document.pk, data={'source_sha256': source_hash.hexdigest(), 'version_id': str(version.pk)})
    item.upload_version_id = str(version.pk)
    item.upload_sha256 = source_hash.hexdigest()
    return item
