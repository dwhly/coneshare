"""Chromium screenshots of the production build; intercepted fictional APIs, real watermark renderer assets."""
import base64
import json
from pathlib import Path
from urllib.parse import urlparse

import yaml
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / 'docs/room-proto/round3-screenshots'
ASSETS = ROOT / '.testtmp/round3-assets'
SHOTS.mkdir(parents=True, exist_ok=True)
brand = yaml.safe_load((ROOT / 'brand.yaml').read_text())
member = {'name': 'Maya Chen', 'email': 'maya@northwind.test', 'org': 'Northwind Ventures'}
signed = {'signed': True, 'signed_at': '2026-11-17T12:00:00Z', 'email': member['email'], 'can_enter': True,
          'state': 'done', 'download_url': '/api/v1/dealroom/recipient/demo/signed-nda/download/'}
room = {'id': 'r', 'name': 'Harbor Light Analytics · Series A', 'member': member,
        'note': 'Thanks for taking a look. Start with the model, then the deck. I’m around this week to walk through it. — Dan',
        'start_here': [], 'answers': [], 'nda_signed': True, 'signed_nda': signed,
        'folders': [{'id': 'finance', 'name': '02 Financials', 'parent_id': ''},
                    {'id': 'forecast', 'name': 'Forecasts', 'parent_id': 'finance'},
                    {'id': 'legal', 'name': '03 Legal', 'parent_id': ''}],
        'files': [{'id': 'model', 'name': 'Financial model.pdf', 'folder_id': 'forecast', 'page_count': 1,
                   'page_url': '/api/v1/links/demo/render-page/1/?dataroom_document_id=model'},
                  {'id': 'host-nda', 'name': 'Mutual NDA.pdf', 'folder_id': 'legal', 'page_count': 2,
                   'page_url': '/api/v1/links/demo/render-page/1/?dataroom_document_id=host-nda'}]}
outline = {'template': '', 'documents': [{'id': 'nda', 'name': 'Mutual NDA.pdf', 'version_id': 'v'}], 'groups': [],
           'slots': {}, 'start_here': [], 'not_needed': [], 'needs_you': [], 'drive_roots': [], 'invitations': [],
           'note': room['note'], 'nda_configured': True, 'policy': {'status': 'active'}, 'watermark_style': None}
state = {'watermark_style': 'diagonal', 'ready': True}
changes = []

