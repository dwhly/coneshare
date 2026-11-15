"""C4a: the counterparty emails use the Fleet design tokens (fds tokens.css, light theme, as hex because mail clients have no
CSS variables), the same as the pages: ink text and primary button, muted secondary text, hairline border, 8px radius,
the Fleet | Dealroom lockup, and human-readable file sizes. The live walk showed off-system greens and raw byte counts."""
import re
from types import SimpleNamespace

from django.template.loader import render_to_string

INK, MUTED, BORDER = '#161a22', '#585e6a', '#dcdfe4'


def _mail(invitation):
    access = SimpleNamespace(sender={'company': ''}, context={'incoming': False, 'note': '', 'pages': 2, 'signatures': 1,
                                                             'due_at': '22 Nov 2026'})
    return render_to_string('dealroom_sign/emails/mail.html', {
        'invitation': invitation, 'access': access, 'sender': 'Dan', 'sending_staff': 'Dan', 'title': 'Harbor Light Mutual NDA',
        'estimated_minutes': 1, 'url': 'https://example.test/s/tok', 'origin': 'https://example.test', 'alternate': 'AAAA',
        'report': 'support@fleet.test', 'link_only': False,
        'parties': [{'name': 'Lee Harbor', 'company': '', 'signed_at': '15 Nov 2026'}],
        'files': [{'name': 'Harbor Light Mutual NDA — signed.pdf', 'size': 48_213}, {'name': 'Signing certificate.pdf', 'size': 1_204_000}]})


def test_emails_use_fleet_tokens_not_off_system_greens():
    for invitation in (True, False):
        html = _mail(invitation).lower()
        for off in ('#183d33', '#185b4c', '#b7cdc5', 'font:16px arial'):
            assert off not in html, (invitation, off)
        assert f'color:{INK}' in html and MUTED in html and f'1px solid {BORDER}' in html
        assert '-apple-system' in html and 'segoe ui' in html


def test_email_primary_action_is_the_ink_button():
    html = _mail(True)
    button = re.search(r'<a [^>]*>Review and sign</a>', html)[0]
    assert f'background:{INK}' in button and 'color:#ffffff' in button and 'border-radius:8px' in button


def test_email_lockup_and_human_file_sizes():
    for invitation in (True, False):
        html = _mail(invitation)
        assert '>Fleet</span>' in html  # product name per email: test_email_app_name_and_inter_first_with_no_remote_font
    final = _mail(False)
    assert 'bytes' not in final and '47.1' in final and '1.1' in final


def test_email_app_name_and_inter_first_with_no_remote_font():
    inv, final = _mail(True), _mail(False)
    assert '>Sign</span>' in inv and '>Dealroom</span>' not in inv
    assert '>Dealroom</span>' in final and '>Sign</span>' not in final
    for html in (inv, final):
        assert "font-family:Inter,-apple-system" in html
        assert '@font-face' not in html and '.woff' not in html  # no remote font: it would act like a tracking pixel

