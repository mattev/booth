"""Pacing helpers: turn a raw burst of session events into something worth calling.

Two jobs, both pure functions over the daemon's event dicts ({kind, desc, tool?, hint?}):

- coalesce(): collapse consecutive same-tool events into one beat, so "Read 10 files" is
  called as "studying the scouting report (×10)" instead of ten separate routine plays.
- detect_big_moment(): spot a genuine win (tests pass, build green) so the daemon can send
  that tick to the bigger model for a real crescendo.

The rolling "game so far" memory lives in commentary (it's LLM-summarized), not here.
"""

# Only tool activity coalesces; a prompt or a stop is always its own beat.
_MERGEABLE = {"pre_tool", "post_tool"}

# A win shows up as one of these in an event description, with no failure word alongside it.
_WIN_WORDS = ("passed", "success", "succeeded", "green", "0 failed", "all tests pass", "ok")
_LOSS_WORDS = ("failed", "error", "traceback", "exception", "fatal", "✗")


def _tool_of(e):
    if e.get("tool"):
        return e["tool"]
    parts = (e.get("desc") or "").split()
    if len(parts) >= 2 and parts[0] in _MERGEABLE:
        return parts[1]
    return ""


def _target_of(e):
    if e.get("hint"):
        return e["hint"]
    # desc like "post_tool Read server.py" -> "server.py"
    parts = (e.get("desc") or "").split(None, 2)
    return parts[2] if len(parts) >= 3 else ""


def coalesce(events, max_beats=12):
    """Merge consecutive same-(kind, tool) events into single beats; keep the tail.

    Returns a list of {kind, desc, tool, count} dicts. A run of n>1 becomes one beat like
    'post_tool Read ×6 (auth/login.py, auth/session.py, auth/token.py, …)'. Non-tool events
    and lone tool calls pass through with count=1.
    """
    runs = []
    for e in events:
        kind = e.get("kind")
        tool = _tool_of(e)
        if (runs and kind in _MERGEABLE and tool
                and runs[-1]["kind"] == kind and runs[-1]["tool"] == tool):
            run = runs[-1]
            run["count"] += 1
            tgt = _target_of(e)
            if tgt:
                run["targets"].append(tgt)
        else:
            tgt = _target_of(e)
            runs.append({"kind": kind, "tool": tool, "count": 1,
                         "targets": [tgt] if tgt else [], "desc": e.get("desc", "")})

    out = []
    for run in runs:
        if run["count"] > 1 and run["tool"]:
            shown = ", ".join(run["targets"][:3])
            more = ", …" if len(run["targets"]) > 3 else ""
            tail = f" ({shown}{more})" if shown else ""
            desc = f"{run['kind']} {run['tool']} ×{run['count']}{tail}"
        else:
            desc = run["desc"]
        out.append({"kind": run["kind"], "desc": desc,
                    "tool": run["tool"], "count": run["count"]})
    return out[-max_beats:]


def detect_big_moment(events):
    """True if any beat reads as a genuine win (a win word, no failure word alongside it)."""
    for e in events:
        d = (e.get("desc") or "").lower()
        if any(w in d for w in _WIN_WORDS) and not any(l in d for l in _LOSS_WORDS):
            return True
    return False
