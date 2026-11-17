"""Browser checks and screenshots against Vite preview on :4175, using fictional API fixtures."""
import ast
import base64
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / 'docs/room-proto/round2-screenshots'
source = ast.parse((ROOT / 'backend/dealroom/drive.py').read_text())
groups = next(ast.literal_eval(n.value) for n in source.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SERIES_A' for t in n.targets))
defs = {slot[0]: {'id': slot[0], 'name': slot[1], 'folder': group['id']} for group in groups for slot in group['slots']}
manifest = json.loads((ROOT / 'backend/dealroom/tests/fixtures/drive/harbor-light/manifest.json').read_text())
nodes = []
exports = {'application/vnd.google-apps.document': ('pdf', 'Google Doc, saved as a PDF copy'), 'application/vnd.google-apps.spreadsheet': ('xlsx', 'Google Sheet, saved as an Excel file copy')}
for node in manifest['nodes']:
    row = {**node, 'type': 'folder' if node['mimeType'].endswith('.folder') else 'file', 'parent_id': node['parents'][0]}
    if row['type'] == 'file':
        ext, text = exports.get(node['mimeType'], (Path(node['name']).suffix[1:], 'PDF, added as is'))
        row.update(final_name=node['name'] if node['name'].endswith('.' + ext) else node['name'] + '.' + ext, final_type=ext, import_description=text)
    nodes.append(row)
files = [n for n in nodes if n['type'] == 'file']
slots = {f['id']: f['id'] for f in files if f['id'] in defs}
docs = [{'id': f['id'], 'document_id': f['id'], 'name': f['final_name'], 'folder_id': defs.get(f['id'], {}).get('folder', ''), 'source': {'modifiedTime': f['modifiedTime'], 'webViewLink': 'https://drive.google.com/file/d/' + f['id'] + '/view'}} for f in files]
outline = {'template': 'series_a', 'note': 'Thanks for taking a look. Start with the model.', 'start_here': ['model', 'deck'], 'slots': slots, 'not_needed': [], 'groups': groups, 'slot_definitions': defs, 'documents': docs, 'drive_roots': ['harbor-light'], 'drive_checked_at': '2026-11-17T12:00:00Z', 'needs_you_count': 1, 'needs_you': [{'id': 'q', 'kind': 'question', 'text': 'What drives the margin?', 'firm': 'Northwind', 'email': 'maya@northwind.test'}], 'nda_configured': True}
brand = {'name': 'AmForge', 'logo': '/brand-mark.svg', 'tokens': {}}
requests = []

def route_api(route):
    req = route.request
    path = urlparse(req.url).path.removeprefix('/api/v1')
    status, data = 200, []
    if path == '/public/settings/': data = {}
    elif path == '/dealroom/brand/': data = brand
    elif path.startswith('/users/'): data = {'id': '1', 'name': 'Dan Whaley', 'email': 'dan@example.test', 'is_staff': True, 'language': 'en'}
    elif path == '/dealroom/rooms/r/': data = {'id': 'r', 'name': 'Harbor Light · Series A', 'entry_url': '/view/demo'}
    elif path == '/datarooms/r/': data = {'items': []}
    elif path.endswith('/outline/'):
        if req.method == 'PATCH': outline.update(req.post_data_json)
        data = outline
    elif path.endswith('/drive-review/'):
        template = req.post_data_json['template']
        data = {'ticket': 'review', 'template': template, 'roots': [{'id': 'harbor-light', 'name': 'Harbor Light'}], 'nodes': nodes, 'matched': [{**f, 'slot': f['id']} for f in files if f['id'] in defs] if template else [], 'skipped': [{'id': 'form', 'name': 'Investor survey', 'skip_reason': 'Google Forms cannot be imported.'}, {'id': 'large', 'name': 'Market research.pdf', 'skip_reason': 'This file exceeds the 50 MiB limit.'}]}
    elif path.endswith('/drive-import/'):
        requests.append(req.post_data_json)
        data = {'imported': ['ok']}
    elif path.endswith('/drive-updates/'): data = {'updates': [], 'checked_at': '2026-11-17T15:00:00Z'}
    elif path.endswith('/challenge/'): data = {'csrf_token': 'fixture', 'brand': brand, 'sender_name': 'Dan Whaley'}
    elif path.endswith('/personal/'): data = {'status': 'verified'}
    elif path.endswith('/room/'): status, data = 403, {'code': 'nda_required', 'room_id': 'r'}
    route.fulfill(status=status, content_type='application/json', body=json.dumps(data))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/**', route_api)
    payload = base64.urlsafe_b64encode(json.dumps({'user_id': '1', 'exp': 9999999999}).encode()).decode().rstrip('=')
    page.add_init_script(f"localStorage.setItem('access_token', 'e30.{payload}.fixture');")
    page.goto('http://127.0.0.1:4175/datarooms/r')
    expect(page.get_by_role('button', name='Add file for Team bios')).to_be_attached()
    expect(page.get_by_role('button', name='Add file for IP assignment agreements')).to_be_attached()
    expect(page.get_by_role('navigation', name='Room sections').get_by_role('button', name='Needs you 1')).to_be_visible()
    page.screenshot(path=str(SHOTS / 'sender-outline.png'), full_page=True)
    page.get_by_role('button', name='Add file for IP assignment agreements').scroll_into_view_if_needed()
    page.screenshot(path=str(SHOTS / 'sender-missing-slots.png'))
    page.get_by_role('button', name='Check Drive for updates').click()
    expect(page.get_by_text('No changes since the last import.')).to_be_visible()
    page.get_by_role('button', name='Start from Google Drive', exact=True).click()
    expect(page.get_by_role('navigation', name='Room sections').get_by_role('button', name='Documents')).to_have_attribute('aria-current', 'page')
    assert 'dr-btn--primary' not in page.get_by_role('button', name='Invite investors').get_attribute('class')
    page.get_by_label('Drive folder links · one per line').fill('https://drive.google.com/drive/folders/harbor-light')
    page.get_by_role('button', name='Read folders').click()
    confirm = page.get_by_role('button', name='Confirm and import 12 files')
    expect(confirm).to_be_visible()
    box = confirm.bounding_box()
    assert 0 <= box['y'] < 1000 - box['height'], box
    page.screenshot(path=str(SHOTS / 'drive-review.png'))
    page.get_by_role('button', name='Exclude Notes for investors - draft').click()
    expect(page.get_by_role('button', name='Confirm and import 11 files')).to_be_visible()
    page.get_by_role('button', name='Move Company overview to').click()
    page.get_by_role('menuitemradio', name='Financials', exact=True).click()
    expect(page.get_by_role('group', name='Financials').get_by_text('Company overview.pdf')).to_be_visible()
    page.get_by_role('button', name='Match to a Series A checklist instead').click()
    expect(page.get_by_text('Matched · 9', exact=True)).to_be_attached()
    expect(page.get_by_text('Unsure · 2', exact=True)).to_be_attached()
    expect(page.get_by_text('Missing · 3', exact=True)).to_be_attached()
    page.get_by_text('Missing · 3', exact=True).scroll_into_view_if_needed()
    expect(page.get_by_text('Missing · 3', exact=True)).to_be_visible()
    page.screenshot(path=str(SHOTS / 'checklist-review.png'))
    page.get_by_role('button', name='Confirm and import 11 files').click()
    expect(page.get_by_role('button', name='Add files', exact=True)).to_be_visible()
    assert requests[0]['excluded'] == ['notes']
    assert requests[0]['destinations']['overview'] == 'financials'
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto('http://127.0.0.1:4175/view/demo#personal=fixture')
    expect(page.get_by_text('Dan Whaley invited you')).to_be_visible()
    assert 'Harbor Light' not in page.locator('body').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(SHOTS / 'visitor-invitation-phone.png'), full_page=True)
    page.get_by_role('button', name='Review the NDA').click()
    expect(page.get_by_text('Before you enter')).to_be_visible()
    expect(page.get_by_text('AmForge', exact=True)).to_be_visible()
    assert 'Harbor Light' not in page.locator('body').inner_text()
    page.screenshot(path=str(SHOTS / 'visitor-nda-phone.png'), full_page=True)
    assert not errors, errors
    browser.close()
print('Browser passed: desktop outline, selected tabs, import sticky bar, exclusion, move, checklist switch, submission; phone branded invitation/NDA privacy and width. No page errors.')
