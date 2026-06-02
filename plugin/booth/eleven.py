"""Thin REST client for ElevenLabs — stdlib only, no SDK dependency.

The Booth needs exactly two calls: list the user's voices (setup wizard) and turn a
line of banter into audio (playback). Doing it over plain HTTP keeps `pip install` out
of the "get started" path entirely — the only requirement is an API key.

Endpoints: https://elevenlabs.io/docs/api-reference
"""
import json
import urllib.error
import urllib.request

API = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_multilingual_v2"      # matches the SDK quick-start
DEFAULT_FORMAT = "mp3_44100_128"


class ElevenError(RuntimeError):
    """Any non-2xx response or network failure talking to ElevenLabs."""


def _request(method, path, api_key, *, body=None, query="", accept="application/json"):
    url = f"{API}{path}" + (f"?{query}" if query else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("xi-api-key", api_key)
    req.add_header("Accept", accept)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        hint = " (check your API key)" if e.code in (401, 403) else ""
        raise ElevenError(f"{e.code} {e.reason}{hint}: {detail}") from None
    except urllib.error.URLError as e:
        raise ElevenError(f"network error reaching ElevenLabs: {e.reason}") from None


def list_voices(api_key):
    """Return [{voice_id, name, description}] for the account. Doubles as key validation."""
    raw = _request("GET", "/voices", api_key)
    voices = json.loads(raw).get("voices", [])
    return [
        {
            "voice_id": v["voice_id"],
            "name": v.get("name", ""),
            "description": (v.get("description") or v.get("labels", {}).get("description") or ""),
        }
        for v in voices
    ]


def tts_bytes(api_key, voice_id, text, *, model=DEFAULT_MODEL, output_format=DEFAULT_FORMAT):
    """Convert text -> mp3 bytes with the given voice. Raises ElevenError on failure."""
    return _request(
        "POST",
        f"/text-to-speech/{voice_id}",
        api_key,
        body={"text": text, "model_id": model},
        query=f"output_format={output_format}",
        accept="audio/mpeg",
    )
