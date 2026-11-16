"""Exercise model read limits against a real loopback HTTP socket."""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from dealroom_sign import placement


def test_blocked_socket_releases_model_slot_within_read_grace(monkeypatch):
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200)
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            try:
                for _ in range(3):
                    self.wfile.write(b'1\r\n \r\n')
                    self.wfile.flush()
                    if release.wait(1.4):
                        return
                release.wait(5)
            except OSError:
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client_class = httpx.Client

    class LocalClient(client_class):
        def __init__(self, **kwargs):
            super().__init__(trust_env=False, **kwargs)

        def stream(self, method, url, **kwargs):
            return super().stream(method, f'http://127.0.0.1:{server.server_port}/', **kwargs)

    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(placement, 'MODEL_SLOTS', slots)
    monkeypatch.setattr(placement.httpx, 'Client', LocalClient)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fictional-local-key')
    monkeypatch.setenv('PLACE_MODEL', 'fixture/local')
    start = time.monotonic()
    try:
        with pytest.raises((TimeoutError, httpx.TimeoutException)):
            placement.bounded_model(None, {}, start + 3)
        assert time.monotonic() - start < 3.5
        assert slots.acquire(timeout=max(0, start + 5.2 - time.monotonic())), 'blocked recv retained the model slot beyond the two-second read grace'
        slots.release()
    finally:
        release.set()
        server.shutdown()
        server.server_close()
