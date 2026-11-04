"""Offline, hash-pinned domain guards. Conservative Unicode script profile."""
import hashlib
import json
import unicodedata
from pathlib import Path
import idna
from rest_framework.exceptions import ValidationError


def canonical_domain(value):
    value = value.strip().rstrip('.').lower()
    if '@' in value or '*' in value or not value or '.' not in value:
        raise ValidationError('Enter an exact domain, without wildcards or email addresses.')
    try:
        unicode_domain = idna.decode(idna.encode(value, uts46=True, std3_rules=True))
        # UTS #39 highly restrictive subset: single-script labels only; ASCII digits/common punctuation exempt.
        for label in unicode_domain.split('.'):
            scripts = set()
            for c in label:
                if c.isalpha():
                    script = unicodedata.name(c, 'UNKNOWN').split()[0]
                    scripts.add(script)
            if len(scripts) > 1 or 'UNKNOWN' in scripts:
                raise ValueError('mixed-script label')
        return idna.encode(unicode_domain, uts46=True, std3_rules=True).decode(), unicode_domain
    except (idna.IDNAError, ValueError) as exc:
        raise ValidationError('Invalid or mixed-script domain.') from exc


def guarded_domain(value):
    alabel, unicode_domain = canonical_domain(value)
    directory = Path(__file__).with_name('data')
    try:
        manifest = json.loads((directory / 'manifest.json').read_text())
        for name in ('freemail.txt', 'disposable.txt'):
            data = (directory / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != manifest[name]['sha256']:
                raise ValueError('domain list checksum mismatch')
            domains = {line.strip().lower() for line in data.decode().splitlines() if line and not line.startswith('#')}
            if not domains:
                raise ValueError('empty domain list')
            if alabel in domains:
                raise ValidationError('Free-mail/disposable org grants are forbidden; use a named-member grant.')
    except (OSError, ValueError, KeyError) as exc:
        raise ValidationError('Domain guard unavailable; new domain grants are blocked.') from exc
    return alabel, unicode_domain
