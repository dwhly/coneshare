#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
CHECKOUT=${CHECKOUT:-$(cd "$HERE/../.." && pwd)}
docker network inspect chief-send-v1-test >/dev/null 2>&1 || docker network create chief-send-v1-test >/dev/null
if ! docker inspect chief-send-v1-test-redis >/dev/null 2>&1; then
 docker run -d --name chief-send-v1-test-redis --network chief-send-v1-test --network-alias redis -m 64m redis:6.2.14-alpine redis-server --maxmemory 32mb --maxmemory-policy allkeys-lru >/dev/null
fi
if ! docker inspect chief-send-v1-test-core >/dev/null 2>&1; then
 docker run -d --name chief-send-v1-test-core --network chief-send-v1-test --network-alias core -m 64m -e INTERNAL_API_TOKEN=send-v1-test -e STORAGE_PATH=/tmp/storage -e PORT=8080 amforge-send-dev-core:latest >/dev/null
fi
docker run --rm -m 1280m --network chief-send-v1-test -v "$CHECKOUT":/src -w /src/backend -e SECRET_KEY=send-v1-test -e DATABASE_URL=sqlite:////tmp/tests.sqlite3 -e REDIS_URL=redis://redis:6379 -e CELERY_TASK_ALWAYS_EAGER=True -e INTERNAL_API_TOKEN=send-v1-test -e FIELD_ENCRYPTION_KEY=S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8= -e CORE_API_URL=http://core:8080 amforge-send-dev-backend:devtest python -m pytest "$@" -q -p no:cacheprovider -rfE
