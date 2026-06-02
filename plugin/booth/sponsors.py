"""Sponsor reads — on-theme, in-character tip-jar asks. Rate-limited and disable-able.

Instead of a popup, the booth does a 'today's broadcast is brought to you by...' read,
written in-voice by the commentary engine, at natural breaks (never mid-action).
"""
import time

_last_read_ts = 0.0


def maybe_inject(lines, cfg):
    """Append a sponsor read to `lines` at most once per `cfg.sponsor_interval_s`."""
    global _last_read_ts
    if not cfg.sponsors_enabled:
        return lines
    if time.time() - _last_read_ts < cfg.sponsor_interval_s:
        return lines

    _last_read_ts = time.time()
    handle = cfg.donate_handle or "the tip jar"
    lines = list(lines) + [
        {"speaker": "miller",
         "text": f"And today's broadcast is brought to you by you, the listener — "
                 f"if you're enjoying the call, send a little something to {handle}."},
        {"speaker": "kuiper", "text": "Don't be shy now. The booth runs on it."},
    ]
    # The daemon/player should also print a clickable donate line to the terminal.
    return lines
