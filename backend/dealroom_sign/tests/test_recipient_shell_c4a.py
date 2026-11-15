"""C4a: the counterparty pages use the shared Fleet visitor shell, the same as Sign's signing page.

Live walk (dealroom-sign/c2a): Send's recipient pages (entry, context, done) rendered a plain "Fleet | Dealroom" text
header and hand-styled buttons, while Sign's signing page uses the visitor header, lockup and Theme button, the
context bar and fds buttons. On "Signed", the two download buttons sat jammed together.
"""
import re
from types import SimpleNamespace

from django.template.loader import render_to_string


def _render(state, **extra):
    access = SimpleNamespace(
        name='Lee Harbor', email='lee@harborlight.fleet.test', workflow_id='wf',
        sender={'name': 'Dan', 'company': ''}, workflow=SimpleNamespace(state=extra.pop('wstate', 'done')),
        context={'title': 'Harbor Light Mutual NDA', 'pages': 2, 'signatures': 1, 'due_at': '22 Nov 2026', 'note': ''})
    ctx = {'state': state, 'access': access, 'csrf': 'x', 'asset_prefix': '/s/assets', 'disclosure_hash': 'h',
           'entry_path': '/s/cap/enter', 'title': 'Harbor Light Mutual NDA', 'sender_name': 'Dan'}
    ctx.update(extra)
    return render_to_string('dealroom_sign/recipient.html', ctx)


def test_recipient_pages_use_the_shared_visitor_header():
    for state in ['entry', 'welcome', 'signed', 'help']:
        html = _render(state)
        assert 'fds-header dr-header dr-header--visitor' in html, state
        assert 'class="fds-lockup"' in html and 'data-fds-theme-toggle' in html, state
        assert '<header>Fleet | Dealroom</header>' not in html, state


def test_recipient_actions_are_fds_buttons_with_no_bespoke_button_css():
    for state in ['entry', 'welcome', 'signed']:
        html = _render(state)
        buttons = re.findall(r'<button\b[^>]*>', html)
        content = [b for b in buttons if 'data-fds-theme-toggle' not in b]
        assert content, state
        assert all('fds-btn' in b for b in content), (state, content)
        assert not re.search(r'(^|[}\s])button\s*\{', html.split('</style>')[0].split('<style>')[-1]), state


def test_signed_downloads_sit_in_a_spaced_action_row():
    html = _render('signed')
    row = re.search(r'<div class="dr-recipient-actions">(.*?)</div>', html, re.S)
    assert row, html
    assert 'Download signed PDF' in row[1] and 'Download certificate' in row[1]
    assert 'fds-btn fds-btn--primary' in row[1]
    assert '.dr-recipient-actions{display:flex;flex-wrap:wrap;gap:var(--space-3)' in html.replace(' ', '')


def test_signed_headline_matches_whether_the_copy_is_ready():
    assert 'your copy is ready' in _render('signed', wstate='done')
    pending = _render('signed', wstate='sent')
    assert 'your copy will follow' in pending and 'your copy is ready' not in pending


def test_context_bar_names_the_document_and_signer_only_after_the_session_starts():
    welcome = _render('welcome')
    bar = re.search(r'<div class="dr-context"[^>]*>(.*?)</div>', welcome, re.S)[1]
    assert 'Harbor Light Mutual NDA' in bar and 'Lee Harbor' in bar and 'lee@harborlight.fleet.test' in bar
    entry = _render('entry')
    assert 'Harbor Light Mutual NDA' not in entry and 'lee@harborlight' not in entry and 'Lee Harbor' not in entry
