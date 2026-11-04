#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
"$HERE/manage.sh" dealroom_registry
"$HERE/manage.sh" spectacular --file /src/deploy/chief-send-v1/out/openapi.yaml
"$ROOT/mcp-server/.venv/bin/python" "$ROOT/mcp-server/scripts/generate_registry_tools.py"
git -C "$ROOT" diff --exit-code -- backend/dealroom/operations.json mcp-server/coneshare_mcp/dealroom_tools.json
"$HERE/test-backend.sh" tests/dealroom
