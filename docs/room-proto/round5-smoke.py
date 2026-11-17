"""Production UI walk-through with fictional APIs and the real gateway entry template.

Native Documenso signing and SMTP are external boundaries, simulated here. The backend
round-five tests exercise actual workflow binding, handoffs and gateway return handlers.
"""
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / 'docs/room-proto/round5-screenshots'
SHOTS.mkdir(parents=True, exist_ok=True)
ROOM_ORIGIN = 'http://127.0.0.1:4175'
GATEWAY = 'https://signer.fictional.test'
PDF = ROOT / 'backend/dealroom/tests/fixtures/Investor NDA (fictional).pdf'

# Render the actual gateway shell; no copied or invented signer UI.
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
os.environ.setdefault('SECRET_KEY', 'fictional-round-five-browser-secret')
os.environ.setdefault('FIELD_ENCRYPTION_KEY', 'S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8=')
os.environ.setdefault('SIGN_CAPABILITY_KEY', 'fictional-browser-capability')
os.environ.setdefault('CORE_API_URL', 'http://127.0.0.1:18080')
os.environ.setdefault('INTERNAL_API_TOKEN', 'fictional-browser-token')
os.environ['FLEET_TENANT_NAME'] = 'AmForge'
import django

django.setup()
from django.test import RequestFactory
from dealroom_sign.recipient_proxy import page as gateway_page

member = {'name': 'Maya Chen', 'email': 'maya@northwind.test', 'org': 'Northwind Ventures'}
work = SimpleNamespace(purpose='nda', source_sha256='0' * 64, state='awaiting_signature')
access = SimpleNamespace(pk=uuid.UUID(int=5), generation=1, revision='fictional', workflow=work,
    workflow_id=uuid.UUID(int=6), sender={'name': 'Dan Whaley', 'company': 'Harbor Light Analytics'},
    name=member['name'], email=member['email'], invite_state='succeeded',
    context={'title': 'Investor NDA (fictional)', 'pages': 1, 'signatures': 1,
             'due_at': '24 Nov 2026, 12:00 PM UTC', 'note': ''})
entry_html = gateway_page(RequestFactory().get('/sign/fictional'), 'welcome', access=access).content
brand = {'name': 'AmForge', 'logo': '/fds/marks/fleet.svg'}
signed = {'signed': True, 'signed_at': '2026-11-17T12:00:00Z', 'email': member['email'],
          'can_enter': True, 'state': 'done', 'download_url': '/api/v1/dealroom/recipient/demo/signed-nda/download/'}
files = [
    {'id': 'overview', 'name': 'Company overview.pdf', 'folder_id': 'company', 'page_count': 2},
    {'id': 'deck', 'name': 'Pitch deck.pdf', 'folder_id': 'company', 'page_count': 6},
    {'id': 'model', 'name': 'Financial model.xlsx', 'folder_id': 'financials', 'page_count': 1, 'sheet_count': 4},
    {'id': 'pnl', 'name': 'Profit and loss.xlsx', 'folder_id': 'financials', 'page_count': 1},
    {'id': 'cap', 'name': 'Cap table.xlsx', 'folder_id': 'ownership', 'page_count': 1, 'sheet_count': 2},
    {'id': 'roadmap', 'name': 'Product roadmap.pdf', 'folder_id': 'product', 'page_count': 3},
    {'id': 'security', 'name': 'Security overview.pdf', 'folder_id': 'security', 'page_count': 2},
    {'id': 'inc', 'name': 'Certificate of incorporation.pdf', 'folder_id': 'legal', 'page_count': 2},
    {'id': 'nda', 'name': 'Mutual NDA.pdf', 'folder_id': 'legal', 'page_count': 2},
    {'id': 'board', 'name': 'Board consent.pdf', 'folder_id': 'legal', 'page_count': 1},
    {'id': 'customers', 'name': 'Customer list - top 10.xlsx', 'folder_id': '', 'page_count': 1},
    {'id': 'notes', 'name': 'Operating notes.pdf', 'folder_id': '', 'page_count': 2},
]
room = {'id': 'r', 'name': 'Harbor Light Analytics · Series A', 'member': member, 'files': files,
        'folders': [{'id': key, 'name': name, 'parent_id': ''} for key, name in [
            ('company', '01 Company'), ('financials', '02 Financials'), ('ownership', '03 Ownership'),
            ('product', '04 Product'), ('security', '05 Security'), ('legal', '06 Legal')]],
        'start_here': ['model', 'deck'], 'answers': [], 'nda_signed': True, 'signed_nda': signed,
        'note': 'Thanks for taking a look. Start with the model, then the deck. I’m around this week to walk through it. — Dan'}
state = {}


