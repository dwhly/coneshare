"""Production UI, real fixture/PDF.js and suggestion geometry; fictional intercepted APIs."""
import base64
import json
from pathlib import Path
from urllib.parse import urlparse

import yaml
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / 'docs/room-proto/round4-screenshots'
SHOTS.mkdir(parents=True, exist_ok=True)
PDF = ROOT / 'backend/dealroom/tests/fixtures/Investor NDA (fictional).pdf'
FIELDS = json.loads((ROOT / '.testtmp/suggestions.json').read_text())
BRAND = yaml.safe_load((ROOT / 'brand.yaml').read_text())
state = {}
changes = []


def reset():
    state.clear()
    state.update(confirmed=False, fields=[], revision='fictional-revision', source_version_id='v', name=PDF.name,
                 suggestions=FIELDS, enabled=True, pdf_url='/api/v1/dealroom/rooms/r/entry-nda-source/?revision=fictional-revision')


def route_api(route):
    req = route.request
    path = urlparse(req.url).path.removeprefix('/api/v1')
    data = []
    if path.endswith('/entry-nda-source/'):
        route.fulfill(content_type='application/pdf', body=PDF.read_bytes())
        return
    if path == '/public/settings/': data = {}
    elif path == '/dealroom/brand/': data = BRAND
    elif path.startswith('/users/'):
        data = {'id': '1', 'name': 'Dan Whaley', 'email': 'dan@example.test', 'is_staff': True, 'language': 'en'}
    elif path == '/dealroom/rooms/r/': data = {'id': 'r', 'name': 'Harbor Light Analytics · Series A', 'entry_url': '/view/demo'}
    elif path == '/datarooms/r/': data = {'items': []}
    elif path.endswith('/outline/'):
        data = {'template': '', 'documents': [{'id': 'mutual', 'name': 'Mutual NDA (fictional).pdf', 'version_id': 'mutual-version', 'folder_id': 'legal'}],
                'groups': [], 'slots': {}, 'start_here': [], 'not_needed': [], 'needs_you': [], 'invitations': [],
                'nda_configured': state['confirmed'], 'share_blocked': not state['confirmed'], 'require_nda': True,
                'policy': {'status': 'active'}, 'watermark_style': None}
    elif path.endswith('/entry-nda/'): data = state
    elif path == '/dealroom-sign/nda-policy/r/':
        if req.method == 'PUT':
            change = req.post_data_json
            changes.append(change)
            assert change['confirm'] is True
            state.update(fields=change['fields'], confirmed=True, suggestions=[])
        data = state
    elif path == '/dealroom/workspace-settings/': data = {'watermark_style': 'diagonal'}
    route.fulfill(content_type='application/json', body=json.dumps(data))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    errors = []
    for label, width, height in [('desktop', 1440, 1000), ('phone', 390, 844)]:
        reset()
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.context.route('**/api/**', route_api)
        payload = base64.urlsafe_b64encode(json.dumps({'user_id': '1', 'exp': 9999999999}).encode()).decode().rstrip('=')
        page.add_init_script(f"localStorage.setItem('access_token', 'e30.{payload}.fictional');")
        page.goto('http://127.0.0.1:4175/datarooms/r')
        expect(page.get_by_role('button', name='Place the NDA fields')).to_be_visible()
        page.get_by_role('button', name='Invite investors').click()
        page.get_by_label('Email addresses').fill('maya@northwind.test')
        expect(page.get_by_role('button', name='Send personal invitations')).to_be_disabled()
        page.screenshot(path=str(SHOTS / f'blocked-share-{label}.png'))
        page.get_by_role('button', name='Place the NDA fields').click()
        expect(page.get_by_role('button', name='Use these positions')).to_be_enabled()
        expect(page.get_by_text('Suggested — check')).to_be_visible()
        placement = page.get_by_role('region', name='NDA field placement')
        placement.scroll_into_view_if_needed()
        canvas = placement.locator('canvas')
        expect(canvas).to_be_visible()
        page.wait_for_function("document.querySelector('canvas')?.width > 0")
        page.wait_for_timeout(500)
        # Fixed viewport captures center the PDF and keep the confirmation action visible.
        placement.evaluate('(el) => window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 75)')
        page.screenshot(path=str(SHOTS / f'placement-suggestions-{label}.png'))
        page.screenshot(path=str(SHOTS / f'placement-suggestions-{label}-full.png'), full_page=True)
        field = page.get_by_role('button', name='Move Signature field 1')
        field.scroll_into_view_if_needed()
        before = field.bounding_box()
        page.mouse.move(before['x'] + 20, before['y'] + before['height'] / 2)
        page.mouse.down()
        page.mouse.move(before['x'] + 35, before['y'] + before['height'] / 2 - 10, steps=8)
        page.mouse.up()
        expect(page.get_by_text('Edited — check')).to_be_attached()
        after = field.bounding_box()
        assert abs(after['x'] - before['x'] - 15) < 2
        assert abs(after['y'] - before['y'] + 10) < 2
        page.screenshot(path=str(SHOTS / f'placement-after-drag-{label}.png'))
        assert not state['confirmed']
        resize = page.get_by_role('button', name='Resize Signature field 1')
        box = resize.bounding_box()
        page.mouse.move(box['x'] + 10, box['y'] + 10)
        page.mouse.down(); page.mouse.move(box['x'] + 20, box['y'] + 14, steps=5); page.mouse.up()
        page.get_by_role('button', name='Use these positions').click()
        expect(page.get_by_text('Positions confirmed')).to_be_visible()
        assert changes[-1]['fields'][0]['positionX'] != FIELDS[0]['positionX']
        assert changes[-1]['fields'][0]['width'] > FIELDS[0]['width']
        page.screenshot(path=str(SHOTS / f'positions-confirmed-{label}.png'))
        expect(page.get_by_role('button', name='Place the NDA fields')).not_to_be_attached()
        # Reopen Settings to prove the saved server coordinates are loaded.
        page.reload()
        page.get_by_role('navigation', name='Room sections').get_by_role('button', name='Settings', exact=True).click()
        expect(page.get_by_text('Positions confirmed')).to_be_visible()
        page.get_by_role('button', name='Edit positions').click()
        expect(page.get_by_role('button', name='Move Signature field 1')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
        page.close()
    assert not errors, errors
    browser.close()
    print('PASS: 1440x1000 and 390x844; PDF.js rendering, blocked invitations, drag, resize, confirmation and saved positions; no page errors or horizontal overflow.')
