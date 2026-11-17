"""Generate screenshot assets with the product's image watermark renderer (fictional data)."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
from django.conf import settings
from PIL import Image

django.setup()
from sharelinks.views import _apply_watermark_to_image, _render_watermark_text
from django.test import RequestFactory

OUT = ROOT / '.testtmp/round3-assets'
OUT.mkdir(parents=True, exist_ok=True)
subprocess.run(['pdftoppm', '-f', '1', '-singlefile', '-scale-to', '1200', '-png',
                str(ROOT / 'backend/dealroom/tests/fixtures/drive/harbor-light/nda.pdf'), str(OUT / 'source')], check=True)
settings.WATERMARK_FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
identity = {'name': 'Maya Chen', 'organisation': 'Northwind Ventures', 'email': 'maya@northwind.test',
            'copy_id': 'CP-FICTIONAL-072', 'date': '2026-11-17', 'timestamp': '2026-11-17 12:00 UTC'}
for style in ('diagonal', 'edge'):
    with Image.open(OUT / 'source.png') as source:
        image = source.convert('RGBA')
        text = _render_watermark_text('CONFIDENTIAL - {{email}}', RequestFactory().get('/'), identity=identity)
        rendered = _apply_watermark_to_image(image, text, {**identity, 'watermark_style': style})
        rendered.convert('RGB').save(OUT / f'{style}.jpg', quality=92)
        rendered.close(); image.close()
print('Generated both styles with the product renderer.')
