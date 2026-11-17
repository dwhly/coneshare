"""Measured golden regions and actual native boxes. Run after render_native.ts."""
import io
import json
from pathlib import Path

import pdfplumber
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter

from dealroom_sign.placement import place, to_native_fields
from dealroom_sign.tests.test_placement import EXPECTED, FIXTURES, model_answer

out = Path(__file__).resolve().parent
results, thumbs = {}, []
for name, golden in EXPECTED['fixtures'].items():
    signers = golden['signers']
    source = (FIXTURES / (name + '.pdf')).read_bytes()
    result = place(source, signers, model_client=model_answer if name == 'unusual' else None)
    native = [f for signer in signers for f in to_native_fields(result, signer['email'])]
    results[name] = {'analysis': result, 'native_fields': native}
    with pdfplumber.open(io.BytesIO(source)) as doc:
        pno = max((f['page'] for f in native), default=len(doc.pages))
        img = doc.pages[pno - 1].to_image(resolution=120).original.convert('RGB')
        draw = ImageDraw.Draw(img, 'RGBA')
        for f in native:
            if f['page'] != pno:
                continue
            x, y = f['positionX'] * img.width / 100, f['positionY'] * img.height / 100
            w, h = f['width'] * img.width / 100, f['height'] * img.height / 100
            draw.rectangle((x, y, x+w, y+h), fill=(10, 110, 170, 35), outline=(10, 110, 170, 255), width=2)
            draw.text((x+3, y+2), f['type'], fill=(10, 80, 130, 255))
        draw.text((12, 12), name + ': ' + result['status'], fill=(0, 0, 0, 255))
        img.save(out / (name + '-overlay.png'))
        img.thumbnail((420, 544))
        thumbs.append(img)
contact = Image.new('RGB', (1680, 1088), 'white')
for i, img in enumerate(thumbs):
    contact.paste(img, ((i % 4) * 420, (i // 4) * 544))
contact.save(out / 'contact.png')
(out / 'placements.json').write_text(json.dumps(results, indent=2) + '\n')

# Merge actual Sign V2 exports onto the immutable Harbor fixture for visual evidence.
metrics = {}
for mode in ('before', 'after'):
    source = PdfReader(FIXTURES / 'harbor.pdf')
    overlay_path = out / f'harbor-{mode}-native.pdf'
    overlay = PdfReader(overlay_path)
    source.pages[1].merge_page(overlay.pages[0])
    writer = PdfWriter()
    writer.append_pages_from_reader(source)
    merged = out / f'harbor-{mode}-rendered.pdf'
    with merged.open('wb') as file:
        writer.write(file)
    with pdfplumber.open(merged) as doc:
        img = doc.pages[1].to_image(resolution=144).original.convert('RGB')
        img.save(out / f'harbor-{mode}-rendered.png')
        # Same crop makes the old float and overflowing timestamp easy to compare.
        img.crop((110, 620, 920, 810)).save(out / f'harbor-{mode}-detail.png')
    with pdfplumber.open(overlay_path) as doc:
        native_image = doc.pages[0].to_image(resolution=144).original.convert('RGB')
        sig = native_image.crop((144, 640, 576, 736)).convert('L').point(lambda x: 255 if x < 200 else 0)
        bounds = sig.getbbox()
        metrics[mode] = {'signature_ink_bottom_pt': (640 + bounds[3]) / 2,
                         'rule_y_pt': 367.2, 'ink_gap_pt': 367.2 - (640 + bounds[3]) / 2}
(out / 'render-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
