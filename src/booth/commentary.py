"""Commentary engine: a batch of session events -> a few lines of booth banter.

M0: real Anthropic call over plain HTTP (no SDK dependency). The persona system prompt is
large and static, so it's marked for PROMPT CACHING. If there's no API key or the call
fails, we fall back to template lines so the booth always talks.

Returns: list[{"speaker": str, "text": str}]
"""
import json
import os
import re
import urllib.error
import urllib.request

from . import personas

MODEL_FAST = "claude-haiku-4-5"
MODEL_BIG = "claude-sonnet-4-6"
API_URL = "https://api.anthropic.com/v1/messages"

SCHEMA_HINT = (
    'Return ONLY a JSON array, no prose, like: '
    '[{"speaker":"miller","text":"..."},{"speaker":"kuiper","text":"..."}]. '
    'Use 2-3 short lines. Valid speakers: miller, kuiper, flemming.'
)


def call(events, pack="giants", memory="", big_moment=False, chatty="lively"):
    """Generate booth banter for a batch of events. Falls back to templates on any error."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _template(events)
    try:
        return _llm(events, pack, memory, big_moment, chatty, key)
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return _template(events)


def _llm(events, pack, memory, big_moment, chatty, key):
    system = personas.system_prompt(pack) + (
        "\n\nBe LIVELY — call most plays." if chatty == "lively"
        else "\n\nBe SELECTIVE — only call notable moments; otherwise return []."
    )
    body = {
        "model": MODEL_BIG if big_moment else MODEL_FAST,
        "max_tokens": 320,
        "system": [{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},  # cache the static personas
        }],
        "messages": [{"role": "user", "content": _render(events, memory)}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    return _parse(text)


def _parse(text):
    """Pull the JSON array out of the model's reply, tolerate stray prose/fences."""
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    lines = json.loads(m.group(0))
    valid = set(personas.PACKS["giants"]["announcers"])
    return [l for l in lines if l.get("speaker") in valid and l.get("text")]


def _render(events, memory):
    plays = "\n".join(f"- {e}" for e in events) or "- (warming up)"
    mem = f"Game so far: {memory}\n\n" if memory else ""
    return f"{mem}Latest plays in the Claude Code session:\n{plays}\n\n{SCHEMA_HINT}"


# --- zero-dependency fallback so the booth always talks --------------------------------

def _template(events):
    out = []
    for e in events:
        kind = e.get("kind") if isinstance(e, dict) else str(e)
        if kind == "prompt":
            out.append({"speaker": "miller", "text": "Here's the windup — a new request comes in from the dugout."})
        elif kind == "pre_tool":
            out.append({"speaker": "flemming", "text": "Claude steps in, takes a look at the next pitch."})
        elif kind == "post_tool":
            out.append({"speaker": "kuiper", "text": "Routine play, gets it over to first. Nothing fancy."})
        elif kind == "stop":
            out.append({"speaker": "miller", "text": "And that'll do it for the half-inning. Back to you."})
        elif kind == "session_start":
            out.append({"speaker": "miller", "text": "Good evening everybody, and welcome to the ballpark."})
    return out[:3] or [{"speaker": "kuiper", "text": "Quiet out there. Grab some pine."}]
