"""Isolated, killable PDF geometry parser. Stdin is PDF bytes; stdout is bounded JSON."""
import json
import sys
import time
from dataclasses import asdict

from .placement import PARSE_REASONS, extract


def main():
    try:
        blocks, sizes, roles = extract(sys.stdin.buffer.read(50 * 1024 * 1024 + 1),
                                      deadline=time.monotonic() + float(sys.argv[1]))
        result = {'blocks': [asdict(b) for b in blocks], 'sizes': sizes, 'roles': roles}
    except TimeoutError:
        result = {'error': 'placement_timeout'}
    except Exception as exc:
        result = {'error': str(exc) if isinstance(exc, ValueError) and str(exc) in PARSE_REASONS else 'unreadable_pdf'}
    print(json.dumps(result))


if __name__ == '__main__':
    main()
