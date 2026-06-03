"""Audio player: a single background worker that speaks queued lines one at a time.

`enqueue()` is non-blocking — it drops a line on an internal queue and returns immediately.
A daemon worker thread drains the queue and calls `tts.speak()`, so exactly one line is ever
spoken at a time (no overlap), while the caller (the booth daemon) stays free to keep pacing,
coalescing, and generating on its own clock.

Backpressure: `is_backed_up()` reflects lines still pending — queued OR currently being
spoken — so the daemon can stop generating new banter when the booth falls behind. (The old
synchronous drain made this impossible: the queue was always empty by the time anyone asked.)
"""
import queue
import threading

from . import config, personas, tts

BACKPRESSURE_LIMIT = 2  # more than this many lines pending → daemon holds off generating

_queue = queue.Queue()
_pending = 0                       # queued + in-flight; guarded by _lock
_lock = threading.Lock()
_worker = None
_worker_lock = threading.Lock()
_muted = False


def enqueue(line, pack="giants", backend="say") -> None:
    """line = {'speaker': 'kuiper', 'text': '...'}. Non-blocking; the worker speaks it."""
    global _pending
    if _muted:
        return
    _ensure_worker()
    with _lock:
        _pending += 1
    _queue.put((line, pack, backend))


def is_backed_up() -> bool:
    return _pending > BACKPRESSURE_LIMIT


def pending() -> int:
    """Lines still queued or being spoken — used for backpressure and diagnostics."""
    return _pending


def mute(on: bool = True) -> None:
    global _muted
    _muted = on


def wait_until_done() -> None:
    """Block until every queued line has finished speaking (one-shot runs like the demo)."""
    _queue.join()


def _ensure_worker() -> None:
    """Lazily start the single consumer thread. Daemon thread → dies with the process."""
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_run, name="booth-player", daemon=True)
        _worker.start()


def _run() -> None:
    global _pending
    while True:
        line, pack, backend = _queue.get()
        try:
            if not _muted:
                _speak(line, pack, backend)
        except Exception:
            # Fail soft: a bad line must never kill the worker, or the booth goes silent.
            pass
        finally:
            with _lock:
                _pending -= 1
            _queue.task_done()


def _speak(line, pack, backend) -> None:
    ann = personas.PACKS[pack]["announcers"].get(line["speaker"])
    if not ann:
        return
    if backend == "say":
        voice = ann["voice_say"]
    else:  # elevenlabs: prefer the voice_id from `booth setup`, fall back to the pack slot
        voice = config.load().eleven_voice(line["speaker"]) or ann["voice_elevenlabs"]
    tts.speak(line["text"], voice, backend)
