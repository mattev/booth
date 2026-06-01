"""Audio player: single consumer of the line queue. No overlap — one line finishes
before the next begins. Supports mute and backpressure signaling.

TODO(M1): real worker thread draining an internal queue and calling tts.speak.
"""
from collections import deque

from . import config, personas, tts

_queue = deque()
_muted = False
BACKPRESSURE_LIMIT = 2  # if more than this is pending, daemon skips generating new lines


def enqueue(line, pack="giants", backend="say") -> None:
    """line = {'speaker': 'kuiper', 'text': '...'}. Maps speaker -> voice and speaks."""
    if _muted:
        return
    _queue.append((line, pack, backend))
    _drain_one()  # TODO: move to a background worker thread


def is_backed_up() -> bool:
    return len(_queue) > BACKPRESSURE_LIMIT


def mute(on: bool = True) -> None:
    global _muted
    _muted = on


def _drain_one() -> None:
    if not _queue:
        return
    line, pack, backend = _queue.popleft()
    ann = personas.PACKS[pack]["announcers"].get(line["speaker"])
    if not ann:
        return
    if backend == "say":
        voice = ann["voice_say"]
    else:  # elevenlabs: prefer the voice_id from `booth setup`, fall back to the pack slot
        voice = config.load().eleven_voice(line["speaker"]) or ann["voice_elevenlabs"]
    tts.speak(line["text"], voice, backend)
