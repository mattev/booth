# The Booth — Design Doc

> Live audio play-by-play of your Claude Code session, called by the booth crew.
> Default voices riff on the Giants' broadcast trio: Jon Miller, Duane "Kuip" Kuiper,
> and Dave Flemming.

Status: **Design / pre-build** · Owner: mevered · Last updated: 2026-05-28

---

## 1. Vision

As you work in Claude Code, a three-person broadcast booth narrates the action in real
time — melodic play-by-play, dry color commentary, and the occasional sponsor read asking
you to throw a few bucks in the tip jar. A clean `git commit` is a routine 6-4-3 double
play. A 200-line refactor that passes tests on the first try is a frozen rope into the
gap. A failing build is a runner thrown out at the plate.

It ships as a **Claude Code plugin** so anyone can install it with one command, flip it
on, and hear their session called.

### Design principles

1. **Zero-config to first sound.** `say`-based free tier means it talks within seconds of
   install, no API key required.
2. **Charm over completeness.** Funny banter beats exhaustive narration. We *batch and
   skip* events rather than read every one.
3. **Never lag the work.** Audio must trail the action by seconds, not minutes. When Claude
   moves fast, we summarize innings, not pitches.
4. **Tasteful monetization.** Sponsor reads are in-character and infrequent — part of the
   bit, not an interruption.

---

## 2. How it hangs together

```
┌─────────────────┐   event JSON    ┌──────────────┐   batched events  ┌────────────────┐
│  Claude Code     │ ──(stdin)────▶ │ hook_handler │ ──(every N s)───▶ │ commentary.py  │
│  hooks fire on:  │                │  enqueue +    │                   │ Claude API →   │
│  prompt, tool,   │                │  throttle     │                   │ 3-voice banter │
│  stop, ...       │                └──────────────┘                   └───────┬────────┘
└─────────────────┘                                                            │ lines
                                                                                ▼
                              ┌──────────┐   audio    ┌──────────┐   text   ┌────────┐
   speakers ◀── play queue ◀──│ player.py │ ◀─────────│  tts.py  │ ◀────────│ (Miller/│
   (no overlap)               └──────────┘            │ EL / say │          │ Kuip/   │
                                                       └──────────┘          │ Flem)  │
                                                                             └────────┘
```

The key unlock: **Claude Code hooks already emit a structured event stream.** We don't
scrape, screen-record, or parse logs. We register hooks and receive clean JSON.

---

## 3. Components

### 3.1 Event capture (hooks)

The plugin registers hooks on these events (see `plugin/hooks/hooks.json`):

| Event              | What it means in the booth                                  |
|--------------------|-------------------------------------------------------------|
| `UserPromptSubmit` | "Here's the windup..." — a new at-bat begins                |
| `PreToolUse`       | The pitch — what Claude is about to attempt                 |
| `PostToolUse`      | The result — hit, out, or error                             |
| `Stop`             | End of the half-inning — Claude's turn is done              |
| `SessionStart`     | "Good evening everybody and welcome to..." — intro          |

Each hook runs `booth-hook` (a thin entry point) with the event JSON on **stdin**. The
handler's only job is fast: tag the event, drop it in a queue file/socket, and exit. All
heavy lifting (LLM, TTS) happens in a **separate long-lived daemon** so we never block
Claude Code's main loop.

> **Why a daemon, not inline:** hooks must return quickly or they stall the session. The
> handler is a ~20ms enqueue. A background `booth-daemon` drains the queue, batches, and
> drives commentary/TTS/playback on its own clock.

### 3.2 Batching & throttling (the pacing brain)

The hardest UX problem. Rules:

