import hashlib
import json
from pathlib import Path
import yaml
from django.conf import settings


def load_brand():
    path = Path(settings.DEALROOM_BRAND_FILE)
    brand = yaml.safe_load(path.read_text())
    for key in ('name', 'logo', 'tokens', 'watermark', 'email_sender'):
        if not brand.get(key):
            raise ValueError(f'Missing brand field: {key}')
    if not {'name', 'organisation', 'email', 'date', 'copy_id'} <= set(__import__('re').findall(r'\{\{(\w+)\}\}', brand['watermark'])):
        raise ValueError('Watermark must include identity and Copy ID')
    brand['revision'] = hashlib.sha256(json.dumps(brand, sort_keys=True).encode()).hexdigest()
    return brand
