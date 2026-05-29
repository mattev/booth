#!/usr/bin/env bash
# Thin shim invoked by Claude Code hooks. Receives event JSON on stdin, passes the
# event-kind arg through, and hands off to the Python handler. Must be FAST — it only
# enqueues. All heavy lifting happens in booth-daemon.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/hook_handler.py" "${1:-event}"
