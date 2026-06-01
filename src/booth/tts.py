"""Text-to-speech backends behind one interface. speak(text, voice) -> blocks until done.

Backends:
  - say        : macOS built-in. Free, zero setup. DEFAULT.
  - elevenlabs : premium, distinct voices. Needs an ElevenLabs key (run `booth setup`).
  - openai     : middle option. Needs OPENAI_API_KEY.
"""
import os
import subprocess
import tempfile

from . import config, eleven

_FALLBACK_SAY_VOICE = "Daniel"   # used if an elevenlabs line can't be produced


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
        return _say(text, _FALLBACK_SAY_VOICE)
    try:
        audio = eleven.tts_bytes(key, voice_id, text)
    except eleven.ElevenError:
        return _say(text, _FALLBACK_SAY_VOICE)

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
