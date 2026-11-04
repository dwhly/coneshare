import hashlib
import json
import tempfile
import zipfile
import requests
from django.http import FileResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from .recipient import get_link, csrf
from .policy import evaluate
from .models import OriginalException, CopyEvidence
from .activity import record
from sharelinks.models import IssuedCopy
from sharelinks.amforge import issue_copy
from documents.fileserver import fileserver_client


class OriginalDownloadView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses={(200,'application/zip'):bytes})
    def post(self, request, slug, exception_id):
        csrf(request)
        link = get_link(slug)
        exception = OriginalException.objects.select_for_update().select_related('version__document', 'member').filter(pk=exception_id, room_id=link.dataroom_id).first()
        if not exception:
            raise PermissionDenied('Original exception unavailable.')
        item = link.dataroom.documents.filter(document=exception.version.document).first()
        if not item:
            raise PermissionDenied('Document no longer in room.')
        decision = evaluate(request,link,document_id=str(item.pk),download=True)
        now=timezone.now()
        if decision.member_id!=str(exception.member_id) or decision.grant_id!=str(exception.grant_id) or decision.effective_download_level!='original' or exception.revoked_at or exception.expires_at<=now or exception.used_count>=exception.max_uses or not exception.approved_by.is_staff:
            raise PermissionDenied('Original exception exhausted, expired or does not match the current policy.')
        # Build on disk under the per-container bound. Source bytes are never modified.
        output=tempfile.TemporaryFile()
        source=tempfile.TemporaryFile()
        source_hash=hashlib.sha256(); total=0
        with requests.get(fileserver_client.generate_download_url(exception.version.original_storage_key),stream=True,timeout=(10,60)) as response:
            response.raise_for_status()
            for chunk in response.iter_content(65536):
                total+=len(chunk)
                if total>50*1024*1024:
                    source.close();output.close();raise ValidationError('Original exceeds the 50 MiB bound.')
                source_hash.update(chunk);source.write(chunk)
        expected_hash = exception.version.metadata.get('source_sha256')
        if expected_hash and expected_hash != source_hash.hexdigest():
            source.close(); output.close()
            raise ValidationError('Immutable source hash mismatch.')
        source.seek(0)
        request.dealroom_decision = decision
        identity=issue_copy(link,request,exception.version.document,IssuedCopy.KIND_ORIGINAL,dataroom_document=item,version_override=exception.version)
        receipt={'copy_id':identity['copy_id'],'issued_to':exception.member.email,'version_id':str(exception.version_id),'exception_id':str(exception.pk),'source_sha256':source_hash.hexdigest(),'reason':exception.reason,'issued_at':now.isoformat(),'notice':'Original — unwatermarked exception; Copy ID records issuance, not proof of disclosure.'}
        receipt_bytes=json.dumps(receipt,sort_keys=True).encode()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as bundle:
            with bundle.open('original'+__import__('pathlib').Path(exception.version.original_storage_key).suffix,'w') as target:
                while chunk:=source.read(65536):target.write(chunk)
            bundle.writestr('receipt.json',receipt_bytes)
        source.close();output.seek(0)
        # Recheck policy immediately before consuming the use and sending bytes.
        evaluate(request,link,document_id=str(item.pk),download=True)
        exception.used_count+=1;exception.save(update_fields=['used_count'])
        CopyEvidence.objects.filter(copy__copy_id=identity['copy_id']).update(original_exception=exception,source_sha256=source_hash.hexdigest(),receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest())
        record('document.downloaded',organization=link.organization,actor=exception.member,room_id=link.dataroom_id,target_id=exception.version.document_id,data={'level':'original','exception_id':str(exception.pk),'copy_id':identity['copy_id'],'receipt_sha256':hashlib.sha256(receipt_bytes).hexdigest()})
        response=FileResponse(output,as_attachment=True,filename=f'original-{identity["copy_id"]}.zip',content_type='application/zip')
        response['Cache-Control']='private, no-store'
        return response
