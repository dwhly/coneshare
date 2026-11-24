#!/usr/bin/env bash
# Disposable test-only PostgreSQL. No Compose project or existing container is used.
set -euo pipefail
cd "$(dirname "$0")/../../.."
S2_PG_NAME="board-room-s2-pg-test-$$"
S2_PG_ID=$(docker run --rm -d --name "$S2_PG_NAME" --label purpose=board-room-s2-tests \
  -e POSTGRES_PASSWORD=fixture-only -e POSTGRES_DB=s2 -p 127.0.0.1::5432 \
  --tmpfs /var/lib/postgresql/data postgres:16)
trap 'docker rm -f "$S2_PG_ID" >/dev/null' EXIT
for attempt in $(seq 1 30); do
  if docker exec "$S2_PG_ID" pg_isready -U postgres -d s2 >/dev/null; then break; fi
  sleep 1
done
S2_PG_PORT=$(docker port "$S2_PG_ID" 5432/tcp)
export S2_POSTGRES_TEST_URL="postgres://postgres:fixture-only@${S2_PG_PORT}/s2"
export S2_PYTHON=${S2_PYTHON:-/root/work/sign-product/send-venv/bin/python}
export SECRET_KEY=fixture-secret-at-least-thirty-two-characters
export FIELD_ENCRYPTION_KEY=S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8=
export INTERNAL_API_TOKEN=fixture CORE_API_URL=http://127.0.0.1:18080
bash docs/implementation/board-room-s2/run-postgres-tests.sh "$@"