def route_api(route):
    req = route.request
    path = urlparse(req.url).path.removeprefix('/api/v1')
    data = []
    if '/render-page/' in path:
        route.fulfill(content_type='image/jpeg', headers={'Cache-Control': 'no-store'}, body=(ASSETS / (state['watermark_style'] + '.jpg')).read_bytes())
        return
    if path.endswith('/signed-nda/download/'):
        route.fulfill(content_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="Your signed NDA.pdf"'},
                      body=(ROOT / 'backend/dealroom/tests/fixtures/drive/harbor-light/nda.pdf').read_bytes())
        return
    if path == '/public/settings/': data = {}
    elif path == '/dealroom/brand/': data = brand
    elif path.startswith('/users/'):
        data = {'id': '1', 'name': 'Dan Whaley', 'email': 'dan@example.test', 'is_staff': True, 'language': 'en'}
    elif path.endswith('/challenge/'): data = {'csrf_token': 'fictional', 'brand': brand, 'sender_name': 'Dan Whaley'}
    elif path.endswith('/signed-nda/'):
        data = signed if state['ready'] else {**signed, 'download_url': None, 'can_enter': False, 'state': 'awaiting_seal'}
    elif path.endswith('/room/'):
        data = {**room, 'watermark_style': state['watermark_style'], 'files': [{**f, 'page_url': f["page_url"] + '&style=' + state['watermark_style']} for f in room['files']]}
    elif path == '/dealroom/workspace-settings/':
        if req.method == 'PATCH':
            state.update(req.post_data_json); changes.append(req.post_data_json)
        data = {'watermark_style': state['watermark_style']}
    elif path == '/dealroom/rooms/r/': data = {'id': 'r', 'name': room['name'], 'entry_url': '/view/demo'}
    elif path == '/datarooms/r/': data = {'items': []}
    elif path.endswith('/outline/'):
        if req.method == 'PATCH': outline.update(req.post_data_json)
        data = outline
    route.fulfill(content_type='application/json', body=json.dumps(data))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    errors = []
    for label, width, height in [('desktop', 1440, 1000), ('phone', 390, 844)]:
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.context.route('**/api/**', route_api)
        payload = base64.urlsafe_b64encode(json.dumps({'user_id': '1', 'exp': 9999999999}).encode()).decode().rstrip('=')
        page.add_init_script(f"localStorage.setItem('access_token', 'e30.{payload}.fictional');")
        state['ready'] = False
        page.goto('http://127.0.0.1:4175/view/demo?nda=complete')
        expect(page.get_by_role('button', name='Preparing your copy…')).to_be_visible()
        expect(page.get_by_role('button', name='Enter the data room')).to_be_disabled()
        page.screenshot(path=str(SHOTS / f'confirmation-preparing-{label}.png'))
        state['ready'] = True
        expect(page.get_by_role('link', name='Download your signed NDA')).to_be_visible(timeout=8000)
        expect(page.get_by_role('button', name='Enter the data room')).to_be_enabled()
        expect(page.get_by_text('A copy is also on its way to maya@northwind.test.')).to_be_visible()
        page.screenshot(path=str(SHOTS / f'confirmation-{label}.png'))
        with page.expect_download() as download:
            page.get_by_role('link', name='Download your signed NDA').click()
        assert download.value.suggested_filename.endswith('.pdf'), (download.value.url, download.value.suggested_filename, download.value.failure())
        page.get_by_role('button', name='Enter the data room').click()
        expect(page.get_by_text(room['note'])).to_be_visible()
        expect(page.get_by_label('Forecasts', exact=True)).to_be_visible()
        expect(page.get_by_text('Your signed NDA', exact=True)).to_be_attached()
        page.screenshot(path=str(SHOTS / f'visitor-room-{label}.png'), full_page=True)
        page.get_by_label('Your signed NDA', exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(SHOTS / f'visitor-signed-nda-{label}.png'))
        page.get_by_text('02 Financials', exact=True).click()
        expect(page.get_by_text('Financial model.pdf')).not_to_be_visible()
        page.get_by_text('02 Financials', exact=True).click()
        for style in ('diagonal', 'edge'):
            state['watermark_style'] = style
            page.goto('http://127.0.0.1:4175/view/demo')
            page.get_by_role('button', name='01 Mutual NDA.pdf 2 pages').click()
            img = page.get_by_alt_text('Watermarked page 1 of Mutual NDA.pdf')
            expect(img).to_be_visible()
            page.wait_for_function("Array.from(document.images).every(i => i.complete)")
            page.screenshot(path=str(SHOTS / f'watermark-{style}-{label}-full.png'), full_page=True)
            if style == 'edge':
                page.evaluate("window.scrollTo(0, document.querySelector('img').getBoundingClientRect().bottom + scrollY - innerHeight + 150)")
            page.screenshot(path=str(SHOTS / f'watermark-{style}-{label}.png'))
            page.get_by_role('button', name='Back to room').click()
        page.goto('http://127.0.0.1:4175/settings')
        control = page.get_by_role('button', name='Watermark style')
        expect(control).to_be_enabled()
        control.click()
        page.get_by_role('menuitemradio', name='Diagonal', exact=True).click()
        expect(page.get_by_text('Watermark style saved.')).to_be_visible()
        control.click()
        page.screenshot(path=str(SHOTS / f'workspace-settings-{label}.png'))
        page.get_by_role('menuitemradio', name='Edge', exact=True).click()
        expect(control).to_have_text('Edge')
        page.goto('http://127.0.0.1:4175/datarooms/r')
        page.get_by_role('navigation', name='Room sections').get_by_role('button', name='Settings', exact=True).click()
        control = page.get_by_role('button', name='Watermark style')
        expect(control).to_have_text('Workspace default')
        control.click()
        page.screenshot(path=str(SHOTS / f'room-settings-{label}.png'))
        page.get_by_role('menuitemradio', name='Diagonal', exact=True).click()
        expect(control).to_have_text('Diagonal')
        control.click()
        page.get_by_role('menuitemradio', name='Workspace default', exact=True).click()
        expect(control).to_have_text('Workspace default')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
        page.close()
    browser.close()
    assert not errors, errors
    assert {'watermark_style': 'edge'} in changes
    print('Chromium: confirmation polling/download/entry, nested folders, own NDA, both renderer styles, workspace default and room override passed at both viewport sizes; no page errors.')
