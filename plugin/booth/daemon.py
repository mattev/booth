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

from . import commentary, config, pacing, player, sponsors
from .hook_handler import QUEUE


MUTE = Path.home() / ".the-booth" / "muted"  # presence = muted (set by booth-ctl)


def run() -> None:
    cursor = _count_lines(QUEUE)  # start at the tail; don't replay old events
    memory = ""                   # rolling "game so far" — fed to commentary for callbacks
    awaiting_pitch = False        # a prompt landed but the first tool hasn't — thinking gap
    pitch_ts = 0.0                # monotonic time the at-bat began (for the gap threshold)
    while True:
        cfg = config.load()       # reload each loop so on/off/mute apply live
        if not cfg.enabled:
            time.sleep(cfg.cadence)
            continue
        batch, cursor = _drain(cursor)  # always advance cursor, even when muted
        now = time.monotonic()
        if batch and not MUTE.exists() and not player.is_backed_up():
            beats = pacing.coalesce(batch)
            big = pacing.detect_big_moment(beats)
            lines = commentary.call(beats, pack=cfg.pack, memory=memory,
                                    big_moment=big, chatty="lively")
            lines = sponsors.maybe_inject(lines, cfg)
            for line in lines:
                player.enqueue(line, pack=cfg.pack, backend=cfg.tts_backend)
            # Fold these plays into the story so the next call can reference them. The player
            # speaks on its own thread, so this extra call doesn't create dead air.
            memory = commentary.summarize(memory, beats)
            awaiting_pitch, pitch_ts = _pitch_state(beats, awaiting_pitch, pitch_ts, now)
        elif (awaiting_pitch and cfg.thinking_color_enabled and not MUTE.exists()
              and not player.is_backed_up() and now - pitch_ts >= cfg.thinking_gap_s):
            # Claude is still thinking before its first move — fill the dead air, once.
            for line in commentary.thinking_gap(memory, pack=cfg.pack):
                player.enqueue(line, pack=cfg.pack, backend=cfg.tts_backend)
            awaiting_pitch = False
        time.sleep(cfg.cadence)


def _pitch_state(beats, awaiting, pitch_ts, now):
    """Track the pre-first-pitch gap: a prompt opens an at-bat; any tool/stop closes the gap.

    Scans this tick's beats in order so a fast prompt→tool burst correctly ends not-awaiting.
    """
    for b in beats:
        kind = b.get("kind")
        if kind == "prompt":
            awaiting, pitch_ts = True, now      # at-bat starts; awaiting the first pitch
        elif kind in ("pre_tool", "post_tool", "stop"):
            awaiting = False                    # the pitch came (or inning ended)
    return awaiting, pitch_ts


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
        return {"kind": kind, "desc": f"user asked: {text}", "tool": "", "hint": ""}
    if kind in ("pre_tool", "post_tool"):
        target = p.get("tool_input", {})
        hint = str(target.get("file_path") or target.get("command") or target.get("pattern") or "")[:80]
        return {"kind": kind, "tool": tool, "hint": hint,
                "desc": f"{kind} {tool} {hint}".strip()}
    return {"kind": kind, "desc": kind, "tool": "", "hint": ""}


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as f:
        return sum(1 for _ in f)


if __name__ == "__main__":
    run()
