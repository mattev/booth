# The Booth — project guide for Claude

Live audio play-by-play of a Claude Code session, called by a three-person baseball
broadcast booth. Dev events (prompts, tool calls, results) get narrated out loud: a clean
`git commit` is a 6-4-3 double play, a failing build is a runner gunned down at the plate.

For the full picture: **[DESIGN.md](./DESIGN.md)** (architecture + milestones),
**[STATUS.md](./STATUS.md)** (current state / handoff), **[README.md](./README.md)** (public docs).

## Architecture (one line)

```
Claude Code hook → hook_handler (fast enqueue) → daemon (batch + throttle)
  → commentary.py (Claude API, Haiku) → player.py → tts.py (3 voices) → speakers
```

Hooks just drop events on a queue (`~/.the-booth/events.jsonl`) and exit (~20ms); a detached
**daemon** does all the heavy lifting on its own clock. Hooks are inert unless the daemon is
running, so there's zero overhead when the booth is off.

## Key files (`plugin/booth/`)

| File | Role |
|---|---|
| `ctl.py` | the `booth` CLI: `on/off/mute/unmute/status/setup/key/eval` |
| `daemon.py` | drains the event queue → commentary → player; reloads config each loop |
| `commentary.py` | one Claude API call per batch (LLM banter + template fallback) |
| `personas.py` | the `giants` pack (miller/kuiper/flemming) + the cacheable system prompt |
| `player.py` | single-consumer audio queue, no overlap, mute, backpressure |
| `tts.py` | backends: `say` (default), `elevenlabs`, `openai` (stub) |
| `eleven.py` | zero-dep ElevenLabs REST client (list voices + text-to-speech) |
| `setup.py` | `booth setup` wizard — enter ElevenLabs key, map a voice per announcer |
| `config.py` | load/save `~/.the-booth/config.toml` |
| `eval.py` / `eval_scenarios.py` | quality/cost/latency eval harness → `evals/*.csv` |
| `demo.py` | run a sample half-inning through the booth without wiring hooks |

## Running it

The `booth` wrapper script `cd`s into `plugin/` and runs `python3 -m booth.ctl`. Equivalently,
from `plugin/`:

```bash
booth status                 # enabled / daemon / audio / tts / pack / sponsors
booth on / off               # start / stop the detached daemon
booth setup                  # premium voices: ElevenLabs key + voice mapping
python3 -m booth.demo        # hear a sample session (uses current tts_backend)
cd plugin && python3 -m booth.eval   # re-run the eval → evals/*.csv
```

## Conventions / gotchas

- **Python 3.11+**, **macOS only** (free tier uses built-in `say`; ElevenLabs plays via `afplay`).
- **Stdlib-first.** Only optional dep is `anthropic` (commentary). ElevenLabs is done over plain
  REST in `eleven.py` — **do not add the `elevenlabs` SDK**; keeping `pip install` out of the
  "get started" path is deliberate.
- **Fail soft in the daemon.** Audio/commentary errors must never crash the loop or go silent —
  `tts.py` falls back to `say` if ElevenLabs hiccups; `commentary.py` falls back to templates
  with no API key. Preserve this.
- **Config is the source of truth**, not env. Keys live in `~/.the-booth/config.toml`
  (gitignored): `anthropic_api_key`, `elevenlabs_api_key`, `eleven_voice_{miller,kuiper,flemming}`.
  The daemon reads config every loop, so changes apply without restart — except new *code*,
  which needs `booth off && booth on`.
- **Personas evoke archetypes, not real-voice clones** (right-of-publicity — see DESIGN §3.4).
  Keep it that way.
- **Local-only state** (not in git): the API keys, the Claude Code hooks in
  `~/.claude/settings.json`, the `booth` alias, and the running daemon/pidfile.

## Milestones

M0 (talking prototype) ✅ · M2 (ElevenLabs voices + `booth setup`) ✅ partial — streaming TODO.
Next big one is **M1**: smarter pacing — event coalescing, backpressure, and a rolling
"game so far" memory so callbacks land. See STATUS.md §"Known issues / next steps".
