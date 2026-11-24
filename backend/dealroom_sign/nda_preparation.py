"""Bounded, read-only preparation of supplied NDA bytes; never writes a policy."""
import hashlib
import io
import time
import zipfile
from pathlib import Path

from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from pypdf import PdfReader
from rest_framework import permissions
from rest_framework.exceptions import APIException, PermissionDenied, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .board_auth import BoardProxyAuthentication
from .placement import bounded_extract


class TooLarge(APIException):
    status_code = 413
    default_detail = 'NDA preparation accepts at most 15 MiB.'


class NdaPlacementView(APIView):
    authentication_classes = [BoardProxyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}, 'required': ['file']}}, responses=dict)
    def post(self, request):
        binding = getattr(request, 'board_binding', None)
        if not binding or 'read' not in binding.room_capabilities:
            raise PermissionDenied('Room read capability required.')
        key = 'room-nda-placement:' + str(binding.pk)
        if cache.add(key, 1, 60):
            count = 1
        else:
            try:
                count = cache.incr(key)
            except ValueError:
                raise Throttled(wait=60) from None
        if count > 10:
            raise Throttled(wait=60)
        if set(request.data) != {'file'} or 'file' not in request.FILES:
            raise ValidationError('Only supplied NDA bytes are accepted.')
        file = request.FILES['file']
        if file.size > 15*1024*1024:
            raise TooLarge()
        data = file.read(); suffix = Path(file.name).suffix.lower()
        if suffix == '.doc':
            raise ValidationError('Please save as .docx.')
        pages = None
        try:
            if suffix == '.pdf':
                reader = PdfReader(io.BytesIO(data))
                if reader.is_encrypted:
                    raise ValueError('encrypted')
                _, sizes, _ = bounded_extract(data, time.monotonic()+8)
                pages = len(sizes)
                if not 1 <= pages <= 50:
                    raise ValueError('pages')
            elif suffix == '.docx':
                with zipfile.ZipFile(io.BytesIO(data)) as package:
                    entries = package.infolist()
                    if (len(entries) > 2000 or sum(e.file_size for e in entries) > 100*1024*1024
                            or any(e.flag_bits & 1 or 'vbaproject' in e.filename.lower() for e in entries)
                            or 'word/document.xml' not in package.namelist()):
                        raise ValueError('office bounds')
            else:
                raise ValueError('unsupported')
        except Exception:
            raise ValidationError('Readable PDF with 1–50 pages or safe DOCX required.') from None
        return Response({'sha256': hashlib.sha256(data).hexdigest(), 'page_count': pages,
                         'fields': [], 'status': 'needs_attention', 'message': 'NDA comes next; no policy has been published.'})
