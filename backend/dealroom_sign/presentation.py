"""Shared recipient display values; never use storage filenames as mail copy."""
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .client import SignError, pdf_filename


def clean_title(title):
    value = pdf_filename(title)[:-4]
    value = re.sub(r'(?:[ _-]+\d{10,13}|[ _-]+\d{4}-\d{2}-\d{2}(?:[T _-]\d{2}[:_-]\d{2}(?::\d{2})?)?)$', '', value)
    # Older board sends used this suffix for internal room-file uniqueness.
    value = re.sub(r' \((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2} \d{4}\)$', '', value)
    return value or 'Document'


def display_name(value):
    parts = value.split() if isinstance(value, str) else []
    return ' '.join(part for part in parts if part.casefold() != 'none') or 'Requester'


def requester_snapshot(value):
    """Only authenticated send metadata may supply this reply address."""
    if not isinstance(value, dict) or set(value) != {'name', 'email'}:
        raise SignError('invalid_requester')
    name, email = value['name'], value['email']
    if (not isinstance(name, str) or not isinstance(email, str) or len(name) > 200 or len(email) > 254
            or any(c in name + email for c in ('\r', '\n'))):
        raise SignError('invalid_requester')
    email = email.strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        raise SignError('invalid_requester') from None
    return {'name': display_name(name), 'email': email}


def referrer_policy(response):
    # HTML documents drive subsequent forms/fetches. Downloads and JSON may
    # retain the stricter policy without changing their referring document.
    content_type = getattr(response, 'accepted_media_type', None) or response.get('Content-Type', '')
    return 'same-origin' if content_type.split(';')[0] == 'text/html' else 'no-referrer'
