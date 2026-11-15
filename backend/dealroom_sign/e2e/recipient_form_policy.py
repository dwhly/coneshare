"""Explicit Chromium test against disposable HTTPS Django, with native Sign stubbed.

Run with the Send pytest runner and this file as its target. PLAYWRIGHT_MODULE
locates the Node package. R6_TEST_OLD_REFERRER_POLICY reproduces the old document
policy as a test-only mutation; the same acceptance assertions must then fail.
"""
import os
import ssl
import subprocess
import threading
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest
from django.core.handlers.wsgi import WSGIHandler
from django.http import HttpResponse
from django.template.loader import render_to_string

from dealroom_sign.counterparty import capability
from dealroom_sign.tests.test_counterparty import access
from dealroom_sign.tests.test_workflows import envelope, fixture, pdf, recipients

pytestmark = pytest.mark.django_db(transaction=True)


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass  # Keep personal capability paths out of test output.


def test_chromium_iphone_real_consent_form(access, tmp_path, settings):
    access.context.update(title='Harbor Light Mutual NDA (Nov 15 1511).pdf', pages=1)
    access.sender = {'name': 'Drew Whaley', 'email': 'dwhaley@amforge.com'}
    access.save()
    cert, key = tmp_path/'cert.pem', tmp_path/'key.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
        '-keyout', str(key), '-out', str(cert), '-subj', '/CN=recipient.test'],
        check=True, capture_output=True)
    django_app = WSGIHandler()
    def listener(environ, start_response):
        environ.update(HTTP_X_FLEET_RECIPIENT_LISTENER='1', HTTP_X_FORWARDED_FOR='127.0.0.1')
        environ['wsgi.url_scheme'] = 'https'
        return django_app(environ, start_response)
    # A serial server avoids SQLite's parallel session-heartbeat write limitation.
    server = make_server('127.0.0.1', 0, listener, handler_class=QuietHandler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    origin = f'https://recipient.test:{server.server_port}'
    settings.SIGN_RECIPIENT_ORIGIN = origin
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, 'recipient.test']
    env = {**os.environ, 'RECIPIENT_ENTRY_URL': origin + '/s/' + capability(access)}
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    with ExitStack() as stack:
        stack.enter_context(patch('dealroom_sign.recipient_proxy.reconcile_native', return_value=envelope(access.workflow)))
        stack.enter_context(patch('dealroom_sign.recipient_proxy.forward',
            side_effect=lambda *args: HttpResponse('<h1>Native signing fixture</h1>')))
        if os.environ.get('R6_TEST_OLD_REFERRER_POLICY'):
            stack.enter_context(patch('dealroom_sign.recipient_proxy.referrer_policy', return_value='no-referrer'))
            stack.enter_context(patch('dealroom_sign.recipient_proxy.render_to_string',
                side_effect=lambda *args, **kwargs: render_to_string(*args, **kwargs).replace(
                    'name="referrer" content="same-origin"', 'name="referrer" content="no-referrer"')))
        thread.start()
        try:
            result = subprocess.run(['node', str(Path(__file__).with_name('recipient-form-policy.cjs'))],
                env=env, text=True, capture_output=True, timeout=60)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
    print(result.stdout)
    assert result.returncode == 0, result.stderr
    access.refresh_from_db()
    assert access.sessions.filter(consented_at__isnull=False).exists()
