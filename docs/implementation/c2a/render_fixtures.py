"""Render the actual engine fields on each fixture. Run from Send root with backend on PYTHONPATH.
The unusual fixture deliberately uses the same offline model stub as the golden test.
"""
import json
from pathlib import Path

import pdfplumber
from PIL import ImageDraw

from dealroom_sign.tests.test_placement import FIXTURES, LEE, TWO, OFFER, model_answer
from dealroom_sign.placement import place

out = Path(__file__).resolve().parent
results = {}
for name in ['bare', 'nda', 'offer', 'roles', 'witness', 'harbor', 'unusual']:
    signers = OFFER if name == 'offer' else LEE if name in {'harbor', 'unusual'} else TWO
    source = (FIXTURES / (name + '.pdf')).read_bytes()
    result = place(source, signers, model_client=model_answer if name == 'unusual' else None)
    results[name] = result
    with pdfplumber.open(FIXTURES / (name + '.pdf')) as doc:
        pages = sorted({f['page'] for f in result['fields']}) or [len(doc.pages)]
        for pno in pages:
            rendered = doc.pages[pno-1].to_image(resolution=120).original.convert('RGB')
            rendered.thumbnail((2000, 2000))
            draw = ImageDraw.Draw(rendered, 'RGBA')
            for f in result['fields']:
                if f['page'] != pno:
                    continue
                color = (15, 110, 175) if f['signer'] == signers[0]['email'] else (180, 90, 0)
                x, y = f['x'] / 100 * rendered.width, f['y'] / 100 * rendered.height
                w, h = f['w'] / 100 * rendered.width, f['h'] / 100 * rendered.height
                draw.rectangle((x, y, x+w, y+h), outline=(*color,255), fill=(*color,38), width=2)
                draw.text((x+3, y+2), f['type'] + ' · ' + f['signer'].split('@')[0], fill=(*color,255))
            draw.text((12, 12), name + ': ' + result['status'] + (' (mocked model)' if name == 'unusual' else ''), fill=(0,0,0,255))
            rendered.save(out / f'{name}-p{pno}.png')
            rendered.close()
(out / 'placements.json').write_text(json.dumps(results, indent=2) + '\n')
