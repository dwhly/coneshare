"""Disposable parser. stdin: signer JSON line then PDF; stdout: sanitized JSON.

Run ``python -m dealroom_sign.placement_worker --health`` to check imports and
OS resource limits. Limits apply before importing the PDF parser or reading stdin.
"""
import json
import math
import resource
import sys
import time
import zlib
from dataclasses import asdict

MEMORY_BYTES = 768 * 1024 * 1024
CPU_SECONDS = min(8, max(1, math.ceil(float(sys.argv[1])) + 1)) if sys.argv[1:2] != ['--health'] else 8
resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))

# Import only after the limits cover parser startup as well as extraction.
from .placement import PARSE_REASONS, extract, prepare_blocks  # noqa: E402


def main():
    if sys.argv[1:2] == ['--health']:
        print(json.dumps({'status': 'ok', 'memory_bytes': resource.getrlimit(resource.RLIMIT_AS)[0],
                          'cpu_seconds': resource.getrlimit(resource.RLIMIT_CPU)[0]}))
        return
    try:
        signers = json.loads(sys.stdin.buffer.readline(65536))
        blocks, sizes, roles = extract(sys.stdin.buffer.read(50 * 1024 * 1024 + 1),
                                      deadline=time.monotonic() + float(sys.argv[1]))
        prepare_blocks(blocks, roles, signers)
        result = {'blocks': [asdict(b) for b in blocks], 'sizes': sizes, 'roles': roles}
    except TimeoutError:
        result = {'error': 'placement_timeout'}
    except MemoryError:
        result = {'error': 'parse_limit'}
    except zlib.error as exc:
        result = {'error': 'parse_limit' if 'Error -4' in str(exc) else 'unreadable_pdf'}
    except Exception as exc:
        # pdfplumber wraps parser exceptions, including allocation failures.
        cause = exc
        for _ in range(8):
            if isinstance(cause, MemoryError) or (isinstance(cause, zlib.error) and 'Error -4' in str(cause)):
                result = {'error': 'parse_limit'}
                break
            cause = cause.__cause__ or cause.__context__
            if cause is None:
                result = {'error': str(exc) if isinstance(exc, ValueError) and str(exc) in PARSE_REASONS else 'unreadable_pdf'}
                break
        else:
            result = {'error': 'unreadable_pdf'}
    print(json.dumps(result))


if __name__ == '__main__':
    main()
