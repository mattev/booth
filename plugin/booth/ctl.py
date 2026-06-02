"""booth-ctl: the remote control behind the /booth skill.

    python3 -m booth.ctl on        # enable + start the daemon
    python3 -m booth.ctl off       # disable + stop the daemon
    python3 -m booth.ctl mute      # keep daemon running, silence audio
    python3 -m booth.ctl unmute
    python3 -m booth.ctl status

'on' starts a detached daemon that drains the event queue and speaks. With no live hooks
registered yet, the queue stays empty, so 'on' is safe — it just sits quietly until hooks
feed it events. 'off' stops the daemon entirely.
"""
import os
import signal
import subprocess
import sys
from pathlib import Path

from . import config

PID = Path.home() / ".the-booth" / "daemon.pid"
MUTE = Path.home() / ".the-booth" / "muted"          # presence = muted
SRC_DIR = Path(__file__).resolve().parents[1]        # .../plugin (dir holding the booth pkg)


def _running():
    if not PID.exists():
        return None
    try:
        pid = int(PID.read_text().strip())
        os.kill(pid, 0)            # signal 0 = existence check
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        return None


def start():
    pid = _running()
    if pid:
        return pid
    PID.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, "-m", "booth.daemon"],
        cwd=str(SRC_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,    # detach so it outlives this process
    )
    PID.write_text(str(proc.pid))
    return proc.pid


def stop():
    pid = _running()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if PID.exists():
        PID.unlink()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "on":
        config.set_field("enabled", True)
        MUTE.unlink(missing_ok=True)   # "on" always means audible
        print(f"🎙️  Booth ON — daemon pid {start()}")
    elif cmd == "off":
        config.set_field("enabled", False)
        stop()
        print("🔇 Booth OFF — daemon stopped")
    elif cmd == "mute":
        MUTE.parent.mkdir(parents=True, exist_ok=True)
        MUTE.touch()
        print("🤫 Booth muted (daemon still running)")
    elif cmd == "unmute":
        MUTE.unlink(missing_ok=True)
        print("🔊 Booth unmuted")
    elif cmd == "key":
        if len(sys.argv) < 3:
            print("usage: booth key <ANTHROPIC_API_KEY>")
            return 2
        config.set_field("anthropic_api_key", sys.argv[2])
        print("🔑 API key saved to config (daemon will use it regardless of shell env)")
    elif cmd == "setup":
        from . import setup as _setup
        return _setup.main(sys.argv[2:])
    elif cmd == "eval":
        from . import eval as _eval
        sys.argv = [sys.argv[0]] + sys.argv[2:]   # hand remaining args to the eval parser
        return _eval.main()
    elif cmd == "status":
        cfg = config.load()
        pid = _running()
        daemon = f"running (pid {pid})" if pid else "stopped"
        muted = "muted" if MUTE.exists() else "live"
        tts = cfg.tts_backend
        mark = Path.home() / ".the-booth" / "tts_fallback"
        if tts == "elevenlabs" and mark.exists():
            tts = f"elevenlabs (⚠️ falling back to `say`: {mark.read_text().strip()[:120]})"
        print(f"enabled={cfg.enabled} · daemon={daemon} · audio={muted} · "
              f"tts={tts} · pack={cfg.pack} · sponsors={cfg.sponsors_enabled}")
    else:
        print(f"unknown command: {cmd!r} — use on | off | mute | unmute | status | setup | key | eval")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
