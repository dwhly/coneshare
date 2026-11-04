import json
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .client import SignError, identifier
from .tasks import reconcile_envelope


@csrf_exempt
@require_POST
def webhook(request):
    expected = getattr(settings, 'SIGN_WEBHOOK_SECRET', '')
    supplied = request.headers.get('X-Documenso-Secret', '')
    if not expected or not secrets.compare_digest(supplied.encode(), expected.encode()):
        return JsonResponse({'error': 'invalid_webhook_secret'}, status=403)
    if int(request.META.get('CONTENT_LENGTH') or 0) > 65536 or len(request.body) > 65536:
        return JsonResponse({'error': 'payload_too_large'}, status=413)
    try:
        payload = json.loads(request.body)
        envelope_id = identifier(payload['payload']['envelopeId'])
    except (ValueError, KeyError, TypeError, SignError):
        return JsonResponse({'error': 'invalid_envelope_hint'}, status=400)
    try:
        reconcile_envelope.delay(envelope_id)
    except Exception:
        return JsonResponse({'error': 'retry_enqueue'}, status=503)
    return JsonResponse({'accepted': True}, status=202)
