"""Private board proxy authentication. No browser-provided identity is accepted by Board."""
import io
import re
import hashlib
import hmac
import json
import time

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import PermissionDenied, APIException

from .models import BoardStaffBinding

HUMAN_VIAS = {'tailscale', 'cloudflare'}


def signature(key, method, path, body, timestamp, context):
    fields = [method, path, hashlib.sha256(body).hexdigest(), timestamp, context]
    message = b''.join(str(len(value.encode())).encode() + b':' + value.encode() for value in fields)
    return hmac.new(key.encode(), message, hashlib.sha256).hexdigest()


class BodyTooLarge(APIException):
    status_code = 413
    default_detail = 'Board upload exceeds the byte limit.'


def signed_body(request):
    # Django's generic in-memory body limit is smaller than room files. Bound only
    # these authenticated transport shapes, then preserve the exact signed bytes
    # for DRF's multipart parser. All other endpoints retain Django's normal limit.
    path = request.path
    limit = None
    if re.fullmatch(r'/api/v1/dealroom/rooms/[^/]+/upload/', path):
        limit = 50*1024*1024 + 65536
    elif path == '/api/v1/dealroom-sign/nda-placement/':
        limit = 15*1024*1024 + 65536
    if limit is None:
        return request.body
    original = request._request
    if not hasattr(original, '_body'):
        content = original.read(limit+1)
        if len(content) > limit:
            raise BodyTooLarge()
        original._body = content
        original._stream = io.BytesIO(content)
    if len(original._body) > limit:
        raise BodyTooLarge()
    return original._body


class BoardProxyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        raw = request.headers.get('X-Board-Context')
        if raw is None:
            return None
        key = getattr(settings, 'BOARD_SIGN_PROXY_KEY', '')
        stamp = request.headers.get('X-Board-Timestamp', '')
        supplied = request.headers.get('X-Board-Signature', '')
        try:
            context = json.loads(raw)
            valid = (key and len(raw) <= 1024 and set(context) == {'board', 'login', 'via'}
                     and all(isinstance(v, str) and len(v) <= 254 for v in context.values())
                     and raw == json.dumps(context, sort_keys=True, separators=(',', ':'))
                     and abs(time.time() - int(stamp)) <= 60
                     and hmac.compare_digest(supplied, signature(key, request.method,
                         request.get_full_path(), signed_body(request), stamp, raw)))
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise PermissionDenied('forbidden')
        binding = BoardStaffBinding.objects.select_related('send_user').filter(
            board_id=context['board'], login=context['login'], enabled=True,
            send_user__is_active=True, send_user__is_staff=True).first()
        if not binding:
            raise PermissionDenied('forbidden')
        request.board_context = context
        request.board_binding = binding
        return binding.send_user, None


class BoardProxyScheme(OpenApiAuthenticationExtension):
    target_class = 'dealroom_sign.board_auth.BoardProxyAuthentication'
    name = 'boardProxy'

    def get_security_definition(self, auto_schema):
        return {'type': 'apiKey', 'in': 'header', 'name': 'X-Board-Signature',
                'description': 'Server-only HMAC binds method, exact path/query, body hash, timestamp and canonical X-Board-Context. Human via: tailscale or cloudflare; service/dev receives agent projection.'}
