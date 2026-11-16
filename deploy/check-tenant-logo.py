"""Deployment smoke: verify the actual public proxy returns the configured PNG, not SPA HTML."""
import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('origin')
parser.add_argument('logo', type=Path)
parser.add_argument('--app', choices=['send', 'sign'], default='send')
args = parser.parse_args()
digest = hashlib.sha256(args.logo.read_bytes()).hexdigest()
route = '/signing/tenant-logo' if args.app == 'send' else '/chief/sign-tenant-logo'
with urlopen(args.origin.rstrip('/') + route + '?v=' + digest, timeout=10) as response:
    assert response.status == 200
    assert response.headers.get_content_type() == 'image/png', 'proxy returned non-PNG content'
    assert hashlib.sha256(response.read()).hexdigest() == digest, 'logo bytes differ'
print('PASS: public logo route returns the configured PNG')
