"""Resource bounds are measured with local children and fake model streams."""
import json
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import FIXTURES, LEE, no_network  # noqa: F401


def test_parse_burst_beyond_slots_holds_without_starting_child(monkeypatch):
    monkeypatch.setattr(placement, 'PARSE_SLOTS', threading.BoundedSemaphore(2), raising=False)
    entered, release = threading.Barrier(3), threading.Event()
    class Child:
        returncode = 0
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def communicate(self, *args, **kwargs):
            entered.wait(timeout=3)
            release.wait(timeout=3)
            return json.dumps({'blocks': [], 'sizes': {}, 'roles': {}}).encode(), b''
    popen = Mock(side_effect=lambda *a, **k: Child())
    monkeypatch.setattr(placement.subprocess, 'Popen', popen)
    with ThreadPoolExecutor(3) as pool:
        active = [pool.submit(placement.place, b'%PDF', LEE) for _ in range(2)]
        entered.wait(timeout=3)
        try:
            held = pool.submit(placement.place, b'%PDF', LEE).result(timeout=1)
            assert held['reason_code'] == 'placement_busy'
            assert popen.call_count == 2
        finally:
            release.set()
        for future in active:
            future.result(timeout=4)
    assert placement.PARSE_SLOTS.acquire(blocking=False)
    placement.PARSE_SLOTS.release()


@pytest.mark.parametrize('returncode,output', [(1, b''), (-9, b''), (0, b''), (0, b'{bad')])
def test_failed_child_is_unavailable_not_bad_document(monkeypatch, returncode, output):
    child = Mock(returncode=returncode)
    child.__enter__ = Mock(return_value=child)
    child.__exit__ = Mock(return_value=False)
    child.communicate.return_value = output, b''
    monkeypatch.setattr(placement.subprocess, 'Popen', Mock(return_value=child))
    result = placement.place(b'%PDF', LEE)
    assert result['reason_code'] == 'placement_unavailable'
    assert result['fields'] == []


def test_child_has_minimal_env_and_works_outside_backend(monkeypatch, tmp_path):
    original = subprocess.Popen
    seen = []
    def launch(*args, **kwargs):
        seen.append(kwargs)
        return original(*args, **kwargs)
    monkeypatch.setenv('SECRET_KEY', 'fictional-secret')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fictional-key')
    monkeypatch.setenv('DATABASE_URL', 'fictional-db')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(placement.subprocess, 'Popen', launch)
    result = placement.place((FIXTURES / 'harbor.pdf').read_bytes(), LEE)
    assert result['status'] == 'placed', result
    assert not {'SECRET_KEY', 'OPENROUTER_API_KEY', 'DATABASE_URL', 'PYTHONPATH'} & set(seen[0]['env'])
    assert Path(seen[0]['cwd']) == Path(placement.__file__).resolve().parents[1]


def test_worker_health_reports_enforced_memory_and_cpu_limits():
    run = subprocess.run([sys.executable, '-m', 'dealroom_sign.placement_worker', '--health'],
                         cwd=Path(placement.__file__).resolve().parents[1], capture_output=True, timeout=3)
    health = json.loads(run.stdout)
    assert health['status'] == 'ok'
    assert health['memory_bytes'] == 768 * 1024 * 1024
    assert 0 < health['cpu_seconds'] <= 8


def compressed_large_pdf():
    compressor = zlib.compressobj()
    compressed = b''.join(compressor.compress(b' ' * (1024 * 1024)) for _ in range(600)) + compressor.flush()
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>',
               b'<< /Length ' + str(len(compressed)).encode() + b' /Filter /FlateDecode >>\nstream\n' + compressed + b'\nendstream']
    out = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(out)
    out += b'xref\n0 5\n0000000000 65535 f \n'
    out += b''.join(f'{n:010} 00000 n \n'.encode() for n in offsets[1:])
    out += f'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    return bytes(out)


def test_flate_expansion_is_bounded_and_parent_rss_stays_flat(monkeypatch):
    pdf = compressed_large_pdf()
    original = subprocess.Popen
    # The red implementation has no cap. Keep the regression safe on that version too.
    def supervised(*args, **kwargs):
        kwargs['preexec_fn'] = lambda: resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        return original(*args, **kwargs)
    monkeypatch.setattr(placement.subprocess, 'Popen', supervised)
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    start = time.monotonic()
    result = placement.place(pdf, LEE)
    elapsed = time.monotonic() - start
    growth_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before
    assert result['status'] == 'needs_sender'
    assert result['reason_code'] == 'parse_limit', result
    assert elapsed < 4
    assert growth_kib < 32 * 1024
    print(f'flate input={len(pdf)} bytes, expanded=600 MiB, elapsed={elapsed:.2f}s, parent RSS growth={growth_kib} KiB')


def test_slow_dripping_model_releases_slot_at_total_deadline(monkeypatch):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(placement, 'MODEL_SLOTS', slots)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fictional-provider-key')
    monkeypatch.setenv('PLACE_MODEL', 'fixture/model')
    closed = threading.Event()
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): closed.set()
        def raise_for_status(self): pass
        def iter_bytes(self):
            for _ in range(100):
                time.sleep(.02)
                yield b' '
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.stream.return_value = Stream()
    monkeypatch.setattr(placement.httpx, 'Client', Mock(return_value=client))
    with pytest.raises(TimeoutError):
        placement.bounded_model(None, {}, time.monotonic() + .1)
    assert closed.wait(.3), 'per-read timeout let the upstream retain a model slot'
    assert slots.acquire(blocking=False)
    slots.release()


def test_parse_timeout_kills_reaps_and_releases_slot(monkeypatch):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(placement, 'PARSE_SLOTS', slots)
    child = Mock(returncode=-9)
    child.__enter__ = Mock(return_value=child)
    child.__exit__ = Mock(return_value=False)
    child.communicate.side_effect = [subprocess.TimeoutExpired('parser', 3), (b'', b'')]
    monkeypatch.setattr(placement.subprocess, 'Popen', Mock(return_value=child))
    result = placement.place(b'%PDF', LEE)
    assert result['reason_code'] == 'placement_timeout'
    child.kill.assert_called_once()
    assert child.communicate.call_count == 2
    assert slots.acquire(blocking=False)
    slots.release()


def test_model_total_budget_closes_transport_even_without_decoded_chunks(monkeypatch):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(placement, 'MODEL_SLOTS', slots)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fictional-provider-key')
    monkeypatch.setenv('PLACE_MODEL', 'fixture/model')
    closed, exited = threading.Event(), threading.Event()
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): exited.set()
        def raise_for_status(self): pass
        def iter_bytes(self):
            closed.wait(2)
            raise TimeoutError
            yield b''
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.close.side_effect = closed.set
    client.stream.return_value = Stream()
    monkeypatch.setattr(placement.httpx, 'Client', Mock(return_value=client))
    with pytest.raises(TimeoutError):
        placement.bounded_model(None, {}, time.monotonic() + .1)
    assert closed.wait(.3), 'total deadline did not close the HTTP transport'
    assert exited.wait(.3)
    assert slots.acquire(blocking=False)
    slots.release()
