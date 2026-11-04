#!/usr/bin/env bash
# Build the frontend natively, overlay it on amforge-send-dev:latest, (re)start the proto container.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT/frontend"
export VITE_APP_VERSION=layout-proto VITE_GIT_SHA=$(git rev-parse --short HEAD)
export VITE_AMFORGE_SEND_URL=${VITE_AMFORGE_SEND_URL:-http://send-proto.100-110-241-2.sslip.io}
export VITE_AMFORGE_SIGN_URL=${VITE_AMFORGE_SIGN_URL:-http://sign-proto.100-110-241-2.sslip.io}
fnm exec --using=24 npm run build
docker build -f "$HERE/Dockerfile" -t "chief-send-proto:$VITE_GIT_SHA" -t chief-send-proto:latest dist
cd "$HERE" && docker compose up -d
