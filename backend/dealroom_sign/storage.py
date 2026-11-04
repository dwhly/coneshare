"""Immutable core storage staging, then atomic local manifest/version publication."""
import io
import logging
import subprocess
import tempfile
from datetime import timedelta

import httpx
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from pypdf import PdfReader

from datarooms.models import DataroomDocument, DataroomFolder
from documents.fileserver import fileserver_client
from documents.models import Document, DocumentVersion, Folder

from .client import SignError
from .models import ExecutedArtifact
from .validation import digest


def source_bytes(version):
    if version.content_type != 'application/pdf':
        raise SignError('source_must_be_pdf')
    url = fileserver_client.generate_download_url(version.original_storage_key)
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    if not response.content.startswith(b'%PDF-') or len(response.content) > 50 * 1024 * 1024:
        raise SignError('invalid_source_pdf')
    return response.content


def verify_seal(pdf):
    """Check signature integrity with Poppler; trust warnings remain separate evidence."""
    with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
        tmp.write(pdf)
        tmp.flush()
        try:
            result = subprocess.run(['pdfsig', tmp.name], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            raise SignError('seal_validator_unavailable') from None
    if result.returncode or 'Signature Validation: Signature is Valid.' not in result.stdout or 'Total document signed' not in result.stdout:
        raise SignError('sealed_signature_invalid')
    return {'signature_valid': True, 'trusted': "Certificate issuer isn't Trusted" not in result.stdout}


def stage(workflow, item_id, kind, content):
    sha = digest(content)
    existing = ExecutedArtifact.objects.filter(workflow=workflow, item_id=item_id, kind=kind).first()
    if existing and existing.sha256 != sha:
        raise SignError('sealed_bytes_conflict')
    # Content-addressed names mean a failed local transaction leaves only reusable bytes.
    key = f'{workflow.room.organization_id}/dealroom-sign/{workflow.pk}/{sha}.pdf'
    fileserver_client.upload_file(key, content, 'application/pdf', timeout=(10, 10))
    return {'item_id': item_id, 'kind': kind, 'sha256': sha, 'size': len(content),
            'key': key, 'pages': len(PdfReader(io.BytesIO(content)).pages)}


def publish(workflow, staged):
    """Caller holds the workflow row lock and a transaction; no remote IO here."""
    room = workflow.room
    folder, _ = DataroomFolder.objects.get_or_create(dataroom=room, parent=None, name='Executed', defaults={'created_by': workflow.owner})
    folder, _ = DataroomFolder.objects.get_or_create(dataroom=room, parent=folder,
        name='NDAs' if workflow.purpose == 'nda' else 'Agreements', defaults={'created_by': workflow.owner})
    folder, _ = DataroomFolder.objects.get_or_create(dataroom=room, parent=folder,
        name=f'{workflow.member_id}-{workflow.policy_revision}' if workflow.purpose == 'nda' else workflow.envelope_id,
        defaults={'created_by': workflow.owner})
    for item in staged:
        existing = ExecutedArtifact.objects.filter(workflow=workflow, item_id=item['item_id'], kind=item['kind']).first()
        if existing:
            if existing.sha256 != item['sha256']:
                raise SignError('sealed_bytes_conflict')
            continue
        document = Document.objects.create(
            organization=room.organization, folder=room.vault_folder, created_by=None,
            name=f"{workflow.title.removesuffix('.pdf')} — {dict(sealed_pdf='Signed', certificate='Certificate', audit='Audit trail')[item['kind']]}.pdf", status='ready',
            storage_key=item['key'], original_storage_key=item['key'], type='pdf',
            content_type='application/pdf', file_size=item['size'], num_pages=item['pages'],
        )
        version = DocumentVersion.objects.create(document=document, version_number=1, is_primary=True,
            original_storage_key=item['key'], storage_key=item['key'], content_type='application/pdf',
            type='pdf', storage_type='local', file_size=item['size'], num_pages=item['pages'],
            render_status=DocumentVersion.RENDER_NOT_GENERATED)
        DataroomDocument.objects.create(dataroom=room, document=document, folder=folder, name=document.name, is_direct_upload=True)
        ExecutedArtifact.objects.create(workflow=workflow, version=version,
            **{k: item[k] for k in ('item_id', 'kind', 'sha256', 'size')})


def recover_previews(limit=4):
    """Dispatch Send's native derivative renderer; never change canonical PDF bytes.

    The manifest is the durable queue, so a crash after publication or a lost
    Celery message is recovered without publishing a second artifact.
    """
    from documents.renderers import get_renderer
    stale = timezone.now() - timedelta(minutes=15)
    versions = DocumentVersion.objects.filter(
        executedartifact__isnull=False, has_pages=False,
    ).filter(Q(render_status__in=[DocumentVersion.RENDER_NOT_GENERATED, DocumentVersion.RENDER_NOT_APPLICABLE]) |
             Q(updated_at__lt=stale)).select_related('document').order_by('updated_at')[:limit]
    for version in versions:
        if version.updated_at < stale:
            DocumentVersion.objects.filter(pk=version.pk, has_pages=False,
                render_status__in=[DocumentVersion.RENDER_FAILED, DocumentVersion.RENDER_QUEUED,
                                   DocumentVersion.RENDER_PROCESSING]).update(
                render_status=DocumentVersion.RENDER_NOT_GENERATED)
            version.refresh_from_db()
        try:
            get_renderer(version).enqueue_render_task(version)
        except Exception:
            logging.getLogger(__name__).warning('Executed PDF preview dispatch failed; retry scheduled')
