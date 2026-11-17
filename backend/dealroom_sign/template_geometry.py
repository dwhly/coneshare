"""Blank, labelled recipient rules. Executed only in the bounded PDF worker."""
import io
import re
import time

import pdfplumber

from .placement import MAX_CHARS, MAX_EDGES, MAX_WORDS

LABELS = {'signature': 'SIGNATURE', 'name': 'NAME', 'company': 'TEXT', 'date': 'DATE'}


def blank_fields(pdf, deadline):
    candidates = []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        if not 1 <= len(doc.pages) <= 500:
            return []
        for page in doc.pages:
            if time.monotonic() >= deadline:
                raise TimeoutError
            if page.rotation or (page.cropbox and tuple(page.cropbox) != tuple(page.mediabox)) or page.bbox[:2] != (0, 0):
                continue
            if len(page.chars) > MAX_CHARS or len(page.edges) > MAX_EDGES:
                return []
            words = page.extract_words()
            if len(words) > MAX_WORDS:
                return []
            rules = [(e['x0'], e['x1'], e['top']) for e in page.edges
                     if abs(e['bottom'] - e['top']) < 1.5 and e['x1'] - e['x0'] >= 40]
            for word in words:
                for match in re.finditer(r'_{4,}', word['text']):
                    unit = (word['x1'] - word['x0']) / len(word['text'])
                    rules.append((word['x0'] + unit * match.start(), word['x0'] + unit * match.end(), word['bottom'] - 2))
            page_fields = []
            for label in words:
                typ = LABELS.get(label['text'].rstrip(':').lower())
                if not typ:
                    continue
                matching = [(x0, x1, y) for x0, x1, y in rules
                            if 0 <= x0 - label['x1'] <= 100 and abs(y - label['bottom']) <= 6]
                if not matching:
                    continue
                x0, x1, y = min(matching, key=lambda line: line[0])
                # Filled or pre-signed rules are never proposed as blanks.
                height = 24 if typ == 'SIGNATURE' else 18
                if any(w != label and w['x1'] > x0 + 1 and w['x0'] < x1 - 1
                       and w['bottom'] > y - height and w['top'] < y
                       and w['text'].strip('_ ') for w in words):
                    continue
                page_fields.append({'type': typ, 'page': page.page_number,
                    'positionX': x0 / page.width * 100, 'positionY': (y - height) / page.height * 100,
                    'width': (x1 - x0) / page.width * 100, 'height': height / page.height * 100, 'identifier': 0})
            # Require a unique blank signature and companions in the same block.
            signatures = [f for f in page_fields if f['type'] == 'SIGNATURE']
            if len(signatures) == 1:
                sig = signatures[0]
                block = [f for f in page_fields if f is sig or (f['positionY'] > sig['positionY']
                    and f['positionY'] - sig['positionY'] < 30 and abs(f['positionX'] - sig['positionX']) < 10)]
                if len({f['type'] for f in block}) == len(block):
                    candidates.append(block)
    return candidates[0] if len(candidates) == 1 else []
