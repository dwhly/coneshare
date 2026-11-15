# C2a r2 evidence

The `*-red.txt` files capture regressions against the relevant unfixed implementation.
`h1-green.txt` proves the identity fix against all seven original goldens. Later
`engine-green.txt`, `send-suite.txt` and `board-suite.txt` cover the final code.

The native Harbor renders use Sign's existing `insertFieldInPDFV2` directly, read-only.
They are export/rendering evidence, not a deployed signing transaction or a cryptographic
seal. `render-metrics.json` measures native signature ink against the detected rule.

Reproduce from Send with the test environment outside the checkout:

```sh
UV_CACHE_DIR=/tmp/c2a-uv-cache uv venv /tmp/send-c2a-r2-venv
UV_CACHE_DIR=/tmp/c2a-uv-cache uv pip install --python /tmp/send-c2a-r2-venv/bin/python -r backend/requirements.txt
C2A_PYTHON=/tmp/send-c2a-r2-venv/bin/python docs/implementation/c2a/run_send_tests.sh backend/dealroom_sign/tests
/root/worktrees/sign-c1b/node_modules/.bin/tsx --tsconfig /root/worktrees/sign-c1b/apps/remix/tsconfig.json docs/implementation/c2a-r2/render_native.ts docs/implementation/c2a-r2
PYTHONPATH=backend /tmp/send-c2a-r2-venv/bin/python docs/implementation/c2a-r2/render_fixtures.py
```

Board tests on this host preload the installed Hermes dashboard module without changing
HOME or writing outside the worktrees. From Board:

```sh
/root/work/sign-product/board-venv/bin/python -c "from hermes_board.sources.hermes_kanban import _plugin_api; _plugin_api('/usr/local/lib/hermes-agent'); import pytest; raise SystemExit(pytest.main(['-q','tests']))"
```

The initial Board run could not find the host's dashboard module at its default path;
preloading its actual install fixed the test environment. The authoritative Board red
run restored all three production files from `ce62d68` inside `try/finally`, ran the
new assertions, and restored r2. The baseline cloud-edition run did the same.

Placement settings: `PLACEMENT_TOTAL_SECONDS` defaults to 12 s (maximum 20), and
`PLACEMENT_PARSE_SECONDS` defaults to 3 s (maximum 8, also bounded by time remaining).
Invalid settings use the defaults. Parser processes are killed and reaped on timeout.
The model call is supervised by the remaining total deadline, uses the remaining time
as its HTTP timeout, and permits at most four concurrent provider calls per process.

Board persists upload-to-submission mappings beside its existing state file in
`signatures.submissions.sqlite3`. Keep this file with the Board state volume. Retries
reuse the version even after a restart. The stable key covers room, PDF SHA-256,
ordered signers, board and card. Existing-room hashes come from an authorized selected
source query; the ordinary source listing does not read every PDF.
