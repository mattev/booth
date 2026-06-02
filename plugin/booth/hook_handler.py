"""Hook handler: read event JSON from stdin, enqueue, exit fast (~20ms target).

Does NOT call the LLM or TTS — that would stall Claude Code's main loop. It only appends
the event to the queue that booth-daemon drains on its own clock.
"""
import json
import sys
import time
from pathlib import Path

QUEUE = Path.home() / ".the-booth" / "events.jsonl"
PIDFILE = Path.home() / ".the-booth" / "daemon.pid"


def main() -> int:
    # If the booth isn't running, do nothing — no queue growth, no overhead.
    # (booth-ctl writes the pidfile on `on`, removes it on `off`.)
    if not PIDFILE.exists():
        return 0

    kind = sys.argv[1] if len(sys.argv) > 1 else "event"
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {"_raw": raw}

    event = {"kind": kind, "ts": time.time(), "payload": payload}

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open("a") as f:
        f.write(json.dumps(event) + "\n")
    # Always exit 0 / no stdout so we never interfere with the session.
    return 0


if __name__ == "__main__":
    sys.exit(main())
