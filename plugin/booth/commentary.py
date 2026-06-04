"""Commentary engine: a batch of session events -> a few lines of booth banter.

M0: real Anthropic call over plain HTTP (no SDK dependency). The persona system prompt is
large and static, so it's marked for PROMPT CACHING. If there's no API key or the call
fails, we fall back to template lines so the booth always talks.

Returns: list[{"speaker": str, "text": str}]
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

from . import config, personas

MODEL_FAST = "claude-haiku-4-5"
MODEL_BIG = "claude-sonnet-4-6"
API_URL = "https://api.anthropic.com/v1/messages"

SCHEMA_HINT = (
    'Return ONLY a JSON array, no prose, like: '
    '[{"speaker":"miller","text":"..."},{"speaker":"kuiper","text":"..."}]. '
    'Use 2-3 short lines. Valid speakers: miller, kuiper, flemming.'
)


def _resolve_key():
    """Config key wins over the env var: detached daemons often inherit a stale env."""
    return config.load().anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")


def call(events, pack="giants", memory="", big_moment=False, chatty="lively"):
    """Generate booth banter for a batch of events. Falls back to templates on any error."""
    return generate(events, pack, memory, big_moment, chatty)["lines"]


def generate(events, pack="giants", memory="", big_moment=False, chatty="lively", model=None):
    """Like call(), but returns a result dict with metadata for evals/diagnostics:
    {lines, model, fallback, error, input_tokens, output_tokens, latency_s}.
    `model` overrides the default fast/big choice (used by the eval harness).
    """
    key = _resolve_key()
    chosen = model or (MODEL_BIG if big_moment else MODEL_FAST)
    # Nothing happened this tick — say nothing. (No filler "welcome to the ballpark".)
    if not events:
        return _result([], chosen, fallback=False)
    if not key:
        return _result(_template(events), chosen, fallback=True, error="no api key")
    t0 = time.time()
    try:
        lines, usage = _llm_raw(events, pack, memory, chatty, key, chosen)
        return _result(lines, chosen, fallback=False,
                       latency_s=time.time() - t0,
                       in_tok=usage.get("input_tokens", 0),
                       out_tok=usage.get("output_tokens", 0))
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as e:
        return _result(_template(events), chosen, fallback=True,
                       error=str(e)[:120], latency_s=time.time() - t0)


def _result(lines, model, fallback, error=None, latency_s=0.0, in_tok=0, out_tok=0):
    return {"lines": lines, "model": model, "fallback": fallback, "error": error,
            "input_tokens": in_tok, "output_tokens": out_tok, "latency_s": latency_s}


def _llm_raw(events, pack, memory, chatty, key, model):
    """Make the API call. Returns (lines, usage_dict). Raises on transport/parse errors."""
    system = personas.system_prompt(pack) + (
        "\n\nBe LIVELY — call most plays." if chatty == "lively"
        else "\n\nBe SELECTIVE — only call notable moments; otherwise return []."
    )
    body = {
        "model": model,
        "max_tokens": 320,
        "system": [{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},  # cache the static personas
        }],
        "messages": [{"role": "user", "content": _render(events, memory)}],
    }
    data = _post(body, key)
    text = "".join(b.get("text", "") for b in data.get("content", []))
    return _parse(text), data.get("usage", {})


def _post(body, key, timeout=20):
    """POST a messages-API request and return the parsed JSON. Raises on transport errors."""
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


MEMORY_SYS = (
    "You keep a terse running 'story so far' for a booth calling a live coding session as a "
    "baseball game. Given the previous summary and the latest plays, reply with an UPDATED "
    "summary in 1-2 short sentences (max ~40 words), plain text only — no JSON, no preamble. "
    "Always preserve the original ask and any notable wins (tests pass, build green) or errors "
    "so the announcers can call back to them later."
)


def summarize(prev_memory, events, model=None):
    """Fold the latest plays into a compact running memory string for callbacks.

    Cheap Haiku call. Fails soft: returns the previous memory unchanged on any error or with
    no key/events, so the rolling memory never breaks (or blocks) the daemon loop.
    """
    key = _resolve_key()
    if not key or not events:
        return prev_memory
    plays = "\n".join(f"- {_desc(e)}" for e in events)
    body = {
        "model": model or MODEL_FAST,
        "max_tokens": 160,
        "system": MEMORY_SYS,
        "messages": [{
            "role": "user",
            "content": f"Previous summary: {prev_memory or '(none yet)'}\n\n"
                       f"Latest plays:\n{plays}\n\nUpdated summary:",
        }],
    }
    try:
        data = _post(body, key, timeout=15)
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return prev_memory
    text = "".join(b.get("text", "") for b in data.get("content", [])).strip()
    return text[:400] or prev_memory


def _parse(text):
    """Pull the JSON array out of the model's reply, tolerate stray prose/fences."""
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    lines = json.loads(m.group(0))
    valid = set(personas.PACKS["giants"]["announcers"])
    return [l for l in lines if l.get("speaker") in valid and l.get("text")]


def _render(events, memory):
    plays = "\n".join(f"- {_desc(e)}" for e in events) or "- (warming up)"
    mem = f"Game so far: {memory}\n\n" if memory else ""
    return f"{mem}Latest plays in the Claude Code session:\n{plays}\n\n{SCHEMA_HINT}"


def _desc(e):
    """A clean one-liner for an event. Events are {kind, desc, ...} dicts; tolerate raw text."""
    if isinstance(e, dict):
        return e.get("desc") or e.get("kind") or ""
    return str(e)


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