- Drain the queue on a cadence (default **every 4s**, configurable).
- If ≥1 event is waiting, summarize the *batch* into one "play," not one line per event.
- **Backpressure:** if the audio queue already has >2 lines pending, skip generating new
  commentary and let the booth catch up (or emit a quick "and Claude's working fast here,
  folks").
- Coalesce noisy sequences (10 `Read`s in a row → "Claude's studying the scouting report").
- Hard rate-limit sponsor reads (see §3.6).

### 3.3 Commentary engine (`commentary.py`)

One Claude API call per batch. Input: the last few events + a short rolling memory of the
"game so far" (so callbacks land — "as we mentioned earlier..."). Output: 1–3 short lines
of multi-speaker dialogue, tagged by announcer.

- Model: `claude-haiku-4-5` for latency/cost on the per-batch calls; optionally
  `claude-sonnet-4-6` for the big moments (session start, a hard bug finally squashed).
- **Prompt caching** on the system prompt (personas + style guide) — it's large and static,
  so cache it to cut latency and cost on every call.
- Output is structured: `[{speaker: "miller", text: "..."}, {speaker: "kuiper", ...}]`.

### 3.4 Personas (`personas.py`)

The whole charm lives here. Each announcer is a system-prompt fragment:

- **Jon Miller** — lead play-by-play. Melodic, classic, builds tension. Does the actual
  "call." Occasional faux-Spanish home-run call energy for big wins.
- **Duane "Kuip" Kuiper** — color. Dry, deadpan, self-deprecating. Catchphrase energy
  ("Grab some pine, meat!"). Roasts sloppy code gently.
- **Dave Flemming** — younger play-by-play/color. Earnest, stats-y, smooths transitions.

Personas are **swappable**. The trio is the default pack; the architecture supports other
booths (a hype streamer, a nature documentarian, a noir detective). Ships as named packs in
`personas/`.

> **Legal note:** we capture *style and rapport*, not a literal voice clone of real
> broadcasters. Cloning a real person's actual voice raises right-of-publicity issues. The
> default voice pack uses generic/synthesized voices that evoke the *type* (warm veteran,
> dry sidekick, eager youngster) without impersonating identifiable individuals. Users can
> wire their own voice IDs at their own discretion.

### 3.5 Text-to-speech (`tts.py`)

Pluggable backends behind one interface:

| Backend         | Cost     | Quality | Multi-voice | Notes                              |
|-----------------|----------|---------|-------------|------------------------------------|
| macOS `say`     | free     | meh     | yes (built-in voices) | **Default free tier**, zero setup |
| ElevenLabs      | $$       | great   | yes         | Premium tier, low latency, 3 voice IDs |
| OpenAI TTS      | $        | good    | limited     | Middle option                      |

Each announcer maps to a voice. Stream audio where the backend supports it to shave
latency. Free tier (`say`) is the demo magnet; premium TTS is a natural reason to donate.

### 3.6 Sponsor reads / donations (`sponsors.py`)

On-theme monetization. Instead of a popup, the booth does a **sponsor read** in character:

- Triggered at most once every **~15 minutes** of active session, or at natural breaks
  (Stop event after a big win), never mid-action.
- Reads are written by the commentary engine in-voice:
  > *Miller:* "And today's broadcast is brought to you by the folks who keep the lights on
  > in the booth — if you're enjoying the call, you can send a little something to the tip
  > jar."
  > *Kuiper:* "Venmo's right there on the screen, Jon. Don't be shy."
- Config holds the donate handle(s): Venmo, Ko-fi, GitHub Sponsors URL. Printed to the
  terminal as a clickable line alongside the audio.
- **Fully disable-able** (`sponsors.enabled = false`) — respect that some users won't want
  it, especially if they're sharing the plugin further.

### 3.7 Player (`player.py`)

Single consumer of the audio queue. Guarantees no overlap (one line finishes before the
next starts), supports duck/skip when the queue backs up, and exposes mute/pause for the
`/booth` control skill.

---

## 4. Distribution: the plugin + the skill

Packaged as a **Claude Code plugin** (`plugin/`). Installing it:

1. Registers the hooks (`hooks/hooks.json`) → the engine.
2. Installs the `booth` **skill** (`skills/booth/SKILL.md`) → the remote control, invoked as
   `/booth`:
   - `/booth on` · `/booth off` — toggle narration
   - `/booth voices <pack>` — switch persona packs
   - `/booth tts <say|elevenlabs|openai>` — pick a backend
   - `/booth mute` · `/booth quiet` — silence without uninstalling
   - `/booth sponsors off` — disable tip-jar reads
   - `/booth setup` — first-run wizard (API keys, donate handle)

> **Why both:** a skill *alone* can't fire on every event — skills are model-invoked, not
> event-driven. Hooks are the engine; the skill is the dashboard. The plugin bundles them so
> distribution is a one-liner.

Publish via a plugin marketplace (a git repo with a `marketplace.json`) so others install
with `/plugin marketplace add <you>/the-booth` then `/plugin install the-booth`.

---

## 5. Tech stack

- **Language:** Python 3.11+ (fast to write, great audio/HTTP libs). Hook entry points are
  tiny CLI shims.
- **LLM:** Anthropic SDK (`anthropic`), prompt caching on personas.
- **TTS:** `say` (built-in) for free tier; `elevenlabs` SDK for premium.
- **Audio:** stream to system output; queue managed in the daemon.
- **IPC:** queue file or unix socket between hook handler and daemon.
- **Config:** `~/.the-booth/config.toml` (keys, voices, cadence, donate handle).

---

## 6. Build plan / milestones

- [x] **M0 — Talking prototype.** ✅ Pipeline runs end-to-end (`booth.demo`): events →
      commentary → 3 mapped `say` voices (Daniel/Fred/Junior). Commentary uses the live
      Claude API when a valid `ANTHROPIC_API_KEY` is present, else a template fallback so it
      always talks. **Note:** the `sk-ant-...` key in the shell env is Claude Code's internal
      token and 401s for direct API calls — full LLM banter needs a real key from
      console.anthropic.com. Live-session hook wiring is the remaining M0→M1 step.
- [ ] **M1 — The booth.** Daemon + batching + 3 personas + multi-voice via `say`. Real
      banter, real pacing.
- [ ] **M2 — Premium audio.** ElevenLabs backend, streaming, voice-per-announcer.
- [~] **M3 — Plugin packaging.** `plugin.json`, `hooks.json`, `/booth` skill scaffolded.
      ✅ `booth-ctl` control (on/off/mute/unmute/status) built & verified — config persists,
      daemon detaches and stops cleanly. Remaining: register live hooks, setup wizard.
- [ ] **M4 — Sponsor reads + polish.** Tip-jar logic, persona packs, rolling game memory,
      backpressure tuning.
- [ ] **M5 — Publish.** Marketplace repo, README/demo gif, install one-liner.

---

## 7. Open questions / decisions to confirm

1. **TTS for the build:** start on free `say` (assumed default) and add ElevenLabs at M2? Or
   go straight to ElevenLabs if you have a key?
2. **Donate handle:** what goes in the sponsor read — Venmo handle, Ko-fi, GitHub Sponsors?
3. **Name:** "The Booth" (working title). Alternatives: "Grab Some Pine," "Play-by-Play,"
   "Bottom of the Ninth."
4. **Default cadence:** 4s batching feels right; tune by ear in M1.
5. **How chatty by default?** Quiet (big moments only) vs. lively (most innings)?

---

## 8. Risks

- **Latency** — mitigated by batching, Haiku for per-batch calls, streaming TTS, backpressure.
- **Annoyance / fatigue** — mitigated by quiet defaults, easy mute, skipping noise.
- **Voice likeness / right of publicity** — default pack evokes archetypes, not real people;
  document this clearly.
- **Cost** — free tier needs no key; premium is opt-in and is itself the donation hook.
