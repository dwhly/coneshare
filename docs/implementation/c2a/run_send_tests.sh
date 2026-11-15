#!/bin/sh
set -eu
C2A_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$C2A_ROOT"
export SECRET_KEY=testing
export FIELD_ENCRYPTION_KEY=S-c9WBE3DEJE2R7i-b-sOmegRChW2McTDIOWcrG0-C8=
export DJANGO_SETTINGS_MODULE=dealroom_sign.test_settings
export PYTHONPATH="$C2A_ROOT/backend"
export REDIS_URL=redis://127.0.0.1:16379
export INTERNAL_API_TOKEN=dummy-internal-api-token-for-ci
export CORE_API_URL=http://127.0.0.1:18080
exec "${C2A_PYTHON:-$C2A_ROOT/.agent/c2a-venv/bin/python}" -m pytest "$@" -q --disable-warnings
