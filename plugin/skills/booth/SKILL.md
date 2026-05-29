---
name: booth
description: Control The Booth — the live audio play-by-play commentator for your Claude Code session. Use to turn narration on/off, mute, switch announcer voice packs, change the TTS backend, run first-time setup, or toggle sponsor reads. Triggers on phrases like "/booth", "turn on the commentator", "mute the booth", "switch announcers".
---

# The Booth — remote control

You are the dashboard for **The Booth**, an audio play-by-play commentator that narrates
the Claude Code session out loud. The narration *engine* runs via hooks + a background
daemon; this skill only manages it via the `booth-ctl` CLI.

## How to run a command

All actions shell out to `booth-ctl`. Run it from the project's `src/` directory so the
`booth` package is importable:

```bash
cd "${BOOTH_SRC:-$HOME/the-booth/src}" && python3 -m booth.ctl <command>
```

Map the user's intent to one of these `<command>` values:

| User says…                         | command   | effect                                          |
|------------------------------------|-----------|-------------------------------------------------|
| "booth on", "turn it on", "start"  | `on`      | sets `enabled=true`, starts the detached daemon |
| "booth off", "stop", "kill it"     | `off`     | sets `enabled=false`, stops the daemon          |
| "mute", "quiet", "shush"           | `mute`    | daemon keeps running, audio silenced            |
| "unmute", "speak again"            | `unmute`  | re-enable audio                                 |
| "status", "is it on?"              | `status`  | print enabled / daemon / mute / tts / pack      |

After running, report the command's printed line back to the user.

## Other settings (edit `~/.the-booth/config.toml` directly)

- **voices <pack>** — set `pack` (default `giants` → Miller / Kuiper / Flemming).
- **tts <say|elevenlabs|openai>** — set `tts_backend`. `say` is free, no key.
- **sponsors <on|off>** — set `sponsors_enabled`. Never enable silently — confirm the
  `donate_handle` (Venmo/Ko-fi/GitHub Sponsors) first.

## Notes

- Default TTS is macOS `say` so it works with zero setup.
- `on` is safe even before live hooks are registered: the daemon just sits quietly until
  the event queue gets fed.
