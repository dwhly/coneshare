"""One export path: authorize, resolve immutable bytes, commit evidence, deliver."""
import io
from types import SimpleNamespace

from django.http import HttpResponse
from django.utils import timezone
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from rest_framework.exceptions import APIException, NotFound, PermissionDenied

from core.models import APIKey
from dealroom.activity import record
from dealroom.hooks import human_staff
from .evidence import snapshot_fields, signer_state
from .client import Documenso, SignError, pdf_filename
from .models import ExecutedArtifact, ObservedSignEvent, RequestArtifact, SignCredential
from .operations import PROTECTED_KINDS, require_export_actor
from .storage import source_bytes, snapshot_version
from .validation import digest
from .workflows import validate_envelope




class SnapshotChanged(APIException):
    status_code = 409
    default_detail = 'snapshot_changed'


class Unavailable(APIException):
    status_code = 503
    default_detail = 'send_unavailable'




def stamp_partial(content, request_id, as_of):
    writer = PdfWriter()
    for source_page in PdfReader(io.BytesIO(content)).pages:
        page = writer.add_page(source_page)
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        overlay = io.BytesIO(); stamp = canvas.Canvas(overlay, pagesize=(width, height))
        stamp.setFillColorRGB(.55, 0, 0); stamp.setFont('Helvetica-Bold', 10)
        stamp.drawString(12, 21, 'NOT FINAL - signed so far')
        stamp.setFont('Helvetica', 7); stamp.drawString(12, 9, f'{request_id} | {as_of}')
        stamp.save(); page.merge_page(PdfReader(io.BytesIO(overlay.getvalue())).pages[0])
    out = io.BytesIO(); writer.write(out)
    return out.getvalue()


def original(row):
    work = row.workflow
    return SimpleNamespace(pk=work.source_version_id, version=work.source_version, sha256=work.source_sha256,
        snapshot_id=work.source_sha256, size=work.source_version.file_size, kind='original', as_of=work.created_at)


def existing_artifact(row, kind, snapshot_id=None):
    if kind == 'original':
        result = original(row)
    elif kind in {'final', 'certificate'} or kind == 'audit' and row.workflow.state == 'done':
        if row.workflow.state != 'done':
            raise NotFound('not_available')
        result = ExecutedArtifact.objects.filter(workflow=row.workflow,
            kind='sealed_pdf' if kind == 'final' else kind).select_related('version').first()
        if result:
            result.snapshot_id = result.sha256
    else:
        rows = RequestArtifact.objects.filter(request=row, kind=kind).select_related('version')
        if snapshot_id:
            rows = rows.filter(snapshot_id=snapshot_id)
        result = rows.order_by('-as_of').first()
        if result and kind == 'partial' and not snapshot_id:
            observed = ObservedSignEvent.objects.filter(workflow=row.workflow, source_id=result.snapshot_id, kind='snapshot.fields').first()
            if not observed or observed.payload.get('signers') != signer_state(row.workflow.signer_projection):
                result = None
    if snapshot_id and (not result or result.snapshot_id != snapshot_id):
        raise SnapshotChanged()
    return result


def resolve_artifact(row, kind, snapshot_id=None, *, fresh=False):
    artifact = existing_artifact(row, kind, snapshot_id)
    if artifact and (not fresh or snapshot_id or kind not in {'partial', 'audit'} or row.workflow.state == 'done'):
        content = source_bytes(artifact.version)
        if digest(content) != artifact.sha256:
            raise SignError('artifact_hash_mismatch')
        return artifact, content
    work = row.workflow
    if kind not in {'partial', 'audit'} or work.state in {'done', 'quarantined', 'failed'}:
        raise NotFound('not_available')
    credential = SignCredential.objects.get(owner=work.owner, enabled=True)
    with Documenso(credential) as client:
        before = client.get(work.envelope_id); validate_envelope(work, before)
        if kind == 'partial' and before['status'] != 'PENDING':
            raise SnapshotChanged()
        if digest(client.item_pdf(work.item_ids[0], 'original')) != work.source_sha256:
            raise SnapshotChanged()
        audit_before = client.audit(work.envelope_id)
        content = client.item_pdf(work.item_ids[0], 'pending') if kind == 'partial' else client.audit_pdf(work.envelope_id)
        after = client.get(work.envelope_id); validate_envelope(work, after)
        audit_after = client.audit(work.envelope_id)
        if before != after or audit_before != audit_after:
            raise SnapshotChanged()
    as_of = timezone.now()
    source_hash = digest(content)
    if kind == 'partial':
        content = stamp_partial(content, str(row.pk), as_of.isoformat())
    sha = digest(content)
    artifact = RequestArtifact.objects.filter(request=row, kind=kind, snapshot_id=sha).first()
    if not artifact:
        version = snapshot_version(row, kind, sha, content)
        artifact = RequestArtifact.objects.create(request=row, kind=kind, snapshot_id=sha, version=version,
            item_id=work.item_ids[0] if kind == 'partial' else work.envelope_id,
            sha256=sha, size=len(content), as_of=as_of, source_sha256=source_hash)
    if kind == 'partial':
        snapshot_fields(work, artifact.snapshot_id, work.item_ids[0], after)
    return artifact, content


def manifest(row, human):
    result = []
    for kind in ['original', 'partial', 'final', 'certificate', 'audit']:
        if not human and kind in PROTECTED_KINDS:
            continue
        try:
            item = existing_artifact(row, kind)
        except NotFound:
            item = None
        available = item is not None or kind in {'partial', 'audit'} and row.workflow.state == 'awaiting_signature'
        result.append({'kind':kind,'snapshot_id':item.snapshot_id if item else None,
            'sha256':item.sha256 if item else None,'size':item.size if item else None,
            'as_of':getattr(item, 'as_of', getattr(item, 'fetched_at', None)) if item else None,
            'available':available,'interim':kind in {'partial','audit'} and row.workflow.state != 'done'})
    return result


def download(request, row, data):
    require_export_actor(request, data['kind'], row)
    try:
        artifact, content = resolve_artifact(row, data['kind'], data.get('snapshot_id'), fresh=True)
        context = getattr(request, 'board_context', {})
        actor = request.auth if isinstance(request.auth, APIKey) else request.user
        evidence = {'kind':data['kind'],'snapshot_id':artifact.snapshot_id,'sha256':digest(content),
            'size':len(content),'reason':data['reason'],'board_id':row.board_id,
            'board_service':context.get('via'), 'board_login':context.get('login')}
        event = record('signature.download_requested', organization=row.workflow.room.organization, actor=actor,
            room_id=row.workflow.room_id, target_id=row.pk, data=evidence,
            actor_kind='staff' if human_staff(request) else 'agent')
        # Bytes are buffered; this records response handoff, never a claim that a person read them.
        record('signature.download_outcome', organization=row.workflow.room.organization, actor=actor,
            room_id=row.workflow.room_id, target_id=row.pk,
            data={'audit_id':str(event.pk),'outcome':'served','delivery':'response_handoff'})
    except (PermissionDenied, NotFound, SnapshotChanged):
        raise
    except Exception:
        raise Unavailable() from None
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="' + pdf_filename(data['kind']+' - '+row.title).encode('ascii', 'replace').decode() + '"'
    response['X-Content-SHA256'] = digest(content)
    response['X-Dealroom-Artifact-ID'] = str(artifact.pk)
    response['X-Dealroom-Audit-ID'] = str(event.pk)
    response['Cache-Control'] = 'private, no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response
