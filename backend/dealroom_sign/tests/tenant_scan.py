"""Test-supplied tenant identity checks; no tenant fixtures belong in runtime code."""
import colorsys
import hashlib
import os
import re

ROOTS = ['backend/dealroom_sign', 'backend/backend/settings.py', 'backend/backend/urls.py',
         'frontend/public/dealroom', 'frontend/public/fds']
SUFFIXES = {'.py', '.html', '.txt', '.js', '.css', '.json', '.svg', '.mjs', '.cjs'}


def normalize_colours(value):
    return re.sub(r'#[0-9a-f]{6}(?![0-9a-f])|#[0-9a-f]{3}(?![0-9a-f])',
                  lambda m: '#' + ''.join(c * 2 for c in m[0][1:]) if len(m[0]) == 4 else m[0],
                  value.casefold())


def colour_forms(value):
    hex_value = normalize_colours(value.strip())
    if not re.fullmatch(r'#[0-9a-f]{6}', hex_value):
        return [hex_value]
    rgb = [int(hex_value[i:i+2], 16) for i in (1, 3, 5)]
    h, light, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    hsl = [h * 360, saturation * 100, light * 100]
    forms = [hex_value, 'rgb(' + ' '.join(map(str, rgb)) + ')']
    for precision in (4, 0):
        values = [f'{v:.{precision}f}'.rstrip('0').rstrip('.') if precision else str(int(v + .5)) for v in hsl]
        forms.append(f'{values[0]} {values[1]}% {values[2]}%')
    return forms


def normalize_source(source):
    return re.sub(r'\s+', ' ', re.sub(r'\s*,\s*', ' ', normalize_colours(source)))


def scan(root, environ=None):
    environ = os.environ if environ is None else environ
    needles = ['Acme Test Co', *environ.get('FLEET_TEST_TENANT_NAMES', '').split(',')]
    needles += [form for value in environ.get('FLEET_TEST_TENANT_COLOURS', '').split(',') for form in colour_forms(value)]
    needles += environ.get('FLEET_TEST_TENANT_DOMAINS', '').split(',')
    needles = [normalize_source(n.strip()) for n in needles if n.strip()]
    hits = []
    for relative in ROOTS:
        target = root / relative
        for file in ([target] if target.is_file() else target.rglob('*')):
            if not file.is_file() or file.suffix not in SUFFIXES:
                continue
            if any(p in {'tests', 'e2e', '__pycache__', 'fixtures'} for p in file.relative_to(root).parts) or file.name == 'seed_sign_fixture.py':
                continue
            source = file.read_text()
            # Exempt only this upstream example in the exact locked asset, never a colour or a whole file.
            if (str(file.relative_to(root)) == 'frontend/public/fds/tokens.css'
                    and hashlib.sha256(file.read_bytes()).hexdigest() == 'b1e227b8139ccbb4da4cc9cc8a294df86348023038dea305cd0ead54a98cbb16'):
                source = re.sub(r'/\* Org title-bar colour .*?\*/', '', source, count=1, flags=re.S)
            source = normalize_source(source)
            if any(n and n.casefold() in source for n in needles):
                hits.append(str(file.relative_to(root)))
    return hits
