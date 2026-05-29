# The Booth 🎙️⚾

**Live audio play-by-play of your Claude Code session, called by a three-person broadcast booth.**

As you work, a baseball broadcast crew narrates the action out loud — melodic play-by-play,
dry color commentary, and the occasional in-character sponsor read for the tip jar. A clean
`git commit` becomes a routine 6-4-3 double play. A failing build is a runner gunned down at
the plate. A flawless refactor that passes on the first try is a frozen rope into the gap.

The default crew riffs on the rhythm of a classic baseball booth — a warm veteran on the
play-by-play, a deadpan sidekick on color, and an eager younger voice filling the gaps.

---

## What it sounds like

A real session — adding a health endpoint and a test — called live:

> **FLEMMING:** Clean prompt, clean execution — reads the file, patches the route, writes the test. Three tools, zero drama.
> **MILLER:** And the 0-2 pitch... pytest swings... THREE passed in 0.4 seconds! A WALK-OFF in the first inning, folks!
> **KUIPER:** First at-bat, first hit. Enjoy it. The codebase gets uglier from here.

Each announcer speaks in a distinct voice through your speakers.

---

## How it works

```
Claude Code hook ──▶ hook_handler ──▶ daemon ──▶ Claude API ──▶ TTS ──▶ speakers
  (event JSON)        (fast enqueue)   (batch +    (writes the   (3 voices)
                                        throttle)   banter)
```

1. **Claude Code [hooks](https://docs.claude.com/en/docs/claude-code/hooks)** stream session
   events (prompts, tool calls, results) — no scraping or screen-recording needed.
2. A lightweight **hook handler** drops each event in a queue and exits fast, so it never
   stalls your session.
3. A background **daemon** batches events, asks Claude to write a few lines of booth banter,
   and speaks them — one at a time, no overlap.

The narration *engine* runs via hooks + the daemon. The `/booth` skill (and the `booth` CLI)
is just the remote control.

---

## Install

Requires **macOS** (uses the built-in `say` voices) and **Python 3.11+**.

```bash
git clone https://github.com/mattev/booth.git ~/the-booth
```

**Optional — better commentary.** Out of the box, commentary uses canned template lines (zero
setup, zero cost). For the *real* LLM-written banter, set an Anthropic API key
([get one here](https://console.anthropic.com/settings/keys); pay-as-you-go, pennies per
session):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # add to your ~/.zshrc to persist
```

**Optional — a handy `booth` command:**

```bash
echo 'alias booth="$HOME/the-booth/booth"' >> ~/.zshrc && source ~/.zshrc
```

### Wire it into Claude Code

Add these hooks to `~/.claude/settings.json` (merge with any existing `hooks` block). They're
inert unless the daemon is running, so there's zero overhead when the booth is off:

```jsonc
{
  "hooks": {
    "SessionStart":     [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/src/booth/hook_entry.sh session_start" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/src/booth/hook_entry.sh prompt" }] }],
    "PreToolUse":       [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/src/booth/hook_entry.sh pre_tool" }] }],
    "PostToolUse":      [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/src/booth/hook_entry.sh post_tool" }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/src/booth/hook_entry.sh stop" }] }]
  }
}
```

> Hooks load when a Claude Code session starts, so open a **new** session after editing settings.

---

## Usage

```bash
booth on        # start the booth — it begins calling new Claude Code sessions
booth off       # stop the daemon; hooks go silent
booth mute      # silence audio without stopping the daemon
booth unmute    # resume audio
booth status    # enabled / daemon / audio / voice pack / sponsors
```

Then open a fresh Claude Code session and get to work. Want to hear it without wiring hooks?
Run the demo:

```bash
cd ~/the-booth/src && python3 -m booth.demo          # generate + speak
python3 -m booth.demo --silent                       # print only, no audio
```

---

## Configuration

Settings live in `~/.the-booth/config.toml` (see [`config.example.toml`](./config.example.toml)):

| Key | Default | Meaning |
|---|---|---|
| `cadence` | `4.0` | Seconds between event-queue drains (pacing). |
| `pack` | `"giants"` | Announcer voice pack. |
| `tts_backend` | `"say"` | `say` (free, macOS) · `elevenlabs` · `openai`. |
| `sponsors_enabled` | `true` | In-character tip-jar reads. Set `false` to disable. |
| `sponsor_interval_s` | `900` | Minimum seconds between sponsor reads. |
| `donate_handle` | `""` | e.g. `"Venmo @you"` — spoken during sponsor reads. |

---

## Tip jar 💸

The booth offers a tasteful, optional way to support whoever's running it: instead of a
popup, it does an in-character **sponsor read** ("today's broadcast is brought to you by...")
at most once every ~15 minutes, never mid-action. Set your `donate_handle` in config, or turn
it off entirely with `sponsors_enabled = false`.

---

## Cost

- **Free tier:** template commentary + macOS `say` = $0, no API key.
- **With an API key:** per-batch calls use a fast, cheap model — fractions of a cent per line.
  A whole lively session runs to a few cents.

---

## Roadmap

- [x] **M0** — Talking prototype: events → commentary → 3 voices.
- [x] On/off/mute control (`booth` CLI + `/booth` skill).
- [ ] **M1** — Smarter pacing, event coalescing, rolling "game so far" memory for callbacks.
- [ ] **M2** — ElevenLabs backend (premium voices, streaming).
- [ ] **M3** — One-command plugin install + setup wizard.
- [ ] **M4** — Sponsor reads polish, more persona packs (hype streamer, nature doc, noir).

See [DESIGN.md](./DESIGN.md) for the full design.

---

## Notes & caveats

- **macOS only** for now (the free `say` backend).
- It narrates **every** Claude Code session while the daemon is up — `booth off` is the kill switch.
- The default voice pack evokes broadcast *archetypes* and rapport, not a clone of any real
  person's voice. (Cloning a real individual's voice raises right-of-publicity issues — don't.)
- Pacing is still naive (M1 work): it can lag if Claude moves fast.

---

## License

MIT
