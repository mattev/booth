# The Booth 🎙️⚾

**Live audio play-by-play of your Claude Code session, called by a three-person broadcast booth.**

### 🎧 Hear the booth in action

<video src="https://github.com/mattev/booth/raw/main/assets/booth-demo-1.mp4" controls width="100%"></video>

> ▶️ If the player doesn't load, [**listen to the demo here**](https://github.com/mattev/booth/raw/main/assets/booth-demo-1.mp4) (or grab the [`.m4a`](assets/booth-demo-1.m4a)).

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
    "SessionStart":     [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/plugin/booth/hook_entry.sh session_start" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/plugin/booth/hook_entry.sh prompt" }] }],
    "PreToolUse":       [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/plugin/booth/hook_entry.sh pre_tool" }] }],
    "PostToolUse":      [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/plugin/booth/hook_entry.sh post_tool" }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "$HOME/the-booth/plugin/booth/hook_entry.sh stop" }] }]
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
booth setup     # premium voices: enter your ElevenLabs key, pick a voice per announcer
```

Then open a fresh Claude Code session and get to work. Want to hear it without wiring hooks?
Run the demo:

```bash
cd ~/the-booth/plugin && python3 -m booth.demo          # generate + speak
python3 -m booth.demo --silent                       # print only, no audio
```

---

## Premium voices (ElevenLabs)

The free `say` voices are fine for a demo, but real distinct announcers make the booth.
The Booth uses **your own** [ElevenLabs](https://elevenlabs.io) account — this is open source,
so there's no shared key.

### Prerequisites

1. An **ElevenLabs account** (the free tier works to try it; heavier use needs paid credits).
2. An **API key** — create one at
   [Settings → API Keys](https://elevenlabs.io/app/settings/api-keys).
3. **The key must allow Text-to-Speech and have credits available.** Two common gotchas —
   both make every announcer fall back to the robotic macOS `say` voice (see
   [Troubleshooting](#troubleshooting-all-voices-sound-the-same)):
   - If you **restrict** the key (Edit API Key → *Restrict Key*), give **Text to Speech**
     the `Access` permission and set the per-key **Usage Limit (Credits)** high enough — each
     spoken line costs ≈ 20–25 credits, so a tiny cap (e.g. 50) is exhausted in two lines.
   - Make sure the **account** has credits / a top-up balance, not just the key.
4. **Three voices** to map to the announcers. Create them with
   [Voice Design](https://elevenlabs.io/app/voice-lab) (or use any voices on your account).
   Tip: name them `Announcer 1` / `Announcer 2` / `Announcer 3` and the wizard auto-assigns
   them in order.

   To recreate the default booth crew, paste these descriptions into ElevenLabs **Voice
   Design** — one per voice:

   - **Announcer 1 → Duane Kuiper** (lead play-by-play):
     > A smooth, resonant male voice of a veteran baseball broadcaster in his later years.
     > Crisp, warm tone with an effortless authority that is both conversational and deeply
     > passionate. Speaking at a steady, relaxed pace that suddenly erupts into booming,
     > electrifying excitement with signature drawn-out crescendos. Perfect audio quality
     > with a subtle, spacious broadcast booth acoustic.
   - **Announcer 2 → Mike Krukow** (color commentary):
     > A deep, gravelly male voice of a former athlete turned color commentator in his later
     > years. Rich, textured rasp with a booming, jovial quality that is intensely passionate
     > and warmly folksy. Speaking at an energetic, storytelling pace, punctuated by emphatic,
     > sudden outbursts of pure excitement and hearty chuckles. Perfect audio quality with a
     > subtle broadcast booth acoustic.
   - **Announcer 3 → Dave Flemming** (younger play-by-play/color):
     > A clear, bright male voice of a sharp, professional sports broadcaster in his middle
     > years. Smooth, polished tone with a slightly youthful, analytical quality that is both
     > precise and highly articulate. Speaking at a brisk, intelligent pace that accelerates
     > into rapid-fire intensity, peaking with a breathless, high-register crescendo during
     > thrilling moments. Perfect audio quality with a subtle broadcast booth acoustic.

### Setup

Run the wizard and follow the prompts:

```bash
booth setup
# or, for a scripted install, skip the key prompt:
booth setup --key sk_...
```

It will:

1. **Validate your key** against ElevenLabs and list the voices on your account.
2. Let you **map a voice to each announcer** — **Miller** (lead play-by-play), **Kuiper**
   (color), **Flemming** (younger play-by-play). Press Enter to accept the smart default.
3. **Save** the key + voice mapping to `~/.the-booth/config.toml` and flip
   `tts_backend` to `elevenlabs`.
4. Offer a **test line from each voice** so you can confirm they sound distinct. If synthesis
   fails (bad key / no credits), it tells you instead of silently falling back.

Then restart the booth so it picks up the new backend:

```bash
booth off && booth on
```

No extra Python package is required: The Booth talks to the ElevenLabs REST API with the
standard library and plays audio through macOS `afplay`. Your key is stored in
`~/.the-booth/config.toml` (gitignored) and never committed. Back to free anytime with
`tts_backend = "say"`.

### Troubleshooting: all voices sound the same

If every announcer comes out in the same robotic voice, the booth is failing to reach
ElevenLabs and **falling back to macOS `say`** (it fails soft so it never goes silent
mid-session). `booth status` flags this:

```
tts=elevenlabs (⚠️ falling back to `say`: 401 … out of ElevenLabs credits …)
```

Almost always it's **credits or key permissions** — see the
[Prerequisites](#prerequisites) above. Common causes: the account is out of credits, or the
API key is *Restricted* with too low a per-key Usage Limit (the credit cap is per-key and
separate from your account balance). Fix it in the ElevenLabs dashboard, then re-run
`booth setup` (or just `booth off && booth on`).

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

If The Booth made your session more fun, you can tip the maintainer:

<p align="center">
  <img src="assets/venmo-qr.png" alt="Venmo QR code for @Matt-Evered" width="260"><br>
  <strong>Venmo <a href="https://venmo.com/u/Matt-Evered">@Matt-Evered</a></strong>
</p>

---

## Cost

- **Free tier:** template commentary + macOS `say` = $0, no API key.
- **With an API key:** per-batch calls use a fast, cheap model — fractions of a cent per line.
  A whole lively session runs to a few cents.

---

## Roadmap

- [x] **M0** — Talking prototype: events → commentary → 3 voices.
- [x] On/off/mute control (`booth` CLI + `/booth` skill).
- [x] **M1** — Smarter pacing: async player + backpressure, event coalescing, rolling "game so far" memory for callbacks, and thinking-gap color (fills the dead air before Claude's first move).
- [x] **M2** — ElevenLabs backend (premium voices) + `booth setup` wizard. Streaming TBD.
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
