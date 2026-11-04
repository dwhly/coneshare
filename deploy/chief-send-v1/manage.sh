#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
docker run --rm -m 768m -v "$ROOT":/src -w /src/backend -e CORE_API_URL=http://core:8080 -e INTERNAL_API_TOKEN=send-v1-local -e SECRET_KEY=send-v1-local -e DATABASE_URL=sqlite:////src/backend/dev.sqlite3 -e FIELD_ENCRYPTION_KEY=S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8= amforge-send-dev-backend:devtest python manage.py "$@"
