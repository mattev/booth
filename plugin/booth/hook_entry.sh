#!/usr/bin/env bash
# Thin shim invoked by Claude Code hooks. Receives event JSON on stdin, passes the
# event-kind arg through, and hands off to the Python handler. Must be FAST — it only
# enqueues. All heavy lifting happens in booth-daemon.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Record where the booth package lives (the dir to run `python3 -m booth.ctl` from), so the
# /booth skill can find it no matter how it was installed — plugin cache, git clone, etc.
# Hooks get CLAUDE_PLUGIN_ROOT and run from the real install path; skills don't, so we
# leave them this breadcrumb. Cheap, and only on session start.
if [ "${1:-}" = "session_start" ]; then
  mkdir -p "$HOME/.the-booth"
  printf '%s\n' "$(dirname "$HERE")" > "$HOME/.the-booth/code_path"
fi
exec python3 "$HERE/hook_handler.py" "${1:-event}"
