"""Canonical attribution and all public delivery paths use deployment settings."""
import importlib
from pathlib import Path
from io import StringIO

import pytest
from django.template.loader import render_to_string
from django.core.management import call_command

from dealroom_sign.tests.test_recipient_shell_c4a import _render

TENANT = {'FLEET_TENANT_NAME': 'Acme <Test> & "Co"',
          'FLEET_ABOUT_URL': 'https://fleet.example.test/about?a=1&b=2',
          'FLEET_SOURCE_URL': 'https://source.example.test/tree/0123456789'}


def module():
    return importlib.import_module('dealroom_sign.fleet_attribution')


def test_sign_integration_url_is_supplied_by_test_settings(settings):
    assert settings.SIGN_INTERNAL_URL == 'http://sign.test'


def test_canonical_neutral_and_configured_lines():
    render = module().render_attribution
    assert render('page', {}) == 'Open-source software built on the Fleet.'
    assert render('email-text', {}) == 'This is open-source software built on the Fleet, open-source agentic software.'
    expected = ('Open-source software run by Acme &lt;Test&gt; &amp; &quot;Co&quot;, built on '
                '<a href="https://fleet.example.test/about?a=1&amp;b=2">the Fleet</a>. '
                '<a href="https://source.example.test/tree/0123456789">Source</a>')
    assert render('page', TENANT) == expected
    assert render('email-html', TENANT) == expected
    assert render('email-text', TENANT) == ('This is open-source software run by Acme <Test> & "Co", built on '
        'the Fleet (https://fleet.example.test/about?a=1&b=2), open-source agentic software. '
        'Source: https://source.example.test/tree/0123456789')


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'http://example.test', '//example.test',
    'https://', 'https://user:pass@example.test', 'https://example.test/\npath',
    'https://example.test/"<tag>', 'https://example.test\\@other.test', 'https://example.test:bad',
    'https://example.test:99999', 'https://exa mple.test', 'https://[broken'])
def test_unsafe_urls_are_omitted(url):
    assert module().render_attribution('page', {'FLEET_ABOUT_URL': url, 'FLEET_SOURCE_URL': url}) == 'Open-source software built on the Fleet.'


@pytest.mark.parametrize('state', ['entry', 'welcome', 'signed', 'help', 'waiting'])
def test_recipient_pages_always_include_attribution_from_settings(settings, state):
    for key, value in TENANT.items():
        setattr(settings, key, value)
    html = _render(state)
    assert module().render_attribution('page', TENANT) in html
    assert 'Powered by Fleet' not in html


@pytest.mark.parametrize('invitation', [True, False])
def test_counterparty_email_templates_always_include_both_slugs(settings, invitation):
    for key, value in TENANT.items():
        setattr(settings, key, value)
    for suffix, slug in [('html', 'email-html'), ('txt', 'email-text')]:
        html = render_to_string('dealroom_sign/emails/mail.' + suffix, {'invitation': invitation})
        assert module().render_attribution(slug, TENANT) in html
        assert 'Powered by Fleet' not in html


def test_other_mail_paths_send_both_attributed_parts(settings, mailoutbox):
    for key, value in TENANT.items():
        setattr(settings, key, value)
    for html in [None, '<html><body><p>Verification code: 123456</p></body></html>']:
        importlib.import_module('dealroom_sign.fleet_mail').send_mail('Verify', 'Verification code: 123456', 'sender@example.test',
                           ['reader@example.test'], html_message=html)
        message = mailoutbox[-1]
        assert message.body.endswith(module().render_attribution('email-text', TENANT))
        assert module().render_attribution('email-html', TENANT) in message.alternatives[0].content
        assert 'Verification code: 123456' in message.alternatives[0].content
    root = Path(__file__).resolve().parents[2]
    for relative in ['dealroom/recipient.py', 'dealroom/approvals.py', 'sharelinks/tasks.py',
                     'sharelinks/views.py', 'core/tasks.py', 'automations/emails.py']:
        assert 'from dealroom_sign.fleet_mail import send_mail' in (root / relative).read_text()


def test_broadcast_mail_has_attribution_and_keeps_personalized_body(settings, tmp_path, mailoutbox):
    for key, value in TENANT.items():
        setattr(settings, key, value)
    recipients = tmp_path / 'recipients.csv'
    recipients.write_text('email,name\nreader@example.test,Reader\n')
    template = tmp_path / 'body.txt'
    template.write_text('Hello [Name],\nRelease notes.')
    call_command('send_broadcast_email', csv=str(recipients), template=str(template),
                 subject='Release', delay=0, log_file=str(tmp_path / 'sent.log'), stdout=StringIO())
    message = mailoutbox[0]
    assert 'Hello Reader,\nRelease notes.' in message.body
    assert module().render_attribution('email-text', TENANT) in message.body
    assert module().render_attribution('email-html', TENANT) in message.alternatives[0].content
