"""Test-supplied tenant identity checks; no tenant fixtures belong in runtime code."""
import os
import re

ROOTS = ['backend/dealroom_sign', 'backend/backend/settings.py', 'backend/backend/urls.py',
         'frontend/public/dealroom', 'frontend/public/fds']
SUFFIXES = {'.py', '.html', '.txt', '.js', '.css', '.json', '.svg', '.mjs', '.cjs'}


def normalize_colours(value):
    return re.sub(r'#[0-9a-f]{6}(?![0-9a-f])|#[0-9a-f]{3}(?![0-9a-f])',
                  lambda m: '#' + ''.join(c * 2 for c in m[0][1:]) if len(m[0]) == 4 else m[0],
                  value.casefold())


def scan(root, environ=None):
    environ = os.environ if environ is None else environ
    needles = ['Acme Test Co', *environ.get('FLEET_TEST_TENANT_NAMES', '').split(',')]
    needles += environ.get('FLEET_TEST_TENANT_COLOURS', '').split(',')
    needles += environ.get('FLEET_TEST_TENANT_DOMAINS', '').split(',')
    needles = [normalize_colours(n.strip()) for n in needles if n.strip()]
    hits = []
    for relative in ROOTS:
        target = root / relative
        for file in ([target] if target.is_file() else target.rglob('*')):
            if not file.is_file() or file.suffix not in SUFFIXES:
                continue
            if any(p in {'tests', 'e2e', '__pycache__', 'fixtures'} for p in file.relative_to(root).parts) or file.name == 'seed_sign_fixture.py':
                continue
            source = normalize_colours(file.read_text())
            if any(n and n.casefold() in source for n in needles):
                hits.append(str(file.relative_to(root)))
    return hits
