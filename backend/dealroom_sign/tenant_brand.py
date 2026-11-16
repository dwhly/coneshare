"""Optional deployment identity; only validated presentation values reach templates."""
import colorsys
import hashlib
import logging
import math
import os
import re
import stat
import zlib
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from django.http import HttpResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)
_warned = set()
_KEYS = ('NAME', 'LOGO', 'LOGO_BASELINE', 'CHROME', 'CHROME_RULE', 'SURFACE', 'POWERED_BY')
HEX = re.compile(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\Z')
MAX_LOGO_BYTES = 200 * 1024


@dataclass(frozen=True)
class TenantBrand:
    name: str = 'Fleet'
    logo_url: str = ''
    logo_baseline: float = .8
    chrome: str = ''
    chrome_hsl: str = ''
    chrome_rule: str = ''
    chrome_rule_hsl: str = ''
    surface: str = ''
    powered_by: bool = False
    logo_bytes: bytes = b''
    logo_mime: str = ''
    logo_hash: str = ''

    @property
    def logo_offset(self):
        return f'{(self.logo_baseline - 1) * 20:g}px'


def _warn(key):
    if key not in _warned:
        _warned.add(key)
        logger.warning('Invalid FLEET_TENANT_%s; using default', key)


def _hsl(value):
    digits = value[1:]
    if len(digits) == 3:
        digits = ''.join(c * 2 for c in digits)
    h, light, saturation = colorsys.rgb_to_hls(*(int(digits[i:i+2], 16) / 255 for i in (0, 2, 4)))
    return f'{h * 360:.4f}'.rstrip('0').rstrip('.') + ' ' + f'{saturation * 100:.4f}'.rstrip('0').rstrip('.') + '% ' + f'{light * 100:.4f}'.rstrip('0').rstrip('.') + '%'


def _logo(path):
    path = Path(path)
    if path.suffix.lower() != '.png' or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('logo_type')
    with path.open('rb') as file:
        content = file.read(MAX_LOGO_BYTES)
    if not content or len(content) >= MAX_LOGO_BYTES:
        raise ValueError('logo_size')
    if (not content.startswith(b'\x89PNG\r\n\x1a\n') or len(content) < 45 or
            content[12:16] != b'IHDR' or not int.from_bytes(content[16:20], 'big') or
            not int.from_bytes(content[20:24], 'big') or not content.endswith(b'\x00\x00\x00\x00IEND\xaeB`\x82')):
        raise ValueError('logo_png')
    offset, has_data = 8, False
    while offset < len(content):
        length = int.from_bytes(content[offset:offset+4], 'big')
        end = offset + 12 + length
        if end > len(content) or zlib.crc32(content[offset+4:end-4]) != int.from_bytes(content[end-4:end], 'big'):
            raise ValueError('logo_png')
        has_data |= content[offset+4:offset+8] == b'IDAT'
        offset = end
    if not has_data:
        raise ValueError('logo_png')
    return content, 'image/png'


def parse_tenant_brand(environ):
    brand = TenantBrand()
    for key in _KEYS:
        value = environ.get('FLEET_TENANT_' + key, '')
        if value == '':
            continue
        try:
            if key == 'NAME':
                if not value.strip() or len(value) > 120 or re.search(r'[\x00-\x1f\x7f-\x9f]', value):
                    raise ValueError('name')
                brand = replace(brand, name=value.strip())
            elif key == 'LOGO_BASELINE':
                if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', value):
                    raise ValueError('baseline')
                number = float(value)
                if not math.isfinite(number) or not 0 <= number <= 1:
                    raise ValueError('baseline')
                brand = replace(brand, logo_baseline=number)
            elif key in {'CHROME', 'CHROME_RULE'}:
                if not HEX.fullmatch(value):
                    raise ValueError('hex')
                field = key.lower()
                brand = replace(brand, **{field: value, field + '_hsl': _hsl(value)})
            elif key == 'SURFACE':
                if value != 'warm':
                    raise ValueError('surface')
                brand = replace(brand, surface=value)
            elif key == 'POWERED_BY':
                if value != '1':
                    raise ValueError('powered_by')
                brand = replace(brand, powered_by=True)
            else:
                content, mime = _logo(value)
                digest = hashlib.sha256(content).hexdigest()
                brand = replace(brand, logo_url='/chief/tenant-logo?v=' + digest,
                    logo_bytes=content, logo_mime=mime, logo_hash=digest)
        except (OSError, ValueError, TypeError):
            _warn(key)
    return brand


@lru_cache(maxsize=1)
def _configured(values):
    return parse_tenant_brand(dict(zip(('FLEET_TENANT_' + key for key in _KEYS), values)))


def get_tenant_brand():
    return _configured(tuple(os.environ.get('FLEET_TENANT_' + key, '') for key in _KEYS))


get_tenant_brand.cache_clear = _configured.cache_clear


@require_GET
def tenant_logo(request):
    brand = get_tenant_brand()
    if not brand.logo_bytes or request.GET.get('v') != brand.logo_hash:
        return HttpResponse(status=404)
    response = HttpResponse(brand.logo_bytes, content_type=brand.logo_mime)
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    response['ETag'] = '"' + brand.logo_hash + '"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response
