#!/bin/sh
# Run from either worktree's backend/; local services are replaced with in-memory test services.
set -eu
export SECRET_KEY=testing
export FIELD_ENCRYPTION_KEY=S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8=
export INTERNAL_API_TOKEN=fixture-internal-api-token
export CORE_API_URL=http://127.0.0.1:18080
export DJANGO_SETTINGS_MODULE=board_room_test_settings
BOARD_ROOM_TEST_SUPPORT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$(pwd):$BOARD_ROOM_TEST_SUPPORT"
exec /root/work/sign-product/send-venv/bin/python -m pytest "$@"
