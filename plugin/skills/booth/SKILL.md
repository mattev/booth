---
name: booth
description: Control The Booth — the live audio play-by-play commentator for your Claude Code session. Use to turn narration on/off, mute, switch announcer voice packs, change the TTS backend, run first-time setup, or toggle sponsor reads. Triggers on phrases like "/booth", "turn on the commentator", "mute the booth", "switch announcers".
---

# The Booth — remote control

You are the dashboard for **The Booth**, an audio play-by-play commentator that narrates
the Claude Code session out loud. The narration *engine* runs via hooks + a background
daemon; this skill only manages it via the `booth-ctl` CLI.

## How to run a command

All actions shell out to `booth-ctl`. Run it from the directory that holds the `booth`
package. The booth's SessionStart hook writes that path to `~/.the-booth/code_path`, so it
works whether the plugin was installed from a marketplace or cloned manually:

```bash
cd "$(cat "$HOME/.the-booth/code_path" 2>/dev/null || echo "$HOME/the-booth/plugin")" && python3 -m booth.ctl <command>
```

(If `~/.the-booth/code_path` doesn't exist yet, the plugin's hooks haven't run — tell the
user to open a fresh Claude Code session so the SessionStart hook fires.)

Map the user's intent to one of these `<command>` values:

| User says…                         | command   | effect                                          |
|------------------------------------|-----------|-------------------------------------------------|
| "booth on", "turn it on", "start"  | `on`      | sets `enabled=true`, starts the detached daemon |
| "booth off", "stop", "kill it"     | `off`     | sets `enabled=false`, stops the daemon          |
| "mute", "quiet", "shush"           | `mute`    | daemon keeps running, audio silenced            |
| "unmute", "speak again"            | `unmute`  | re-enable audio                                 |
| "status", "is it on?"              | `status`  | print enabled / daemon / mute / tts / pack      |
| "setup", "use real voices",        | `setup`   | interactive ElevenLabs wizard: enter key, map a  |
| "elevenlabs", "premium voices"     |           | voice per announcer, switch tts to `elevenlabs`  |

After running, report the command's printed line back to the user.

> `setup` is **interactive** (it prompts for the user's ElevenLabs API key and voice
> choices). Don't run it silently in the background — tell the user to run `booth setup` in
> their terminal, or pass a key non-interactively with `booth setup --key <KEY>`.

## Other settings (edit `~/.the-booth/config.toml` directly)

- **voices <pack>** — set `pack` (default `giants` → Miller / Kuiper / Flemming).
- **tts <say|elevenlabs|openai>** — set `tts_backend`. `say` is free, no key.
- **sponsors <on|off>** — set `sponsors_enabled`. Never enable silently — confirm the
  `donate_handle` (Venmo/Ko-fi/GitHub Sponsors) first.

## Notes

- Default TTS is macOS `say` so it works with zero setup.
- `on` is safe even before live hooks are registered: the daemon just sits quietly until
  the event queue gets fed.
