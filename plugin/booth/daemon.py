"""booth-daemon: the long-lived process that turns the event queue into audio.

M0 loop:
  1. Drain new events from ~/.the-booth/events.jsonl (every `cadence` seconds).
  2. If anything's waiting AND the player isn't backed up, summarize the batch.
  3. Ask the commentary engine for booth banter (3 voices) -> speak them, no overlap.

Run:  python3 -m booth.daemon
TODO(M1): rolling "game so far" memory, smarter coalescing, big-moment detection.
"""
import json
import time
from pathlib import Path

from . import commentary, config, player, sponsors
from .hook_handler import QUEUE


MUTE = Path.home() / ".the-booth" / "muted"  # presence = muted (set by booth-ctl)


def run() -> None:
    cursor = _count_lines(QUEUE)  # start at the tail; don't replay old events
    while True:
        cfg = config.load()       # reload each loop so on/off/mute apply live
        if not cfg.enabled:
            time.sleep(cfg.cadence)
            continue
        batch, cursor = _drain(cursor)  # always advance cursor, even when muted
        if batch and not MUTE.exists() and not player.is_backed_up():
            lines = commentary.call(batch, pack=cfg.pack, chatty="lively")
            lines = sponsors.maybe_inject(lines, cfg)
            for line in lines:
                player.enqueue(line, pack=cfg.pack, backend=cfg.tts_backend)
        time.sleep(cfg.cadence)


def _drain(cursor):
    """Read events appended past `cursor`. Returns (events, new_cursor)."""
    if not QUEUE.exists():
        return [], cursor
    events = []
    new_cursor = cursor
    with QUEUE.open() as f:
        for i, raw in enumerate(f):
            if i < cursor:
                continue
            new_cursor = i + 1
            try:
                e = json.loads(raw)
                events.append(_summarize(e))
            except json.JSONDecodeError:
                continue
    return events, new_cursor


def _summarize(event):
    """Compress a raw hook event into a short, LLM-friendly description."""
    kind = event.get("kind", "event")
    p = event.get("payload", {})
    tool = p.get("tool_name") or p.get("tool") or ""
    if kind == "prompt":
        text = (p.get("prompt") or p.get("user_prompt") or "")[:160]
        return {"kind": kind, "desc": f"user asked: {text}"}
    if kind in ("pre_tool", "post_tool"):
        target = p.get("tool_input", {})
        hint = target.get("file_path") or target.get("command") or target.get("pattern") or ""
        return {"kind": kind, "desc": f"{kind} {tool} {str(hint)[:80]}".strip()}
    return {"kind": kind, "desc": kind}


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as f:
        return sum(1 for _ in f)


if __name__ == "__main__":
    run()
