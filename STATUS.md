# The Booth — Project Status / Handoff

**Last worked: 2026-05-31** · Repo: https://github.com/mattev/booth · See [DESIGN.md](./DESIGN.md) for full design.

> Picking this back up? Read §"Resume in 60 seconds" first. The code is all in git, but a few
> things live only on this Mac (API key, hooks, daemon) — those are in §"Local machine state".

---

## TL;DR — where we're at

A working **M0+**: the booth genuinely narrates a live Claude Code session out loud with
three voices, LLM-written banter, on/off control, and an eval harness. The core "pitch →
play-by-play" experience works and is measured at ~4.7 (Haiku) / ~4.9 (Sonnet) out of 5.

What's **done and shipped**:
- ✅ End-to-end pipeline: Claude Code hooks → event queue → daemon → Claude API → 3-voice `say` TTS.
- ✅ Real LLM commentary that summarizes your prompt as "the pitch" and calls the plays. Template fallback if no key.
- ✅ `booth` control CLI: `on / off / mute / unmute / status / setup / key / eval`.
- ✅ **M2 (partial): ElevenLabs premium voices.** `booth setup` wizard — enter your key, it
  validates against your account, maps a voice to each announcer, flips `tts_backend` to
  `elevenlabs`, offers a test line. Zero new deps: REST via stdlib (`eleven.py`) + `afplay`.
  Streaming is still TODO.
- ✅ Eval harness (`booth eval`): model comparison, quality judging, cost/latency, silent-failure detection → CSV + summary.
- ✅ Fixed the "same intro every time" bug (two causes: daemon using a stale/invalid key; welcome-filler on every session start).

What's **not done** (next session): see §"Next steps".

---

## Resume in 60 seconds

```bash
cd ~/the-booth
booth status              # is the daemon running? what's configured?
booth on                  # start narrating (then open a FRESH Claude Code session)
python3 -m booth.demo     # hear it without wiring a session (generate + speak)
cd plugin && python3 -m booth.eval   # re-run quality/cost eval → evals/*.csv
booth off                 # stop
```

If `booth` isn't found: open a new terminal (alias is in `~/.zshrc`) or use `~/the-booth/booth`.

---

## How it works (1-paragraph recap)

Claude Code **hooks** (registered in `~/.claude/settings.json`) fire on every prompt/tool/stop
and pipe event JSON to `hook_entry.sh` → `hook_handler.py`, which appends to a queue at
`~/.the-booth/events.jsonl` (only when the daemon is running). The detached **daemon**
(`booth.daemon`) drains the queue every ~4s, sends the batch to **`commentary.generate()`**
(Anthropic API, Haiku by default, persona system prompt with prompt-caching), and feeds the
returned speaker-tagged lines to **`player.py`**, which speaks them one at a time via macOS `say`.

---

## Repo layout (what's in git)

```
the-booth/
├── DESIGN.md              # full design + milestone checklist
├── STATUS.md              # ← this file
├── README.md              # public-facing overview
├── plugin/                # Claude Code plugin packaging (hooks.json, /booth skill, manifest)
└── plugin/booth/
    ├── hook_handler.py    # fast enqueue; no-ops unless daemon running (pidfile gate)
    ├── hook_entry.sh      # shim the hooks call
    ├── daemon.py          # drain queue → commentary → player; reloads config each loop
    ├── commentary.py      # generate()/call(): LLM banter + template fallback + metadata
    ├── personas.py        # the giants pack (Miller/Kuiper/Flemming) + system prompt
    ├── tts.py             # say (works) / elevenlabs+openai (stubs, M2)
    ├── player.py          # no-overlap audio queue + mute
    ├── sponsors.py        # rate-limited in-character tip-jar reads
    ├── config.py          # ~/.the-booth/config.toml load/save
    ├── ctl.py             # the `booth` CLI (on/off/mute/key/eval/status)
    ├── demo.py            # run a sample session through the booth
    ├── eval.py            # eval harness → CSV + summary
    └── eval_scenarios.py  # 10 golden scenarios
```

---

## Local machine state (NOT in git — lives only on this Mac)

These make it run here and must be recreated if you move machines:

1. **API key** — stored in `~/.the-booth/config.toml` as `anthropic_api_key` (gitignored).
   Also exported in `~/.zshrc`. Funded with ~$20 of Anthropic credit (pay-as-you-go).
   ⚠️ This key was pasted in chat during setup — consider rotating it at
   console.anthropic.com/settings/keys (set the new one with `booth key <KEY>`).
2. **Hooks** — added to `~/.claude/settings.json` (booth entries merged with your existing
   force-push/notify/tab-title hooks). Backup at `~/.claude/settings.json.bak-booth`.
3. **`booth` alias** — in `~/.zshrc` → `~/the-booth/booth`.
4. **Daemon** — runs detached; pidfile at `~/.the-booth/daemon.pid`. Event queue at
   `~/.the-booth/events.jsonl`.

> **Daemon left OFF at handoff.** Run `booth on` to resume. (When on, it narrates *every*
> Claude Code session until `booth off`.)

---

## Eval baseline (compare against this after future changes)

Run on 2026-05-31, 10 scenarios × 2 models × 2 repeats + judge:

| Model | Overall /5 | Accuracy | Persona | Humor | Latency | Cost/run |
|---|---|---|---|---|---|---|
| haiku  | 4.69 | 4.0  | 4.25 | 3.65 | 1.54s | $0.020 |
| sonnet | 4.93 | 4.25 | 4.65 | 3.9  | 3.11s | $0.056 |

0 fallbacks · 0 no-variation · silence-by-design 2/2. CSVs in `evals/` (gitignored).

---

## Known issues / next steps

- **M1 — pacing & memory** (the big one): the daemon batches naively every 4s and can lag if
  Claude moves fast. Want: event coalescing (10 reads → "studying the scouting report"),
  backpressure, a rolling "game so far" memory so callbacks land, and "thinking-gap" color
  (narrate the pause before Claude's first tool — this was the "harmonizing/considering
  options" idea from the screenshot; the spinner word itself isn't exposed to hooks).
- **`stop_after_win` on Sonnet** returned empty once in the eval — possible dead air at
  end-of-turn. Worth a look.
- **M2** — ✅ ElevenLabs backend + `booth setup` wizard shipped (`eleven.py`, `setup.py`).
  Remaining: streaming playback (currently synth-then-`afplay` per line), and tuning latency.
- **M3** — finish plugin packaging (setup wizard; `/booth` skill is scaffolded).
- **Distribution** — README install steps are written for others, but untested by a second
  person on a clean machine.
- **Humor** is the lowest-scoring dimension (~3.65–3.9) — persona prompt has headroom.

---

## Quick reference

| Command | Does |
|---|---|
| `booth on` / `off` | start / stop the daemon |
| `booth setup` | ElevenLabs wizard: enter key, map a voice per announcer, switch to premium |
| `booth mute` / `unmute` | silence / resume audio, daemon keeps running |
| `booth status` | enabled / daemon / audio / tts / pack / sponsors |
| `booth key <KEY>` | store Anthropic API key in config (daemon-independent of shell env) |
| `booth eval [--models haiku] [--repeats N] [--no-judge]` | run the eval |
| `python3 -m booth.demo [--silent]` | hear a sample session |
