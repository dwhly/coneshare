#!/usr/bin/env bash
# Manager: use an isolated PostgreSQL test database; never a running Dealroom stack.
set -euo pipefail
: "${S2_POSTGRES_TEST_URL:?Set an isolated PostgreSQL test database URL}"
: "${S2_PYTHON:?Set the backend virtualenv Python executable}"
cd "$(dirname "$0")/../../../backend"
export DATABASE_URL="$S2_POSTGRES_TEST_URL"
export DJANGO_SETTINGS_MODULE=s2_postgres_settings
export PYTHONPATH="$PWD:$PWD/../docs/implementation/board-room-s2"
exec "$S2_PYTHON" -m pytest tests/s2_postgres tests/dealroom/test_room_commands_s2.py -q "$@"