def route_api(route):
    request = route.request
    path = urlparse(request.url).path
    status = 200
    if path.endswith('/challenge/'):
        data = {'csrf_token': 'fictional', 'brand': brand, 'sender_name': 'Dan Whaley'}
    elif path.endswith('/personal/'):
        state['verified'] = True
        data = {'status': 'verified'}
    elif path.endswith('/room/'):
        if state.get('signed'):
            data = room
        else:
            data, status = {'code': 'nda_required', 'room_id': 'r'}, 403
    elif path.endswith('/nda/r/enter/'):
        assert state.get('started') and state.get('verified')
        state['handoffs'] += 1
        data = {'signing_url': GATEWAY + '/s/nda/fictional-one-time-' + str(state['handoffs'])}
    elif path.endswith('/nda/r/'):
        if request.method == 'POST':
            state['started'] = True
            data = {'state': 'queued'}
        else:
            state['reads'] += 1
            ready = state.get('started') and state['reads'] >= 3
            data = {'state': 'awaiting_signature' if ready else 'queued' if state.get('started') else 'not_started',
                    'can_enter': bool(ready), 'accepted': False, 'email_sent': bool(ready)}
    elif path.endswith('/signed-nda/download/'):
        route.fulfill(content_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="Your signed NDA.pdf"'}, body=PDF.read_bytes())
        return
    elif path.endswith('/signed-nda/'):
        data = signed if state.get('sealed') else {**signed, 'can_enter': False, 'download_url': None, 'state': 'awaiting_seal'}
    elif path == '/api/v1/dealroom/brand/':
        data = brand
    else:
        data = {}
    route.fulfill(status=status, content_type='application/json', body=json.dumps(data))


def route_gateway(route):
    path = urlparse(route.request.url).path
    if path.startswith('/s/nda/'):
        route.fulfill(content_type='text/html', body=entry_html)
    elif path.startswith('/s/assets/'):
        asset = ROOT / 'frontend/public' / path.removeprefix('/s/assets/')
        if asset.is_file():
            route.fulfill(content_type=mimetypes.guess_type(asset.name)[0] or 'application/octet-stream', body=asset.read_bytes())
        else:
            route.fulfill(content_type='application/javascript', body='')
    elif path == '/s/session/original':
        route.fulfill(content_type='application/pdf', body=PDF.read_bytes())
    elif path.startswith('/s/return/'):
        # Native completion is simulated; backend tests check this redirect against
        # persisted workflow evidence, including ignored caller return parameters.
        assert state.get('signed')
        route.fulfill(status=303, headers={'Location': ROOM_ORIGIN + '/view/demo?nda=complete'})
    else:
        route.fulfill(content_type='text/html', body=entry_html)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    errors = []
    for label, width, height in [('desktop', 1440, 1000), ('phone', 390, 844)]:
        state.clear()
        state.update(reads=0, handoffs=0)
        context = browser.new_context(viewport={'width': width, 'height': height})
        context.route('**/api/**', route_api)
        context.route(GATEWAY + '/**', route_gateway)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))

        def capture(name):
            page.evaluate('document.fonts.ready')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), name + ' overflow'
            page.screenshot(path=str(SHOTS / f'{name}-{label}.png'))

        page.goto(ROOM_ORIGIN + '/view/demo#personal=fictional')
        expect(page.get_by_text('Dan Whaley invited you')).to_be_visible()
        capture('invite')
        page.get_by_role('button', name='Review the NDA').click()
        page.wait_for_url(GATEWAY + '/s/nda/**')
        assert len(context.pages) == 1
        expect(page.get_by_role('button', name='Review and sign')).to_be_visible()
        expect(page.get_by_text('We’ve also emailed you this link.')).to_be_visible()
        capture('signing')
        # Going back without a signature exposes a resumable action, never room content.
        page.go_back()
        expect(page.get_by_role('button', name='Continue signing')).to_be_visible()
        expect(page.get_by_text(room['name'], exact=True)).to_have_count(0)
        capture('continue-signing')
        page.get_by_role('button', name='Continue signing').click()
        page.wait_for_url(GATEWAY + '/s/nda/**')
        assert state['handoffs'] == 2 and len(context.pages) == 1
        state['signed'] = True
        page.goto(GATEWAY + '/s/return/fictional-workflow?return_url=https://elsewhere.test')
        expect(page.get_by_role('button', name='Preparing your copy…')).to_be_visible()
        expect(page.get_by_role('button', name='Enter the data room')).to_be_disabled()
        state['sealed'] = True
        expect(page.get_by_role('link', name='Download your signed NDA')).to_be_visible(timeout=8000)
        expect(page.get_by_text('A copy is also on its way to maya@northwind.test.')).to_be_visible()
        capture('confirmation')
        with page.expect_download() as download:
            page.get_by_role('link', name='Download your signed NDA').click()
        assert download.value.suggested_filename == 'Your signed NDA.pdf'
        page.get_by_role('button', name='Enter the data room').click()
        expect(page.get_by_text(room['note'])).to_be_visible()
        expect(page.get_by_text('1 page', exact=True)).to_have_count(1)  # Board consent, never an xlsx.
        capture('room-top')
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        expect(page.get_by_role('region', name='Other documents')).to_be_visible()
        capture('room-bottom')
        page.screenshot(path=str(SHOTS / f'room-full-{label}.png'), full_page=True)
        assert len(context.pages) == 1
        context.close()
    browser.close()
    assert not errors, errors
    print('Chromium: same-tab invite → real gateway entry template → simulated native completion → confirmation → room passed at 1440×1000 and 390×844. Back/Continue, polling, download, sections and overflow checked; no page errors. Native editor, SMTP and sealing not exercised.')
