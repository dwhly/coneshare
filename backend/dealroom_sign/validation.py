import hashlib
import io
import json
import math

from pypdf import PdfReader
from rest_framework.exceptions import ValidationError

FIELD_TYPES = {'SIGNATURE', 'FREE_SIGNATURE', 'INITIALS', 'NAME', 'EMAIL', 'DATE', 'TEXT', 'NUMBER', 'RADIO', 'CHECKBOX', 'DROPDOWN'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def request_digest(data):
    return digest(json.dumps(data, sort_keys=True, separators=(',', ':')).encode())


def validate_recipients(recipients, pdf):
    try:
        page_count = len(PdfReader(io.BytesIO(pdf)).pages)
    except Exception:
        raise ValidationError('A valid PDF source is required.') from None
    if not 1 <= page_count <= 500 or not isinstance(recipients, list) or not 1 <= len(recipients) <= 20:
        raise ValidationError('Invalid page or recipient count.')
    normalized = []
    emails = set()
    for recipient in recipients:
        if set(recipient) - {'email', 'name', 'role', 'signingOrder', 'fields'}:
            raise ValidationError('Unsupported recipient property.')
        from django.core.validators import validate_email
        email = str(recipient.get('email', '')).strip().lower()
        try:
            validate_email(email)
        except Exception:
            raise ValidationError('Invalid signer email.') from None
        if email in emails or recipient.get('role', 'SIGNER') != 'SIGNER':
            raise ValidationError('Each signer must have a unique email and SIGNER role.')
        emails.add(email)
        fields = recipient.get('fields', [])
        if not fields or not any(f.get('type') in {'SIGNATURE', 'FREE_SIGNATURE'} for f in fields):
            raise ValidationError('Each signer requires a sender-placed signature field.')
        for field in fields:
            if set(field) - {'type', 'page', 'positionX', 'positionY', 'width', 'height', 'identifier', 'fieldMeta'}:
                raise ValidationError('Unsupported field property.')
            if field.get('type') not in FIELD_TYPES or type(field.get('page')) is not int or not 1 <= field['page'] <= page_count:
                raise ValidationError('Invalid field type or page.')
            coords = [field.get(k) for k in ('positionX', 'positionY', 'width', 'height')]
            if not all(type(v) in (float, int) and math.isfinite(v) for v in coords):
                raise ValidationError('Field coordinates must be finite numbers.')
            x, y, w, h = coords
            if min(x, y) < 0 or min(w, h) <= 0 or x + w > 100 or y + h > 100:
                raise ValidationError('Field must fit the page.')
            if field.get('identifier', 0) != 0:
                raise ValidationError('Field must reference the pinned source item.')
            # Rich metadata is validated upstream, before distribution. Do not accept arbitrary overrides.
            if field.get('fieldMeta') is not None:
                raise ValidationError('Rich field metadata requires the native editor in this slice.')
        order = recipient.get('signingOrder', 1)
        if type(order) is not int or not 1 <= order <= 20:
            raise ValidationError('Invalid signing order.')
        normalized.append({'email': email, 'name': str(recipient.get('name', ''))[:200], 'role': 'SIGNER',
                           'signingOrder': order, 'fields': [dict(f, identifier=0) for f in fields]})
    return normalized
