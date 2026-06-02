"""`booth setup` — first-run wizard for premium ElevenLabs voices.

The free tier (macOS `say`) needs no setup. This wizard is the "get started" flow shown
when someone installs the plugin and wants the real, distinct announcer voices:

  1. enter your personal ElevenLabs API key   (https://elevenlabs.io/app/settings/api-keys)
  2. it's validated against your account
  3. pick which of your voices plays each announcer (Miller / Kuiper / Flemming)
  4. config is saved and the TTS backend flips to `elevenlabs`
  5. optional: hear a test line from each voice

Run:  booth setup            (interactive)
      booth setup --key sk_…  (skip the key prompt, e.g. for scripted installs)

The key is stored in ~/.the-booth/config.toml (gitignored), never committed. Each user
brings their own key — this is an open-source project, so there is no shared/default key.
"""
import os
import sys

from . import config, eleven, personas, tts

KEY_URL = "https://elevenlabs.io/app/settings/api-keys"
# The three announcers we need voices for, in the order we ask about them.
ANNOUNCERS = [
    ("miller", "lead play-by-play — warm veteran, does the big calls"),
    ("kuiper", "color commentary — dry, deadpan sidekick"),
    ("flemming", "younger play-by-play/color — earnest, stats-minded"),
]
SAMPLE_LINES = {
    "miller": "And the 0-2 pitch... pytest swings... three passed in point-four seconds! A walk-off, folks!",
    "kuiper": "First at-bat, first hit. Enjoy it. The codebase gets uglier from here.",
    "flemming": "Clean prompt, clean execution — reads the file, patches the route, writes the test.",
}


def _prompt(msg, default=""):
    try:
        ans = input(msg).strip()
    except EOFError:
        return default
    return ans or default


def _read_key(argv):
    """Resolve the API key: --key flag, else $ELEVENLABS_API_KEY (confirm), else prompt."""
    for i, a in enumerate(argv):
        if a == "--key" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--key="):
            return a.split("=", 1)[1]

    env = os.environ.get("ELEVENLABS_API_KEY", "")
    if env:
        use = _prompt(f"Found ELEVENLABS_API_KEY in your environment (…{env[-4:]}). Use it? [Y/n] ", "y")
        if use.lower() != "n":
            return env

    print(f"\nGet a key (free tier available): {KEY_URL}")
    return _prompt("Paste your ElevenLabs API key: ")


def _assign_voices(voices):
    """Map each announcer -> voice_id. Pre-fills smart defaults, lets the user override."""
    print("\nYour ElevenLabs voices:")
    for i, v in enumerate(voices, 1):
        desc = f" — {v['description']}" if v["description"] else ""
        print(f"  {i}. {v['name']}{desc}")

    # Default mapping: match by name ("Announcer 1/2/3") if present, else first-three by order.
    def default_index(n):
        for i, v in enumerate(voices):
            if v["name"].strip().lower() in (f"announcer {n}", f"announcer{n}"):
                return i
        return n - 1 if n - 1 < len(voices) else 0

    chosen = {}
    print("\nAssign a voice to each announcer (press Enter to accept the default):")
    for n, (speaker, role) in enumerate(ANNOUNCERS, 1):
        di = default_index(n)
        default_name = voices[di]["name"] if voices else ""
        while True:
            raw = _prompt(f"  {speaker.upper():9} ({role})\n    voice # [{di + 1}: {default_name}]: ", str(di + 1))
            try:
                idx = int(raw) - 1
            except ValueError:
                print("    enter a number from the list")
                continue
            if 0 <= idx < len(voices):
                chosen[speaker] = voices[idx]
                break
            print(f"    pick 1–{len(voices)}")
    return chosen


def _save(api_key, chosen):
    cfg = config.load()
    cfg.elevenlabs_api_key = api_key
    cfg.tts_backend = "elevenlabs"
    cfg.eleven_voice_miller = chosen["miller"]["voice_id"]
    cfg.eleven_voice_kuiper = chosen["kuiper"]["voice_id"]
    cfg.eleven_voice_flemming = chosen["flemming"]["voice_id"]
    config.save(cfg)


def _test(chosen):
    ans = _prompt("\nHear a quick test from each voice? [Y/n] ", "y")
    if ans.lower() == "n":
        return
    for speaker, _ in ANNOUNCERS:
        print(f"  🔊 {speaker} ({chosen[speaker]['name']})…")
        tts.speak(SAMPLE_LINES[speaker], chosen[speaker]["voice_id"], "elevenlabs")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    print("🎙️  The Booth — premium voice setup (ElevenLabs)\n")

    api_key = _read_key(argv)
    if not api_key:
        print("No key entered. The booth still works on the free `say` backend — nothing changed.")
        return 1

    print("Validating key…")
    try:
        voices = eleven.list_voices(api_key)
    except eleven.ElevenError as e:
        print(f"❌ Couldn't reach ElevenLabs: {e}")
        print("   Nothing was saved. Re-run `booth setup` with a valid key.")
        return 1

    if not voices:
        print("✅ Key works, but your account has no voices yet.")
        print(f"   Create three (Miller / Kuiper / Flemming) at https://elevenlabs.io/app/voice-lab,")
        print("   then re-run `booth setup`.")
        return 1

    chosen = _assign_voices(voices)
    _save(api_key, chosen)

    print("\n✅ Saved. tts_backend = elevenlabs · key stored in ~/.the-booth/config.toml")
    for speaker, _ in ANNOUNCERS:
        print(f"     {speaker:9} → {chosen[speaker]['name']}")

    _test(chosen)
    print("\nDone. Run `booth on` (or restart it) and open a fresh Claude Code session.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
