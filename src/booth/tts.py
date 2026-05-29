"""Text-to-speech backends behind one interface. speak(text, voice) -> blocks until done.

Backends:
  - say        : macOS built-in. Free, zero setup. DEFAULT.
  - elevenlabs : premium, low-latency, distinct voices. Needs ELEVENLABS_API_KEY.
  - openai     : middle option. Needs OPENAI_API_KEY.
"""
import subprocess


def speak(text: str, voice: str, backend: str = "say") -> None:
    if backend == "say":
        _say(text, voice)
    elif backend == "elevenlabs":
        _elevenlabs(text, voice)   # TODO(M2)
    elif backend == "openai":
        _openai(text, voice)       # TODO
    else:
        raise ValueError(f"unknown TTS backend: {backend}")


def _say(text: str, voice: str) -> None:
    """macOS `say`. `voice` is a system voice name (e.g. Daniel/Fred/Alex)."""
    subprocess.run(["say", "-v", voice, text], check=False)


def _elevenlabs(text: str, voice_id: str) -> None:
    """TODO(M2): stream from ElevenLabs and play. `voice` is a voice_id here."""
    raise NotImplementedError


def _openai(text: str, voice: str) -> None:
    raise NotImplementedError
