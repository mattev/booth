"""Text-to-speech backends behind one interface. speak(text, voice) -> blocks until done.

Backends:
  - say        : macOS built-in. Free, zero setup. DEFAULT.
  - elevenlabs : premium, distinct voices. Needs an ElevenLabs key (run `booth setup`).
  - openai     : middle option. Needs OPENAI_API_KEY.
"""
import os
import subprocess
import tempfile

from pathlib import Path

from . import config, eleven

_FALLBACK_SAY_VOICE = "Daniel"   # used if an elevenlabs line can't be produced
# Truthful health signal for `booth status`: present == last elevenlabs line had to fall
# back to robotic `say` (bad key / out of credits). Cleared on the next success.
_FALLBACK_MARK = Path.home() / ".the-booth" / "tts_fallback"


def _mark_fallback(reason: str) -> None:
    try:
        _FALLBACK_MARK.parent.mkdir(parents=True, exist_ok=True)
        _FALLBACK_MARK.write_text(reason)
    except OSError:
        pass


def _clear_fallback() -> None:
    try:
        _FALLBACK_MARK.unlink(missing_ok=True)
    except OSError:
        pass


def speak(text: str, voice: str, backend: str = "say") -> None:
    if backend == "say":
        _say(text, voice)
    elif backend == "elevenlabs":
        _elevenlabs(text, voice)
    elif backend == "openai":
        _openai(text, voice)       # TODO
    else:
        raise ValueError(f"unknown TTS backend: {backend}")


def _say(text: str, voice: str) -> None:
    """macOS `say`. `voice` is a system voice name (e.g. Daniel/Fred/Alex)."""
    subprocess.run(["say", "-v", voice, text], check=False)


def _eleven_key() -> str:
    return config.load().elevenlabs_api_key or os.environ.get("ELEVENLABS_API_KEY", "")


def _elevenlabs(text: str, voice_id: str) -> None:
    """Synthesize via ElevenLabs and play through `afplay`. `voice` is a voice_id.

    Fails soft: if the key/voice is missing or the API errors, fall back to `say` so the
    booth keeps talking rather than going silent mid-session.
    """
    key = _eleven_key()
    if not key or not voice_id:
        _mark_fallback("no elevenlabs key or voice_id configured")
        return _say(text, _FALLBACK_SAY_VOICE)
    try:
        audio = eleven.tts_bytes(key, voice_id, text)
    except eleven.ElevenError as e:
        _mark_fallback(str(e))
        return _say(text, _FALLBACK_SAY_VOICE)
    _clear_fallback()

    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio)
            path = f.name
        subprocess.run(["afplay", path], check=False)
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


def _openai(text: str, voice: str) -> None:
    raise NotImplementedError
